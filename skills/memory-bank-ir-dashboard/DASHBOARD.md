# IR Dashboard — Technical Reference

## Storage and deployment

Tracked deployed code is `dashboard/{app.py,templates/,start.sh,requirements.txt}`
and `scripts/{intake.py,sync_check.py,ir_common.py}`. The only live memory bank is
`.memory-bank/`; no legacy fallback is supported. It directly contains cognitive
records, incoming, artifacts, sensitive, references, planning, backups and runtime.
Configuration is `.memory-bank/dashboard.config.json`; TLS certificates, venv,
cache and deployment receipt are under `.memory-bank/runtime/dashboard/`.
The intake lock, journal and custody manifest remain alongside private artifacts.
The launcher and scripts disable source bytecode caches.

Setup checks conflicts before updating code, preserves changed files in a unique
private backup, and records source hashes. `--upgrade` explicitly permits replacing
locally modified or previously unrecognized managed files after backup. Unrelated
files and existing configuration are preserved. Run the installer migration first
for legacy banks/runtime stores. This remains a private-development Flask tool;
there is no production WSGI or locking architecture change.

## API

All data endpoints require the configured authentication; POST requests additionally
require `X-CSRF-Token`. Login is public with its own CSRF form token.

| Method | Path | Contract |
|---|---|---|
| GET | `/` | Main dashboard |
| GET/POST | `/login` | Login form / authenticate |
| POST | `/logout` | Clear session |
| GET | `/api/data` | Parsed investigative records, executive projection and `execution_status` directly from the internal authority |
| GET | `/api/artifact/<ART-id>` | Artifact metadata |
| GET | `/download/<ART-id>` | Contained, non-symlink artifact download |
| GET | `/api/atomic-sources` | Bounded JSON event sources |
| GET | `/api/atomic-query` | Event query / metadata |
| GET | `/api/atomic-search` | Text search across sources |
| GET | `/api/sync-check` | Real errors, warnings and counts |
| GET | `/api/incoming` | `drops: [{name, selectable}]`, including hidden and nested pending drops (except `.gitkeep`) |
| POST | `/api/intake` | `{kind:"artifact", files:["selected-name.json"]}`; empty files runs recovery only |
| GET | `/api/review-queue` | Explicit-status/checklist-derived pending/done arrays, pending counts and consistency `errors` |

Intake rejects non-basename selections and symlinks. Unselected files are never
acquired. A successful response has `results`, `ingested`, `failed`, and `message`;
transaction or per-file failures return HTTP 409. UI clients must check HTTP status,
not treat an error object as an empty dataset. A selected incoming source is removed
only after committed verified acquisition. The CLI additionally supports
`--retain-source --json` for the classified workspace workflow.

## Event queries

| Parameter | Meaning |
|---|---|
| `source` | Filename relative to `.memory-bank/artifacts/` |
| `from`, `to` | UTC timestamp bounds; minute and second precision accepted |
| `ip` | Detected IP-field value |
| `q` | Text across fields |
| `f_<field>` | Exact field-value filter |
| `limit`, `offset` | Bounded pagination |
| `meta=1` | Field metadata / unique filter values |

Time input is serialized once with `Z`, never by blindly appending seconds.
Histograms select a bucket size based on range. JSON records must all be objects
and satisfy configured file/record/union-field limits. Supported timestamps include
`Timestamp`, `Time`, `CreatedDateTime`, and `EventTime`. IP filtering recognizes
`IPAddress`, `IP`, `ClientIP`, and `SourceIP`. Confirmed IP indicators are visually
highlighted; a raw download event or inventory count does not establish exfiltration.
Raw record values are escaped in text and attribute contexts and never evaluated.

## Authority and shared validation

`.memory-bank/project-status.md` is the execution-status authority and is displayed
as literal local Markdown content. Executive JSON is an internal analytical
projection only; its `status` field is not a competing execution display or external
publication source. No projection means no inferred attack phases. Invalid JSON or
schema/reference failures produce a visible analytical-projection error.

`ir_common.projection_errors(value, findings=..., artifacts=...)` is used by both
server and checker. It requires schema 1, an explicit UTC `generated_at`, at most
20 phases/100 findings, required string fields, nonnegative integer counts (not
booleans), supported colors/confidence/severity, and known finding/artifact
references. Finding references accept either current descriptive headings or
retained legacy F-IDs as identified by the working log.

`ir_common.parse_review_queue(content)` derives completion from one valid explicit
status and a fully checked nonempty checklist; misplaced entries remain visible
and raise consistency errors. Section placement alone never completes review.

## Historical custody paths

The installer writes `.memory-bank/path-migrations.json`:

```json
{"schema":1,"prefixes":{"artifacts/":".memory-bank/artifacts/","incoming/":".memory-bank/incoming/"},"project_roots":["/original/project"]}
```

`canonical_path(root, recorded_path)` applies only that explicit map and known
absolute roots. The result must stay within the canonical bank, and callers still
require the artifact/incoming root and reject symlinks. Hash-chained manifest and
journal bytes remain unchanged. Hashes, ART/RQ IDs and transaction identities
survive recovery/migration; historical paths compare by their resolved canonical
identity. No directory is read through a legacy alias.
