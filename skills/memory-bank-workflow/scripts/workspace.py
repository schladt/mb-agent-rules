#!/usr/bin/env python3
"""Explicit local memory-bank workflows. Python standard library only."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from urllib.parse import quote, unquote


PROFILES = {
    "pentest": ("projectBrief", "scopeAuthorization", "targets", "findings", "evidenceIndex"),
    "incident-response": ("incidentBrief", "scopeAuthorization", "affectedAssets", "timeline", "indicators", "findings", "evidenceIndex", "reviewQueue"),
    "academic-research": ("researchBrief", "methodology", "researchQuestions", "sourcesIndex", "literatureNotes", "openQuestions"),
    "general-project": ("projectBrief", "requirements", "decisions", "risks", "handoff"),
}
COMMON = ("activeContext", "progress", "sensitiveDataPolicy", "project-status")
SECTIONS = ("Progress", "Milestones", "Blockers", "Next Steps", "Client Actions")
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
SENSITIVE = (
    ("credential indicator", re.compile(r"(?i)(?:password|passwd|secret|api[_-]?key|access[_-]?token|authorization)\s*[:=]|\bBearer\s+\S+|-----BEGIN (?:[A-Z ]*PRIVATE KEY)-----|\bAKIA[A-Z0-9]{16}\b|\bgh[pousr]_[A-Za-z0-9]{20,}")),
    ("email/PII indicator", re.compile(r"\b[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("network address indicator", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b|(?<!\w)(?:[0-9a-fA-F]{0,4}:){2,}[0-9a-fA-F:]{0,4}(?!\w)")),
    ("internal store reference", re.compile(r"(?i)\.memory-bank[/\\]|(?:^|[\s(/])(?:artifacts|sensitive|incoming)[/\\]")),
)


class WorkflowError(Exception):
    """A deliberately nonsecret diagnostic, never a raw exception string."""


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(2, "error: invalid command arguments; use --help for the required options.\n")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def hash_file(path):
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def identity(path):
    info = path.stat()
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def safe_path(root, value, *, root_alias=None):
    """Canonicalize only the declared root; reject traversal and child symlinks."""
    alias = Path(os.path.abspath(root if root_alias is None else root_alias))
    root = Path(root).resolve(strict=True)
    path = Path(value)
    if ".." in path.parts:
        raise WorkflowError("path must not contain parent traversal")
    if not path.is_absolute():
        path = root / path
    elif path.is_relative_to(alias):
        path = root / path.relative_to(alias)
    try:
        relative = path.relative_to(root)
    except ValueError:
        raise WorkflowError("path must remain inside the project root") from None
    cursor = root
    for part in relative.parts:
        cursor /= part
        if cursor.is_symlink():
            raise WorkflowError("symlink paths are not accepted by workspace commands")
    return path


def secure_directory(root, path):
    path = safe_path(root, path)
    missing = []
    current = path
    while not current.exists():
        missing.append(current)
        current = current.parent
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)
    if not path.is_dir():
        raise WorkflowError("required workspace directory is not a directory")


def stage(root, path, content, mode=0o600):
    path = safe_path(root, path)
    secure_directory(root, path.parent)
    if path.exists() and not path.is_file():
        raise WorkflowError("output destination is not a regular file")
    if path.exists():
        mode = stat.S_IMODE(path.stat().st_mode)
    descriptor, name = tempfile.mkstemp(prefix=".workspace-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return temporary


def atomic_write(root, path, content, mode=0o600):
    temporary = stage(root, path, content, mode)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def load_json(path, default=None):
    if not path.exists() and default is not None:
        return default
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError):
        raise WorkflowError("workspace metadata is malformed; preserve it and repair before retrying") from None
    if not isinstance(value, dict):
        raise WorkflowError("workspace metadata must be an object")
    return value


@contextmanager
def mutation_lock(root):
    """An interrupted writer leaves a visible lock; never guess it is safe to steal."""
    runtime = safe_path(root, ".memory-bank/runtime")
    secure_directory(root, runtime)
    lock = safe_path(root, runtime / "workspace.lock")
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise WorkflowError("workspace writer lock exists; stop the other writer, or confirm crash recovery before removing .memory-bank/runtime/workspace.lock") from None
    try:
        os.close(descriptor)
        yield
    finally:
        lock.unlink(missing_ok=True)


def commit_documents(root, changes):
    """Stage every document, retain rollback copies, then atomically replace each."""
    originals = {path: path.read_bytes() if path.exists() else None for path in changes}
    staged = {}
    backup = None
    committed = []
    try:
        for path, data in changes.items():
            staged[path] = stage(root, path, data)
        backups = safe_path(root, ".memory-bank/backups")
        secure_directory(root, backups)
        backup = Path(tempfile.mkdtemp(prefix="workflow-", dir=backups))
        manifest = []
        for index, (path, content) in enumerate(originals.items()):
            manifest.append({"path": str(path.relative_to(root)), "existed": content is not None, "backup": str(index) if content is not None else None})
            if content is not None:
                atomic_write(root, backup / str(index), content)
        atomic_write(root, backup / "manifest.json", json_bytes({"files": manifest}))
        for path, temporary in staged.items():
            if (path.read_bytes() if path.exists() else None) != originals[path]:
                raise WorkflowError("a workspace document changed during the operation; retry after reconciling edits")
            os.replace(temporary, path)
            committed.append(path)
    except BaseException:
        rollback_failed = False
        for path in reversed(committed):
            previous = originals[path]
            try:
                if previous is None:
                    path.unlink(missing_ok=True)
                else:
                    atomic_write(root, path, previous)
            except (OSError, WorkflowError):
                rollback_failed = True
        if rollback_failed:
            raise WorkflowError("document update and rollback failed; original bytes remain in .memory-bank/backups/workflow-*/; reconcile before retrying") from None
        raise
    finally:
        for temporary in staged.values():
            temporary.unlink(missing_ok=True)
    return backup


def project_root(value):
    if value:
        return Path(value).resolve(strict=True)
    try:
        result = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return Path.cwd().resolve()
    return Path(result.stdout.strip()).resolve() if result.returncode == 0 else Path.cwd().resolve()


def layout(root, explicit=None):
    bank = safe_path(root, ".memory-bank")
    if not bank.is_dir():
        raise WorkflowError(".memory-bank is missing; initialize or migrate it before using workspace commands")
    metadata = load_json(safe_path(root, bank / "layout.json"), {})
    profile = metadata.get("profile", explicit)
    if explicit and metadata.get("profile") not in (None, explicit):
        raise WorkflowError("explicit profile conflicts with installed layout metadata")
    if profile not in PROFILES:
        raise WorkflowError("profile is unavailable; use installed layout metadata or explicit --profile")
    if metadata and metadata.get("schema") != 1:
        raise WorkflowError("unsupported layout metadata schema")
    external = metadata.get("external_status", profile in ("pentest", "incident-response"))
    if not isinstance(external, bool):
        raise WorkflowError("external_status metadata must be a boolean")
    return bank, profile, external


def publication(source):
    """Strict positive selection; internal text is never a fallback."""
    lines = source.splitlines()
    expected = ["# Project Status", "## Publishable", *("### " + section for section in SECTIONS), "## Internal"]
    position = 0
    selected = {section: [] for section in SECTIONS}
    selected_lines = []
    section = None
    for number, line in enumerate(lines, 1):
        if position == len(expected):
            # Structural public markers cannot be duplicated in the internal tail.
            if line in expected:
                raise WorkflowError("status grammar contains duplicate required headings")
            continue
        if line.startswith("#"):
            if line != expected[position]:
                raise WorkflowError("status grammar requires the exact ordered publishable headings")
            if line.startswith("### "):
                section = line[4:]
            if line == "## Internal":
                section = None
            position += 1
        elif section is not None:
            if line.lstrip().startswith(("#", "```", "~~~")):
                raise WorkflowError("publishable status supports ordinary paragraphs and bullets, not headings or code fences")
            selected[section].append(line)
            selected_lines.append((number, line))
        elif line.strip():
            raise WorkflowError("status text must be inside the named publishable sections or Internal")
    if position != len(expected) or any(not "\n".join(value).strip() for value in selected.values()):
        raise WorkflowError("status grammar is incomplete or contains an empty publishable section")
    output = "# Project Status\n\n" + "\n\n".join("## " + section + "\n\n" + "\n".join(selected[section]).strip() for section in SECTIONS) + "\n"
    warnings = []
    for number, line in selected_lines:
        for category, pattern in SENSITIVE:
            if pattern.search(line):
                warnings.append({"line": number, "category": category})
    return output.encode("utf-8"), warnings


def status_command(root, args, bank, external):
    if not external:
        raise WorkflowError("outward status is disabled; enable --external-status with the installer before generation")
    source = safe_path(root, bank / "project-status.md")
    target = safe_path(root, "project-status.md")
    receipt_path = safe_path(root, bank / "runtime/status-receipt.json")
    receipt = load_json(receipt_path, {})
    source_hash = None
    try:
        content = source.read_bytes()
        source_hash = digest(content)
        try:
            rendered, warnings = publication(content.decode("utf-8"))
        except UnicodeError:
            raise WorkflowError("status source is not UTF-8") from None
        for warning in warnings:
            print(f"warning: .memory-bank/project-status.md:{warning['line']}: {warning['category']}; review publishable content", file=sys.stderr)
        output_hash = digest(rendered)
        if args.check:
            current = (receipt.get("state") == "generated" and receipt.get("source_sha256") == source_hash and receipt.get("output_sha256") == output_hash and target.is_file() and hash_file(target) == output_hash)
            print("Status projection is current; heuristic warnings are not a sanitization guarantee." if current else "Status projection is stale or absent; run status to regenerate. Previous output is not certified current.")
            return 0 if current else 1
        if source.read_bytes() != content:
            raise WorkflowError("status source changed during generation; previous output retained")
        updated = {"schema": 1, "state": "generated", "source_sha256": source_hash, "output_sha256": output_hash, "generated_at": now(), "source_modified_at": datetime.fromtimestamp(source.stat().st_mtime, timezone.utc).isoformat(), "warnings": warnings}
        # Both writes are staged first; failures restore the prior outward document.
        commit_documents(root, {target: rendered, receipt_path: json_bytes(updated)})
        print("Generated project-status.md from publishable fields only. No upload performed; review warnings before sharing.")
        return 0
    except (WorkflowError, OSError, ValueError) as error:
        if not args.check:
            failed = dict(receipt)
            failed.update({"schema": 1, "state": "failed", "attempted_at": now(), "attempted_source_sha256": source_hash, "error": "generation-failed"})
            try:
                atomic_write(root, receipt_path, json_bytes(failed))
            except OSError:
                pass
        if isinstance(error, WorkflowError):
            raise
        raise WorkflowError("status generation failed; prior output retained; receipt or output may be stale") from None


def valid_date(value):
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise WorkflowError("date must be YYYY-MM-DD") from None
    if parsed.isoformat() != value:
        raise WorkflowError("date must be YYYY-MM-DD")
    return value


def cognitive_paths(root, bank, profile):
    names = (*COMMON, *PROFILES[profile])
    metadata = load_json(safe_path(root, bank / "layout.json"), {})
    if profile == "general-project" and metadata.get("findings") is True:
        names += ("findings",)
    return [safe_path(root, bank / (name + ".md")) for name in names]


def active_plans(root, planning):
    result = []
    for directory, dirs, files in os.walk(planning, followlinks=False):
        dirs[:] = sorted(name for name in dirs if name != "archive" and not (Path(directory) / name).is_symlink())
        result.extend(safe_path(root, Path(directory) / name) for name in sorted(files) if name.endswith(".md"))
    return result


def moved_references(text, document, root, source, target, *, directory=False, code_paths=True):
    old = source.relative_to(root).as_posix()
    new = target.relative_to(root).as_posix()
    # Preserve dated/history prose; only the current link targets/code path references change.
    if code_paths:
        if directory:
            text = re.sub(r"`" + re.escape(old) + r"(/[^`\n]*)?`",
                          lambda match: "`" + new + (match.group(1) or "") + "`", text)
        else:
            text = text.replace("`" + old + "`", "`" + new + "`")
    pattern = re.compile(r"(?P<prefix>\]\(|^\s*\[[^]\n]+\]:\s*)(?P<angle><)?(?P<url>[^\s)>]+)(?P<close>>)?", re.MULTILINE)
    def replace(match):
        url = match.group("url")
        path_part, separator, fragment = url.partition("#")
        if re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", path_part):
            return match.group(0)
        decoded = unquote(path_part)
        candidate = Path(os.path.abspath(document.parent / decoded))
        if decoded.lstrip("/") == old:
            destination = ("/" if decoded.startswith("/") else "") + new
        elif directory and decoded.lstrip("/").startswith(old + "/"):
            destination = ("/" if decoded.startswith("/") else "") + new + decoded.lstrip("/")[len(old):]
        elif candidate == source:
            destination = os.path.relpath(target, document.parent)
        elif directory and candidate.is_relative_to(source):
            destination = os.path.relpath(target / candidate.relative_to(source), document.parent)
        else:
            return match.group(0)
        if "%" in path_part:
            destination = quote(destination, safe="/.-_")
        return match.group("prefix") + (match.group("angle") or "") + destination + separator + fragment + (match.group("close") or "")
    return pattern.sub(replace, text)


def archive_command(root, args, bank, profile):
    source = safe_path(root, args.path)
    planning = safe_path(root, bank / "planning")
    archive = safe_path(root, planning / "archive")
    if not source.is_relative_to(planning) or source.is_relative_to(archive) or source.suffix != ".md" or not source.is_file():
        raise WorkflowError("archive-plan requires an active Markdown plan under .memory-bank/planning")
    stamp = valid_date(args.date)
    secure_directory(root, archive)
    target = safe_path(root, archive / f"{stamp}-{source.name}")
    serial = 2
    while target.exists():
        target = safe_path(root, archive / f"{stamp}-{source.stem}-{serial}.md")
        serial += 1
    source_content = source.read_bytes()
    candidates = cognitive_paths(root, bank, profile) + active_plans(root, planning) + [safe_path(root, bank / "references/reference.md")]
    changes = {target: source_content}
    progress = safe_path(root, bank / "progress.md")
    if not progress.is_file():
        raise WorkflowError("progress.md is required before plan archival")
    for path in dict.fromkeys(candidates):
        if path == source or not path.exists():
            continue
        original = path.read_text(encoding="utf-8")
        updated = moved_references(original, path, root, source, target)
        if updated != original:
            changes[path] = updated.encode("utf-8")
    old_path = source.relative_to(root).as_posix()
    new_path = target.relative_to(root).as_posix()
    progress_text = changes.get(progress, progress.read_bytes()).decode("utf-8")
    progress_text += f"\n## {stamp} — Plan completed and archived\n\n- Previous path: `{old_path}`\n- Archived path: `{new_path}`\n- Original plan content and prior history preserved.\n"
    changes[progress] = progress_text.encode("utf-8")
    if source.read_bytes() != source_content:
        raise WorkflowError("plan changed during archival; source retained")
    commit_documents(root, changes)
    if source.read_bytes() != source_content:
        raise WorkflowError("plan changed before removal; source and archived copy retained; reconcile references")
    source.unlink()
    print("Plan archived; cognitive/active-plan/reference links and progress updated. Original history retained in archive and transaction backups.")
    return 0


def one_line(value):
    if not value.strip() or any(ord(character) < 32 for character in value):
        raise WorkflowError("metadata fields must be nonempty single-line values")
    return value


def markdown_value(value):
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("`", "&#96;")


def override_block(record, revoked=False):
    heading = f"\n### Project override `{record['id']}` — {'revoked' if revoked else 'confirmed'} {record['date']}\n\n"
    fields = (("Confirmed by", "confirmed_by"), ("Reason", "reason")) if revoked else (("Safe default", "default"), ("Risk disclosed", "risk"), ("Authorized action", "action"), ("Exact scope", "scope"), ("Confirmed by", "confirmed_by"))
    body = "".join(f"- {label}: {markdown_value(record[key])}\n" for label, key in fields)
    return heading + body + ("- State: Revoked; the safe default applies again.\n" if revoked else "- Lifetime: Project-wide until explicitly revoked; no broader risk or scope is authorized.\n")


def check_override_authority(paths, identifier, existing):
    """Derived registry state cannot outrank later or edited authority history."""
    history = existing.get("history") if existing else []
    if not isinstance(history, list) or (existing and not history) or any(not isinstance(block, str) or not block.strip() for block in history):
        raise WorkflowError("override registry history is unavailable; reconcile it with authority/context before proceeding")
    heading = re.compile(r"^### Project override `" + re.escape(identifier) + r"` — (?:confirmed|revoked) [^\n]+$", re.MULTILINE)
    for path in paths:
        if not path.is_file():
            raise WorkflowError("both activeContext and the named authority file must exist")
        text = path.read_text(encoding="utf-8")
        events = list(heading.finditer(text))
        if len(events) != len(history) or any(not text[event.start():].startswith(block.lstrip("\n")) for event, block in zip(events, history)):
            raise WorkflowError("override registry conflicts with authority/context history; a later revocation or manual change must be reconciled without granting or restoring permission")


def override_command(root, args, bank):
    if not args.confirm:
        raise WorkflowError("override changes require explicit owner confirmation (--confirm)")
    if not SLUG.fullmatch(args.id):
        raise WorkflowError("override id must be a lowercase hyphenated slug")
    registry_path = safe_path(root, bank / "runtime/overrides.json")
    registry = load_json(registry_path, {"schema": 1, "overrides": {}})
    entries = registry.get("overrides")
    if registry.get("schema") != 1 or not isinstance(entries, dict):
        raise WorkflowError("override registry is malformed")
    active = safe_path(root, bank / "activeContext.md")
    existing = entries.get(args.id)
    record = {"id": args.id, "date": valid_date(args.date), "confirmed_by": one_line(args.confirmed_by)}
    if args.operation == "record":
        policy = safe_path(root, args.policy)
        if policy.parent != bank or policy.suffix != ".md" or policy.name in ("activeContext.md", "progress.md", "project-status.md"):
            raise WorkflowError("override policy must be the relevant root cognitive authority file, not a working-state file")
        record.update({key: one_line(getattr(args, key)) for key in ("default", "risk", "action", "scope")})
        record["policy"] = policy.relative_to(root).as_posix()
        if existing and existing.get("policy") != record["policy"]:
            raise WorkflowError("override id belongs to a different authority file; use a new id after confirmation")
        check_override_authority((active, policy), args.id, existing)
        block = override_block(record)
        if existing and existing.get("state") == "active":
            if any(existing.get(key) != record[key] for key in ("policy", "default", "risk", "action", "scope", "confirmed_by")):
                raise WorkflowError("active override id has a different scope; revoke it or use a new id after confirmation")
            if existing["block"] != existing["history"][-1]:
                raise WorkflowError("override registry state conflicts with its history; reconcile without granting permission")
            print("Exact override already active; no duplicate record or new authorization created.")
            return 0
        if existing and existing.get("state") != "revoked":
            raise WorkflowError("override registry state is invalid; reconcile before recording")
        record.update({"state": "active", "block": block, "history": [*(existing["history"] if existing else []), block]})
        entries[args.id] = record
    else:
        if not existing or existing.get("state") != "active":
            raise WorkflowError("override is not active; no revocation performed")
        policy = safe_path(root, existing["policy"])
        check_override_authority((active, policy), args.id, existing)
        record["reason"] = one_line(args.reason)
        block = override_block(record, revoked=True)
        existing.update({"state": "revoked", "revocation": record})
        existing["history"].append(block)
    changes = {path: (path.read_text(encoding="utf-8").rstrip() + "\n" + block).encode("utf-8") for path in (active, policy)}
    changes[registry_path] = json_bytes(registry)
    commit_documents(root, changes)
    print("Override confirmation recorded in activeContext and authority." if args.operation == "record" else "Override revoked in activeContext and authority; confirmation history preserved.")
    return 0


def copy_verified(root, source, target, expected, source_identity):
    secure_directory(root, target.parent)
    descriptor, name = tempfile.mkstemp(prefix=".workspace-copy-", dir=target.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as output, source.open("rb") as incoming:
            os.fchmod(output.fileno(), 0o600)
            for block in iter(lambda: incoming.read(1024 * 1024), b""):
                output.write(block)
            output.flush()
            os.fsync(output.fileno())
        if hash_file(temporary) != expected or identity(source) != source_identity or hash_file(source) != expected:
            raise WorkflowError("source or stored copy changed; source retained")
        if target.exists():
            if not target.is_file() or hash_file(target) != expected:
                raise WorkflowError("destination collision; source retained")
        else:
            os.replace(temporary, target)
        if hash_file(target) != expected:
            raise WorkflowError("stored copy verification failed; source retained")
    finally:
        temporary.unlink(missing_ok=True)


def custody_acquire(root, source, origin, expected):
    script = safe_path(root, "scripts/intake.py")
    if not script.is_file():
        raise WorkflowError("IR custody intake is not installed; run memory-bank-ir-dashboard setup or the profile's authorized manual custody procedure. Source retained; generic artifact routing is not a substitute")
    result = subprocess.run([sys.executable, str(script), "--retain-source", "--json", "--source-system", origin, str(source)], cwd=root, capture_output=True, text=True, check=False)
    try:
        payload = json.loads(result.stdout)
        items = payload["results"]
        if result.returncode or payload["failed"] != 0 or len(items) != 1:
            raise ValueError
        item = items[0]
        stored = safe_path(root, item["stored_path"])
        if not stored.is_relative_to(root / ".memory-bank/artifacts") or item["verified"] is not True or item["sha256"] != expected or hash_file(stored) != expected or not re.fullmatch(r"ART-\d{4}", item["artifact_id"]):
            raise ValueError
    except (ValueError, KeyError, TypeError, OSError):
        raise WorkflowError("IR custody intake failed or returned no verified acquisition receipt; source retained; inspect custody state without bypassing it") from None
    return stored, item["artifact_id"]


def pending_counts(root, bank):
    incoming = safe_path(root, bank / "incoming")
    counts = {"files": 0, "directories": 0, "symlinks": 0, "hidden": 0, "unreadable": 0}
    def inaccessible(error):
        counts["unreadable"] += 1
    for directory, dirs, files in os.walk(incoming, followlinks=False, onerror=inaccessible):
        for name in dirs + files:
            path = Path(directory) / name
            if name == ".gitkeep" and path.is_file() and not path.is_symlink() and path.stat().st_size == 0:
                continue
            if name.startswith("."):
                counts["hidden"] += 1
            if path.is_symlink():
                counts["symlinks"] += 1
            elif path.is_dir():
                counts["directories"] += 1
            else:
                counts["files"] += 1
    return counts


def print_pending(root, bank):
    counts = pending_counts(root, bank)
    print("Incoming pending (metadata only): " + ", ".join(f"{key}={value}" for key, value in counts.items()) + ". Retained, hidden, nested and ambiguous drops are not automatically complete.")


def intake_command(root, args, bank, profile):
    source = safe_path(root, args.path)
    incoming = safe_path(root, bank / "incoming")
    if not source.is_relative_to(incoming) or not source.is_file():
        raise WorkflowError("intake requires one explicitly classified regular file under .memory-bank/incoming; nested/hidden drops remain pending until individually selected")
    origin = one_line(args.origin)
    topic = args.topic or args.kind
    if not SLUG.fullmatch(topic):
        raise WorkflowError("topic must be a lowercase hyphenated slug")
    if args.delete and not args.confirm:
        raise WorkflowError("deletion requires --confirm after completed review/promotion and explicit owner approval; source retained")
    ledger_path = safe_path(root, bank / "runtime/intake.json")
    ledger = load_json(ledger_path, {"schema": 1, "items": {}})
    if ledger.get("schema") != 1 or not isinstance(ledger.get("items"), dict):
        raise WorkflowError("intake metadata is malformed; source retained")
    source_identity = identity(source)
    source_hash = hash_file(source)
    if identity(source) != source_identity:
        raise WorkflowError("source changed during hashing; source retained")
    key = digest((str(source.relative_to(root)) + "\0" + source_hash).encode())
    previous = ledger["items"].get(key, {})
    if previous and (previous.get("kind") != args.kind or previous.get("origin") != origin):
        raise WorkflowError("source already has a different classification/origin; reconcile its receipt before rerouting")
    disposition = "archive" if args.archive else "delete" if args.delete else "retain"
    # A failed attempt must not erase the acquisition it is required to validate.
    record = dict(previous)
    record.update({"source": source.relative_to(root).as_posix(), "sha256": source_hash, "kind": args.kind, "origin": origin, "topic": topic, "updated_at": now(), "disposition": disposition, "state": "pending", "analysis": "not assessed by this CLI; acquisition is not analysis", "review_completion_attested": bool(args.delete and args.confirm), "events": list(previous.get("events", []))})
    ledger["items"][key] = record
    try:
        stored = None
        if args.kind != "reference" or args.archive:
            previous_stored = previous.get("stored_path")
            if previous_stored:
                stored = safe_path(root, previous_stored)
                permitted = bank / ("artifacts" if args.kind == "artifact" else "sensitive" if args.kind == "operational" else "references/raw")
                if not stored.is_relative_to(permitted) or hash_file(stored) != source_hash:
                    raise WorkflowError("previous acquisition receipt does not match stored bytes; source retained")
                if profile == "incident-response" and args.kind == "artifact" and not previous.get("artifact_id"):
                    raise WorkflowError("previous artifact lacks IR custody identity; source retained")
                if previous.get("artifact_id"):
                    record["artifact_id"] = previous["artifact_id"]
            elif profile == "incident-response" and args.kind == "artifact":
                stored, record["artifact_id"] = custody_acquire(root, source, origin, source_hash)
            else:
                directory = bank / ("references/raw" if args.kind == "reference" else "sensitive" if args.kind == "operational" else "artifacts")
                destination = safe_path(root, directory / (date.today().isoformat() + "-" + topic))
                stored = safe_path(root, destination / (key[:12] + "-" + source_hash[:12] + ".bin"))
                copy_verified(root, source, stored, source_hash, source_identity)
            record["stored_path"] = stored.relative_to(root).as_posix()
            record["verified_sha256"] = hash_file(stored)
            if record["verified_sha256"] != source_hash:
                raise WorkflowError("acquisition hash mismatch; source retained")
        if identity(source) != source_identity or hash_file(source) != source_hash:
            raise WorkflowError("source changed before disposition; source retained")
        record["state"] = "retained-pending-disposition" if disposition == "retain" else "disposition-authorized"
        record["events"].append({"at": record["updated_at"], "disposition": disposition, "state": record["state"]})
        # Commit provenance/consent before unlink. A crash leaves the actual source visible.
        atomic_write(root, ledger_path, json_bytes(ledger))
        if disposition != "retain":
            if identity(source) != source_identity or hash_file(source) != source_hash:
                raise WorkflowError("source changed after receipt write; source retained")
            source.unlink()
    except (OSError, WorkflowError, ValueError) as error:
        record["state"] = "failed-source-retained"
        record["events"].append({"at": now(), "state": record["state"], "error": "intake-failed"})
        try:
            atomic_write(root, ledger_path, json_bytes(ledger))
        except OSError:
            pass
        if isinstance(error, WorkflowError):
            raise
        raise WorkflowError("intake could not complete; source retained; inspect internal receipts and acquired copies before retrying") from None
    print("Intake disposition recorded; source retained visibly pending." if disposition == "retain" else "Approved source disposition completed; provenance/hash receipt retained internally.")
    if profile == "incident-response" and args.kind == "artifact":
        print("IR custody preserved; evidence analysis remains pending in reviewQueue.md.")
    return 0


def make_parser():
    parser = Parser(description=__doc__)
    parser.add_argument("--root", help="Project root; defaults to git root or cwd")
    parser.add_argument("--profile", choices=tuple(PROFILES), help="Explicit profile when layout metadata is absent")
    commands = parser.add_subparsers(dest="command", required=True)
    status = commands.add_parser("status", help="Generate the explicit publishable status projection")
    status.add_argument("--check", action="store_true", help="Read-only staleness check; exit 1 when stale")
    archive = commands.add_parser("archive-plan", help="Archive a completed plan and repair active references")
    archive.add_argument("path")
    archive.add_argument("--date", default=date.today().isoformat())
    intake = commands.add_parser("intake", help="Classify one incoming file and record explicit disposition")
    intake.add_argument("path")
    intake.add_argument("--kind", required=True, choices=("reference", "operational", "artifact"))
    intake.add_argument("--origin", required=True, help="Nonsecret provenance description; never a credential value")
    intake.add_argument("--topic")
    disposition = intake.add_mutually_exclusive_group()
    disposition.add_argument("--archive", action="store_true", help="Approve verified archival/routing and removal from incoming")
    disposition.add_argument("--delete", action="store_true", help="Approve source deletion after review and required preservation")
    disposition.add_argument("--retain", action="store_true", help="Retain the source visibly pending (default)")
    intake.add_argument("--confirm", action="store_true", help="Attest owner-approved deletion and completed review/promotion")
    commands.add_parser("intake-pending", help="Count pending incoming entries without reading raw contents")
    override = commands.add_parser("override", help="Persist or revoke a precise repo-owned policy exception")
    operations = override.add_subparsers(dest="operation", required=True)
    for name in ("record", "revoke"):
        operation = operations.add_parser(name)
        operation.add_argument("--id", required=True)
        operation.add_argument("--confirmed-by", required=True)
        operation.add_argument("--date", default=date.today().isoformat())
        operation.add_argument("--confirm", action="store_true")
        if name == "record":
            for field in ("policy", "default", "risk", "action", "scope"):
                operation.add_argument("--" + field, required=True)
        else:
            operation.add_argument("--reason", required=True)
    return parser


def main(argv=None):
    args = make_parser().parse_args(argv)
    try:
        root = project_root(args.root)
        for field in ("path", "policy"):
            if getattr(args, field, None) is not None:
                setattr(args, field, safe_path(root, getattr(args, field), root_alias=args.root))
        bank, profile, external = layout(root, args.profile)
        if args.command == "intake-pending":
            print_pending(root, bank)
            return 0
        if args.command == "status" and args.check:
            return status_command(root, args, bank, external)
        with mutation_lock(root):
            if args.command == "status":
                return status_command(root, args, bank, external)
            if args.command == "archive-plan":
                return archive_command(root, args, bank, profile)
            if args.command == "override":
                return override_command(root, args, bank)
            return intake_command(root, args, bank, profile)
    except WorkflowError as error:
        print("error: " + str(error), file=sys.stderr)
        return 2
    except (OSError, ValueError, UnicodeError, TypeError, KeyError, AttributeError, IndexError):
        print("error: workspace I/O or metadata failure; raw values suppressed. Preserve sources and inspect internal receipts/backups before retrying.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
