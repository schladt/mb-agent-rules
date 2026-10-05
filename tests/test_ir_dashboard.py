"""Consumer-visible IR dashboard regressions; Flask tests need dashboard dependencies."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / 'skills/memory-bank-ir-dashboard'


@unittest.skipUnless(importlib.util.find_spec('flask'), 'Install dashboard requirements for HTTP regression tests')
class DashboardTests(unittest.TestCase):
    def setUp(self):
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location('ir_dashboard_regression', SKILL / 'dashboard/app.py')
        self.app = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = self.app
        spec.loader.exec_module(self.app)
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.bank = self.root / '.memory-bank'
        (self.bank / 'artifacts').mkdir(parents=True)
        (self.bank / 'incoming').mkdir()
        self.app.PROJECT_ROOT = self.root
        self.app.MEMORY_BANK = self.bank
        self.app.ARTIFACTS_DIR = self.bank / 'artifacts'
        self.app.CONFIG_FILE = self.bank / 'dashboard.config.json'
        self.app.DASHBOARD_CONFIG = self.app.load_config()
        self.app.app.config.update(TESTING=True)
        self.client = self.app.app.test_client()
        with self.client.session_transaction() as session:
            session['csrf_token'] = 'test-token'
            session['authenticated'] = True
        import intake
        self.intake = intake
        self.restore = dict(vars(intake))
        values = {'PROJECT_ROOT': self.root, 'MEMORY_BANK': self.bank,
                  'INCOMING_DIR': self.bank / 'incoming', 'ARTIFACTS_DIR': self.bank / 'artifacts',
                  'CONFIG_FILE': self.bank / 'dashboard.config.json',
                  'EVIDENCE_INDEX': self.bank / 'evidenceIndex.md', 'REVIEW_QUEUE': self.bank / 'reviewQueue.md',
                  'PROGRESS': self.bank / 'progress.md', 'LOCK_FILE': self.bank / 'artifacts/.intake.lock',
                  'JOURNAL_FILE': self.bank / 'artifacts/.intake-journal.json',
                  'CUSTODY_MANIFEST': self.bank / 'artifacts/.custody-manifest.jsonl'}
        vars(intake).update(values)

    def tearDown(self):
        vars(self.intake).update(self.restore)
        self.temp.cleanup()
        sys.modules.pop('ir_dashboard_regression', None)

    def test_selection_is_classified_and_other_drops_remain_pending(self):
        for name in ('evidence.json', 'credentials.txt', '.hidden'):
            (self.bank / 'incoming' / name).write_text('synthetic')
        (self.bank / 'incoming/nested').mkdir()
        drops = self.client.get('/api/incoming').get_json()['drops']
        self.assertEqual(len(drops), 4)
        self.assertFalse(next(x for x in drops if x['name'] == 'nested')['selectable'])
        headers = {'X-CSRF-Token': 'test-token'}
        self.assertEqual(self.client.post('/api/intake', json={'files': ['credentials.txt']}, headers=headers).status_code, 400)
        result = self.client.post('/api/intake', json={'kind': 'artifact', 'files': ['evidence.json']}, headers=headers)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.get_json()['ingested'], 1)
        self.assertTrue((self.bank / 'incoming/credentials.txt').exists())
        self.assertTrue((self.bank / 'incoming/.hidden').exists())
        self.assertFalse((self.bank / 'incoming/evidence.json').exists())
        self.assertEqual(self.client.post('/api/intake', json={'kind': 'artifact', 'files': ['../escape']}, headers=headers).status_code, 400)

    def test_empty_selection_still_attempts_recovery(self):
        (self.bank / 'artifacts/.intake-journal.json').write_text('{}')
        result = self.client.post('/api/intake', json={'files': []}, headers={'X-CSRF-Token': 'test-token'})
        self.assertEqual(result.status_code, 409)
        self.assertIn('error', result.get_json())
        self.assertTrue((self.bank / 'artifacts/.intake-journal.json').exists())

    def test_seconds_bounds_and_invalid_query_errors(self):
        (self.bank / 'artifacts/events.json').write_text(json.dumps([
            {'Timestamp': '2026-10-04T12:34:56Z', 'Value': '\" data-injected=\"literal'},
            {'Timestamp': '2026-10-04T12:34:57Z', 'Value': 'second'},
        ]))
        result = self.client.get('/api/atomic-query', query_string={'source': 'events.json', 'from': '2026-10-04T12:34:56Z'})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.get_json()['total_matched'], 2)
        bad = self.client.get('/api/atomic-query', query_string={'source': 'events.json', 'from': 'not-a-timestamp'})
        self.assertEqual(bad.status_code, 400)
        self.assertIn('error', bad.get_json())

    def test_inventory_and_responder_download_do_not_imply_attack(self):
        assets = {'data': [{'Volume / record count': '1000 files, 3 sites'}]}
        timeline = [{'actor': 'Responder', 'title': 'Downloaded evidence', 'time': '2026-10-04T12:00:00Z'}]
        metrics = self.app.extract_key_metrics([], assets, timeline)
        self.assertNotIn('files_downloaded', metrics)
        self.assertNotIn('sites_affected', metrics)
        summary = self.app.build_executive_summary({}, [], timeline, {}, assets, {}, [])
        self.assertEqual(summary['attack_phases'], [])

    def test_status_and_finding_authorities(self):
        status = '# Project Status\n## Publishable\n### Progress\n- Owner-reported progress\n'
        (self.bank / 'project-status.md').write_text(status)
        (self.bank / 'findings.md').write_text('# Findings\n## Entries\n### Descriptive finding\n- Status: Suspected\n- Confidence: Low\n- Supporting evidence: ART-0001\n\n### F-001: Legacy finding\n- Status: Confirmed\n')
        data = self.client.get('/api/data').get_json()
        self.assertEqual(data['execution_status']['content'], status)
        self.assertEqual([x['id'] for x in data['findings']], ['Descriptive finding', 'F-001'])
        self.assertEqual(data['findings'][0]['status'], 'Suspected')

    def test_malformed_projection_fields_leave_dashboard_data_available(self):
        (self.bank / 'findings.md').write_text('# Findings\n## Entries\n### F-001: Synthetic observation\n- Status: Confirmed\n')
        projection = {
            'schema_version': 1, 'generated_at': '2026-10-05T00:00:00Z',
            'narrative': '', 'theory_summary': '',
            'attack_phases': [{'name': 'Synthetic phase', 'icon': '', 'date_range': '',
                               'color': 'info', 'summary': '', 'event_count': 0, 'key_findings': ['F-001']}],
            'key_findings': [{'id': 'F-001', 'headline': 'Synthetic observation', 'confidence': 'High', 'artifacts': []}],
            'status': {'completed': [], 'in_progress': [], 'blocked': [{'severity': 'low', 'item': '', 'reason': ''}]},
            'unresolved': [],
        }
        self.assertEqual(self.app.validate_executive_summary(projection), projection)
        for field in ('color', 'confidence', 'id', 'severity'):
            for invalid in ([], {}):
                with self.subTest(field=field, invalid=invalid):
                    malformed = json.loads(json.dumps(projection))
                    row = (malformed['attack_phases'][0] if field == 'color' else
                           malformed['status']['blocked'][0] if field == 'severity' else
                           malformed['key_findings'][0])
                    row[field] = invalid
                    (self.bank / 'executiveSummary.json').write_text(json.dumps(malformed))
                    response = self.client.get('/api/data')
                    self.assertEqual(response.status_code, 200)
                    data = response.get_json()
                    self.assertTrue(data['executive_summary']['projection_error'])
                    self.assertEqual(data['executive_summary']['attack_phases'], [])
                    self.assertEqual([finding['id'] for finding in data['findings']], ['F-001'])

    def test_queue_explicit_status_and_projection_validator_match(self):
        (self.bank / 'reviewQueue.md').write_text('## Done\n### RQ-001 — unfinished\n- Status: PENDING\n- [ ] Review\n')
        result = self.client.get('/api/review-queue').get_json()
        self.assertEqual(result['total_pending'], 1)
        self.assertTrue(result['errors'])
        projection = {'schema_version': 1, 'generated_at': 'invalid', 'narrative': '', 'theory_summary': '', 'attack_phases': [], 'key_findings': [], 'status': {'completed': [], 'in_progress': [], 'blocked': []}, 'unresolved': []}
        (self.bank / 'executiveSummary.json').write_text(json.dumps(projection))
        self.assertIsNone(self.app.validate_executive_summary(projection))
        self.assertTrue(self.client.get('/api/data').get_json()['executive_summary']['projection_error'])


@unittest.skipUnless(shutil.which('node'), 'Node is needed for UI helper regressions')
class RenderingTests(unittest.TestCase):
    def test_quoted_evidence_seconds_and_http_errors(self):
        html = (SKILL / 'dashboard/templates/dashboard.html').read_text()
        helpers = '\n'.join(line for line in html.splitlines() if line.startswith((
            'function esc(', 'function utcBound(', 'async function apiJSON(')))
        script = helpers + r'''
        (async()=>{
          let error='';
          try { await apiJSON({ok:false,status:400,json:async()=>({error:'Invalid timestamp'})}); }
          catch(e){error=e.message;}
          console.log(JSON.stringify({
            escaped:esc('" data-injected="literal\'<script>&'),
            bound:utcBound('2026-10-04T12:34:56'), error
          }));
        })();
        '''
        result = subprocess.run(['node', '-e', script], check=True, capture_output=True, text=True)
        data = json.loads(result.stdout)
        self.assertNotIn('"', data['escaped'])
        self.assertNotIn("'", data['escaped'])
        self.assertNotIn('<script>', data['escaped'])
        self.assertIn('&quot;', data['escaped'])
        self.assertEqual(data['bound'], '2026-10-04T12:34:56Z')
        self.assertEqual(data['error'], 'Invalid timestamp')


class DeploymentTests(unittest.TestCase):
    def test_upgrade_preserves_user_edits_and_private_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bank = root / '.memory-bank'
            bank.mkdir()
            for name in ('incidentBrief.md', 'scopeAuthorization.md'):
                (bank / name).write_text('# Synthetic authority\n')
            command = ['bash', str(SKILL / 'setup.sh'), str(root)]
            subprocess.run(command, check=True, capture_output=True, text=True)
            app = root / 'dashboard/app.py'
            custom = app.read_text() + '\n# User customization\n'
            app.write_text(custom)
            (root / 'dashboard/custom.txt').write_text('user file')
            failed = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(failed.returncode, 0)
            self.assertEqual(app.read_text(), custom)
            subprocess.run(command + ['--upgrade'], check=True, capture_output=True, text=True)
            backups = list((bank / 'backups').glob('*/dashboard/app.py'))
            self.assertTrue(any(p.read_text() == custom for p in backups))
            self.assertEqual((root / 'dashboard/custom.txt').read_text(), 'user file')
            self.assertTrue((root / 'scripts/ir_common.py').is_file())
            self.assertTrue((bank / 'runtime/dashboard/deployment.json').is_file())
            self.assertFalse((root / 'dashboard.config.json').exists())
            self.assertEqual((root / '.gitignore').read_text().strip(), '/.memory-bank/')


if __name__ == '__main__':
    unittest.main()
