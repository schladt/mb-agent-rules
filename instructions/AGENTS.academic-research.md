# Academic Research Memory Bank Instructions

Use a project-local memory bank for academic research work.

## Required Workflow

### 1) Bootstrap and Load

- Resolve `PROJECT_ROOT` as the current git repo root. If no git root exists, use current working directory.
- Ensure `PROJECT_ROOT/memory-bank` exists.
- Ensure these files exist (create if missing):
  - `memory-bank/researchBrief.md`
  - `memory-bank/researchQuestions.md`
  - `memory-bank/literatureNotes.md`
  - `memory-bank/methodology.md`
  - `memory-bank/sourcesIndex.md`
  - `memory-bank/activeContext.md`
  - `memory-bank/progress.md`
  - `memory-bank/openQuestions.md`
- Read all required memory files before planning or execution.

### 2) Authority and Safety Gates

- Treat `researchBrief.md`, `researchQuestions.md`, and `methodology.md` as authority for research direction, scope, and analysis plan.
- If ethics, consent, data permissions, citation status, or methodology constraints are unclear, stop and ask before collecting data, analyzing restricted material, or asserting research conclusions.
- Do not fabricate citations, quotes, results, datasets, or methods.
- Clearly distinguish hypotheses, notes, verified claims, and source-backed conclusions.
- Do not store sensitive participant data, private datasets, credentials, or restricted full-text materials in memory files. Store references to secure storage locations instead.
- Use citation keys or links for sources; include uncertainty when metadata is incomplete.

### 3) Recording Rules

- Track current research focus, hypotheses, blockers, and next steps in `activeContext.md`.
- Track completed and pending work in `progress.md`.
- Track literature themes, disagreements, gaps, and claims to verify in `literatureNotes.md`.
- Track methodology updates, analysis plan changes, validation checks, and limitations in `methodology.md`.
- Track citation metadata and artifact references in `sourcesIndex.md`.
- Track unresolved questions in `openQuestions.md`.

### 4) Completion Updates

Before completing each task, update at least these files:
- `activeContext.md`
- `progress.md`
- `sourcesIndex.md` (write `No new sources reviewed` if none)
- `openQuestions.md` (write `No new open questions` if none)

Also update `literatureNotes.md`, `researchQuestions.md`, `methodology.md`, or `researchBrief.md` if durable understanding changed.

### 5) Update Style

- Markdown only.
- Use concise entries with timestamps and status labels: `Planned`, `In Progress`, `Done`, `Blocked`, `Needs Verification`.
- Never delete historical notes. Append and mark superseded content.
- Keep claims source-linked and label uncertainty clearly.

### 6) Response Contract

Every response must end with a memory bank status line. No exceptions.

- `Memory bank: updated — <comma-separated list of files changed>`
  Use when you modified one or more memory-bank/ files.
- `Memory bank: read, no update needed`
  Use when you consulted memory-bank/ but no significant progress warrants an update.
- `Memory bank: not consulted`
  Use only for requests completely unrelated to project work.

Never omit the status line. Never combine it with other output.
