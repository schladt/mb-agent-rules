#!/usr/bin/env python3
"""Atomic evidence intake for incident-response projects.

The artifact copy, custody entry, review queue entry, and acquisition progress
entry are serialized under a project-local lock. A small recovery journal makes
an interrupted multi-file commit idempotently resumable on the next run.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import html
import json
import os
import re
import shutil
import tempfile
import uuid
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INCOMING_DIR = PROJECT_ROOT / "incoming"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
MEMORY_BANK = PROJECT_ROOT / "memory-bank"
EVIDENCE_INDEX = MEMORY_BANK / "evidenceIndex.md"
REVIEW_QUEUE = MEMORY_BANK / "reviewQueue.md"
PROGRESS = MEMORY_BANK / "progress.md"
CONFIG_FILE = PROJECT_ROOT / "dashboard.config.json"
LOCK_FILE = ARTIFACTS_DIR / ".intake.lock"
JOURNAL_FILE = ARTIFACTS_DIR / ".intake-journal.json"
CUSTODY_MANIFEST = ARTIFACTS_DIR / ".custody-manifest.jsonl"


def _reject_nonfinite_json(value: str):
    raise ValueError(f"non-finite JSON number is not supported: {value}")


def load_security_config() -> dict:
    try:
        raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"), parse_constant=_reject_nonfinite_json)
    except (OSError, ValueError):
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    return {"shared_group_access": raw.get("shared_group_access", False) is True}


def _modes() -> tuple[int, int]:
    shared = load_security_config()["shared_group_access"]
    return (0o770, 0o660) if shared else (0o700, 0o600)


def ensure_secure_directories() -> None:
    dir_mode, _ = _modes()
    for directory in (INCOMING_DIR, ARTIFACTS_DIR):
        if directory.is_symlink():
            raise RuntimeError(f"Sensitive directory must not be a symlink: {directory}")
        directory.mkdir(parents=True, exist_ok=True, mode=dir_mode)
        directory.chmod(dir_mode)


def sha256_file(filepath: Path) -> str:
    digest = hashlib.sha256()
    with filepath.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stat_identity(path: Path) -> dict[str, int]:
    stat = path.stat()
    return {
        "device": stat.st_dev,
        "inode": stat.st_ino,
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def _public_result(item: dict, **extra: object) -> dict:
    internal = {"pending_path", "index_entry", "remove_source", "source_identity"}
    return {key: value for key, value in item.items() if key not in internal} | extra


def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r"[^\w.\-]", "_", name)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    cleaned = cleaned or "unnamed-artifact"
    if len(cleaned.encode("utf-8")) <= 180:
        return cleaned
    suffix = Path(cleaned).suffix
    if len(suffix.encode("utf-8")) > 24:
        suffix = ""
    stem = cleaned[:-len(suffix)] if suffix else cleaned
    budget = 180 - len(suffix.encode("utf-8"))
    stem = stem.encode("utf-8")[:budget].decode("utf-8", errors="ignore").rstrip("._-")
    return (stem or "artifact") + suffix


def _markdown_value(value: object) -> str:
    """Keep provenance text literal and confined to a single Markdown line."""
    text = str(value).replace("\r", " ").replace("\n", " ")
    text = "".join(ch if ch.isprintable() else "�" for ch in text)
    return html.escape(text, quote=True).replace("`", "&#96;")


def _fsync_dir(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _canonical_sha256(value: dict) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _ensure_custody_manifest_entry(journal: dict) -> str:
    """Append one idempotent, hash-chained transaction record."""
    previous_hash = "0" * 64
    if CUSTODY_MANIFEST.is_symlink():
        raise RuntimeError("Custody manifest must not be a symlink")
    if CUSTODY_MANIFEST.exists():
        for line_number, line in enumerate(CUSTODY_MANIFEST.read_text(encoding="utf-8").splitlines(), 1):
            try:
                existing = json.loads(line, parse_constant=_reject_nonfinite_json)
            except ValueError as exc:
                raise RuntimeError(f"Invalid custody manifest line {line_number}; refusing to append") from exc
            if not isinstance(existing, dict):
                raise RuntimeError(f"Invalid custody manifest object on line {line_number}; refusing to append")
            entry_hash = str(existing.pop("entry_sha256", ""))
            if (
                existing.get("previous_entry_sha256") != previous_hash
                or not re.fullmatch(r"[0-9a-f]{64}", entry_hash)
                or _canonical_sha256(existing) != entry_hash
            ):
                raise RuntimeError(f"Custody manifest chain verification failed on line {line_number}")
            if existing.get("transaction_id") == journal["transaction_id"]:
                return entry_hash
            previous_hash = entry_hash
    payload = {
        "schema_version": 1,
        "transaction_id": journal["transaction_id"],
        "committed_at": journal["created_at"],
        "queue_id": journal["queue_id"],
        "previous_entry_sha256": previous_hash,
        "artifacts": [
            {
                key: item[key] for key in (
                    "artifact_id", "original_name", "source_path", "source_system",
                    "provided_by", "acquisition_method", "sha256", "size",
                    "ingest_utc", "stored_path",
                )
            }
            for item in journal["items"]
        ],
    }
    entry = {**payload, "entry_sha256": _canonical_sha256(payload)}
    _, file_mode = _modes()
    with CUSTODY_MANIFEST.open("a", encoding="utf-8", newline="\n") as handle:
        CUSTODY_MANIFEST.chmod(file_mode)
        handle.write(json.dumps(entry, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    _fsync_dir(CUSTODY_MANIFEST.parent)
    return entry["entry_sha256"]


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temp_path.chmod(mode)
        os.replace(temp_path, path)
        _fsync_dir(path.parent)
    finally:
        temp_path.unlink(missing_ok=True)


def _atomic_write_json(path: Path, value: dict) -> None:
    _, file_mode = _modes()
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temp_path.chmod(file_mode)
        os.replace(temp_path, path)
        _fsync_dir(path.parent)
    finally:
        temp_path.unlink(missing_ok=True)


@contextmanager
def intake_lock():
    ensure_secure_directories()
    _, file_mode = _modes()
    if LOCK_FILE.is_symlink():
        raise RuntimeError("Intake lock must not be a symlink")
    with LOCK_FILE.open("a+", encoding="utf-8") as handle:
        LOCK_FILE.chmod(file_mode)
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _next_id(content: str, prefix: str, width: int) -> str:
    ids = re.findall(rf"{re.escape(prefix)}-(\d{{{width}}})", content)
    number = max((int(value) for value in ids), default=0) + 1
    if number >= 10 ** width:
        raise RuntimeError(f"{prefix} identifier space exhausted at {width} digits")
    return f"{prefix}-{number:0{width}d}"


def next_artifact_id(content: str | None = None) -> str:
    if content is None:
        content = EVIDENCE_INDEX.read_text(encoding="utf-8") if EVIDENCE_INDEX.exists() else ""
    return _next_id(content, "ART", 4)


def next_queue_id(content: str | None = None) -> str:
    if content is None:
        content = REVIEW_QUEUE.read_text(encoding="utf-8") if REVIEW_QUEUE.exists() else ""
    return _next_id(content, "RQ", 3)


def _unique_stored_path(base_name: str, reserved: set[str]) -> Path:
    candidate = base_name
    counter = 2
    while candidate in reserved or (ARTIFACTS_DIR / candidate).exists():
        path = Path(base_name)
        candidate = f"{path.stem}__{counter}{path.suffix}"
        counter += 1
    reserved.add(candidate)
    return ARTIFACTS_DIR / candidate


def _artifact_entry(item: dict) -> str:
    safe = {key: _markdown_value(value) for key, value in item.items()}
    return f"""
### {safe['artifact_id']} — {safe['original_name']} (auto-ingested)

- Artifact ID: `{safe['artifact_id']}`
- Original name: `{safe['original_name']}`
- Source path / system of origin: {safe['source_system']}
- Intake source path: `{safe['source_path']}`
- Provided by: {safe['provided_by']}
- Acquisition method: {safe['acquisition_method']}
- SHA-256: `{safe['sha256']}`
- Copy verified: Yes — re-hash of stored copy matched source digest
- Size: {item['size']:,} bytes
- Ingested (UTC): {safe['ingest_utc']}
- Stored path: `{safe['stored_path']}`
- Related timeline entries: PENDING — analyst review needed
- Relevance: PENDING — analyst review needed
- Handling notes: Auto-ingested. Requires analyst review; artifact content is untrusted data.
"""


def _queue_entry(rq_id: str, items: list[dict], now: str) -> str:
    if len(items) == 1:
        title = f"{items[0]['artifact_id']} — {_markdown_value(items[0]['original_name'])}"
    else:
        title = f"Batch intake: {items[0]['artifact_id']}–{items[-1]['artifact_id']} ({len(items)} files)"
    artifacts = "\n".join(
        f"  - {item['artifact_id']}: `{_markdown_value(item['original_name'])}`" for item in items
    )
    return f"""
### {rq_id} — {title}

- Added: {now}
- Source: intake.py (atomic auto-intake)
- Artifacts:
{artifacts}
- Status: PENDING
- Checklist:
  - [ ] Assess relevance and write summary for each artifact
  - [ ] Place key events on timeline (if new events discovered)
  - [ ] Record findings (if analytical conclusions exist)
  - [ ] Extract new IOCs (if any)
  - [ ] Update activeContext.md (current objective, blockers)
  - [ ] Regenerate executiveSummary.json (narrative, phases, key findings, status)

"""


def _progress_entry(rq_id: str, items: list[dict], now: str) -> str:
    artifacts = ", ".join(item["artifact_id"] for item in items)
    return f"""
## {now} — Automated evidence intake ({rq_id})

### Completed
- Atomically copied, hashed, re-hashed, indexed, and queued {len(items)} artifact(s).

### Acquisitions
- {artifacts}

### Response Actions Taken
- None. Intake is evidence preservation, not a response action.

### Verification / Checks Run
- SHA-256 source/stored-copy comparison: verified for every listed artifact.

### Pending
- Evidence review queue item `{rq_id}` remains pending; no event time, relevance, finding, or IOC inference was made during intake.
"""


def _insert_before(content: str, marker: str, entry: str) -> str:
    if marker in content:
        return content.replace(marker, entry + "\n" + marker, 1)
    return content.rstrip() + "\n" + entry


def _validate_journal(journal: dict) -> None:
    if not isinstance(journal, dict):
        raise RuntimeError("Intake recovery journal must contain an object")
    if journal.get("schema_version") != 1:
        raise RuntimeError("Unsupported intake recovery journal")
    if not re.fullmatch(r"[0-9a-f]{32}", str(journal.get("transaction_id", ""))):
        raise RuntimeError("Invalid intake recovery transaction ID")
    if not re.fullmatch(r"RQ-\d{3}", str(journal.get("queue_id", ""))):
        raise RuntimeError("Invalid intake recovery queue ID")
    if not all(isinstance(journal.get(key), str) for key in ("created_at", "queue_entry", "progress_entry")):
        raise RuntimeError("Intake recovery journal is missing required transaction text")
    items = journal.get("items")
    if not isinstance(items, list) or not items:
        raise RuntimeError("Intake recovery journal has no artifact items")
    artifacts_root = ARTIFACTS_DIR.absolute()
    incoming_root = INCOMING_DIR.resolve(strict=True)
    for item in items:
        if not isinstance(item, dict) or not re.fullmatch(r"ART-\d{4}", str(item.get("artifact_id", ""))):
            raise RuntimeError("Invalid artifact item in intake recovery journal")
        if not isinstance(item.get("index_entry"), str):
            raise RuntimeError("Invalid evidence-index entry in intake recovery journal")
        if not re.fullmatch(r"[0-9a-f]{64}", str(item.get("sha256", ""))):
            raise RuntimeError("Invalid artifact digest in intake recovery journal")
        pending = Path(str(item.get("pending_path", "")))
        if (
            not pending.is_absolute()
            or pending.parent.absolute() != artifacts_root
            or not pending.name.startswith(".pending-")
            or pending.is_symlink()
        ):
            raise RuntimeError("Unsafe pending path in intake recovery journal")
        stored = Path(str(item.get("stored_path", "")))
        if stored.parent != Path("artifacts") or stored.name in ("", ".", ".."):
            raise RuntimeError("Unsafe stored path in intake recovery journal")
        if not isinstance(item.get("remove_source"), bool):
            raise RuntimeError("Invalid source-removal flag in intake recovery journal")
        if item.get("remove_source") is True:
            identity = item.get("source_identity")
            if not isinstance(identity, dict) or set(identity) != {"device", "inode", "size", "mtime_ns"} or not all(
                isinstance(value, int) for value in identity.values()
            ):
                raise RuntimeError("Invalid source identity in intake recovery journal")
            source = Path(str(item.get("source_path", "")))
            try:
                if source.parent.resolve(strict=True) != incoming_root or source.is_symlink():
                    raise RuntimeError("unsafe source")
            except (OSError, RuntimeError) as exc:
                raise RuntimeError("Unsafe removable source in intake recovery journal") from exc


def _commit_journal(journal: dict, *, prepared_verified: bool = False) -> None:
    _validate_journal(journal)
    _, file_mode = _modes()
    for item in journal["items"]:
        pending = Path(item["pending_path"])
        final = PROJECT_ROOT / item["stored_path"]
        if final.is_symlink():
            raise RuntimeError(f"Refusing symlinked artifact destination during recovery: {final}")
        if pending.exists() and final.exists():
            raise RuntimeError(f"Both pending and final artifact paths exist: {final}")
        if pending.exists():
            if not prepared_verified and sha256_file(pending) != item["sha256"]:
                raise RuntimeError(f"Pending artifact digest changed during recovery: {pending}")
            os.replace(pending, final)
            final.chmod(file_mode)
            _fsync_dir(final.parent)
        elif not final.is_file():
            raise RuntimeError(f"Missing verified artifact during recovery: {final}")
        elif sha256_file(final) != item["sha256"]:
            raise RuntimeError(f"Artifact digest changed during recovery: {final}")

    _ensure_custody_manifest_entry(journal)

    index = EVIDENCE_INDEX.read_text(encoding="utf-8") if EVIDENCE_INDEX.exists() else "# Evidence Index\n\n## Entries\n"
    for item in journal["items"]:
        marker = f"### {item['artifact_id']} "
        if marker not in index:
            index = _insert_before(index, "## Custody Transfers", item["index_entry"])
    _atomic_write_text(EVIDENCE_INDEX, index)

    queue = REVIEW_QUEUE.read_text(encoding="utf-8") if REVIEW_QUEUE.exists() else "# Review Queue\n\n## Pending Review\n\n---\n\n## Done\n"
    if f"### {journal['queue_id']} " not in queue:
        queue = _insert_before(queue, "## Done", journal["queue_entry"])
        queue = queue.replace("(No pending items)\n", "", 1)
    _atomic_write_text(REVIEW_QUEUE, queue)

    progress = PROGRESS.read_text(encoding="utf-8") if PROGRESS.exists() else "# Progress\n\n## Entries\n"
    progress_marker = f"Automated evidence intake ({journal['queue_id']})"
    if progress_marker not in progress:
        progress = progress.rstrip() + "\n" + journal["progress_entry"] + "\n"
    _atomic_write_text(PROGRESS, progress)

    for item in journal["items"]:
        source = Path(item["source_path"])
        if item["remove_source"] and source.exists():
            try:
                unchanged = _stat_identity(source) == item["source_identity"]
            except OSError:
                unchanged = False
            if unchanged:
                source.unlink()
    JOURNAL_FILE.unlink(missing_ok=True)


def recover_pending_transaction() -> bool:
    if not JOURNAL_FILE.exists():
        return False
    if JOURNAL_FILE.is_symlink():
        raise RuntimeError("Intake recovery journal must not be a symlink")
    journal = json.loads(JOURNAL_FILE.read_text(encoding="utf-8"), parse_constant=_reject_nonfinite_json)
    _commit_journal(journal)
    return True


def cleanup_unjournaled_pending_files() -> None:
    """Remove incomplete copies that can never be committed; sources remain intact."""
    if JOURNAL_FILE.exists():
        return
    for pending in ARTIFACTS_DIR.glob(".pending-*"):
        if pending.is_file() or pending.is_symlink():
            pending.unlink(missing_ok=True)


def ingest_files(
    filepaths: list[Path],
    *,
    dry_run: bool = False,
    provided_by: str = "UNVERIFIED — provider not supplied to intake",
    source_system: str = "UNVERIFIED — system of origin not supplied to intake",
    acquisition_method: str = "File transfer into incoming/",
) -> list[dict]:
    lock_context = nullcontext() if dry_run else intake_lock()
    with lock_context:
        if not dry_run:
            recover_pending_transaction()
            cleanup_unjournaled_pending_files()
        index_content = EVIDENCE_INDEX.read_text(encoding="utf-8") if EVIDENCE_INDEX.exists() else ""
        queue_content = REVIEW_QUEUE.read_text(encoding="utf-8") if REVIEW_QUEUE.exists() else ""
        next_art_num = int(next_artifact_id(index_content).split("-")[1])
        reserved: set[str] = set()
        prepared: list[dict] = []
        queue_id: str | None = None
        results: list[dict] = []
        _, file_mode = _modes()

        for candidate in filepaths:
            try:
                source = candidate.resolve(strict=True)
                if not source.is_file():
                    raise OSError("not a regular file")
            except (OSError, RuntimeError) as exc:
                results.append({
                    "error": f"File not found or not a regular file: {candidate} ({exc})",
                    "original_name": candidate.name,
                })
                continue
            now = datetime.now(timezone.utc)
            ingest_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            ingest_name = now.strftime("%Y-%m-%dT%H%M%SZ")
            try:
                source_identity = _stat_identity(source)
                source_hash = sha256_file(source)
                if _stat_identity(source) != source_identity:
                    raise RuntimeError("source changed while it was being hashed")
            except (OSError, RuntimeError) as exc:
                results.append({"error": f"Failed to hash stable source {source}: {exc}", "original_name": source.name})
                continue
            original_name = source.name
            stored_base = f"{ingest_name}__{source_hash[:12]}__{sanitize_filename(original_name)}"
            stored_path = _unique_stored_path(stored_base, reserved)
            if next_art_num >= 10_000:
                results.append({"error": "ART identifier space exhausted", "original_name": original_name})
                continue
            artifact_id = f"ART-{next_art_num:04d}"
            next_art_num += 1
            item = {
                "artifact_id": artifact_id,
                "original_name": original_name,
                "source_path": str(source),
                "source_system": source_system,
                "provided_by": provided_by,
                "acquisition_method": acquisition_method,
                "sha256": source_hash,
                "ingest_utc": ingest_iso,
                "stored_path": str(stored_path.relative_to(PROJECT_ROOT)),
                "size": source_identity["size"],
                "source_identity": source_identity,
                "remove_source": source.parent == INCOMING_DIR.resolve(),
            }
            if dry_run:
                results.append(_public_result(item, dry_run=True, verified=True))
                continue
            if queue_id is None:
                queue_id = next_queue_id(queue_content)

            pending_path = ARTIFACTS_DIR / f".pending-{uuid.uuid4().hex}"
            try:
                with source.open("rb") as src, pending_path.open("xb") as dst:
                    shutil.copyfileobj(src, dst, length=1024 * 1024)
                    dst.flush()
                    os.fsync(dst.fileno())
                pending_path.chmod(file_mode)
                if _stat_identity(source) != source_identity:
                    raise RuntimeError("source changed while it was being copied")
                stored_hash = sha256_file(pending_path)
                if stored_hash != source_hash:
                    quarantine = ARTIFACTS_DIR / f".quarantine-{uuid.uuid4().hex}-{sanitize_filename(original_name)}"
                    os.replace(pending_path, quarantine)
                    quarantine.chmod(file_mode)
                    results.append({
                        "error": f"Hash mismatch; source preserved and copy quarantined at {quarantine.name}",
                        "original_name": original_name,
                        "sha256": source_hash,
                    })
                    continue
            except Exception as exc:
                pending_path.unlink(missing_ok=True)
                results.append({"error": f"Failed to prepare {source}: {exc}", "original_name": original_name})
                continue

            item["pending_path"] = str(pending_path)
            item["index_entry"] = _artifact_entry(item)
            prepared.append(item)
            results.append(_public_result(item, verified=True))

        if dry_run or not prepared:
            return results

        if queue_id is None:
            raise RuntimeError("Review queue ID was not reserved")
        transaction_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        journal = {
            "schema_version": 1,
            "transaction_id": uuid.uuid4().hex,
            "created_at": transaction_time,
            "queue_id": queue_id,
            "items": prepared,
            "queue_entry": _queue_entry(queue_id, prepared, transaction_time),
            "progress_entry": _progress_entry(queue_id, prepared, transaction_time),
        }
        try:
            _atomic_write_json(JOURNAL_FILE, journal)
            _commit_journal(journal, prepared_verified=True)
        except Exception:
            if not JOURNAL_FILE.exists():
                for item in prepared:
                    Path(item["pending_path"]).unlink(missing_ok=True)
            raise
        return results


def ingest_file(filepath: Path, dry_run: bool = False, **metadata) -> dict:
    """Compatibility wrapper; a single-file call still commits queue/progress."""
    return ingest_files([filepath], dry_run=dry_run, **metadata)[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Atomically ingest incident evidence")
    parser.add_argument("files", nargs="*", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--provided-by", default="UNVERIFIED — provider not supplied to intake")
    parser.add_argument("--source-system", default="UNVERIFIED — system of origin not supplied to intake")
    parser.add_argument("--acquisition-method", default="File transfer into incoming/")
    args = parser.parse_args()

    if args.files:
        files = args.files
    elif INCOMING_DIR.exists():
        files = sorted(path for path in INCOMING_DIR.iterdir() if path.is_file() and not path.name.startswith("."))
    else:
        files = []
    if not files:
        print("No files to process.")
        return

    results = ingest_files(
        files,
        dry_run=args.dry_run,
        provided_by=args.provided_by,
        source_system=args.source_system,
        acquisition_method=args.acquisition_method,
    )
    ok = 0
    for result in results:
        if "error" in result:
            print(f"✗ {result.get('original_name', 'file')}: {result['error']}")
            continue
        ok += 1
        status = "WOULD INGEST" if args.dry_run else "✓ VERIFIED"
        print(f"{status}: {result['artifact_id']} — {result['original_name']}")
        print(f"  SHA-256: {result['sha256']}")
        print(f"  Ingested: {result['ingest_utc']}")
        print(f"  Stored: {result['stored_path']}")
    action = "would ingest" if args.dry_run else "ingested"
    print(f"Summary: {ok} {action}, {len(results) - ok} failed")
    if ok and not args.dry_run:
        print("Analysis remains pending in memory-bank/reviewQueue.md.")


if __name__ == "__main__":
    main()
