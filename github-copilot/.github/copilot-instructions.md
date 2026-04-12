# GitHub Copilot Project Instructions

Use exactly one project-local memory-bank profile for this repository.

## Profile Selection

Choose the matching profile-specific instruction file from `.github/instructions/`:

- Pentest: `pentest-memory.instructions.md`
- Academic research: `academic-research-memory.instructions.md`
- General project: `general-project-memory.instructions.md`

If multiple profile instruction files are present and their required memory files conflict, ask which profile should govern the work before proceeding.

## Universal Required Behavior

- Use project-local memory in `memory-bank/`.
- Before planning or coding, read the required memory files for the active profile.
- If memory files are missing, create them using the active profile templates.
- Treat the active profile's authority files as the source of truth:
  - Pentest: `scopeAuthorization.md`, `targets.md`, `projectBrief.md`
  - Academic research: `researchBrief.md`, `researchQuestions.md`, `methodology.md`
  - General project: `projectBrief.md`, `requirements.md`
- If scope, authorization, ethics, requirements, ownership, or data permissions are unclear, stop and ask before high-impact or irreversible actions.
- Keep sensitive data out of memory files. Do not store plaintext secrets, private keys, credentials, exploit payloads, PII, sensitive participant data, or restricted datasets.
- Before finalizing each task, update the active profile's required memory files.

## Response Footer

Include this line in final responses:
- `Memory bank: consulted and updated`
