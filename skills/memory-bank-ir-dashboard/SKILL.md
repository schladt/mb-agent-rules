---
name: memory-bank-ir-dashboard
description: Set up and operate the optional local incident-response dashboard and evidence pipeline. Use when an incident-response project needs evidence intake, investigation visualization, event search, or dashboard operation.
---

# IR Dashboard Skill

Procedures for setting up and operating the incident response dashboard — a live
web application that reads directly from the memory bank and artifact store to
provide a visual interface for the investigation.

## When to Use

Use this skill when:
- Setting up a new incident response project that needs a visual dashboard
- The user asks to visualize the investigation, browse evidence, or search events
- The incident has accumulated enough data (timeline entries, findings, artifacts)
  that a dashboard would improve situational awareness

## Prerequisites

- An incident-response memory bank must be initialized (`AGENTS.md` with the
  incident-response profile, `memory-bank/` with the required files)
- Python 3.10+ available on the system
- `flask` and `cryptography` packages (auto-installed by `start.sh`)

## Setup

### Automated Setup

Run the setup script from the `mb-agent-rules` repository:

```bash
bash /path/to/mb-agent-rules/skills/memory-bank-ir-dashboard/setup.sh /path/to/project \
  --title "Operation Cobalt" \
  --brand "Security Team" \
  --accent "#10b981" \
  --with-sample-data
```

This copies the dashboard, scripts, and configuration into the project.

### Manual Setup

1. Copy `skills/memory-bank-ir-dashboard/dashboard/` → `<project>/dashboard/`
2. Copy `skills/memory-bank-ir-dashboard/scripts/` → `<project>/scripts/`
3. Create `<project>/incoming/` and `<project>/artifacts/`
4. Create `<project>/dashboard.config.json` with branding preferences
5. Create `<project>/memory-bank/reviewQueue.md` from the template
6. Confirm `.agents/skills/memory-bank-ir-evidence-review/SKILL.md` is installed
7. Add evidence and dashboard runtime paths to `.gitignore`

### Configuration

Create `dashboard.config.json` at the project root:

```json
{
  "title": "Operation Name — IR Dashboard",
  "brand": "Your Team",
  "accent_color": "#3b82f6",
  "logo_url": "",
  "shared_group_access": false,
  "atomic_max_file_bytes": 104857600,
  "atomic_max_records": 250000,
  "atomic_max_fields": 250,
  "css_overrides": {
    "bg": "#0a0e14",
    "surface": "#111827"
  }
}
```

| Key | Description | Default |
|-----|-------------|---------|
| `title` | Dashboard title (header + browser tab) | `IR Dashboard` |
| `brand` | Small uppercase text in header left corner | _(empty)_ |
| `accent_color` | Primary UI accent color (hex) | `#3b82f6` |
| `logo_url` | `/static/` path or `data:image/` URL | _(empty)_ |
| `css_overrides` | Map of CSS custom property names to values | `{}` |
| `shared_group_access` | Use 0770/0660 instead of private 0700/0600 evidence modes | `false` |
| `atomic_max_file_bytes` | Maximum JSON event-source size | 100 MiB |
| `atomic_max_records` | Maximum records per JSON event source | 250,000 |
| `atomic_max_fields` | Maximum union of fields per source | 250 |

Available CSS variables for `css_overrides`: `bg`, `surface`, `surface-raised`,
`border`, `border-light`, `text`, `text-secondary`, `text-dim`, `accent`,
`danger`, `warning`, `success`, `info`, `purple`.

## Starting the Dashboard

```bash
cd <project>/dashboard
bash start.sh --port 8443
```

Options:
- `--port <N>` — listen port (default: 8443)
- `--host <addr>` — bind address (default: 127.0.0.1)
- `--password <pw>` — dashboard password (auto-generated if omitted)
- `--no-ssl` — disable HTTPS (use HTTP)
- `--no-auth` — disable password authentication entirely
- `--allow-insecure-remote` — explicit acknowledgement required if a
  non-loopback bind is combined with `--no-ssl` or `--no-auth`

Environment variable `DASHBOARD_PASSWORD` is also supported and is preferred
over `--password`, which can expose a secret in process listings or shell history.

## Dashboard Tabs

| Tab | Data Source | Description |
|-----|------------|-------------|
| Executive Summary | `incidentBrief.md`, all files | Dynamic overview with metrics, classification, and verification status |
| Timeline | `timeline.md` | Chronological events with actor filtering and artifact links |
| Evidence | `evidenceIndex.md` | All indexed artifacts with hash verification and download |
| Findings | `findings.md` | Analytical conclusions with expandable details |
| Questions | `findings.md` (gaps section) | Open and answered investigation questions |
| IOCs & TTPs | `indicators.md` | Indicator tables and ATT&CK technique mapping |
| Assets | `affectedAssets.md` | Systems, accounts, and data with status tracking |
| Theory & Plan | `activeContext.md` | Working theory, current objective, and blockers |
| Next Steps | `activeContext.md` | Prioritized action items parsed from context |

## Atomic Event Viewer

The Timeline tab includes an Atomic Events toggle that provides a raw event
browser for JSON data sources in `artifacts/`.

**Auto-detection**: Any contained, non-symlink JSON file in `artifacts/` within
the configured size/record/field bounds and with a `Timestamp`, `Time`,
`CreatedDateTime`, or `EventTime` field is discovered as a data source.

**Features**:
- Dynamic filter dropdowns (searchable, with attacker IP highlighting)
- Time range selection with histogram visualization
- Global search across all data sources simultaneously
- Click any row for full detail in the side panel
- Attacker IP rows highlighted in red

**Adding new data sources**: Drop any JSON file with timestamped records into
`artifacts/`. It appears in the dropdown immediately — no code changes needed.

## Evidence Intake Pipeline

### Via Dashboard

Click **Sync Check** → **Run Intake** in the dashboard header.

### Via Command Line

```bash
python scripts/intake.py                    # process all files in incoming/
python scripts/intake.py --dry-run          # preview without processing
python scripts/intake.py path/to/file.json  # process a specific file
python scripts/intake.py --provided-by "Analyst Name" --source-system "EDR export"
```

### Intake Steps

1. Take an exclusive project intake lock and recover any journaled transaction
2. Compute the source SHA-256 and UTC intake timestamp
3. Copy to a private pending file and re-hash the copy
4. Allocate sequential artifact and queue IDs while still holding the lock
5. Persist a recovery journal, place artifacts, and atomically update
   `evidenceIndex.md`, `reviewQueue.md`, and `progress.md`
6. Append a hash-chained transaction to `artifacts/.custody-manifest.jsonl`
7. Remove an `incoming/` source only after the full metadata commit

A mismatch preserves the source and quarantines the failed copy. Intake records
custody and queues analysis; it never infers event times, relevance, findings, or
IOCs. Use the installed `memory-bank-ir-evidence-review` skill to perform that judgment-bearing
work when an analyst asks for it.

The custody manifest detects interior edits and reordering. It is stored beside
the evidence, so a higher-assurance deployment should copy each latest manifest
hash into an external immutable case-management or logging system; a local chain
alone cannot prove that the entire file was replaced or truncated.

### Review Queue

After intake, artifacts are placed in a review queue (`reviewQueue.md`). Each
entry includes a checklist:
- Assess relevance
- Place events on timeline
- Record findings
- Extract IOCs
- Update active context

The dashboard shows a badge on the Queue button when items are pending.

## Sync Check

The consistency validator checks operational authority/readiness fields,
required schemas, artifact custody fields and streaming hashes, path containment,
symlinks, permissions, interrupted transactions, orphans/quarantine, dangling
references, ART/F/RQ ID integrity, review queue status, and the complete
`executiveSummary.json` schema and references.

Run from CLI:
```bash
python scripts/sync_check.py          # human-readable report
python scripts/sync_check.py --json   # JSON for programmatic use
```

Or click **Sync Check** in the dashboard header.

## Executive Summary

The Executive Summary tab is driven by `memory-bank/executiveSummary.json`,
an AI-generated file that contains structured narrative content, attack phase
summaries, curated key findings, investigation status, and unresolved questions.

This file is generated by the `memory-bank-ir-evidence-review` skill as the final step of
post-intake analysis. If the file does not exist, the dashboard falls back to
parsing raw markdown from the memory bank files.

See `skills/memory-bank-ir-evidence-review/SKILL.md` for the JSON schema and writing guidelines.

## Sample Data

The `sample-data/` directory contains a synthetic ransomware scenario for
demo purposes. See `sample-data/README.md` for details.

To load it during setup:
```bash
bash setup.sh /path/to/project --with-sample-data
```

Or manually copy the JSON files to `<project>/incoming/` and run intake.

## Constraints

- The dashboard is read-only outside explicit intake, which transactionally
  updates `evidenceIndex.md`, `reviewQueue.md`, and `progress.md`
- All data is served from the local filesystem — no external API calls
- Session cookies use `HttpOnly`, `SameSite=Lax`, and `Secure` under HTTPS;
  unsafe methods are CSRF protected and login attempts are rate-limited
- HTTPS uses auto-generated self-signed certificates (production deployments
  should provide real certificates)
