# GitHub Copilot Project Instructions

Follow the pentest memory-bank workflow for every task.

## Required behavior

- Use project-local memory in `memory-bank/`.
- Before planning or coding, read required memory files.
- If memory files are missing, create them using the project templates.
- Treat `memory-bank/scopeAuthorization.md` as the scope/authorization source of truth.
- If scope or authorization is unclear, stop and ask before intrusive/offensive actions.
- Keep sensitive data out of memory files (no plaintext secrets, private keys, exploit payloads, or PII).
- Before finalizing each task, update memory files and explicitly note whether new findings/evidence were added.

## Required files in `memory-bank/`

- `projectBrief.md`
- `scopeAuthorization.md`
- `targets.md`
- `activeContext.md`
- `findings.md`
- `progress.md`
- `evidenceIndex.md`

## Response footer

Include this line in final responses:
- `Memory bank: consulted and updated`
