# General Project Memory Bank Instructions (Codex)

Use a project-local memory bank for general project work.

## Required Workflow

1. Before each task:
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

2. During each task:
- Treat `projectBrief.md` and `requirements.md` as authority for goals, constraints, non-goals, and acceptance criteria.
- If requirements, ownership, privacy, or production-impacting behavior are unclear, stop and ask before irreversible or high-impact actions.
- Record short-term work state in `activeContext.md`.
- Record completed and pending work in `progress.md`.
- Record durable tradeoffs and decisions in `decisions.md`.
- Record meaningful risks and mitigations in `risks.md`.
- Keep `handoff.md` current enough that another contributor can resume the work.

3. After each task (before final response):
- Update `activeContext.md`.
- Update `progress.md`.
- Update `handoff.md`.
- Update `decisions.md` (write `No new decisions` if none).
- Update `risks.md` (write `No new risks` if none).
- Update `projectBrief.md` or `requirements.md` if durable understanding changed.

## Data Handling

- Do not store plaintext secrets, credentials, private keys, or sensitive customer/user data in memory files.
- Store references to secure storage locations instead.

## Update Style

- Markdown only.
- Use concise entries with timestamps and status labels: `Planned`, `In Progress`, `Done`, `Blocked`.
- Never delete historical notes. Append and mark superseded content.

## Response Contract

Every final task response must include:
- `Memory bank: consulted and updated`
- If skipped, explain exactly why.
