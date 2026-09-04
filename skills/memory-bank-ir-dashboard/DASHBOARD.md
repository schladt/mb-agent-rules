# IR Dashboard — Technical Reference

## Architecture

```
project-root/
├── dashboard/
│   ├── app.py              ← Flask backend (parsers, API, auth)
│   ├── templates/
│   │   ├── dashboard.html  ← Single-page app (CSS + HTML + JS)
│   │   └── login.html      ← Login form
│   ├── start.sh            ← Launcher with auto-venv
│   ├── requirements.txt
│   └── certs/              ← Auto-generated SSL certs (gitignored)
├── scripts/
│   ├── intake.py           ← Evidence intake pipeline
│   └── sync_check.py       ← Consistency validator
├── memory-bank/            ← Source of truth (markdown files)
├── artifacts/              ← Binary evidence store (gitignored)
├── incoming/               ← Drop zone for new evidence
└── dashboard.config.json   ← Theme and branding configuration
```

## Data Flow

```
memory-bank/*.md ─── app.py parsers ──→ /api/data ──→ dashboard.html (render)
                                                          │
artifacts/*.json ─── auto-discovery ──→ /api/atomic-* ──→ Atomic Event Viewer
                                                          │
incoming/ ──────── intake.py ─────────→ artifacts/ + evidenceIndex.md
```

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | Yes | Main dashboard (renders template) |
| GET | `/login` | No | Login page |
| POST | `/login` | No | Authenticate |
| POST | `/logout` | No | Clear session (CSRF protected) |
| GET | `/api/data` | Yes | All parsed dashboard data (JSON) |
| GET | `/api/artifact/<id>` | Yes | Single artifact metadata |
| GET | `/download/<id>` | Yes | Download artifact file |
| GET | `/api/atomic-sources` | Yes | List auto-detected JSON data sources |
| GET | `/api/atomic-query` | Yes | Query a data source with filters |
| GET | `/api/atomic-search` | Yes | Global text search across all sources |
| GET | `/api/sync-check` | Yes | Run consistency checks |
| POST | `/api/intake` | Yes | Process files from incoming/ |
| GET | `/api/review-queue` | Yes | Get review queue status |

## Atomic Query Parameters

| Param | Description |
|-------|-------------|
| `source` | JSON filename in artifacts/ |
| `from` | Start timestamp filter |
| `to` | End timestamp filter |
| `ip` | IP address filter (uses auto-detected IP field) |
| `q` | Free-text search across all fields |
| `f_<field>` | Filter by specific field value |
| `limit` | Max rows to return (default 500, max 5000) |
| `offset` | Zero-based pagination offset |
| `meta` | Set to `1` to get field metadata and unique values only |

## Histogram Bucketing

The histogram auto-selects bucket size based on the time span of filtered results:

| Span | Bucket Size |
|------|------------|
| < ~80 min | 1 minute |
| < ~7 hours | 5 minutes |
| < ~20 hours | 15 minutes |
| < ~3 days | 1 hour |
| < ~20 days | 6 hours |
| > 20 days | 1 day |

## Attacker IP Detection

The dashboard reads `indicators.md` and extracts all IPs with `Type: IP` and
`Status: Confirmed`. These are cached and re-read when the file changes.

Attacker IPs are highlighted:
- Red rows in the atomic event table
- Warning icons in filter dropdowns
- "ATTACKER IP DETECTED" banner in event detail panels
- Count shown in the status bar

## Adding Custom Data Sources

Any JSON file placed in `artifacts/` is automatically detected if it:
1. Contains an array of objects (or `{"results": [...]}`)
2. Has at least 2 records
3. Has a field named `Timestamp`, `Time`, `CreatedDateTime`, or `EventTime`

The complete dataset must consist of objects and remain within the configured
file, record, and field limits. Paths are containment-checked and symlinks are
rejected. Fields are the union across all records, not only the first row.

Optional: if a field is named `IPAddress`, `IP`, `ClientIP`, or `SourceIP`, the
dashboard enables IP-based filtering and attacker detection.
