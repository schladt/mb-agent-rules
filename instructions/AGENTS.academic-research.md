# Academic Research Memory Bank Instructions

Use a project-local memory bank for academic research work.

**Core rule: if you change any file in the project, you MUST update the memory bank in the same response. The only exception is when you change no files. See the Response Contract.**

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
- Sensitive material may be written to a store the project owner explicitly designated for it, such as a data or restricted-sources directory they created or asked you to create. Do not invent such a store on your own initiative, and do not repurpose an existing directory as one. Participant data additionally requires that consent and data permissions already cover the intended storage.
- When you write sensitive material to that store, say so in your response: name the path, say what class of data it now holds, and confirm it is excluded from version control — or flag it clearly if it is not. Memory files record the reference, never the data.
- Use citation keys or links for sources; include uncertainty when metadata is incomplete.
- The project `memory-bank` directory is the store of record. Some tools keep their own automatic memory outside the project. That memory is machine-local, tool-specific, and not shared with collaborators: never treat it as authoritative and never let it substitute for a memory bank update. Durable research facts belong in the memory bank.

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

Two rules, both mandatory.

**Update rule (non-negotiable).** If you created, modified, or deleted ANY file in the project during this response — except files inside `memory-bank/` itself — you MUST update the memory bank in the SAME response. The only case where no update is required is when you changed zero project files. "Small", "trivial", or "obvious" changes are NOT exempt. When an update is required, update at minimum `activeContext.md` and `progress.md`, plus any other files named in Recording Rules and Completion Updates that apply.

**Status line.** End every response with exactly one of:

- `Memory bank: updated — <comma-separated list of files changed>`
  Required whenever you changed any project file (see the update rule).
- `Memory bank: read, no update needed`
  Allowed ONLY when you changed zero project files.
- `Memory bank: not consulted`
  Only for requests completely unrelated to this project.

Self-check before sending: if you changed any file outside `memory-bank/` and your status line is not `updated`, the contract is violated — stop and update the memory bank first. Never omit the status line. Never combine it with other output.
