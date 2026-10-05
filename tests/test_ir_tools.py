import tempfile
import unittest
from pathlib import Path
import contextlib
import io
import json
import sys
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_script(relative_path: str) -> dict:
    path = REPO_ROOT / relative_path
    sys.dont_write_bytecode = True
    scripts = str(REPO_ROOT / "skills/memory-bank-ir-dashboard/scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    namespace = {"__file__": str(path), "__name__": f"test_{path.stem}"}
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), namespace)
    return namespace


def retarget_sync_check(namespace: dict, root: Path) -> None:
    namespace.update({
        "PROJECT_ROOT": root,
        "MEMORY_BANK": root / ".memory-bank",
        "ARTIFACTS_DIR": root / ".memory-bank/artifacts",
        "INCOMING_DIR": root / ".memory-bank/incoming",
        "SENSITIVE_DIR": root / ".memory-bank/sensitive",
        "CONFIG_FILE": root / ".memory-bank/dashboard.config.json",
        "CUSTODY_MANIFEST": root / ".memory-bank/artifacts/.custody-manifest.jsonl",
    })


def retarget_intake(namespace: dict, root: Path) -> None:
    memory_bank = root / ".memory-bank"
    artifacts = root / ".memory-bank/artifacts"
    namespace.update({
        "PROJECT_ROOT": root,
        "INCOMING_DIR": root / ".memory-bank/incoming",
        "ARTIFACTS_DIR": artifacts,
        "MEMORY_BANK": memory_bank,
        "EVIDENCE_INDEX": memory_bank / "evidenceIndex.md",
        "REVIEW_QUEUE": memory_bank / "reviewQueue.md",
        "PROGRESS": memory_bank / "progress.md",
        "CONFIG_FILE": root / ".memory-bank/dashboard.config.json",
        "LOCK_FILE": artifacts / ".intake.lock",
        "JOURNAL_FILE": artifacts / ".intake-journal.json",
        "CUSTODY_MANIFEST": artifacts / ".custody-manifest.jsonl",
    })


class SyncCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.namespace = load_script("skills/memory-bank-ir-dashboard/scripts/sync_check.py")
        self.temporary = tempfile.TemporaryDirectory(prefix="mb-sync-test-")
        self.root = Path(self.temporary.name)
        for directory in (".memory-bank", ".memory-bank/incoming", ".memory-bank/artifacts", ".memory-bank/sensitive"):
            path = self.root / directory
            path.mkdir(mode=0o700)
            path.chmod(0o700)
        (self.root / ".memory-bank/dashboard.config.json").write_text("{}\n", encoding="utf-8")
        retarget_sync_check(self.namespace, self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_projection_field_types_return_structured_errors(self):
        bank = self.root / ".memory-bank"
        (bank / "findings.md").write_text("# Findings\n## Entries\n### F-001: Synthetic observation\n- Status: Confirmed\n")
        projection = {
            "schema_version": 1, "generated_at": "2026-10-05T00:00:00Z",
            "narrative": "", "theory_summary": "",
            "attack_phases": [{"name": "Synthetic phase", "icon": "", "date_range": "",
                               "color": "info", "summary": "", "event_count": 0, "key_findings": ["F-001"]}],
            "key_findings": [{"id": "F-001", "headline": "Synthetic observation", "confidence": "High", "artifacts": []}],
            "status": {"completed": [], "in_progress": [], "blocked": [{"severity": "low", "item": "", "reason": ""}]},
            "unresolved": [],
        }
        path = bank / "executiveSummary.json"
        path.write_text(json.dumps(projection))
        self.assertEqual(self.namespace["check_executive_summary"]([]), [])
        for field in ("color", "confidence", "id", "severity"):
            for invalid in ([], {}):
                with self.subTest(field=field, invalid=invalid):
                    malformed = json.loads(json.dumps(projection))
                    row = (malformed["attack_phases"][0] if field == "color" else
                           malformed["status"]["blocked"][0] if field == "severity" else
                           malformed["key_findings"][0])
                    row[field] = invalid
                    path.write_text(json.dumps(malformed))
                    issues = self.namespace["check_executive_summary"]([])
                    self.assertEqual({item["category"] for item in issues}, {"executive-summary"})
                    self.assertEqual({item["severity"] for item in issues}, {"error"})

    def test_sensitive_policy_is_required(self) -> None:
        issues = self.namespace["check_memory_bank_semantics"]()
        messages = [item["message"] for item in issues]
        self.assertIn("Required file missing: sensitiveDataPolicy.md", messages)

    def test_ir_policy_template_is_semantically_valid(self) -> None:
        template = REPO_ROOT / "templates/incident-response-memory-bank/sensitiveDataPolicy.md"
        (self.root / ".memory-bank/sensitiveDataPolicy.md").write_text(
            template.read_text(encoding="utf-8"), encoding="utf-8"
        )
        self.assertEqual([], self.namespace["check_sensitive_policy"]())

    def test_invalid_policy_values_and_missing_ir_store_are_reported(self) -> None:
        template = REPO_ROOT / "templates/incident-response-memory-bank/sensitiveDataPolicy.md"
        content = template.read_text(encoding="utf-8")
        content = content.replace("Mode: `designated-store`", "Mode: `invalid`")
        content = content.replace("`.memory-bank/artifacts/`", "`other/`")
        (self.root / ".memory-bank/sensitiveDataPolicy.md").write_text(content, encoding="utf-8")
        messages = [item["message"] for item in self.namespace["check_sensitive_policy"]()]
        self.assertTrue(any("unsupported mode" in message for message in messages))
        self.assertTrue(any("artifacts/ store is not declared" in message for message in messages))

    def test_insecure_sensitive_store_is_reported(self) -> None:
        sensitive = self.root / ".memory-bank/sensitive"
        sensitive.chmod(0o777)
        messages = [item["message"] for item in self.namespace["check_permissions"]()]
        self.assertTrue(any("sensitive/ mode 0777" in message for message in messages))

    def test_invalid_dashboard_config_is_reported(self) -> None:
        (self.root / ".memory-bank/dashboard.config.json").write_text("{not json", encoding="utf-8")
        issues = self.namespace["check_permissions"]()
        self.assertTrue(any(item["category"] == "configuration" for item in issues))

    def test_missing_sensitive_store_is_warning_not_error(self) -> None:
        (self.root / ".memory-bank/artifacts").rmdir()
        issues = self.namespace["check_permissions"]()
        missing = [it for it in issues if it["category"] == "permissions" and "artifacts/" in it["message"]]
        self.assertTrue(missing, "a missing store should still be surfaced")
        self.assertTrue(all(it["severity"] == "warning" for it in missing))
        self.assertFalse(any(it["severity"] == "error" for it in missing))


class IntakeTests(unittest.TestCase):
    def test_queue_exhaustion_leaves_no_pending_artifact(self) -> None:
        namespace = load_script("skills/memory-bank-ir-dashboard/scripts/intake.py")
        with tempfile.TemporaryDirectory(prefix="mb-intake-test-") as temporary:
            root = Path(temporary)
            for directory in (".memory-bank", ".memory-bank/incoming", ".memory-bank/artifacts"):
                (root / directory).mkdir()
            source = root / ".memory-bank/incoming/evidence.txt"
            source.write_text("fictional evidence\n", encoding="utf-8")
            (root / ".memory-bank/evidenceIndex.md").write_text("# Evidence Index\n", encoding="utf-8")
            (root / ".memory-bank/reviewQueue.md").write_text("### RQ-999 — Previous batch\n", encoding="utf-8")
            (root / ".memory-bank/progress.md").write_text("# Progress\n", encoding="utf-8")
            (root / ".memory-bank/dashboard.config.json").write_text("{}\n", encoding="utf-8")
            retarget_intake(namespace, root)

            with self.assertRaisesRegex(RuntimeError, "RQ identifier space exhausted"):
                namespace["ingest_files"]([source])

            self.assertTrue(source.exists())
            self.assertEqual([], list((root / ".memory-bank/artifacts").glob(".pending-*")))
            self.assertFalse((root / ".memory-bank/artifacts/.intake-journal.json").exists())

    def test_preview_never_claims_copy_verified(self):
        namespace = load_script("skills/memory-bank-ir-dashboard/scripts/intake.py")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            retarget_intake(namespace, root)
            source = root / "evidence.txt"
            source.write_text("synthetic", encoding="utf-8")
            result = namespace["ingest_files"]([source], dry_run=True)[0]
            self.assertFalse(result["verified"])
            self.assertTrue(result["source_hashed"])
            self.assertTrue(source.exists())
            self.assertFalse((root / ".memory-bank").exists())

    def test_empty_cli_recovers_journal_after_source_removal(self):
        namespace = load_script("skills/memory-bank-ir-dashboard/scripts/intake.py")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            retarget_intake(namespace, root)
            namespace["ensure_secure_directories"]()
            source = namespace["INCOMING_DIR"] / "evidence.txt"
            source.write_text("synthetic", encoding="utf-8")
            real_commit = namespace["_commit_journal"]
            namespace["_commit_journal"] = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("interrupted"))
            with self.assertRaisesRegex(RuntimeError, "interrupted"):
                namespace["ingest_files"]([source])
            namespace["_commit_journal"] = real_commit
            source.unlink()
            with patch.object(sys, "argv", ["intake.py", "--json"]), contextlib.redirect_stdout(io.StringIO()) as out:
                namespace["main"]()
            self.assertEqual(json.loads(out.getvalue())["failed"], 0)
            self.assertFalse(namespace["JOURNAL_FILE"].exists())
            self.assertIn("ART-0001", namespace["EVIDENCE_INDEX"].read_text())
            self.assertIn("RQ-001", namespace["REVIEW_QUEUE"].read_text())
            self.assertEqual(len(namespace["CUSTODY_MANIFEST"].read_text().splitlines()), 1)

    def test_no_selection_preserves_all_pending_drops(self):
        namespace = load_script("skills/memory-bank-ir-dashboard/scripts/intake.py")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            retarget_intake(namespace, root)
            namespace["ensure_secure_directories"]()
            for name in ("credentials.txt", ".hidden"):
                (namespace["INCOMING_DIR"] / name).write_text("synthetic")
            (namespace["INCOMING_DIR"] / "nested").mkdir()
            with patch.object(sys, "argv", ["intake.py", "--json"]), contextlib.redirect_stdout(io.StringIO()):
                namespace["main"]()
            self.assertEqual(len(list(namespace["INCOMING_DIR"].iterdir())), 3)
            self.assertFalse(namespace["CUSTODY_MANIFEST"].exists())

    def test_retained_source_receipt_and_migrated_custody(self):
        namespace = load_script("skills/memory-bank-ir-dashboard/scripts/intake.py")
        checker = load_script("skills/memory-bank-ir-dashboard/scripts/sync_check.py")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            retarget_intake(namespace, root)
            retarget_sync_check(checker, root)
            namespace["ensure_secure_directories"]()
            source = namespace["INCOMING_DIR"] / "evidence.txt"
            source.write_text("synthetic")
            result = namespace["ingest_files"]([source], retain_source=True)[0]
            self.assertTrue(source.exists())
            self.assertTrue(result["verified"])
            self.assertEqual(namespace["sha256_file"](root / result["stored_path"]), result["sha256"])
            self.assertEqual(checker["check_custody_manifest"](checker["parse_indexed_artifact_entries"]()), [])
            original = namespace["CUSTODY_MANIFEST"].read_bytes()
            (namespace["MEMORY_BANK"] / "path-migrations.json").write_text(json.dumps({
                "schema": 1, "prefixes": {"artifacts/": ".memory-bank/artifacts/"}, "project_roots": [str(root)]
            }))
            index = namespace["EVIDENCE_INDEX"]
            index.write_text(index.read_text().replace(".memory-bank/artifacts/", "artifacts/"))
            self.assertEqual(checker["check_custody_manifest"](checker["parse_indexed_artifact_entries"]()), [])
            self.assertEqual(checker["check_orphan_artifacts"](checker["parse_indexed_artifact_entries"]()), [])
            self.assertEqual(namespace["CUSTODY_MANIFEST"].read_bytes(), original)

    def test_historical_journal_recovers_without_changing_identity(self):
        namespace = load_script("skills/memory-bank-ir-dashboard/scripts/intake.py")
        checker = load_script("skills/memory-bank-ir-dashboard/scripts/sync_check.py")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            retarget_intake(namespace, root)
            retarget_sync_check(checker, root)
            namespace["ensure_secure_directories"]()
            source = namespace["INCOMING_DIR"] / "evidence.txt"
            source.write_text("synthetic")
            commit = namespace["_commit_journal"]
            namespace["_commit_journal"] = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("interrupted"))
            with self.assertRaises(RuntimeError):
                namespace["ingest_files"]([source])
            namespace["_commit_journal"] = commit
            journal_path = namespace["JOURNAL_FILE"]
            # Simulate unchanged journal bytes authored before the bank migration.
            original = journal_path.read_text().replace(".memory-bank/artifacts/", "artifacts/").replace(".memory-bank/incoming/", "incoming/")
            journal_path.write_text(original)
            journal = json.loads(original)
            (namespace["MEMORY_BANK"] / "path-migrations.json").write_text(json.dumps({
                "schema": 1, "prefixes": {"artifacts/": ".memory-bank/artifacts/", "incoming/": ".memory-bank/incoming/"},
                "project_roots": [str(root)]
            }))
            self.assertEqual(namespace["ingest_files"]([]), [])
            manifested = json.loads(namespace["CUSTODY_MANIFEST"].read_text())
            self.assertEqual(manifested["transaction_id"], journal["transaction_id"])
            self.assertEqual(manifested["artifacts"][0]["stored_path"], journal["items"][0]["stored_path"])
            self.assertEqual(manifested["artifacts"][0]["sha256"], journal["items"][0]["sha256"])
            self.assertFalse(source.exists())
            self.assertFalse(journal_path.exists())
            self.assertEqual(checker["check_custody_manifest"](checker["parse_indexed_artifact_entries"]()), [])
            self.assertEqual(checker["check_orphan_artifacts"](checker["parse_indexed_artifact_entries"]()), [])
            namespace["ingest_files"]([])
            self.assertEqual(len(namespace["CUSTODY_MANIFEST"].read_text().splitlines()), 1)


class SharedSemanticsTests(unittest.TestCase):
    def setUp(self):
        self.common = load_script("skills/memory-bank-ir-dashboard/scripts/ir_common.py")

    def test_queue_status_and_checklist_are_authoritative(self):
        content = "# Review Queue\n## Pending Review\n### RQ-001 — complete\n- Status: DONE\n- [x] Reviewed\n## Done\n### RQ-002 — incomplete\n- Status: PENDING\n- [ ] Review\n"
        items = self.common["parse_review_queue"](content)
        self.assertEqual([x["section"] for x in items], ["done", "pending"])
        self.assertTrue(all(x["errors"] for x in items))
        incomplete = self.common["parse_review_queue"]("## Done\n### RQ-001 — incomplete\n- Status: DONE\n- [ ] Review\n")[0]
        self.assertEqual(incomplete["section"], "pending")

    def test_projection_rejects_timestamp_bounds_counts_colors_and_references(self):
        value = {"schema_version": 1, "generated_at": "2026-10-04T00:00:00Z", "narrative": "", "theory_summary": "",
                 "attack_phases": [], "key_findings": [], "status": {"completed": [], "in_progress": [], "blocked": []}, "unresolved": []}
        validate = self.common["projection_errors"]
        self.assertEqual(validate(value, findings=set(), artifacts=set()), [])
        for timestamp in ("invalid", "2026-10-04T00:00:00", "2026-10-04T00:00:00+01:00"):
            self.assertTrue(validate(dict(value, generated_at=timestamp)))
        phase = {"name": "Phase", "icon": "", "date_range": "", "color": "info", "summary": "", "event_count": 0, "key_findings": []}
        for bad in (dict(phase, color=""), dict(phase, event_count=-1), dict(phase, event_count=True)):
            self.assertTrue(validate(dict(value, attack_phases=[bad])))
        self.assertTrue(validate(dict(value, attack_phases=[phase] * 21)))
        self.assertTrue(validate(dict(value, attack_phases=[dict(phase, key_findings=["missing"])]), findings=set()))

    def test_old_paths_require_explicit_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(ValueError):
                self.common["canonical_path"](root, "artifacts/example")
            (root / ".memory-bank").mkdir()
            (root / ".memory-bank/path-migrations.json").write_text(json.dumps({
                "schema": 1, "prefixes": {"artifacts/": ".memory-bank/artifacts/"}, "project_roots": ["/old/project"]
            }))
            self.assertEqual(self.common["canonical_path"](root, "/old/project/artifacts/example"), root / ".memory-bank/artifacts/example")
            with self.assertRaises(ValueError):
                self.common["canonical_path"](root, "artifacts/../../outside")


if __name__ == "__main__":
    unittest.main()
