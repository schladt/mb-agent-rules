"""
Incident Response Dashboard
Live incident response dashboard with optional HTTPS and password auth.
Reads directly from the memory-bank/ directory for always-current data.
"""

import os
import re
import sys
import ssl
import json
import secrets
import argparse
import heapq
import ipaddress
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from functools import wraps

from flask import (
    Flask, render_template, jsonify, request, session,
    redirect, url_for, send_file, abort, Response
)
from werkzeug.security import generate_password_hash, check_password_hash

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEMORY_BANK = PROJECT_ROOT / "memory-bank"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
CERTS_DIR = Path(__file__).resolve().parent / "certs"
CONFIG_FILE = PROJECT_ROOT / "dashboard.config.json"

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

PASSWORD_HASH = None
DASHBOARD_CONFIG = {}
LOGIN_ATTEMPTS: dict[str, list[float]] = {}
ALLOWED_CSS_OVERRIDES = {
    "bg", "surface", "surface-raised", "border", "border-light", "text",
    "text-secondary", "text-dim", "accent", "danger", "warning", "success",
    "info", "purple",
}
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?(?:[0-9a-fA-F]{2})?$")


def _reject_nonfinite_json(value: str):
    raise ValueError(f"non-finite JSON number is not supported: {value}")


def load_config() -> dict:
    defaults = {
        "title": "IR Dashboard",
        "brand": "",
        "accent_color": "#3b82f6",
        "logo_url": "",
        "css_overrides": {},
        "shared_group_access": False,
        "atomic_max_file_bytes": 100 * 1024 * 1024,
        "atomic_max_records": 250_000,
        "atomic_max_fields": 250,
    }
    if CONFIG_FILE.exists():
        try:
            user = json.loads(
                CONFIG_FILE.read_text(encoding="utf-8"),
                parse_constant=_reject_nonfinite_json,
            )
        except (OSError, ValueError) as exc:
            raise ValueError(f"Invalid dashboard.config.json: {exc}") from exc
        if not isinstance(user, dict):
            raise ValueError("dashboard.config.json must contain a JSON object")
        defaults.update(user)
    for key in ("title", "brand", "accent_color", "logo_url"):
        if not isinstance(defaults[key], str):
            raise ValueError(f"dashboard config {key!r} must be a string")
    if not HEX_COLOR.fullmatch(defaults["accent_color"]):
        raise ValueError("dashboard accent_color must be a 3, 6, or 8 digit hex color")
    overrides = defaults.get("css_overrides")
    if not isinstance(overrides, dict) or not set(overrides).issubset(ALLOWED_CSS_OVERRIDES):
        raise ValueError("dashboard css_overrides contains unsupported properties")
    for value in overrides.values():
        if not isinstance(value, str) or not HEX_COLOR.fullmatch(value):
            raise ValueError("dashboard CSS override values must be hex colors")
    logo = defaults["logo_url"]
    if logo and not (logo.startswith("/static/") or logo.startswith("data:image/")):
        raise ValueError("logo_url must be empty, a /static/ path, or a data:image URL")
    if not isinstance(defaults.get("shared_group_access"), bool):
        raise ValueError("dashboard config 'shared_group_access' must be a boolean")
    for key in ("atomic_max_file_bytes", "atomic_max_records", "atomic_max_fields"):
        if isinstance(defaults[key], bool) or not isinstance(defaults[key], int) or defaults[key] <= 0:
            raise ValueError(f"dashboard config {key!r} must be a positive integer")
    return defaults


def csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def _login_rate_limited(remote_addr: str) -> bool:
    now = time.monotonic()
    recent = [stamp for stamp in LOGIN_ATTEMPTS.get(remote_addr, []) if now - stamp < 300]
    LOGIN_ATTEMPTS[remote_addr] = recent
    return len(recent) >= 10


@app.before_request
def enforce_csrf():
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return None
    supplied = request.headers.get("X-CSRF-Token", "") or request.form.get("csrf_token", "")
    expected = session.get("csrf_token", "")
    if not expected or not secrets.compare_digest(expected, supplied):
        return jsonify({"error": "invalid CSRF token"}), 403
    return None


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; object-src 'none'; "
        "base-uri 'none'; frame-ancestors 'none'; form-action 'self'; "
        "script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    )
    response.headers["Cache-Control"] = "no-store"
    return response


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("authenticated"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "unauthorized"}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
#  Markdown / Memory-Bank Parsers
# ---------------------------------------------------------------------------

def read_mb(filename: str) -> str:
    p = MEMORY_BANK / filename
    if p.exists():
        return p.read_text(encoding="utf-8")
    return ""


def contained_artifact_path(candidate: Path, *, must_exist: bool = True) -> Path | None:
    """Resolve a path and prove it remains beneath the artifact root."""
    if ARTIFACTS_DIR.is_symlink():
        return None
    try:
        base = ARTIFACTS_DIR.resolve(strict=True)
        target = candidate.resolve(strict=must_exist)
        target.relative_to(base)
    except (OSError, RuntimeError, ValueError):
        return None
    raw = candidate.absolute()
    try:
        relative = raw.relative_to(ARTIFACTS_DIR.absolute())
    except ValueError:
        return None
    cursor = ARTIFACTS_DIR.absolute()
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            return None
    return target


def parse_markdown_table(text: str) -> list[dict]:
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    if len(lines) < 2:
        return []
    header_line = lines[0]
    headers = [h.strip() for h in header_line.strip("|").split("|")]
    rows = []
    for line in lines[2:]:
        if line.startswith("|--") or all(c in "-| " for c in line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(c == "" for c in cells):
            continue
        row = {}
        for i, h in enumerate(headers):
            row[h] = cells[i] if i < len(cells) else ""
        rows.append(row)
    return rows


def _extract_sort_date(time_str: str) -> str:
    if not time_str:
        return "0000-00-00"
    m = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", time_str)
    if m:
        return m.group(1)
    m = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})", time_str)
    if m:
        return m.group(1) + ":00"
    m = re.search(r"(\d{4}-\d{2}-\d{2})", time_str)
    if m:
        return m.group(1) + "T23:59:59"
    m = re.search(r"(\d{4}-\d{2})", time_str)
    if m:
        return m.group(1) + "-01T00:00:00"
    return "0000-00-00"


def parse_timeline() -> list[dict]:
    content = read_mb("timeline.md")
    entries = []
    blocks = re.split(r"^### ", content, flags=re.MULTILINE)
    for file_idx, block in enumerate(blocks[1:]):
        lines = block.strip().splitlines()
        title = lines[0].strip()
        entry = {"title": title, "fields": {}, "raw": block.strip()}
        for line in lines[1:]:
            m = re.match(r"^-\s+\*\*?(.+?)\*\*?\s*[:\u2014]\s*(.+)$", line.strip())
            if not m:
                m = re.match(r"^-\s+(.+?):\s+(.+)$", line.strip())
            if m:
                key = m.group(1).strip().rstrip(":")
                val = m.group(2).strip()
                entry["fields"][key] = val
        event_time = entry["fields"].get("Event time (UTC)", "")
        actor = entry["fields"].get("Actor", "Unknown")
        actor_clean = re.sub(r"[`*]", "", actor).strip()
        source = entry["fields"].get("Source", "")
        confidence = entry["fields"].get("Confidence", "")
        event_desc = entry["fields"].get("Event", "")
        notes = entry["fields"].get("Notes", "")
        art_ids = re.findall(r"ART-\d{4}", source + " " + event_desc + " " + notes)
        entries.append({
            "title": title,
            "time": event_time,
            "actor": actor_clean,
            "event": event_desc,
            "source": source,
            "confidence": confidence,
            "notes": notes,
            "artifact_ids": list(set(art_ids)),
            "fields": entry["fields"],
            "_file_order": file_idx,
        })
    entries.sort(key=lambda e: (_extract_sort_date(e["time"]), e.get("_file_order", 0)))
    for e in entries:
        e.pop("_file_order", None)
    return entries


def parse_evidence_index() -> dict[str, dict]:
    content = read_mb("evidenceIndex.md")
    artifacts = {}
    blocks = re.split(r"^### (ART-\d{4})", content, flags=re.MULTILINE)
    i = 1
    while i < len(blocks) - 1:
        art_id = blocks[i].strip()
        body = blocks[i + 1].strip()
        art = {"id": art_id, "fields": {}}
        title_match = re.match(r"[^a-zA-Z]*(.+?)$", body.splitlines()[0]) if body.splitlines() else None
        art["summary"] = title_match.group(1).strip().lstrip("\u2014 ").strip() if title_match else art_id
        for line in body.splitlines():
            m = re.match(r"^-\s+(.+?):\s+(.+)$", line.strip())
            if m:
                key = m.group(1).strip()
                val = m.group(2).strip().strip("`")
                art["fields"][key] = val
        art["name"] = art["fields"].get("Original name", "")
        art["sha256"] = art["fields"].get("SHA-256", "")
        art["stored_path"] = art["fields"].get("Stored path", "")
        art["relevance"] = art["fields"].get("Relevance", "")
        art["ingested"] = art["fields"].get("Ingested (UTC)", "")
        art["size"] = art["fields"].get("Size", "")
        art["provided_by"] = art["fields"].get("Provided by", "")
        art["acquisition"] = art["fields"].get("Acquisition method", "")
        art["verified"] = art["fields"].get("Copy verified", "")
        art["handling"] = art["fields"].get("Handling notes", "")
        artifacts[art_id] = art
        i += 2
    return artifacts


def parse_findings() -> tuple[list[dict], list[dict]]:
    content = read_mb("findings.md")
    findings = []
    questions = []
    findings_section = content.split("## Entries")[-1] if "## Entries" in content else content

    blocks = re.split(r"^### (F-\d{3})", findings_section, flags=re.MULTILINE)
    i = 1
    while i < len(blocks) - 1:
        fid = blocks[i].strip()
        body = blocks[i + 1].strip()
        finding = {"id": fid, "fields": {}}
        title_line = body.splitlines()[0] if body.splitlines() else ""
        finding["title"] = re.sub(r"^[^a-zA-Z]*", "", title_line).strip()
        for line in body.splitlines():
            m = re.match(r"^-\s+(.+?):\s+(.+)$", line.strip())
            if m:
                key = m.group(1).strip().rstrip("*").lstrip("*")
                val = m.group(2).strip()
                finding["fields"][key] = val
        finding["status"] = re.sub(r"[`*]", "", finding["fields"].get("Status", "")).strip()
        finding["confidence"] = finding["fields"].get("Confidence", "")
        art_refs = re.findall(r"ART-\d{4}", body)
        finding["artifact_ids"] = list(set(art_refs))
        findings.append(finding)
        i += 2

    gaps_split = findings_section.split("## Gaps and Unanswered Questions")
    gaps_text = gaps_split[1] if len(gaps_split) > 1 else ""
    for line in gaps_text.splitlines():
        m = re.match(r"^\d+\.\s+\*\*(.+?)\*\*\s*[\u2014\-]+\s*(.+)$", line.strip())
        if m:
            label = m.group(1).strip()
            desc = m.group(2).strip()
            answered = label.startswith("~~") and label.endswith("~~")
            label_clean = re.sub(r"~~", "", label)
            questions.append({
                "label": label_clean,
                "description": desc,
                "answered": answered,
            })

    return findings, questions


def parse_indicators() -> tuple[list[dict], list[dict]]:
    content = read_mb("indicators.md")
    iocs = []
    ttps = []

    ioc_table_pattern = re.compile(
        r"(?:## Indicators of Compromise|## New IOCs[^\n]*)\s*\n(\|.+?\n(?:\|.+?\n)*)",
        re.DOTALL
    )
    key_map = {
        "Indicator": "Indicator (defanged)",
        "Source": "Provenance (artifact ID or feed)",
        "First Seen": "First seen (UTC)",
    }
    for m in ioc_table_pattern.finditer(content):
        rows = parse_markdown_table(m.group(1))
        for row in rows:
            normalized = {}
            for k, v in row.items():
                normalized[key_map.get(k, k)] = v
            iocs.append(normalized)

    ttp_table_match = re.search(
        r"## Observed TTPs\s*\n(\|.+?\n(?:\|.+?\n)*)",
        content, re.DOTALL
    )
    if ttp_table_match:
        ttps = parse_markdown_table(ttp_table_match.group(1))

    return iocs, ttps


def parse_affected_assets() -> dict:
    content = read_mb("affectedAssets.md")
    result = {"systems": [], "accounts": [], "data": []}
    for section_name, key in [("## Systems", "systems"), ("## Accounts", "accounts"), ("## Data", "data")]:
        match = re.search(
            rf"{re.escape(section_name)}\s*\n(\|.+?\n(?:\|.+?\n)*)",
            content, re.DOTALL
        )
        if match:
            result[key] = parse_markdown_table(match.group(1))
    return result


def parse_active_context() -> dict:
    content = read_mb("activeContext.md")
    ctx = {}
    sections = re.split(r"^## ", content, flags=re.MULTILINE)
    for sec in sections[1:]:
        lines = sec.strip().splitlines()
        header = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
        body = re.sub(r"^<!--.*?-->$", "", body, flags=re.MULTILINE).strip()
        ctx[header] = body
    return ctx


def parse_incident_brief() -> dict:
    content = read_mb("incidentBrief.md")
    brief = {}
    sections = re.split(r"^## ", content, flags=re.MULTILINE)
    for sec in sections[1:]:
        lines = sec.strip().splitlines()
        header = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
        body = re.sub(r"^<!--.*?-->$", "", body, flags=re.MULTILINE).strip()
        brief[header] = body
    return brief


def parse_scope_authorization() -> dict:
    content = read_mb("scopeAuthorization.md")
    scope = {}
    sections = re.split(r"^## ", content, flags=re.MULTILINE)
    for sec in sections[1:]:
        lines = sec.strip().splitlines()
        header = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
        scope[header] = body
    return scope


def validate_executive_summary(value: object) -> dict | None:
    """Accept only the documented v1 projection shape consumed by the UI."""
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        return None
    required_root = {
        "schema_version", "generated_at", "narrative", "attack_phases",
        "theory_summary", "key_findings", "status", "unresolved",
    }
    if not required_root.issubset(value):
        return None
    string_keys = ("generated_at", "narrative", "theory_summary")
    if any(not isinstance(value.get(key, ""), str) for key in string_keys):
        return None
    try:
        generated_at = datetime.fromisoformat(value["generated_at"].replace("Z", "+00:00"))
    except ValueError:
        return None
    if generated_at.tzinfo is None or generated_at.utcoffset() != timezone.utc.utcoffset(generated_at):
        return None
    phases = value.get("attack_phases", [])
    findings = value.get("key_findings", [])
    status = value.get("status", {})
    unresolved = value.get("unresolved", [])
    if not isinstance(phases, list) or len(phases) > 20:
        return None
    if not isinstance(findings, list) or len(findings) > 100:
        return None
    if not isinstance(status, dict) or not isinstance(unresolved, list):
        return None
    if not all(isinstance(question, str) for question in unresolved):
        return None
    for phase in phases:
        if not isinstance(phase, dict):
            return None
        if not {"name", "icon", "date_range", "color", "summary", "event_count", "key_findings"}.issubset(phase):
            return None
        if any(not isinstance(phase.get(key, ""), str) for key in ("name", "icon", "date_range", "color", "summary")):
            return None
        if phase.get("color", "") not in ("", "warning", "danger", "purple", "success", "info", "accent"):
            return None
        if isinstance(phase.get("event_count"), bool) or not isinstance(phase.get("event_count"), int) or phase["event_count"] < 0:
            return None
        if not isinstance(phase.get("key_findings", []), list) or not all(
            isinstance(item, str) for item in phase.get("key_findings", [])
        ):
            return None
    for finding in findings:
        if not isinstance(finding, dict):
            return None
        if not {"id", "headline", "confidence", "artifacts"}.issubset(finding):
            return None
        if any(not isinstance(finding.get(key, ""), str) for key in ("id", "headline", "confidence")):
            return None
        if finding.get("confidence", "") not in ("High", "Medium", "Low"):
            return None
        if not isinstance(finding.get("artifacts", []), list) or not all(
            isinstance(item, str) for item in finding.get("artifacts", [])
        ):
            return None
    if not {"completed", "in_progress", "blocked"}.issubset(status):
        return None
    for key in ("completed", "in_progress"):
        if not isinstance(status.get(key, []), list) or not all(isinstance(item, str) for item in status.get(key, [])):
            return None
    blocked = status.get("blocked", [])
    if not isinstance(blocked, list):
        return None
    for item in blocked:
        if not isinstance(item, dict) or any(not isinstance(item.get(key, ""), str) for key in ("item", "severity", "reason")):
            return None
        if not {"item", "severity", "reason"}.issubset(item):
            return None
        if item.get("severity", "") not in ("high", "medium", "low"):
            return None
    return value


def _known_affected(rows: list[dict]) -> int:
    affected_statuses = {"confirmed affected", "contained", "rebuilt"}
    return sum(
        1 for row in rows
        if re.sub(r"[`*]", "", row.get("Status", "")).strip().lower() in affected_statuses
    )


def build_executive_summary(brief, findings, timeline, evidence, assets, context, iocs) -> dict:
    """Build a fully dynamic executive summary from parsed memory bank data."""
    summary = {}
    summary["classification"] = brief.get("Classification", "Not yet classified")
    summary["severity"] = brief.get("Severity", "Unknown")
    summary["current_phase"] = brief.get("Current Phase", "Unknown")
    summary["incident_id"] = brief.get("Incident ID", "")

    # Key metrics
    summary["total_findings"] = len(findings)
    summary["total_artifacts"] = len(evidence)
    summary["total_timeline_events"] = len(timeline)
    summary["total_iocs"] = len(iocs)
    attacker_events = sum(1 for e in timeline if e.get("actor", "").lower() == "attacker")
    summary["attacker_events"] = attacker_events

    # Extract notable facts from brief
    summary["summary_text"] = ""
    for key in ["Summary of Known Facts", "Summary"]:
        if key in brief:
            summary["summary_text"] = brief[key]
            break

    # Affected assets counts
    summary["systems_affected"] = _known_affected(assets.get("systems", []))
    summary["accounts_affected"] = _known_affected(assets.get("accounts", []))

    # Current objective from active context
    summary["current_objective"] = context.get("Current Objective", "")
    summary["blockers"] = context.get("Blockers / Questions", context.get("Blockers", ""))

    # Verification table from incident brief
    verification_tables = []
    for key, val in brief.items():
        if "verification" in key.lower():
            rows = parse_markdown_table(val)
            if rows:
                verification_tables.extend(rows)
    summary["verification_table"] = verification_tables

    # Load AI-generated executive summary if available
    ai_path = MEMORY_BANK / "executiveSummary.json"
    if ai_path.exists():
        try:
            ai = json.loads(
                ai_path.read_text(encoding="utf-8"),
                parse_constant=_reject_nonfinite_json,
            )
            summary["ai"] = validate_executive_summary(ai)
            if summary["ai"] is None:
                app.logger.warning("executiveSummary.json does not match schema version 1")
        except (OSError, UnicodeError, ValueError):
            summary["ai"] = None
    else:
        summary["ai"] = None

    # Fallback: build attack phases from timeline keywords if no AI summary
    if not summary["ai"]:
        summary["working_theory"] = context.get("Working Theory", "")
        summary["pending_approvals"] = context.get(
            "Pending Approvals", context.get("Pending Approvals / Action Items", "")
        )
        phase_keywords = {
            "Recon": ["recon", "sspr", "credential stuff", "password spray", "bav2ropc", "scanning"],
            "Initial Access": ["vishing", "initial access", "phishing", "login", "brute force"],
            "Persistence": ["mfa", "oath", "token", "persistence", "registration", "backdoor"],
            "Lateral Movement": ["lateral", "pivoting", "pass-the-hash", "rdp"],
            "Exfiltration": ["exfiltrat", "download", "file access", "staging", "upload"],
            "Impact": ["extortion", "ransomware", "encrypt", "ransom", "wiper", "destruction"],
            "Remediation": ["password reset", "remediat", "containment", "blocked", "rebuilt"],
        }
        phases = []
        for phase_name, keywords in phase_keywords.items():
            phase_events = []
            for e in timeline:
                title_lower = (e.get("title", "") + " " + e.get("event", "")).lower()
                if any(kw in title_lower for kw in keywords):
                    phase_events.append(e)
            if phase_events:
                dates = [e.get("time", "") for e in phase_events if e.get("time")]
                date_range = ""
                if dates:
                    first = min(dates)[:10]
                    last = max(dates)[:10]
                    date_range = first if first == last else f"{first} – {last}"
                phases.append({
                    "name": phase_name,
                    "date_range": date_range,
                    "event_count": len(phase_events),
                    "summary": phase_events[0].get("title", ""),
                })
        summary["attack_phases"] = phases

    return summary


def extract_key_metrics(findings: list[dict], assets: dict, timeline: list[dict]) -> dict:
    metrics = {}
    for d in assets.get("data", []):
        vol = d.get("Volume / record count", "")
        m = re.search(r"([\d,]+)\s*(?:downloads|files)", vol, re.IGNORECASE)
        if m:
            metrics["files_downloaded"] = m.group(1)
        m2 = re.search(r"([\d,]+)\s*(?:SharePoint\s*sites|sites|servers|hosts)", vol, re.IGNORECASE)
        if m2:
            metrics["sites_affected"] = m2.group(1)
    attacker_times = [
        parsed for event in timeline
        if event.get("actor", "").strip().lower() == "attacker"
        for parsed in [_parse_event_time(event.get("time", ""))]
        if parsed is not None
    ]
    if len(attacker_times) >= 2:
        duration = max(attacker_times) - min(attacker_times)
        seconds = int(duration.total_seconds())
        if seconds >= 86400:
            value = f"{seconds / 86400:.1f} days"
        elif seconds >= 3600:
            value = f"{seconds / 3600:.1f} hours"
        else:
            value = f"{max(seconds // 60, 1)} minutes"
        metrics["attack_duration"] = value.replace(".0 ", " ")
    return metrics


def get_dashboard_data() -> dict:
    brief = parse_incident_brief()
    timeline = parse_timeline()
    evidence = parse_evidence_index()
    findings, questions = parse_findings()
    iocs, ttps = parse_indicators()
    assets = parse_affected_assets()
    context = parse_active_context()
    scope = parse_scope_authorization()

    open_q = [q for q in questions if not q["answered"]]
    answered_q = [q for q in questions if q["answered"]]

    exec_summary = build_executive_summary(
        brief, findings, timeline, evidence, assets, context, iocs
    )

    return {
        "brief": brief,
        "timeline": timeline,
        "evidence": evidence,
        "findings": findings,
        "open_questions": open_q,
        "answered_questions": answered_q,
        "iocs": iocs,
        "ttps": ttps,
        "assets": assets,
        "context": context,
        "scope": scope,
        "attacker_ips": sorted(get_attacker_ips()),
        "key_metrics": extract_key_metrics(findings, assets, timeline),
        "executive_summary": exec_summary,
        "config": DASHBOARD_CONFIG,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


# ---------------------------------------------------------------------------
#  Routes
# ---------------------------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    token = csrf_token()
    if request.method == "POST":
        if PASSWORD_HASH is None:
            session["authenticated"] = True
            return redirect(url_for("dashboard"))
        remote = request.remote_addr or "unknown"
        if _login_rate_limited(remote):
            return render_template("login.html", error="Too many attempts; try again later", config=DASHBOARD_CONFIG, csrf_token=token), 429
        pw = request.form.get("password", "")
        if check_password_hash(PASSWORD_HASH, pw):
            LOGIN_ATTEMPTS.pop(remote, None)
            session["authenticated"] = True
            return redirect(url_for("dashboard"))
        LOGIN_ATTEMPTS.setdefault(remote, []).append(time.monotonic())
        return render_template("login.html", error="Invalid password", config=DASHBOARD_CONFIG, csrf_token=token)
    return render_template("login.html", error=None, config=DASHBOARD_CONFIG, csrf_token=token)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@require_auth
def dashboard():
    data = get_dashboard_data()
    return render_template("dashboard.html", data=data, csrf_token=csrf_token())


@app.route("/api/data")
@require_auth
def api_data():
    return jsonify(get_dashboard_data())


@app.route("/api/artifact/<art_id>")
@require_auth
def api_artifact(art_id):
    evidence = parse_evidence_index()
    if art_id not in evidence:
        abort(404)
    return jsonify(evidence[art_id])


def _get_attacker_ips() -> set[str]:
    iocs, _ = parse_indicators()
    ips = set()
    for ioc in iocs:
        if ioc.get("Type", "").strip() == "IP":
            status = ioc.get("Status", "")
            if "Confirmed" in status:
                raw = ioc.get("Indicator (defanged)", "")
                ips.add(raw.replace("[.]", "."))
    return ips


_attacker_ips_cache: set[str] = set()
_attacker_ips_stamp: tuple[int, int] | None = None


def get_attacker_ips() -> set[str]:
    global _attacker_ips_cache, _attacker_ips_stamp
    ind_file = MEMORY_BANK / "indicators.md"
    try:
        stat = ind_file.stat()
    except OSError:
        _attacker_ips_cache = set()
        _attacker_ips_stamp = None
        return _attacker_ips_cache
    stamp = (stat.st_mtime_ns, stat.st_size)
    if stamp != _attacker_ips_stamp:
        _attacker_ips_cache = _get_attacker_ips()
        _attacker_ips_stamp = stamp
    return _attacker_ips_cache


_source_cache: dict[str, dict] = {}
_source_cache_stamp: dict[str, tuple[int, int]] = {}
_rows_cache: dict[str, tuple[tuple[int, int], list[dict]]] = {}


def _load_json_rows(filepath: Path) -> list[dict] | None:
    try:
        stat = filepath.stat()
        stamp = (stat.st_mtime_ns, stat.st_size)
        maximum_size = DASHBOARD_CONFIG.get("atomic_max_file_bytes", 100 * 1024 * 1024)
        if stat.st_size > maximum_size:
            app.logger.warning("atomic source rejected as oversized: %s", filepath.name)
            return None
        cached = _rows_cache.get(str(filepath))
        if cached and cached[0] == stamp:
            return cached[1]
        raw = json.loads(
            filepath.read_text(encoding="utf-8"),
            parse_constant=_reject_nonfinite_json,
        )
    except (OSError, UnicodeError, ValueError):
        return None
    if isinstance(raw, dict) and "results" in raw:
        rows = raw["results"]
    elif isinstance(raw, list):
        rows = raw
    else:
        return None
    if not isinstance(rows, list) or not rows or not all(isinstance(row, dict) for row in rows):
        return None
    if len(rows) > DASHBOARD_CONFIG.get("atomic_max_records", 250_000):
        app.logger.warning("atomic source rejected for excessive records: %s", filepath.name)
        return None
    _rows_cache[str(filepath)] = (stamp, rows)
    return rows


def _collect_fields(rows: list[dict]) -> list[str] | None:
    fields: list[str] = []
    seen: set[str] = set()
    maximum = DASHBOARD_CONFIG.get("atomic_max_fields", 250)
    for row in rows:
        for key in row:
            if not isinstance(key, str):
                return None
            if key not in seen:
                seen.add(key)
                fields.append(key)
                if len(fields) > maximum:
                    return None
    return fields


def _parse_event_time(value: object) -> datetime | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        seconds = float(value)
        if abs(seconds) > 100_000_000_000:
            seconds /= 1000
        try:
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_query_bound(value: str, *, end: bool = False) -> datetime | None:
    parsed = _parse_event_time(value)
    if parsed is not None and end and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value.strip()):
        return parsed + timedelta(days=1)
    return parsed


def _detect_ip_field(fields: list[str]) -> str:
    for f in fields:
        if f.lower() in ("ipaddress", "ip", "clientip", "sourceip", "src_ip"):
            return f
    return ""


def _detect_time_field(fields: list[str]) -> str:
    for f in fields:
        if f.lower() in ("timestamp", "time", "createddatetime", "eventtime"):
            return f
    return ""


def discover_atomic_sources() -> list[dict]:
    sources = []
    if not ARTIFACTS_DIR.exists():
        return sources
    for f in sorted(ARTIFACTS_DIR.iterdir()):
        safe_file = contained_artifact_path(f)
        if safe_file is None or safe_file.parent != ARTIFACTS_DIR.resolve():
            continue
        try:
            stat = safe_file.stat()
        except OSError:
            continue
        if not f.name.endswith(".json") or stat.st_size < 100:
            continue
        stamp = (stat.st_mtime_ns, stat.st_size)
        if f.name in _source_cache_stamp and _source_cache_stamp[f.name] == stamp:
            if f.name in _source_cache:
                sources.append(_source_cache[f.name])
            continue
        rows = _load_json_rows(safe_file)
        if rows is None or len(rows) < 2:
            continue
        fields = _collect_fields(rows)
        if not fields:
            continue
        time_field = _detect_time_field(fields)
        if not time_field:
            continue
        ip_field = _detect_ip_field(fields)
        name_parts = f.name.split("__")
        raw_label = name_parts[-1] if len(name_parts) >= 2 else f.name
        label = raw_label.removesuffix(".json").replace("_", " ").strip().title()
        src = {
            "id": f.name,
            "label": label,
            "fields": fields,
            "time_field": time_field,
            "ip_field": ip_field,
            "record_count": len(rows),
        }
        _source_cache[f.name] = src
        _source_cache_stamp[f.name] = stamp
        sources.append(src)
    return sources


@app.route("/api/atomic-sources")
@require_auth
def api_atomic_sources():
    return jsonify(discover_atomic_sources())


@app.route("/api/atomic-query")
@require_auth
def api_atomic_query():
    source_id = request.args.get("source", "")
    if not source_id:
        return jsonify({"events": [], "error": "No source specified"})

    if Path(source_id).name != source_id:
        return jsonify({"events": [], "error": "Source not found"}), 404
    known_sources = {source["id"] for source in discover_atomic_sources()}
    if source_id not in known_sources:
        return jsonify({"events": [], "error": "Source not found"}), 404
    filepath = contained_artifact_path(ARTIFACTS_DIR / source_id)
    if filepath is None:
        return jsonify({"events": [], "error": "Source not found"})

    rows = _load_json_rows(filepath)
    if rows is None:
        return jsonify({"events": [], "error": "Failed to load data"})

    fields = _collect_fields(rows)
    if not fields:
        return jsonify({"events": [], "error": "Dataset has invalid or excessive fields"}), 422
    time_field = _detect_time_field(fields)
    ip_field = _detect_ip_field(fields)

    date_from = request.args.get("from", "")
    date_to = request.args.get("to", "")
    ip_filter = request.args.get("ip", "")
    text_search = request.args.get("q", "").lower()
    field_filters = {}
    for key in request.args:
        if key.startswith("f_"):
            field_filters[key[2:]] = request.args[key]
    try:
        limit = max(1, min(int(request.args.get("limit", "500")), 5000))
        offset = max(0, int(request.args.get("offset", "0")))
    except ValueError:
        return jsonify({"events": [], "error": "limit and offset must be integers"}), 400
    meta_only = request.args.get("meta") == "1"

    date_from_dt = _parse_query_bound(date_from) if date_from else None
    date_to_dt = _parse_query_bound(date_to, end=True) if date_to else None
    if date_from and date_from_dt is None:
        return jsonify({"events": [], "error": "Invalid from timestamp"}), 400
    if date_to and date_to_dt is None:
        return jsonify({"events": [], "error": "Invalid to timestamp"}), 400
    unknown_filters = sorted(set(field_filters) - set(fields))
    if unknown_filters:
        return jsonify({"events": [], "error": f"Unknown filter field: {unknown_filters[0]}"}), 400

    if meta_only:
        uniques = {}
        for f in fields:
            vals = set()
            for row in rows:
                v = row.get(f)
                if v and isinstance(v, str) and len(v) < 200:
                    vals.add(v)
                if len(vals) >= 200:
                    break
            if 2 <= len(vals) <= 200:
                sorted_vals = sorted(vals)
                if ip_field and f == ip_field:
                    sorted_vals = sorted(vals, key=lambda x: (x not in get_attacker_ips(), x))
                uniques[f] = sorted_vals
        return jsonify({"fields": fields, "uniques": uniques,
                        "time_field": time_field, "ip_field": ip_field,
                        "record_count": len(rows)})

    events = []
    all_times: list[datetime] = []
    matched_count = 0
    for row in rows:
        ts = row.get(time_field, "") if time_field else ""
        parsed_time = _parse_event_time(ts)
        if date_from_dt and (parsed_time is None or parsed_time < date_from_dt):
            continue
        if date_to_dt and (parsed_time is None or parsed_time >= date_to_dt):
            continue
        if ip_filter and ip_field:
            if ip_filter != row.get(ip_field, ""):
                continue
        skip = False
        for fk, fv in field_filters.items():
            rv = str(row.get(fk, ""))
            if fv.lower() not in rv.lower():
                skip = True
                break
        if skip:
            continue
        if text_search:
            haystack = " ".join(str(v) for v in row.values()).lower()
            if text_search not in haystack:
                continue
        matched_count += 1
        if parsed_time:
            all_times.append(parsed_time)
        if matched_count > offset and len(events) < limit:
            evt = dict(row)
            if ip_field:
                evt["_is_attacker"] = row.get(ip_field, "") in get_attacker_ips()
            evt["_time"] = ts
            events.append(evt)

    BUCKET_OPTIONS = [
        60, 300, 900, 3600, 21600, 86400,
    ]

    bucket_seconds = 3600
    if len(all_times) >= 2:
        t_min, t_max = min(all_times), max(all_times)
        span = max((t_max - t_min).total_seconds(), 1)
        bucket_seconds = next((size for size in BUCKET_OPTIONS if span / size <= 80), 86400)

    histogram = {}
    for event_time in all_times:
        bucket_epoch = int(event_time.timestamp()) // bucket_seconds * bucket_seconds
        key = datetime.fromtimestamp(bucket_epoch, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        histogram[key] = histogram.get(key, 0) + 1

    return jsonify({
        "events": events,
        "total_in_dataset": len(rows),
        "total_matched": matched_count,
        "returned": len(events),
        "offset": offset,
        "truncated": matched_count > offset + len(events),
        "fields": fields,
        "time_field": time_field,
        "ip_field": ip_field,
        "histogram": dict(sorted(histogram.items())),
        "bucket_seconds": bucket_seconds,
    })


@app.route("/api/atomic-search")
@require_auth
def api_atomic_search():
    q = request.args.get("q", "").lower()
    if not q or len(q) < 2:
        return jsonify({"results": [], "error": "Query too short (min 2 chars)"})
    try:
        limit = max(1, min(int(request.args.get("limit", "200")), 1000))
    except ValueError:
        return jsonify({"results": [], "error": "limit must be an integer"}), 400

    sources = discover_atomic_sources()
    ranked_results: list[tuple[float, int, dict]] = []
    total_matched = 0
    sequence = 0
    for src in sources:
        filepath = contained_artifact_path(ARTIFACTS_DIR / src["id"])
        if filepath is None:
            continue
        rows = _load_json_rows(filepath)
        if not rows:
            continue
        time_field = src["time_field"]
        ip_field = src["ip_field"]
        for row in rows:
            haystack = " ".join(str(v) for v in row.values()).lower()
            if q in haystack:
                total_matched += 1
                sequence += 1
                evt = dict(row)
                evt["_source"] = src["label"]
                evt["_source_id"] = src["id"]
                evt["_time"] = row.get(time_field, "")
                if ip_field:
                    evt["_is_attacker"] = row.get(ip_field, "") in get_attacker_ips()
                parsed = _parse_event_time(evt["_time"])
                rank = parsed.timestamp() if parsed is not None else float("inf")
                candidate = (-rank, -sequence, evt)
                if len(ranked_results) < limit:
                    heapq.heappush(ranked_results, candidate)
                elif rank < -ranked_results[0][0]:
                    heapq.heapreplace(ranked_results, candidate)

    all_results = [item[2] for item in ranked_results]
    all_results.sort(key=lambda e: _parse_event_time(e.get("_time")) or datetime.max.replace(tzinfo=timezone.utc))
    return jsonify({
        "results": all_results,
        "total_returned": len(all_results),
        "total_matched": total_matched,
        "truncated": total_matched > len(all_results),
        "sources_searched": len(sources),
    })


@app.route("/download/<art_id>")
@require_auth
def download_artifact(art_id):
    evidence = parse_evidence_index()
    if art_id not in evidence:
        abort(404)
    stored = evidence[art_id].get("stored_path", "")
    if not stored:
        abort(404)
    filepath = contained_artifact_path(PROJECT_ROOT / stored)
    if filepath is None:
        abort(404)
    app.logger.info("artifact download id=%s remote=%s", art_id, request.remote_addr)
    return send_file(filepath, as_attachment=True, download_name=evidence[art_id].get("name", filepath.name))


@app.route("/api/sync-check")
@require_auth
def api_sync_check():
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    import sync_check
    return jsonify(sync_check.run_all_checks())


@app.route("/api/intake", methods=["POST"])
@require_auth
def api_intake():
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    import intake
    incoming = PROJECT_ROOT / "incoming"
    if not incoming.exists():
        return jsonify({"results": [], "message": "No incoming/ directory"})
    files = sorted(f for f in incoming.iterdir() if f.is_file() and not f.name.startswith("."))
    if not files:
        return jsonify({"results": [], "message": "No files to process"})
    try:
        results = intake.ingest_files(files)
    except (OSError, RuntimeError, ValueError) as exc:
        app.logger.exception("evidence intake transaction failed")
        return jsonify({"results": [], "ingested": 0, "failed": len(files), "error": str(exc)}), 409
    ok = [r for r in results if "error" not in r and r.get("verified", True)]
    app.logger.info("evidence intake remote=%s ingested=%d failed=%d", request.remote_addr, len(ok), len(results) - len(ok))
    public_results = []
    for result in results:
        public_results.append({key: value for key, value in result.items() if key in {
            "artifact_id", "original_name", "sha256", "verified", "ingest_utc",
            "stored_path", "size", "error",
        }})
    return jsonify({
        "results": public_results,
        "ingested": len(ok),
        "failed": len(results) - len(ok),
        "message": f"{len(ok)} file(s) ingested; analysis remains pending in the review queue" if ok else "No files ingested successfully",
    })


@app.route("/api/review-queue")
@require_auth
def api_review_queue():
    content = read_mb("reviewQueue.md")
    items = []
    blocks = re.split(r"^### (RQ-\d{3})\s*\u2014\s*(.+?)$", content, flags=re.MULTILINE)
    i = 1
    while i < len(blocks) - 1:
        rq_id = blocks[i].strip()
        title = blocks[i + 1].strip()
        body = blocks[i + 2] if i + 2 < len(blocks) else ""
        block_pos = content.find(f"### {rq_id}")
        done_pos = content.find("## Done")
        section = "done" if (done_pos != -1 and block_pos > done_pos) else "pending"
        status_m = re.search(r"- Status:\s*(\w+)", body)
        status = status_m.group(1) if status_m else "PENDING"
        checked = len(re.findall(r"- \[x\]", body))
        unchecked = len(re.findall(r"- \[ \]", body))
        added_m = re.search(r"- Added:\s*(.+)", body)
        added = added_m.group(1).strip() if added_m else ""
        items.append({
            "id": rq_id,
            "title": title,
            "status": status,
            "section": section,
            "checked": checked,
            "unchecked": unchecked,
            "total_tasks": checked + unchecked,
            "added": added,
        })
        i += 3

    pending = [it for it in items if it["section"] == "pending"]
    done = [it for it in items if it["section"] == "done"]
    total_unchecked = sum(it["unchecked"] for it in pending)

    return jsonify({
        "pending": pending,
        "done": done,
        "total_pending": len(pending),
        "total_unchecked_tasks": total_unchecked,
    })


# ---------------------------------------------------------------------------
#  SSL Certificate Generation
# ---------------------------------------------------------------------------

def generate_self_signed_cert():
    cert_file = CERTS_DIR / "cert.pem"
    key_file = CERTS_DIR / "key.pem"
    shared = bool(DASHBOARD_CONFIG.get("shared_group_access", False))
    dir_mode, file_mode = (0o770, 0o660) if shared else (0o700, 0o600)
    if CERTS_DIR.is_symlink() or cert_file.is_symlink() or key_file.is_symlink():
        raise RuntimeError("TLS certificate directory and files must not be symlinks")
    CERTS_DIR.mkdir(parents=True, exist_ok=True, mode=dir_mode)
    CERTS_DIR.chmod(dir_mode)
    if cert_file.exists() and key_file.exists():
        cert_file.chmod(file_mode)
        key_file.chmod(file_mode)
        return str(cert_file), str(key_file)

    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    import datetime as dt

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "IR Dashboard"),
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(dt.datetime.now(dt.timezone.utc))
        .not_valid_after(dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.IPAddress(__import__("ipaddress").IPv4Address("127.0.0.1")),
                x509.IPAddress(__import__("ipaddress").IPv4Address("0.0.0.0")),
            ]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    key_file.write_bytes(
        key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption())
    )
    cert_file.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_file.chmod(file_mode)
    cert_file.chmod(file_mode)

    return str(cert_file), str(key_file)


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------

def main():
    global PASSWORD_HASH, DASHBOARD_CONFIG

    DASHBOARD_CONFIG = load_config()

    parser = argparse.ArgumentParser(description="Incident Response Dashboard")
    parser.add_argument("--port", type=int, default=8443)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--password", default=None, help="Dashboard password (generated if omitted)")
    parser.add_argument("--no-ssl", action="store_true", help="Disable HTTPS")
    parser.add_argument("--no-auth", action="store_true", help="Disable password authentication")
    parser.add_argument(
        "--allow-insecure-remote", action="store_true",
        help="Explicitly permit a non-loopback bind with --no-ssl or --no-auth",
    )
    args = parser.parse_args()

    try:
        loopback = args.host.lower() == "localhost" or ipaddress.ip_address(args.host).is_loopback
    except ValueError:
        loopback = False
    if not loopback and (args.no_ssl or args.no_auth) and not args.allow_insecure_remote:
        parser.error(
            "a non-loopback bind with --no-ssl or --no-auth requires "
            "--allow-insecure-remote"
        )

    title = DASHBOARD_CONFIG.get("title", "IR Dashboard")

    if args.no_auth:
        PASSWORD_HASH = None
        # Bypass auth decorator
        app.before_request_funcs.setdefault(None, []).insert(0, lambda: session.update(authenticated=True))
    else:
        password = args.password or os.environ.get("DASHBOARD_PASSWORD")
        if not password:
            password = secrets.token_urlsafe(16)
            print(f"\n  Generated password: {password}\n")
        PASSWORD_HASH = generate_password_hash(password)

    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)
    print(f"  Memory bank : {MEMORY_BANK}")
    print(f"  Artifacts   : {ARTIFACTS_DIR}")

    if args.no_ssl:
        app.config["SESSION_COOKIE_SECURE"] = False
        url = f"http://{args.host}:{args.port}"
        print(f"  URL         : {url}")
        print("=" * 60)
        app.run(host=args.host, port=args.port, debug=False)
    else:
        app.config["SESSION_COOKIE_SECURE"] = True
        cert_file, key_file = generate_self_signed_cert()
        url = f"https://{args.host}:{args.port}"
        print(f"  URL         : {url}")
        print(f"  Certs       : {cert_file}")
        print("=" * 60)

        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert_file, key_file)
        app.run(host=args.host, port=args.port, ssl_context=context, debug=False)


if __name__ == "__main__":
    main()
