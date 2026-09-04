#!/usr/bin/env python3
"""Semantic consistency and readiness checks for an IR memory bank."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEMORY_BANK = PROJECT_ROOT / "memory-bank"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
INCOMING_DIR = PROJECT_ROOT / "incoming"
CONFIG_FILE = PROJECT_ROOT / "dashboard.config.json"
SENSITIVE_DIR = PROJECT_ROOT / "sensitive"
CUSTODY_MANIFEST = ARTIFACTS_DIR / ".custody-manifest.jsonl"

REQUIRED_SECTIONS = {
    "incidentBrief.md": ["Incident ID", "Classification", "Severity", "Current Phase", "Detection", "Summary of Known Facts"],
    "scopeAuthorization.md": [
        "Engagement Authorization Reference", "In-Scope Systems / Environments",
        "Out-of-Scope Systems / Environments", "Response Approval Authority",
        "Evidence Preservation Requirements", "Prohibited Actions", "Escalation Contacts",
    ],
    "sensitiveDataPolicy.md": [
        "Policy Status", "Standard Store", "Profile Stores",
        "Additional Owner-Designated Stores", "Handling Rules", "Notes",
    ],
    "timeline.md": ["Clock Skew and Timezone Notes", "Entries"],
    "affectedAssets.md": ["Systems", "Accounts", "Data", "Scope Change Log"],
    "indicators.md": ["Indicators of Compromise", "Observed TTPs", "Detection and Hunt Coverage"],
    "findings.md": ["Entries", "Gaps and Unanswered Questions"],
    "evidenceIndex.md": ["Entries", "Custody Transfers"],
    "activeContext.md": [
        "Timestamp (UTC)", "Current Phase", "Current Objective", "Working Theory",
        "Immediate Next Steps (1-3)", "Blockers / Questions", "Pending Approvals", "Shift Handover",
    ],
    "progress.md": ["Entries"],
    "reviewQueue.md": ["Pending Review", "Done"],
}

READINESS_FIELDS = {
    "incidentBrief.md": ["Incident ID", "Classification", "Severity", "Current Phase", "Summary of Known Facts"],
    "scopeAuthorization.md": [
        "Engagement Authorization Reference", "In-Scope Systems / Environments",
        "Out-of-Scope Systems / Environments", "Response Approval Authority",
        "Evidence Preservation Requirements", "Prohibited Actions", "Escalation Contacts",
    ],
    "activeContext.md": ["Timestamp (UTC)", "Current Phase", "Current Objective", "Immediate Next Steps (1-3)"],
}

ARTIFACT_REQUIRED_FIELDS = [
    "Artifact ID", "Original name", "Source path / system of origin", "Provided by",
    "Acquisition method", "SHA-256", "Copy verified", "Size", "Ingested (UTC)",
    "Stored path", "Related timeline entries", "Relevance", "Handling notes",
]


def issue(severity: str, category: str, message: str) -> dict:
    return {"severity": severity, "category": category, "message": message}


def _reject_nonfinite_json(value: str):
    raise ValueError(f"non-finite JSON number is not supported: {value}")


def read_mb(filename: str) -> str:
    path = MEMORY_BANK / filename
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _sections(content: str) -> dict[str, str]:
    result = {}
    blocks = re.split(r"^## ", content, flags=re.MULTILINE)
    for block in blocks[1:]:
        lines = block.splitlines()
        result[lines[0].strip()] = "\n".join(lines[1:]).strip()
    return result


def _has_meaningful_value(value: str) -> bool:
    value = re.sub(r"<!--.*?-->", "", value, flags=re.DOTALL).strip()
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    labeled = [re.match(r"^[-*]\s+.+?:\s*(.*)$", line) for line in lines]
    if lines and all(match is not None for match in labeled):
        return any(bool(match.group(1).strip()) for match in labeled if match)
    value = re.sub(r"^[-*]\s*", "", value, flags=re.MULTILINE).strip()
    value = re.sub(r"^\d+\.\s*", "", value, flags=re.MULTILINE).strip()
    value = value.replace("|", "").replace("-", "").strip()
    return bool(value and not re.fullmatch(r"(?:pending|unknown|tbd|n/?a)(?:\s*[—:.-].*)?", value.lower()))


def _policy_fields(section: str) -> dict[str, str]:
    fields = {}
    for line in section.splitlines():
        match = re.match(r"^[-*]\s+([^:]+):\s*(.*?)\s*$", line.strip())
        if match:
            fields[match.group(1).strip()] = match.group(2).strip().strip("`")
    return fields


def check_sensitive_policy() -> list[dict]:
    path = MEMORY_BANK / "sensitiveDataPolicy.md"
    if not path.exists():
        return []
    try:
        sections = _sections(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        return []
    status = _policy_fields(sections.get("Policy Status", ""))
    issues = []
    for field in ("Mode", "Approved by", "Version-control policy", "Memory-bank plaintext"):
        if not status.get(field):
            issues.append(issue("error", "sensitive-policy", f"sensitiveDataPolicy.md: missing policy value: {field}"))
    mode = status.get("Mode")
    version_control = status.get("Version-control policy")
    plaintext = status.get("Memory-bank plaintext")
    if mode and mode not in {"restricted", "designated-store", "private-lab"}:
        issues.append(issue("error", "sensitive-policy", f"sensitiveDataPolicy.md: unsupported mode: {mode}"))
    if version_control and version_control not in {"excluded", "permitted", "external"}:
        issues.append(issue("error", "sensitive-policy", f"sensitiveDataPolicy.md: unsupported version-control policy: {version_control}"))
    if plaintext and plaintext not in {"prohibited", "synthetic-only"}:
        issues.append(issue("error", "sensitive-policy", f"sensitiveDataPolicy.md: unsupported memory-bank plaintext policy: {plaintext}"))
    if plaintext == "synthetic-only" and mode != "private-lab":
        issues.append(issue("error", "sensitive-policy", "sensitiveDataPolicy.md: synthetic-only plaintext requires private-lab mode"))
    if "`sensitive/`" not in sections.get("Standard Store", ""):
        issues.append(issue("error", "sensitive-policy", "sensitiveDataPolicy.md: standard sensitive/ store is not declared"))
    if "`artifacts/`" not in sections.get("Profile Stores", ""):
        issues.append(issue("error", "sensitive-policy", "sensitiveDataPolicy.md: incident-response artifacts/ store is not declared"))
    return issues


def check_memory_bank_semantics() -> list[dict]:
    issues = []
    for filename, required in REQUIRED_SECTIONS.items():
        path = MEMORY_BANK / filename
        if not path.exists():
            issues.append(issue("error", "memory-bank", f"Required file missing: {filename}"))
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            issues.append(issue("error", "memory-bank", f"Cannot read {filename}: {exc}"))
            continue
        sections = _sections(content)
        for heading in required:
            if heading not in sections:
                issues.append(issue("error", "memory-bank", f"{filename}: required section missing: {heading}"))
        for heading in READINESS_FIELDS.get(filename, []):
            if heading in sections and not _has_meaningful_value(sections[heading]):
                severity = "error" if filename == "scopeAuthorization.md" else "warning"
                issues.append(issue(severity, "readiness", f"{filename}: required operational value is not populated: {heading}"))
    issues.extend(check_sensitive_policy())
    return issues


def parse_indexed_artifact_entries() -> list[tuple[str, dict[str, str]]]:
    content = read_mb("evidenceIndex.md")
    entries = []
    blocks = re.split(r"^### (ART-\d{4})", content, flags=re.MULTILINE)
    for index in range(1, len(blocks) - 1, 2):
        artifact_id = blocks[index].strip()
        fields = {}
        for line in blocks[index + 1].splitlines():
            match = re.match(r"^-\s+(.+?):\s*(.*)$", line.strip())
            if match:
                fields[match.group(1).strip()] = match.group(2).strip().strip("`")
        entries.append((artifact_id, fields))
    return entries


def _check_sequence(ids: list[str], prefix: str, width: int, category: str) -> list[dict]:
    issues = []
    counts = Counter(ids)
    duplicates = sorted(identifier for identifier, count in counts.items() if count > 1)
    if duplicates:
        issues.append(issue("error", category, f"Duplicate IDs: {', '.join(duplicates)}"))
    numbers = sorted({int(identifier.split("-")[1]) for identifier in ids})
    if numbers:
        missing = sorted(set(range(1, numbers[-1] + 1)) - set(numbers))
        if missing:
            rendered = ", ".join(f"{prefix}-{number:0{width}d}" for number in missing)
            issues.append(issue("warning", category, f"ID sequence gaps: {rendered}"))
    return issues


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(value: dict) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _contained_artifact(stored: str) -> Path | None:
    try:
        if Path(stored).is_absolute():
            return None
        base = ARTIFACTS_DIR.resolve(strict=True)
        candidate = (PROJECT_ROOT / stored).resolve(strict=True)
        candidate.relative_to(base)
        raw = (PROJECT_ROOT / stored).absolute()
        relative = raw.relative_to(ARTIFACTS_DIR.absolute())
        cursor = ARTIFACTS_DIR.absolute()
        for part in relative.parts:
            cursor /= part
            if cursor.is_symlink():
                return None
        return candidate if candidate.is_file() else None
    except (OSError, RuntimeError, ValueError):
        return None


def _parse_utc(value: str) -> bool:
    value = value.strip()
    if not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() == timezone.utc.utcoffset(parsed)


def check_artifacts(entries: list[tuple[str, dict[str, str]]]) -> list[dict]:
    issues = _check_sequence([artifact_id for artifact_id, _ in entries], "ART", 4, "artifacts")
    for artifact_id, fields in entries:
        if fields.get("Artifact ID", "").strip("`") != artifact_id:
            issues.append(issue("error", "artifacts", f"{artifact_id}: Artifact ID field does not match heading"))
        missing = [field for field in ARTIFACT_REQUIRED_FIELDS if not fields.get(field, "").strip()]
        if missing:
            issues.append(issue("error", "artifacts", f"{artifact_id}: missing required fields: {', '.join(missing)}"))
        digest = fields.get("SHA-256", "").strip("`").lower()
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            issues.append(issue("error", "artifacts", f"{artifact_id}: SHA-256 is missing or invalid"))
        if not fields.get("Copy verified", "").lower().startswith("yes"):
            issues.append(issue("error", "artifacts", f"{artifact_id}: stored-copy verification is not recorded as Yes"))
        if not _parse_utc(fields.get("Ingested (UTC)", "")):
            issues.append(issue("warning", "artifacts", f"{artifact_id}: Ingested (UTC) is not an explicit UTC timestamp"))
        for provenance in ("Source path / system of origin", "Provided by"):
            if "UNVERIFIED" in fields.get(provenance, "").upper():
                issues.append(issue("warning", "provenance", f"{artifact_id}: {provenance} remains unverified"))
        stored = fields.get("Stored path", "").strip("`")
        filepath = _contained_artifact(stored) if stored else None
        if filepath is None:
            issues.append(issue("error", "artifacts", f"{artifact_id}: stored path is missing, unsafe, symlinked, or not a regular file: {stored or '(empty)'}"))
        elif re.fullmatch(r"[0-9a-f]{64}", digest):
            try:
                actual = _sha256_file(filepath)
            except OSError as exc:
                issues.append(issue("error", "artifacts", f"{artifact_id}: cannot hash stored file: {exc}"))
            else:
                if actual != digest:
                    issues.append(issue("error", "artifacts", f"{artifact_id}: SHA-256 mismatch for stored file"))
        if "PENDING" in " ".join(fields.get(field, "") for field in ("Related timeline entries", "Relevance")):
            issues.append(issue("warning", "pending-review", f"{artifact_id}: analytical fields remain pending"))
    return issues


def check_orphan_artifacts(entries: list[tuple[str, dict[str, str]]]) -> list[dict]:
    issues = []
    if not ARTIFACTS_DIR.exists():
        return issues
    indexed = {fields.get("Stored path", "").strip("`") for _, fields in entries}
    for path in sorted(ARTIFACTS_DIR.iterdir()):
        if path.name in {".intake.lock", CUSTODY_MANIFEST.name}:
            continue
        if path.name == ".intake-journal.json":
            issues.append(issue("error", "intake-recovery", "An interrupted intake transaction is awaiting recovery"))
        elif path.name.startswith(".pending-"):
            issues.append(issue("error", "intake-recovery", f"Unjournaled incomplete artifact copy: {path.name}"))
        elif path.name.startswith(".quarantine-"):
            issues.append(issue("warning", "quarantine", f"Quarantined failed-verification copy requires review: {path.name}"))
        elif path.is_file() and f"artifacts/{path.name}" not in indexed:
            issues.append(issue("warning", "orphan-artifacts", f"File is not indexed: {path.name}"))
    return issues


def check_custody_manifest(entries: list[tuple[str, dict[str, str]]]) -> list[dict]:
    if not CUSTODY_MANIFEST.exists():
        if entries:
            return [issue("warning", "custody-manifest", "No hash-chained custody manifest exists; artifacts may predate this feature")]
        return []
    issues = []
    expected_previous = "0" * 64
    transaction_ids = set()
    manifested: dict[str, dict] = {}
    try:
        lines = CUSTODY_MANIFEST.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        return [issue("error", "custody-manifest", f"Cannot read custody manifest: {exc}")]
    for line_number, line in enumerate(lines, 1):
        try:
            record = json.loads(line, parse_constant=_reject_nonfinite_json)
        except ValueError as exc:
            issues.append(issue("error", "custody-manifest", f"Line {line_number} is invalid JSON: {exc}"))
            break
        if not isinstance(record, dict):
            issues.append(issue("error", "custody-manifest", f"Line {line_number} is not an object"))
            break
        entry_hash = record.pop("entry_sha256", "")
        if record.get("previous_entry_sha256") != expected_previous:
            issues.append(issue("error", "custody-manifest", f"Line {line_number} breaks the previous-hash chain"))
        if not isinstance(entry_hash, str) or _canonical_sha256(record) != entry_hash:
            issues.append(issue("error", "custody-manifest", f"Line {line_number} content hash does not match"))
        expected_previous = entry_hash if isinstance(entry_hash, str) else ""
        transaction_id = record.get("transaction_id")
        if not isinstance(transaction_id, str) or not transaction_id:
            issues.append(issue("error", "custody-manifest", f"Line {line_number} has no transaction ID"))
        elif transaction_id in transaction_ids:
            issues.append(issue("error", "custody-manifest", f"Duplicate transaction ID on line {line_number}"))
        else:
            transaction_ids.add(transaction_id)
        artifacts = record.get("artifacts")
        if not isinstance(artifacts, list):
            issues.append(issue("error", "custody-manifest", f"Line {line_number} artifacts value is not an array"))
            continue
        for artifact in artifacts:
            if not isinstance(artifact, dict) or not isinstance(artifact.get("artifact_id"), str):
                issues.append(issue("error", "custody-manifest", f"Line {line_number} has an invalid artifact record"))
                continue
            artifact_id = artifact["artifact_id"]
            if artifact_id in manifested:
                issues.append(issue("error", "custody-manifest", f"Artifact appears in multiple manifest transactions: {artifact_id}"))
            manifested[artifact_id] = artifact
    indexed = {artifact_id: fields for artifact_id, fields in entries}
    for artifact_id, artifact in manifested.items():
        fields = indexed.get(artifact_id)
        if fields is None:
            issues.append(issue("error", "custody-manifest", f"Manifest references non-indexed artifact {artifact_id}"))
            continue
        if fields.get("SHA-256", "").strip("`").lower() != artifact.get("sha256"):
            issues.append(issue("error", "custody-manifest", f"{artifact_id}: index digest differs from custody manifest"))
        if fields.get("Stored path", "").strip("`") != artifact.get("stored_path"):
            issues.append(issue("error", "custody-manifest", f"{artifact_id}: index path differs from custody manifest"))
    for artifact_id, fields in entries:
        if "Auto-ingested" in fields.get("Handling notes", "") and artifact_id not in manifested:
            issues.append(issue("warning", "custody-manifest", f"{artifact_id}: auto-ingested artifact has no manifest transaction"))
    return issues


def check_permissions() -> list[dict]:
    issues = []
    shared = False
    try:
        config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"), parse_constant=_reject_nonfinite_json)
    except (OSError, ValueError) as exc:
        issues.append(issue("error", "configuration", f"dashboard.config.json is missing or invalid: {exc}"))
        config = {}
    if not isinstance(config, dict):
        issues.append(issue("error", "configuration", "dashboard.config.json must contain an object"))
        config = {}
    shared_value = config.get("shared_group_access", False)
    if not isinstance(shared_value, bool):
        issues.append(issue("error", "configuration", "dashboard.config.json shared_group_access must be a boolean"))
    else:
        shared = shared_value

    evidence_forbidden = 0o007 if shared else 0o077
    directories = (
        (INCOMING_DIR, evidence_forbidden, "world permissions" if shared else "group/world permissions"),
        (ARTIFACTS_DIR, evidence_forbidden, "world permissions" if shared else "group/world permissions"),
        (SENSITIVE_DIR, 0o077, "group/world permissions"),
    )
    for directory, forbidden, policy in directories:
        if directory.is_symlink():
            issues.append(issue("error", "permissions", f"Sensitive directory must not be a symlink: {directory.name}/"))
            continue
        if not directory.exists():
            issues.append(issue("warning", "permissions", f"Sensitive store not present: {directory.name}/ (nothing to verify; create it before storing evidence)"))
            continue
        mode = directory.stat().st_mode & 0o777
        if mode & forbidden:
            issues.append(issue("error", "permissions", f"{directory.name}/ mode {mode:04o} grants prohibited {policy}"))
        for path in directory.rglob("*"):
            relative = path.relative_to(PROJECT_ROOT)
            if path.is_symlink():
                issues.append(issue("error", "permissions", f"Symlink not allowed in sensitive directory: {relative}"))
                continue
            if (path.is_file() or path.is_dir()) and (path.stat().st_mode & 0o777) & forbidden:
                mode = path.stat().st_mode & 0o777
                issues.append(issue("error", "permissions", f"{relative} mode {mode:04o} grants prohibited {policy}"))
    return issues


def collect_all_art_refs() -> dict[str, set[str]]:
    refs = {}
    for filename in [
        "timeline.md", "findings.md", "indicators.md", "affectedAssets.md",
        "activeContext.md", "progress.md", "reviewQueue.md", "executiveSummary.json",
    ]:
        content = read_mb(filename)
        found = set(re.findall(r"ART-\d{4}", content))
        if found:
            refs[filename] = found
    return refs


def check_references(entries: list[tuple[str, dict[str, str]]]) -> list[dict]:
    issues = []
    indexed = {artifact_id for artifact_id, _ in entries}
    for filename, artifact_ids in collect_all_art_refs().items():
        for artifact_id in sorted(artifact_ids - indexed):
            issues.append(issue("error", "dangling-refs", f"{artifact_id} is referenced in {filename} but not indexed"))
    finding_ids = re.findall(r"^### (F-\d{3})", read_mb("findings.md"), re.MULTILINE)
    issues.extend(_check_sequence(finding_ids, "F", 3, "findings"))
    return issues


def check_review_queue() -> list[dict]:
    content = read_mb("reviewQueue.md")
    ids = re.findall(r"^### (RQ-\d{3})\s*—", content, re.MULTILINE)
    issues = _check_sequence(ids, "RQ", 3, "review-queue")
    pending_section = content.split("## Pending Review", 1)[-1].split("## Done", 1)[0]
    pending = re.findall(r"^### (RQ-\d{3})\s*—", pending_section, re.MULTILINE)
    if pending:
        unchecked = len(re.findall(r"- \[ \]", pending_section))
        issues.append(issue("warning", "review-queue", f"{len(pending)} item(s) pending review with {unchecked} unchecked tasks"))
    return issues


def check_unprocessed_incoming() -> list[dict]:
    if not INCOMING_DIR.exists():
        return []
    files = [path for path in INCOMING_DIR.iterdir() if path.is_file() and not path.name.startswith(".")]
    if not files:
        return []
    names = ", ".join(path.name for path in files[:5])
    return [issue("warning", "incoming", f"{len(files)} unprocessed file(s) in incoming/: {names}")]


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def check_executive_summary(entries: list[tuple[str, dict[str, str]]]) -> list[dict]:
    path = MEMORY_BANK / "executiveSummary.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_nonfinite_json)
    except (OSError, UnicodeError, ValueError) as exc:
        return [issue("error", "executive-summary", f"executiveSummary.json is invalid JSON: {exc}")]
    issues = []
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        return [issue("error", "executive-summary", "executiveSummary.json must be a schema_version 1 object")]
    for key in ("generated_at", "narrative", "theory_summary"):
        if not isinstance(data.get(key), str):
            issues.append(issue("error", "executive-summary", f"{key} must be a string"))
    if isinstance(data.get("generated_at"), str) and not _parse_utc(data["generated_at"]):
        issues.append(issue("warning", "executive-summary", "generated_at is not an explicit UTC timestamp"))
    phases = data.get("attack_phases")
    if not isinstance(phases, list):
        issues.append(issue("error", "executive-summary", "attack_phases must be an array"))
        phases = []
    known_findings = set(re.findall(r"^### (F-\d{3})", read_mb("findings.md"), re.MULTILINE))
    for index, phase in enumerate(phases):
        if not isinstance(phase, dict):
            issues.append(issue("error", "executive-summary", f"attack_phases[{index}] must be an object"))
            continue
        if phase.get("color") not in {"warning", "danger", "purple", "success", "info", "accent"}:
            issues.append(issue("error", "executive-summary", f"attack_phases[{index}].color is invalid"))
        for key in ("name", "icon", "date_range", "summary"):
            if not isinstance(phase.get(key), str):
                issues.append(issue("error", "executive-summary", f"attack_phases[{index}].{key} must be a string"))
        if isinstance(phase.get("event_count"), bool) or not isinstance(phase.get("event_count"), int):
            issues.append(issue("error", "executive-summary", f"attack_phases[{index}].event_count must be an integer"))
        if not _is_string_list(phase.get("key_findings")):
            issues.append(issue("error", "executive-summary", f"attack_phases[{index}].key_findings must be a string array"))
        else:
            for finding_id in sorted(set(phase["key_findings"]) - known_findings):
                issues.append(issue("error", "executive-summary", f"attack_phases[{index}] references unknown finding {finding_id}"))
    findings = data.get("key_findings")
    if not isinstance(findings, list):
        issues.append(issue("error", "executive-summary", "key_findings must be an array"))
        findings = []
    known_artifacts = {artifact_id for artifact_id, _ in entries}
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            issues.append(issue("error", "executive-summary", f"key_findings[{index}] must be an object"))
            continue
        if finding.get("id") not in known_findings:
            issues.append(issue("error", "executive-summary", f"key_findings[{index}] references unknown finding {finding.get('id')!r}"))
        if finding.get("confidence") not in {"High", "Medium", "Low"}:
            issues.append(issue("error", "executive-summary", f"key_findings[{index}].confidence is invalid"))
        if not isinstance(finding.get("headline"), str):
            issues.append(issue("error", "executive-summary", f"key_findings[{index}].headline must be a string"))
        artifacts = finding.get("artifacts")
        if not _is_string_list(artifacts):
            issues.append(issue("error", "executive-summary", f"key_findings[{index}].artifacts must be a string array"))
        else:
            for artifact_id in sorted(set(artifacts) - known_artifacts):
                issues.append(issue("error", "executive-summary", f"key_findings[{index}] references unknown artifact {artifact_id}"))
    status = data.get("status")
    if not isinstance(status, dict):
        issues.append(issue("error", "executive-summary", "status must be an object"))
    else:
        for key in ("completed", "in_progress"):
            if not _is_string_list(status.get(key)):
                issues.append(issue("error", "executive-summary", f"status.{key} must be a string array"))
        blocked = status.get("blocked")
        valid_blocked = isinstance(blocked, list) and all(
            isinstance(item, dict) and item.get("severity") in {"high", "medium", "low"}
            and isinstance(item.get("item"), str) and isinstance(item.get("reason"), str)
            for item in blocked
        )
        if not valid_blocked:
            issues.append(issue("error", "executive-summary", "status.blocked does not match the v1 schema"))
    if not _is_string_list(data.get("unresolved")):
        issues.append(issue("error", "executive-summary", "unresolved must be a string array"))
    return issues


def run_all_checks() -> dict:
    entries = parse_indexed_artifact_entries()
    checks = [
        check_memory_bank_semantics(), check_artifacts(entries), check_orphan_artifacts(entries),
        check_custody_manifest(entries), check_permissions(), check_unprocessed_incoming(), check_references(entries),
        check_review_queue(), check_executive_summary(entries),
    ]
    all_issues = [item for group in checks for item in group]
    counts = Counter(item["severity"] for item in all_issues)
    finding_ids = re.findall(r"^### F-\d{3}", read_mb("findings.md"), re.MULTILINE)
    timeline_entries = re.findall(r"^### (?!<)", read_mb("timeline.md"), re.MULTILINE)
    return {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": {
            "total_issues": len(all_issues), "errors": counts["error"],
            "warnings": counts["warning"], "info": counts["info"],
            "status": "error" if counts["error"] else ("warning" if counts["warning"] else "ok"),
        },
        "counts": {
            "indexed_artifacts": len(entries), "findings": len(finding_ids),
            "timeline_entries": len(timeline_entries),
        },
        "issues": all_issues,
    }


def print_report(result: dict) -> None:
    summary, counts = result["summary"], result["counts"]
    print(f"\n{'=' * 60}\n  Sync Check — {result['timestamp']}\n{'=' * 60}")
    print(f"  Artifacts: {counts['indexed_artifacts']}  |  Findings: {counts['findings']}  |  Timeline: {counts['timeline_entries']}")
    symbol = {"ok": "✓", "warning": "⚠", "error": "✗"}
    print(f"  Status: {symbol[summary['status']]} {summary['status'].upper()} — {summary['errors']} errors, {summary['warnings']} warnings, {summary['info']} info\n{'=' * 60}\n")
    for item in result["issues"]:
        marker = {"error": "✗", "warning": "⚠", "info": "·"}.get(item["severity"], "?")
        print(f"  {marker} [{item['category']}] {item['message']}")
    if not result["issues"]:
        print("  No issues found — the incident state is ready and internally consistent.")
    print()


if __name__ == "__main__":
    result = run_all_checks()
    if "--json" in sys.argv:
        print(json.dumps(result, indent=2))
    else:
        print_report(result)
    sys.exit(1 if result["summary"]["errors"] else 0)
