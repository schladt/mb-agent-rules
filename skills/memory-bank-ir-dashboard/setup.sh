#!/usr/bin/env bash
# Install/update private-development dashboard code; preserve changed files before replacement.
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
export PYTHONDONTWRITEBYTECODE=1
exec python3 - "$SKILL_DIR" "$@" <<'PY'
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

source = Path(sys.argv.pop(1))
parser = argparse.ArgumentParser(description='Install/update the optional private-development IR dashboard')
parser.add_argument('project_root', type=Path)
parser.add_argument('--title', default='IR Dashboard')
parser.add_argument('--brand', default='')
parser.add_argument('--accent', default='#3b82f6')
parser.add_argument('--logo', default='')
parser.add_argument('--shared-group', action='store_true')
parser.add_argument('--with-sample-data', action='store_true')
parser.add_argument('--upgrade', action='store_true', help='Back up and replace locally modified or unrecognized managed files')
args = parser.parse_args()
root = args.project_root.resolve(strict=True)
bank = root / '.memory-bank'
if not bank.is_dir() or bank.is_symlink():
    parser.error('Initialize the incident-response .memory-bank first; use init-agent-rules --migrate for legacy projects')
for legacy in ('memory-bank', 'incoming', 'artifacts', 'sensitive', 'dashboard.config.json', 'dashboard/certs', 'dashboard/venv', 'dashboard/cache'):
    if (root / legacy).exists() or (root / legacy).is_symlink():
        parser.error('Legacy workspace paths remain; run init-agent-rules --migrate before dashboard setup')
if not (bank / 'incidentBrief.md').is_file() or not (bank / 'scopeAuthorization.md').is_file():
    parser.error('An incident-response authority bank is required')
if not re.fullmatch(r'#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?(?:[0-9a-fA-F]{2})?', args.accent):
    parser.error('--accent must be a 3, 6 or 8 digit hex color')
if args.logo and not (args.logo.startswith('/static/') or args.logo.startswith('data:image/')):
    parser.error('--logo must be a /static/ path or data:image URL')

def safe(path):
    relative = path.relative_to(root)
    cursor = root
    for part in relative.parts:
        cursor /= part
        if cursor.is_symlink():
            parser.error(f'Refusing symlinked deployment path: {relative}')

config_path = bank / 'dashboard.config.json'
safe(config_path)
config = json.loads(config_path.read_text()) if config_path.exists() else {
    'title': args.title, 'brand': args.brand, 'accent_color': args.accent,
    'logo_url': args.logo, 'css_overrides': {}, 'shared_group_access': False,
    'atomic_max_file_bytes': 104857600, 'atomic_max_records': 250000, 'atomic_max_fields': 250,
}
if not isinstance(config, dict):
    parser.error('dashboard.config.json must contain an object')
if args.shared_group:
    config['shared_group_access'] = True
shared = config.get('shared_group_access') is True
dir_mode, file_mode = (0o770, 0o660) if shared else (0o700, 0o600)
os.umask(0o007 if shared else 0o077)
managed = {str(p.relative_to(source)): p for folder in ('dashboard', 'scripts') for p in (source / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
receipt = bank / 'runtime/dashboard/deployment.json'
safe(receipt)
previous = json.loads(receipt.read_text()) if receipt.exists() else {'files': {}}
if not isinstance(previous, dict) or not isinstance(previous.get('files'), dict):
    parser.error('Invalid dashboard deployment receipt')
changes = []
conflicts = []
for relative, src in managed.items():
    dest = root / relative
    safe(dest)
    if dest.exists() and not dest.is_file():
        parser.error(f'Managed destination is not a file: {relative}')
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    current = hashlib.sha256(dest.read_bytes()).hexdigest() if dest.exists() else None
    if current != digest:
        changes.append((relative, src, dest))
        if current is not None and current != previous['files'].get(relative):
            conflicts.append(relative)
if conflicts and not args.upgrade:
    parser.error('Locally modified/unrecognized managed files: ' + ', '.join(conflicts) + '. Re-run --upgrade to back them up before replacement; unrelated files are never removed.')
for relative in ('', 'incoming', 'artifacts', 'runtime', 'runtime/dashboard', 'backups'):
    path = bank / relative
    safe(path)
    path.mkdir(parents=True, exist_ok=True, mode=dir_mode)
    path.chmod(dir_mode)
for folder in ('incoming', 'artifacts'):
    for path in (bank / folder).rglob('*'):
        safe(path)
        path.chmod(dir_mode if path.is_dir() else file_mode)

def atomic(path, content, mode):
    safe(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.deploy-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)

backup = None
if any(dest.exists() for _, _, dest in changes):
    backup = Path(tempfile.mkdtemp(prefix='dashboard-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-', dir=bank / 'backups'))
    backup.chmod(dir_mode)
    for relative, _, dest in changes:
        if dest.exists():
            target = backup / relative
            target.parent.mkdir(parents=True, exist_ok=True, mode=dir_mode)
            shutil.copy2(dest, target)
            target.chmod(file_mode)
for relative, src, dest in changes:
    atomic(dest, src.read_bytes(), 0o755 if dest.suffix == '.sh' else 0o644)
atomic(config_path, (json.dumps(config, indent=2) + '\n').encode(), file_mode)
record = {'schema': 1, 'files': {relative: hashlib.sha256(src.read_bytes()).hexdigest() for relative, src in managed.items()}}
atomic(receipt, (json.dumps(record, indent=2) + '\n').encode(), file_mode)
queue = bank / 'reviewQueue.md'
if not queue.exists():
    atomic(queue, b'# Review Queue\n\nStatus values: `PENDING` | `IN_PROGRESS` | `DONE`\n\n## Pending Review\n\n## Done\n', file_mode)
ignore = root / '.gitignore'
safe(ignore)
text = ignore.read_text() if ignore.exists() else ''
if '/.memory-bank/' not in text.splitlines():
    atomic(ignore, (text.rstrip('\n') + '\n/.memory-bank/\n').encode(), 0o644)
if args.with_sample_data:
    for src in (source / 'sample-data').glob('*.json'):
        dest = bank / 'incoming' / src.name
        if not dest.exists():
            atomic(dest, src.read_bytes(), file_mode)
print(f'Installed/updated {len(changes)} managed files; configuration preserved at .memory-bank/dashboard.config.json')
if backup:
    print('Previous changed files preserved at ' + str(backup.relative_to(root)))
print('Start: bash dashboard/start.sh --port 8443')
print('Intake: select acquired evidence in the dashboard, or python3 -B scripts/intake.py PATH [PATH ...]')
print('No selected paths means transaction recovery only; reference/operational drops remain pending.')
PY
