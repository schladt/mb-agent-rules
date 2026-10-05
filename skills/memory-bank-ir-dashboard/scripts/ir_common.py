"""Shared deployed IR path, queue and analytical-projection contracts."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re


def canonical_path(root: Path, value: str) -> Path:
    """Resolve recorded paths via an explicit migration receipt, never old stores."""
    path = Path(value)
    receipt = root / '.memory-bank/path-migrations.json'
    prefixes = {}
    roots = [str(root), str(root.resolve())]
    if receipt.exists():
        data = json.loads(receipt.read_text(encoding='utf-8'))
        if data.get('schema') != 1 or not isinstance(data.get('prefixes'), dict):
            raise ValueError('Invalid path migration receipt')
        prefixes = data['prefixes']
        roots += data.get('project_roots', [])
    if path.is_absolute():
        for old_root in roots:
            try:
                path = path.relative_to(old_root)
                break
            except ValueError:
                continue
        else:
            raise ValueError('Recorded path is outside known project roots')
    text = path.as_posix()
    for old, new in sorted(prefixes.items(), key=lambda pair: -len(pair[0])):
        if text.startswith(old):
            text = new + text[len(old):]
            break
    path = Path(text)
    if path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0] != '.memory-bank':
        raise ValueError('Recorded path is outside the canonical bank')
    return root / path


def parse_review_queue(content: str) -> list[dict]:
    items = []
    section = ''
    current = None
    for line in content.splitlines():
        if line.startswith('## '):
            section = line[3:].strip()
            current = None
        match = re.match(r'^### (RQ-\d{3})\s*[—:]\s*(.+)$', line)
        if match:
            current = {'id': match[1], 'title': match[2], 'location': section,
                       'statuses': [], 'checked': 0, 'unchecked': 0, 'added': ''}
            items.append(current)
        elif current is not None:
            status = re.match(r'^- Status:\s*`?([A-Z_]+)`?\s*$', line)
            if status:
                current['statuses'].append(status[1])
            if re.match(r'\s*- \[[xX]\]', line):
                current['checked'] += 1
            if re.match(r'\s*- \[ \]', line):
                current['unchecked'] += 1
            if line.startswith('- Added:'):
                current['added'] = line.split(':', 1)[1].strip()
    for item in items:
        statuses = item.pop('statuses')
        item['status'] = statuses[0] if len(statuses) == 1 else 'INVALID'
        item['total_tasks'] = item['checked'] + item['unchecked']
        complete = item['status'] == 'DONE' and item['unchecked'] == 0 and item['checked'] > 0
        item['section'] = 'done' if complete else 'pending'
        errors = []
        if item['status'] not in {'PENDING', 'IN_PROGRESS', 'DONE'}:
            errors.append('missing, duplicate or invalid explicit status')
        if item['status'] == 'DONE' and not complete:
            errors.append('DONE requires a completed nonempty checklist')
        if (item['location'] == 'Done') != complete:
            errors.append('section disagrees with explicit status/checklist')
        item['errors'] = errors
    return items


def projection_errors(value: object, *, findings=None, artifacts=None) -> list[str]:
    """One strict schema for the dashboard and checker; references are authoritative."""
    def strings(v):
        return isinstance(v, list) and all(isinstance(x, str) for x in v)
    if not isinstance(value, dict) or type(value.get('schema_version')) is not int or value['schema_version'] != 1:
        return ['Expected schema_version 1 object']
    errors = []
    for key in ('generated_at', 'narrative', 'theory_summary'):
        if not isinstance(value.get(key), str):
            errors.append(f'{key} must be a string')
    try:
        stamp = datetime.fromisoformat(value.get('generated_at', '').replace('Z', '+00:00'))
        if stamp.tzinfo is None or stamp.utcoffset() != timezone.utc.utcoffset(stamp):
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        errors.append('generated_at must be an explicit UTC timestamp')
    for key, limit in (('attack_phases', 20), ('key_findings', 100)):
        rows = value.get(key)
        if not isinstance(rows, list) or len(rows) > limit:
            errors.append(f'{key} must be an array of at most {limit} items')
            continue
        for row in rows:
            if not isinstance(row, dict):
                errors.append(f'{key} entry must be an object')
                continue
            required = ('name', 'icon', 'date_range', 'color', 'summary') if key == 'attack_phases' else ('id', 'headline', 'confidence')
            if any(not isinstance(row.get(k), str) for k in required):
                errors.append(f'{key} entry is missing required strings')
                continue
            if key == 'attack_phases':
                if row.get('color') not in {'warning', 'danger', 'purple', 'success', 'info', 'accent'}:
                    errors.append('Invalid phase color')
                if type(row.get('event_count')) is not int or row['event_count'] < 0:
                    errors.append('event_count must be a nonnegative integer')
                refs = row.get('key_findings')
                if not strings(refs):
                    errors.append('phase key_findings must be a string array')
                elif findings is not None and set(refs) - set(findings):
                    errors.append('Phase references unknown findings')
            else:
                if row.get('confidence') not in {'High', 'Medium', 'Low'}:
                    errors.append('Invalid finding confidence')
                if findings is not None and row.get('id') not in findings:
                    errors.append('Unknown finding reference')
                refs = row.get('artifacts')
                if not strings(refs):
                    errors.append('artifacts must be a string array')
                elif artifacts is not None and set(refs) - set(artifacts):
                    errors.append('Unknown artifact reference')
    status = value.get('status')
    if not isinstance(status, dict):
        errors.append('status must be an object (investigative projection, not execution authority)')
    else:
        for key in ('completed', 'in_progress'):
            if not strings(status.get(key)):
                errors.append(f'status.{key} must be a string array')
        blocked = status.get('blocked')
        if not isinstance(blocked, list) or not all(isinstance(x, dict) and isinstance(x.get('severity'), str) and x['severity'] in {'high', 'medium', 'low'} and all(isinstance(x.get(k), str) for k in ('item', 'reason')) for x in blocked):
            errors.append('Invalid status.blocked entries')
    if not strings(value.get('unresolved')):
        errors.append('unresolved must be a string array')
    return errors
