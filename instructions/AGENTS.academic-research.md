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
  - `memory-bank/sensitiveDataPolicy.md`
  - `memory-bank/sourcesIndex.md`
  - `memory-bank/activeContext.md`
  - `memory-bank/progress.md`
  - `memory-bank/openQuestions.md`
- Read all required memory files before planning or execution.

### 2) Authority and Safety Gates

- Treat `researchBrief.md`, `researchQuestions.md`, `methodology.md`, and `sensitiveDataPolicy.md` as authority for research direction, scope, analysis, and sensitive-data handling.
- If ethics, consent, data permissions, citation status, or methodology constraints are unclear, stop and ask before collecting data, analyzing restricted material, or asserting research conclusions.
- Do not fabricate citations, quotes, results, datasets, or methods.
- Clearly distinguish hypotheses, notes, verified claims, and source-backed conclusions.
- Read `sensitiveDataPolicy.md` before writing credentials, restricted sources, private datasets, participant data, or other sensitive material. Selecting this profile designates `sensitive/` as the standard store for authorized restricted inputs.
- Additional paths are authorized only when the owner records them in `sensitiveDataPolicy.md`. Participant data also requires consent and data permissions covering the destination; directory existence alone is not authorization.
- Memory files reference sensitive material rather than reproducing it. Synthetic values may appear there only when the policy explicitly sets `private-lab` mode and `Memory-bank plaintext: synthetic-only`; live production secrets and real participant data remain prohibited.
- A compliant write to a declared store needs no repeated warning. Report and stop for missing or ambiguous policy, an undeclared path or data class, missing consent or permission, a version-control conflict, unsafe permissions, or another policy violation. Repository visibility never implies `private-lab`.
- New sensitive-store directories use mode `0700` and newly written files use mode `0600` where POSIX permissions are supported.
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
