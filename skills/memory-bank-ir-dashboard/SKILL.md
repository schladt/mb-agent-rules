---
name: memory-bank-ir-dashboard
description: Set up and operate the optional private-development incident-response dashboard and classified evidence pipeline. Use for evidence intake, investigation visualization, event search, and preservation-aware deployment upgrades.
---

# IR Dashboard

Read project `AGENTS.md` and authority files first. This optional Flask dashboard
is a private development tool, not production infrastructure or an external
client-status publisher. Python 3.10+, Flask and cryptography are required; the
launcher provisions dependencies locally. No external APIs or uploads are used.

## Setup and upgrade

Initialize the incident-response profile with `.memory-bank/` first. Legacy
projects must run the installer’s explicit `--migrate` flow before setup; there
is no old-bank fallback.

```bash
bash /path/to/mb-agent-rules/skills/memory-bank-ir-dashboard/setup.sh /path/to/project \
  --title "Operation Cobalt" --brand "Security Team" --accent "#10b981"
```

Setup deploys the complete `dashboard/` and `scripts/` packages, including
`ir_common.py`. These source files remain trackable. Configuration lives at
`.memory-bank/dashboard.config.json`; certificates, virtual environment, cache,
and deployment receipt live beneath `.memory-bank/runtime/dashboard/`.
Custody manifest, transaction journal and intake lock live in
`.memory-bank/artifacts/`. Only `/.memory-bank/` is added to `.gitignore`;
existing user exclusions are preserved.

Re-running setup updates unchanged managed code. Locally modified or
unrecognized managed files cause a conflict before code replacement. Review
those changes, then use `--upgrade` to authorize replacement: previous changed
files are copied beneath `.memory-bank/backups/dashboard-<timestamp>-*/` before
any replacement. Unrelated user files are never removed. Do not delete the
existing dashboard to reinstall. Configuration is preserved; `--shared-group`
explicitly enables 0770/0660 handling rather than default 0700/0600.

`--with-sample-data` copies synthetic samples to the bank incoming directory
without overwriting existing drops. It does not classify or ingest them.

## Run

```bash
bash dashboard/start.sh --port 8443
```

Options: `--host` (default 127.0.0.1), `--port` (8443), `--password`, `--no-ssl`,
`--no-auth`. Prefer `DASHBOARD_PASSWORD` over a command-line password. Remote
binding without TLS or authentication requires `--allow-insecure-remote`.
Cookies are HttpOnly, SameSite=Lax, and Secure with TLS. Unsafe methods use CSRF
protection, login attempts are rate-limited, and TLS defaults to a local
self-signed certificate. These safeguards do not make this a production server.

## Configuration

`.memory-bank/dashboard.config.json` accepts:

| Key | Default / meaning |
|---|---|
| `title` | `IR Dashboard` |
| `brand` | Empty brand text |
| `accent_color` | `#3b82f6`, 3/6/8-digit hex color |
| `logo_url` | Empty; otherwise `/static/` or `data:image/` |
| `css_overrides` | Empty map; supported theme variables only |
| `shared_group_access` | `false`; explicit group access policy |
| `atomic_max_file_bytes` | 104857600 |
| `atomic_max_records` | 250000 |
| `atomic_max_fields` | 250 |

## Classified evidence intake

Incoming is `.memory-bank/incoming/`, shared with reference and operational
intake. Do not treat every drop as incident evidence. **Sync Check → Run Intake**
opens a selection view: choose only acquired evidence, then acquire the selected
files. Unselected files, hidden drops and nested directories remain visible and
pending. Operational credentials and reference material use the shared
`memory-bank-workflow` classified intake instead. Selecting evidence authorizes
its custody acquisition and source removal only after the verified transaction
commits; acquisition is distinct from optional reference archival and analysis.

```bash
python3 -B scripts/intake.py .memory-bank/incoming/selected-evidence.json
python3 -B scripts/intake.py --dry-run path/to/selected-evidence.json
python3 -B scripts/intake.py --provided-by "Analyst" --source-system "EDR export" path/to/evidence.json
python3 -B scripts/intake.py --retain-source --json path/to/evidence.json
python3 -B scripts/intake.py  # recover any pending transaction; never bulk-ingest drops
```

Positional files are an explicit acquired-evidence classification. `--dry-run`
hashes the source but performs no copying, recovery, ID reservation or writes;
its receipt has `verified: false`, `source_hashed: true`, and proposed IDs.
`--retain-source` leaves incoming evidence in place for the shared workflow’s
separate authorized disposition. `--json` emits
`{"results":[...],"ingested":N,"failed":N}`. A committed result includes
`artifact_id`, project-relative `stored_path`, `sha256`, and `verified: true`.
Failures exit nonzero; never interpret a preview or failed acquisition as custody.

Real intake:
1. Locks the artifact store and recovers a journal even when incoming is empty.
2. Hashes a stable source, copies to a private pending artifact, re-hashes it.
3. Allocates ART and RQ IDs under the lock and writes a recovery journal.
4. Places evidence, appends the hash-chained custody transaction, and atomically
   updates `evidenceIndex.md`, `reviewQueue.md`, and `progress.md`.
5. Removes an unchanged incoming source only after the complete commit, unless
   `--retain-source` was selected. External sources are retained.

Mismatches preserve the source and quarantine the bad copy. Interrupted
transactions retain stable artifact/queue IDs and transaction identity. Existing
custody bytes and hashes are never rewritten for migration: an explicit
`.memory-bank/path-migrations.json` receipt resolves historical paths into the
canonical bank, not into old stores. For stronger custody, anchor manifest hashes
in an external immutable case system; a local chain alone cannot prove no whole
file truncation or replacement occurred.

## Review, status and executive narrative

Acquisition queues analysis; it does not infer event times, relevance, findings,
IOCs, exfiltration or attack phases. Ask the `memory-bank-ir-evidence-review`
skill to perform authorized inert analysis. Queue state comes from explicit
PENDING / IN_PROGRESS / DONE plus the checklist, never section location alone.
DONE requires a nonempty, fully checked checklist. Section/status contradictions
are displayed and reported by Sync Check rather than silently hiding work.

The dashboard reads investigative records from the bank. Executive narrative
is the internal derived `executiveSummary.json`, validated by the same schema
and reference validator used by Sync Check. Invalid projections are visibly
unavailable. Without one, only documented facts/theory are shown; there is no
keyword-generated attack phase or inventory-to-exfiltration inference.

Execution status is shown directly from `.memory-bank/project-status.md`, the
single execution-status authority. The analytical JSON `status` member is
retained as a schema-required investigative snapshot, not displayed as a competing
execution source. The dashboard does not publish root `team-status.md`.
Use the shared workflow’s `status` / `status --check` commands for that projection,
headed `# Team Status`. It provides detailed coordination for teammates without
memory-bank access, not client-facing reporting. Client-facing reports/exports
belong in `deliverables/` and client updates in the project's separate client
update file. `--external-status` and `external_status` mean team output outside the
bank. Publishable means approved for team readership, not public/client permission;
the source and receipt remain private.

When editing execution status, preserve `# Project Status`, `## Publishable`,
the five ordered `###` sections Progress, Milestones, Blockers, Next Steps,
Client Actions, then `## Internal`. Keep sections nonempty, without extra
subheadings or code fences in Publishable. Use bold workstream labels and nested
bullets or tables for substantive standalone context/scope and coverage,
work/results, milestones and known owners/dates, blocker impacts and unblocking
steps, prioritized actionable next steps and client dependencies. State unknowns;
never fabricate completion, certainty, owners or dates. Dates describe sourced facts,
not generator timestamps. Describe results/context in prose even with links.
Links must be team-accessible and resolve relative to root `team-status.md`, not
the bank source; `.memory-bank/` links, raw evidence and opaque artifact IDs cannot
be required context. Generation depends on the private authority; readership does
not. Preserve warning-only privacy diagnostics and prior valid output on generation
failure; disclose errors/staleness. Warnings do not prove sanitization or grant
sharing permission.

## Atomic event viewer and checks

Contained, non-symlink JSON files in `.memory-bank/artifacts/` within configured
bounds are discovered automatically when records have a supported timestamp
field. Use custody intake rather than dropping unindexed originals directly into
the artifact store. Evidence fields are literal inert text, including quoted
attribute values. The viewer supports dynamic filters, UTC ranges with minute or
second precision, global search, histogram navigation and event detail. Invalid
queries and non-success API responses are displayed as errors, not zero results.

```bash
python3 -B scripts/sync_check.py
python3 -B scripts/sync_check.py --json
```

Sync Check reports authority/readiness, schema, custody hashes and transaction
chain, containment/symlinks/permissions, pending transaction, orphan/quarantine,
ART/F/RQ references, queue consistency, all pending incoming drops, and the
shared executive projection validator. Actual errors remain errors regardless of
soft repository conventions. See `DASHBOARD.md` for API contracts.
