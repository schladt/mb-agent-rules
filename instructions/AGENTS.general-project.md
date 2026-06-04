# General Project Memory Bank Instructions

Use a project-local memory bank for general project work.

## Required Workflow

### 1) Bootstrap and Load

- Resolve `PROJECT_ROOT` as the current git repo root. If no git root exists, use current working directory.
- Ensure `PROJECT_ROOT/memory-bank` exists.
- Ensure these files exist (create if missing):
  - `memory-bank/projectBrief.md`
  - `memory-bank/requirements.md`
  - `memory-bank/decisions.md`
  - `memory-bank/activeContext.md`
  - `memory-bank/progress.md`
  - `memory-bank/risks.md`
  - `memory-bank/handoff.md`
- Read all required memory files before planning or execution.

### 2) Authority and Safety Gates

- Treat `projectBrief.md` and `requirements.md` as authority for goals, constraints, non-goals, and acceptance criteria.
- If requirements, ownership, privacy, or production-impacting behavior are unclear, stop and ask before irreversible or high-impact actions.
- Do not store plaintext secrets, credentials, private keys, or sensitive customer/user data in memory files. Store references to secure storage locations instead.

### 3) Recording Rules

- Track current objective, approach, blockers, and next steps in `activeContext.md`.
- Track completed and pending work in `progress.md`.
- Track durable tradeoffs and decisions in `decisions.md`.
- Track meaningful risks, impacts, owners, and mitigations in `risks.md`.
- Keep `handoff.md` current enough that another contributor can resume the work.

### 4) Completion Updates

Before completing each task, update at least these files:
- `activeContext.md`
- `progress.md`
- `handoff.md`
- `decisions.md` (write `No new decisions` if none)
- `risks.md` (write `No new risks` if none)

Also update `projectBrief.md` or `requirements.md` if durable understanding changed.

### 5) Update Style

- Markdown only.
- Use concise entries with timestamps and status labels: `Planned`, `In Progress`, `Done`, `Blocked`.
- Never delete historical notes. Append and mark superseded content.

### 6) Response Contract

Every response must end with a memory bank status line. No exceptions.

- `Memory bank: updated — <comma-separated list of files changed>`
  Use when you modified one or more memory-bank/ files.
- `Memory bank: read, no update needed`
  Use when you consulted memory-bank/ but no significant progress warrants an update.
- `Memory bank: not consulted`
  Use only for requests completely unrelated to project work.

Never omit the status line. Never combine it with other output.
