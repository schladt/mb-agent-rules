#!/usr/bin/env python3
"""Tool-neutral finding promotion, status synchronization and warning-only preflight."""
import argparse
from datetime import datetime, timezone
import html
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import quote, unquote, urlsplit


PENTEST_STATES = {"Hypothesis", "Validated", "Informational", "False Positive"}
IR_STATES = {"Suspected", "Confirmed", "Ruled Out"}
STATUS = re.compile(r"^\*\*Status:\*\*[ \t]*(?:`([^`\n]+)`|([^\n]+))", re.M)
TITLE = re.compile(r"^# (.+)$", re.M)
FIELDS = re.compile(r"^- ([^:\n]+):[ \t]*(.*)$", re.M)
SECTIONS = ["## Affected Assets", "## Description", "### Affected assets",
            "### Steps to reproduce / observed behavior", "## Impact",
            "## Remediation", "## References"]
METRICS = {
    "AV": ("Attack Vector", {"N": "Network", "A": "Adjacent", "L": "Local", "P": "Physical"}),
    "AC": ("Attack Complexity", {"L": "Low", "H": "High"}),
    "PR": ("Required Privileges", {"N": "None", "L": "Low", "H": "High"}),
    "UI": ("User Interaction", {"N": "None", "R": "Required"}),
    "S": ("Scope", {"U": "Unchanged", "C": "Changed"}),
    "C": ("Confidentiality", {"N": "None", "L": "Low", "H": "High"}),
    "I": ("Integrity", {"N": "None", "L": "Low", "H": "High"}),
    "A": ("Availability", {"N": "None", "L": "Low", "H": "High"}),
}
SECRET_PATTERNS = [
    ("private-key material", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("credential assignment", re.compile(r"(?i)\b(?:password|passwd|api[_-]?key|access[_-]?token|secret)\s*[:=]\s*[\"'`]?[^\s<>\"'`]{6,}")),
    ("access-key identifier", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("bearer credential", re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]{12,}")),
    ("email-like personal data", re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")),
    ("government-identifier-like data", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
]


class FindingError(Exception):
    pass


def inside(path, parent):
    return path.resolve().is_relative_to(parent.resolve())


def has_symlink_component(path, root):
    """Inspect lexical components before resolve() can hide an alias."""
    while path != root and path != path.parent:
        if path.is_symlink():
            return True
        path = path.parent
    return False


def read_text(path):
    return path.read_text(encoding="utf-8")


def atomic_write(path, text, mode=None):
    """Replace one file without truncating its previous contents on write failure."""
    previous_mode = path.stat().st_mode & 0o777 if path.exists() else (mode or 0o644)
    fd, temporary = tempfile.mkstemp(prefix=".findings-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, previous_mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def root_path(value):
    if value:
        return Path(value).resolve(strict=True)
    try:
        result = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    except FileNotFoundError:
        return Path.cwd().resolve()
    return Path(result.stdout.strip()).resolve() if result.returncode == 0 else Path.cwd().resolve()


def profile_for(root, explicit):
    metadata = root / ".memory-bank/layout.json"
    layout = json.loads(read_text(metadata)) if metadata.exists() else {}
    if not isinstance(layout, dict):
        raise FindingError("layout.json must be an object")
    if explicit and layout.get("profile") not in (None, explicit):
        raise FindingError("explicit profile conflicts with installed layout metadata")
    profile = explicit or layout.get("profile")
    if profile not in {"pentest", "incident-response", "general-project"}:
        raise FindingError("findings require explicit --profile or supported layout.json profile")
    if layout.get("findings") is False or (profile == "general-project" and not layout.get("findings")):
        raise FindingError("findings workflow is not enabled in layout.json")
    if (root / "findings").is_symlink() or (root / ".memory-bank").is_symlink():
        raise FindingError("findings and memory-bank roots must not be symlinks")
    return profile


def status_of(text):
    match = STATUS.search(text)
    return (match.group(1) or match.group(2)).strip() if match else None


def title_of(text):
    match = TITLE.search(text)
    return match.group(1) if match else None


def log_entries(text):
    """Parse only Entries, retaining byte offsets so history remains untouched."""
    section = re.search(r"^## Entries\s*$", text, re.M)
    if not section:
        raise FindingError("working log requires a ## Entries section")
    end = re.search(r"^## ", text[section.end():], re.M)
    stop = section.end() + end.start() if end else len(text)
    headings = list(re.finditer(r"^### (.+)$", text[section.end():stop], re.M))
    entries = {}
    for index, heading in enumerate(headings):
        start = section.end() + heading.start()
        finish = section.end() + headings[index + 1].start() if index + 1 < len(headings) else stop
        title = re.sub(r"^F-\d+:\s*", "", heading.group(1)).strip()
        if title in entries:
            raise FindingError("working log contains duplicate finding titles")
        body = text[start:finish]
        fields = {}
        for field in FIELDS.finditer(body):
            key, value = field.groups()
            if key in {"Status", "Report path"} and key in fields:
                raise FindingError("working log contains duplicate status or report-path fields")
            fields[key] = value.strip().strip("`")
        state = fields.get("Status", "")
        state_match = re.match(r"`?([^`]+)`", state)
        if state_match:
            state = state_match.group(1)
        entries[title] = {"title": title, "status": state, "path": parse_report_path(fields.get("Report path", "")),
                          "start": start, "end": finish, "body": body}
    return entries


def parse_report_path(value):
    match = re.fullmatch(r"\[[^\]]*\]\((?:<([^>]+)>|([^\s)]+))\)", value)
    return unquote((match.group(1) or match.group(2)) if match else value.strip("`"))


def log_path(root):
    path = root / ".memory-bank/findings.md"
    if not inside(path, root / ".memory-bank"):
        raise FindingError("working log escapes memory bank")
    return path


def report_path(root, value):
    path = root / value
    if Path(value).is_absolute() or not inside(path, root / "findings"):
        raise FindingError("report path must remain within findings/")
    relative = path.relative_to(root / "findings")
    if len(relative.parts) != 3 or relative.name != "finding.md" or "_TEMPLATE" in relative.parts:
        raise FindingError("report path must be findings/<workstream>/<slug>/finding.md")
    return path


def report_files(root, selection=None):
    base = root / "findings"
    if not base.is_dir():
        raise FindingError("findings directory is missing")
    selected = root / selection if selection else base
    if not inside(selected, base) or "_TEMPLATE" in selected.relative_to(base).parts:
        raise FindingError("selection must be a report path inside findings/, not a template")
    if not selected.exists():
        raise FindingError("selected report path does not exist")
    files = [selected] if selected.is_file() else sorted(selected.rglob("finding.md"))
    if any(not inside(path, base) for path in files):
        raise FindingError("discovered report escapes findings containment")
    return [p for p in files if "_TEMPLATE" not in p.relative_to(base).parts]


def set_status(text, state):
    matches = list(STATUS.finditer(text))
    if len(matches) > 1:
        raise FindingError("report contains duplicate Status headers")
    if matches:
        match = matches[0]
        # Replace only the state token, preserving any authored qualifier.
        start, end = match.span(1) if match.group(1) is not None else match.span(2)
        text = text[:start] + state + text[end:]
    else:
        title = TITLE.search(text)
        if not title:
            raise FindingError("report requires a descriptive H1 title")
        text = text[:title.end()] + "\n\n**Status:** `" + state + "`" + text[title.end():]
    text = re.sub(r"^\*\*Provisional:\*\*.*\n?", "", text, flags=re.M)
    if state in {"Hypothesis", "Suspected"}:
        match = STATUS.search(text)
        line_end = text.find("\n", match.end())
        if line_end < 0:
            line_end = len(text)
        qualifier = "unvalidated hypothesis; score and impact are provisional" if state == "Hypothesis" else "suspected incident conclusion; confidence and alternatives remain investigative"
        text = text[:line_end] + "\n**Provisional:** Yes — " + qualifier + "." + text[line_end:]
    return text


def cvss_base(vector):
    """CVSS v3.1 base metrics and specified Roundup (not Python bankers rounding)."""
    if not vector.startswith("CVSS:3.1/"):
        raise ValueError("not a v3.1 vector")
    pairs = [part.split(":") for part in vector[9:].split("/")]
    if any(len(pair) != 2 for pair in pairs):
        raise ValueError("invalid metric")
    metrics = dict(pairs)
    if len(metrics) != len(pairs) or set(metrics) != set(METRICS):
        raise ValueError("base vector requires exactly eight unique metrics")
    for key, value in metrics.items():
        if value not in METRICS[key][1]:
            raise ValueError("invalid metric value")
    changed = metrics["S"] == "C"
    impact_values = {"N": 0, "L": .22, "H": .56}
    iss = 1 - math.prod(1 - impact_values[metrics[key]] for key in ("C", "I", "A"))
    impact = 7.52 * (iss - .029) - 3.25 * (iss - .02) ** 15 if changed else 6.42 * iss
    exploitability = (8.22 * {"N": .85, "A": .62, "L": .55, "P": .2}[metrics["AV"]]
                      * {"L": .77, "H": .44}[metrics["AC"]]
                      * ({"N": .85, "L": .68, "H": .5} if changed else {"N": .85, "L": .62, "H": .27})[metrics["PR"]]
                      * {"N": .85, "R": .62}[metrics["UI"]])
    raw = min((1.08 if changed else 1) * (impact + exploitability), 10) if impact > 0 else 0
    # FIRST reference algorithm: integer rounding avoids floating-point over-roundup.
    integer = round(raw * 100000)
    score = integer / 100000 if integer % 10000 == 0 else (integer // 10000 + 1) / 10
    return score, metrics


def severity(score):
    return "Informational" if score == 0 else "Low" if score < 4 else "Medium" if score < 7 else "High" if score < 9 else "Critical"


def link_targets(text):
    """Yield destination spans for inline, reference and HTML Markdown assets/links."""
    targets = []
    for opener in re.finditer(r"!?\[[^\]\n]*\]\(\s*", text):
        start = opener.end()
        if start >= len(text):
            continue
        if text[start] == "<":
            end = text.find(">", start + 1)
            if end >= 0:
                targets.append((start + 1, end, text[start + 1:end]))
            continue
        depth, end = 0, start
        while end < len(text):
            char = text[end]
            if char == "\\" and end + 1 < len(text):
                end += 2
                continue
            if char == "(" :
                depth += 1
            elif char == ")":
                if depth == 0:
                    break
                depth -= 1
            elif char.isspace() and depth == 0:
                break
            end += 1
        if end > start:
            targets.append((start, end, text[start:end]))
    for pattern in (r"^\s*\[[^\]\n]+\]:\s*(?:<([^>\n]+)>|([^\s]+))",
                    r"\b(?:src|href)\s*=\s*(?:\"([^\"]+)\"|'([^']+)')"):
        for match in re.finditer(pattern, text, re.M | re.I):
            group = 1 if match.group(1) is not None else 2
            targets.append((*match.span(group), match.group(group)))
    return sorted(set(targets))


def local_target(raw):
    raw = html.unescape(re.sub(r"\\([() ])", r"\1", raw))
    parsed = urlsplit(raw)
    if parsed.scheme in {"https", "http", "mailto"}:
        return None
    if parsed.scheme or parsed.netloc or raw.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", raw):
        return False
    return unquote(parsed.path)


def scan_asset(root, path):
    """Check linked report-owned text only; binary contents are not interpreted."""
    if path.suffix.lower() in {".txt", ".csv", ".json", ".yaml", ".yml", ".md", ".log", ".xml", ".html", ".svg", ".har"}:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for number, line in enumerate(handle, 1):
                for category, pattern in SECRET_PATTERNS:
                    if pattern.search(line):
                        warn(path.relative_to(root).as_posix(), number, "possible " + category + "; review without reproducing values")
    else:
        with path.open("rb") as handle:
            handle.read(1)


def warn(path, line, category):
    # Never echo suspicious values, source lines or link destinations.
    print(f"warning: {path}:{line}: {category}", file=sys.stderr)


def lint_one(root, path, profile, entries):
    text = read_text(path)
    display = path.relative_to(root).as_posix()
    def issue(category, position=0):
        warn(display, text.count("\n", 0, position) + 1, category)
    title = title_of(text)
    if not title or len(TITLE.findall(text)) != 1:
        issue("expected one descriptive H1 title")
    if title and re.match(r"(?:F[- ]?\d+|\[F[- ]?\d+\])[: .-]", title, re.I):
        issue("report title must not carry a finding identifier")
    if re.search(r"\bF-\d+\b", text):
        issue("cross-reference findings by title, not finding identifier")
    if "TEMPLATE" in text or re.search(r"<[^>\n]*(?:Descriptive|score|actionable|observed|summary)[^>\n]*>", text, re.I):
        issue("unfinished template content")
    state = status_of(text)
    states = IR_STATES if profile == "incident-response" else PENTEST_STATES
    if state not in states or len(STATUS.findall(text)) != 1:
        issue("missing, duplicate or invalid report status")
    entry = entries.get(title)
    if not entry:
        issue("no matching title in working log")
    else:
        if state != entry["status"]:
            issue("report status differs from working-log truth; run sync")
        if entry["path"] != display:
            issue("working-log report backlink differs or is absent")
    if state in {"Hypothesis", "Suspected"} and not re.search(r"^\*\*Provisional:\*\* Yes", text, re.M):
        issue("unconfirmed finding requires explicit provisional label")
    for field in ("Workstream", "Date", "Origin"):
        if len(re.findall(r"^\*\*" + field + r":\*\*[ \t]*\S", text, re.M)) != 1:
            issue("missing or duplicate " + field + " header")
    required = list(SECTIONS)
    vulnerability = bool(re.search(r"^\*\*Finding type:\*\*\s*`?Vulnerability`?\s*$", text, re.M))
    scored_schema = profile != "incident-response" or vulnerability
    if scored_schema:
        required.insert(0, "## CVSSv3.1 Score and Severity")
    elif "CVSS" in text:
        issue("incident conclusions must not use CVSS without explicit Finding type: Vulnerability")
    if profile == "incident-response":
        for field in ("Finding type", "Confidence"):
            if not re.search(r"^\*\*" + field + r":\*\*[ \t]*\S", text, re.M):
                issue("missing incident " + field + " header")
        if not re.search(r"^\*\*Confidence:\*\*[ \t]*`?(Low|Medium|High)\b", text, re.M):
            issue("incident confidence must retain Low, Medium or High and its basis")
        for heading in ("### Statement of fact", "### Inference", "### Alternative explanations considered"):
            if heading not in text.splitlines():
                issue("missing incident section: " + heading[4:])
    positions = []
    for section in required:
        occurrences = list(re.finditer(r"^" + re.escape(section) + r"\s*$", text, re.M))
        if len(occurrences) != 1:
            issue("missing or duplicate canonical section: " + section.lstrip("# "))
        else:
            positions.append(occurrences[0].start())
    if positions != sorted(positions):
        issue("canonical sections are out of order")
    for label in ("Technical", "Business"):
        if not re.search(r"\*\*" + label + r"[.:]?\*\*", text):
            issue("missing " + label + " impact")
    if not re.search(r"^\*Evidence source:", text, re.M):
        issue("missing evidence source footer")
    if scored_schema:
        lint_cvss(text, issue, state)
    for start, _, destination in link_targets(text):
        target = local_target(destination)
        if target is None or target == "":
            continue
        if target is False:
            issue("asset/link must use a report-safe relative path or supported external URL", start)
            continue
        resolved = path.parent / target
        if not inside(resolved, root / "findings"):
            issue("asset/link escapes report findings containment", start)
        else:
            try:
                resolved.stat()
            except FileNotFoundError:
                issue("relative asset/link does not resolve", start)
                continue
            if resolved.is_file():
                scan_asset(root, resolved)
    for category, pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            issue("possible " + category + "; review without reproducing values", match.start())


def lint_cvss(text, issue, state):
    score_match = re.search(r"\*\*CVSSv3\.1 score:\s*([0-9]+(?:\.[0-9]+)?)\s*\(([^)]+)\)\*\*", text)
    vector_match = re.search(r"^Vector:\s*`?(CVSS:[^`\s]+|N/A)", text, re.M)
    if not score_match or not vector_match:
        issue("missing or malformed CVSS score/severity/vector")
        return
    score = float(score_match.group(1))
    label = score_match.group(2)
    vector = vector_match.group(1)
    if not 0 <= score <= 10 or not re.fullmatch(r"\d+\.\d", score_match.group(1)):
        issue("CVSS score must be 0.0–10.0 with one-decimal precision")
    if label != severity(score):
        issue("CVSS severity does not match score")
    has_grid = bool(re.search(r"^\|\s*Metric\s*\|", text, re.M))
    if score == 0:
        if vector != "N/A" or has_grid:
            issue("informational 0.0 requires N/A vector and no metric grid")
        return
    if state == "Informational":
        issue("Informational status requires CVSS 0.0 / N/A")
    if not has_grid:
        issue("scored finding requires canonical CVSS metric grid")
    try:
        expected, metrics = cvss_base(vector)
    except ValueError:
        issue("invalid CVSSv3.1 base vector")
        return
    if score != expected:
        issue("CVSS score differs from calculated vector score")
    table = {}
    for line in text.splitlines():
        if line.startswith("|"):
            cells = [cell.strip().strip("*`") for cell in line.strip("|").split("|")]
            if len(cells) == 4:
                table[cells[0]] = cells[1]
                table[cells[2]] = cells[3]
    for key, (name, values) in METRICS.items():
        if table.get(name) != values[metrics[key]]:
            issue("CVSS metric grid missing or inconsistent: " + name)


def render_index(root, entries, pending=()):
    path = root / "findings/README.md"
    if not inside(path, root / "findings"):
        raise FindingError("findings index escapes report containment")
    start, end = "<!-- findings:index:start -->", "<!-- findings:index:end -->"
    text = read_text(path)
    if text.count(start) != 1 or text.count(end) != 1 or text.index(start) > text.index(end):
        raise FindingError("findings README requires one ordered findings:index marker pair")
    rows = ["| Finding | Status |", "|---|---|"]
    for title, entry in sorted(entries.items()):
        if not entry["path"]:
            continue
        report = report_path(root, entry["path"])
        if not report.is_file() and report not in pending:
            raise FindingError("indexed report path is missing")
        label = title.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]").replace("|", "&#124;").replace("<", "&lt;")
        rows.append(f"| [{label}]({quote(report.relative_to(root / 'findings').as_posix(), safe='/')}) | {entry['status']} |")
    new = text[:text.index(start) + len(start)] + "\n" + "\n".join(rows) + "\n" + text[text.index(end):]
    return path, text, new


def add_backlink(text, entry, relative, promotion=False):
    body = entry["body"]
    line = "- Report path: " + relative
    match = re.search(r"^- Report path:.*$", body, re.M)
    if match:
        body = body[:match.start()] + line + body[match.end():]
    else:
        heading_end = body.find("\n")
        if heading_end < 0:
            body += "\n" + line + "\n"
        else:
            body = body[:heading_end] + "\n" + line + body[heading_end:]
    if promotion and not entry["path"]:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        body += ("" if body.endswith("\n") else "\n") + f"- Promotion: {stamp} — report source promoted to {relative}.\n"
    return text[:entry["start"]] + body + text[entry["end"]:]


def eligible(state, profile, provisional=False):
    if profile == "incident-response":
        return state == "Confirmed" or (provisional and state == "Suspected")
    return state in {"Validated", "Informational"} or (provisional and state == "Hypothesis")


def promote(root, profile, args):
    for value in (args.workstream, args.slug):
        if not re.fullmatch(r"[^\W_]+(?:-[^\W_]+)*", value, re.UNICODE):
            raise FindingError("workstream and slug must be Unicode alphanumeric words separated by hyphens")
    if "\n" in args.title or "\r" in args.title or not args.title.strip():
        raise FindingError("title must be one nonempty line")
    log = log_path(root)
    original = read_text(log)
    entries = log_entries(original)
    entry = entries.get(args.title)
    if not entry:
        raise FindingError("title must already exist in working log")
    if not eligible(entry["status"], profile, args.include_suspected if profile == "incident-response" else args.include_hypothesis):
        raise FindingError("working-log state is not eligible; unconfirmed findings require the profile's explicit provisional flag")
    target = report_path(root, f"findings/{args.workstream}/{args.slug}/finding.md")
    source = root / args.source
    if not inside(source, root) or "_TEMPLATE" in source.parts:
        raise FindingError("source must be an explicitly authored project file, not a template")
    if has_symlink_component(source, root):
        raise FindingError("promotion source must not contain a symlink component")
    text = read_text(source)
    if title_of(text) != args.title or len(TITLE.findall(text)) != 1:
        raise FindingError("supplied prose must have exactly the requested title-only H1")
    if entry["path"] and entry["path"] != target.relative_to(root).as_posix():
        raise FindingError("working log already has another canonical report path")
    if target.exists() and source.resolve() != target.resolve():
        raise FindingError("canonical report already exists; edit it instead of creating a duplicate")
    text = set_status(text, entry["status"])
    copies = []
    replacements = []
    for start, end, destination in link_targets(text):
        local = local_target(destination)
        if local is None or local is False or local == "":
            continue
        asset = source.parent / local
        if has_symlink_component(asset, root):
            raise FindingError("promotion assets must not contain a symlink component")
        if source.resolve() == target.resolve():
            continue
        if inside(asset, source.parent / "assets") and asset.is_file():
            destination_path = target.parent / "assets" / asset.relative_to(source.parent / "assets")
            if not inside(destination_path, target.parent):
                raise FindingError("asset destination escapes canonical finding")
            if destination_path.exists():
                raise FindingError("asset destination already exists; promotion never overwrites assets")
            copies.append((asset, destination_path))
            parsed = urlsplit(destination)
            suffix = ("?" + parsed.query if parsed.query else "") + ("#" + parsed.fragment if parsed.fragment else "")
            replacements.append((start, end, quote(destination_path.relative_to(target.parent).as_posix(), safe='/') + suffix))
        elif inside(asset, root / "findings"):
            parsed = urlsplit(destination)
            relative = os.path.relpath(asset, target.parent)
            suffix = ("?" + parsed.query if parsed.query else "") + ("#" + parsed.fragment if parsed.fragment else "")
            replacements.append((start, end, quote(relative, safe='/') + suffix))
    for start, end, replacement in reversed(replacements):
        text = text[:start] + replacement + text[end:]
    relative = target.relative_to(root).as_posix()
    updated_log = add_backlink(original, entry, relative, promotion=True)
    index_path, index_text, new_index = render_index(root, log_entries(updated_log), (target,))
    target.parent.mkdir(parents=True, exist_ok=True)
    for asset, destination in dict(copies).items():
        destination.parent.mkdir(parents=True, exist_ok=True)
        with asset.open("rb") as incoming, destination.open("xb") as outgoing:
            shutil.copyfileobj(incoming, outgoing)
    atomic_write(target, text)
    atomic_write(log, updated_log, 0o600)
    if new_index != index_text:
        atomic_write(index_path, new_index)
    if source.resolve() != target.resolve():
        source.unlink()
    lint_one(root, target, profile, log_entries(updated_log))
    print(relative)


def sync(root, profile, selection):
    log = log_path(root)
    original = read_text(log)
    entries = log_entries(original)
    states = IR_STATES if profile == "incident-response" else PENTEST_STATES
    changes = []
    backlinks = []
    seen = set()
    for path in report_files(root, selection):
        report_path(root, path.relative_to(root).as_posix())
        text = read_text(path)
        title = title_of(text)
        entry = entries.get(title)
        if not entry or title in seen:
            raise FindingError("each report must have one unique matching working-log title")
        seen.add(title)
        if entry["status"] not in states:
            raise FindingError("working log has an invalid domain status")
        relative = path.relative_to(root).as_posix()
        if entry["path"] and entry["path"] != relative:
            raise FindingError("report conflicts with existing working-log backlink")
        revised = set_status(text, entry["status"])
        if revised != text:
            changes.append((path, revised))
        if not entry["path"]:
            backlinks.append((entry, relative))
    updated = original
    for entry, relative in sorted(backlinks, key=lambda pair: pair[0]["start"], reverse=True):
        updated = add_backlink(updated, entry, relative)
    index_path, index_text, new_index = render_index(root, log_entries(updated))
    for path, text in changes:
        atomic_write(path, text)
    if updated != original:
        atomic_write(log, updated, 0o600)
    if new_index != index_text:
        atomic_write(index_path, new_index)
    print(f"Synchronized {len(changes)} report header(s), {len(backlinks)} backlink(s).")


def list_reports(root, profile, provisional):
    entries = log_entries(read_text(log_path(root)))
    for title, entry in entries.items():
        if not entry["path"] or not eligible(entry["status"], profile, provisional):
            continue
        path = report_path(root, entry["path"])
        text = read_text(path)
        if title_of(text) != title or status_of(text) != entry["status"]:
            warn(entry["path"], 1, "report/log mismatch; excluded until synchronized")
            continue
        if entry["status"] in {"Hypothesis", "Suspected"} and not re.search(r"^\*\*Provisional:\*\* Yes", text, re.M):
            warn(entry["path"], 1, "unconfirmed finding lacks provisional label; excluded")
            continue
        print(f"{entry['status']}\t{title}\t{entry['path']}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="project root (default: git root or cwd)")
    parser.add_argument("--profile", choices=["pentest", "incident-response", "general-project"])
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("lint", "sync"):
        command = commands.add_parser(name)
        command.add_argument("path", nargs="?")
    listing = commands.add_parser("list")
    listing.add_argument("--include-hypothesis", action="store_true")
    listing.add_argument("--include-suspected", action="store_true", help="explicitly select provisional IR conclusions")
    promotion = commands.add_parser("promote")
    for name in ("title", "workstream", "slug", "source"):
        promotion.add_argument("--" + name, required=True)
    promotion.add_argument("--include-hypothesis", action="store_true")
    promotion.add_argument("--include-suspected", action="store_true", help="explicitly promote a provisional IR conclusion")
    args = parser.parse_args(argv)
    try:
        root = root_path(args.root)
        profile = profile_for(root, args.profile)
        if args.command in {"promote", "list"}:
            if (profile == "incident-response" and args.include_hypothesis) or (profile != "incident-response" and args.include_suspected):
                raise FindingError("use --include-suspected for IR or --include-hypothesis for pentest/general findings")
        if args.command == "promote":
            promote(root, profile, args)
        elif args.command == "sync":
            sync(root, profile, args.path)
        elif args.command == "list":
            list_reports(root, profile, args.include_suspected if profile == "incident-response" else args.include_hypothesis)
        else:
            entries = log_entries(read_text(log_path(root)))
            for path in report_files(root, args.path):
                lint_one(root, path, profile, entries)
        return 0
    except (FindingError, OSError, UnicodeError, ValueError) as exc:
        # OS errors and malformed JSON may contain sensitive input/path values.
        message = str(exc) if isinstance(exc, FindingError) else "input/output or input-format failure (details withheld)"
        print("error: " + message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
