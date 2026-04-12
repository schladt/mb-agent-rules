# Academic Research Memory Bank Instructions (Codex)

Use a project-local memory bank for academic research work.

## Required Workflow

1. Before each task:
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

2. During each task:
- Treat `researchBrief.md`, `researchQuestions.md`, and `methodology.md` as authority for the current research direction.
- If ethics, consent, data permissions, citation status, or methodology constraints are unclear, stop and ask before collecting data, analyzing restricted material, or asserting research conclusions.
- Do not fabricate citations, quotes, results, datasets, or methods.
- Clearly distinguish hypotheses, notes, verified claims, and source-backed conclusions.
- Record current research state in `activeContext.md`.
- Record completed and pending work in `progress.md`.
- Record source metadata and artifact references in `sourcesIndex.md`.
- Record unresolved research questions in `openQuestions.md`.
- Record durable literature themes, disagreements, and gaps in `literatureNotes.md`.

3. After each task (before final response):
- Update `activeContext.md`.
- Update `progress.md`.
- Update `sourcesIndex.md` (write `No new sources reviewed` if none).
- Update `openQuestions.md` (write `No new open questions` if none).
- Update `literatureNotes.md`, `researchQuestions.md`, `methodology.md`, or `researchBrief.md` if durable understanding changed.

## Data Handling

- Do not store sensitive participant data, private datasets, credentials, or restricted full-text materials in memory files.
- Store references to secure storage locations instead.
- Use citation keys or links for sources; include uncertainty when metadata is incomplete.

## Update Style

- Markdown only.
- Use concise entries with timestamps and status labels: `Planned`, `In Progress`, `Done`, `Blocked`, `Needs Verification`.
- Never delete historical notes. Append and mark superseded content.

## Response Contract

Every final task response must include:
- `Memory bank: consulted and updated`
- If skipped, explain exactly why.
