---
description: Run the end-of-task memory-bank update per CLAUDE.md
---

Apply the "after each task" workflow defined in `CLAUDE.md`:

1. Update `activeContext.md` with the current objective, approach, next steps, and blockers.
2. Update `progress.md` with completed, in-progress, and pending work plus any verification run.
3. Update the profile-specific completion files listed in `CLAUDE.md` (e.g. `handoff.md`, `findings.md`/`evidenceIndex.md`, `openQuestions.md`/`sourcesIndex.md`, `decisions.md`/`risks.md`).
4. Update authority files (`projectBrief.md`, `requirements.md`, `scopeAuthorization.md`, `targets.md`, `researchBrief.md`, `researchQuestions.md`, `methodology.md`) only if durable understanding changed.

Style:
- Append-only. Never delete historical notes; mark superseded items instead.
- Use timestamps and status labels (`Planned`, `In Progress`, `Done`, `Blocked`, `Needs Verification`).
- If a required completion file has no new content, write the explicit placeholder phrase from `CLAUDE.md` (e.g. `No new validated findings`).

End with the line: `Memory bank: consulted and updated`.
