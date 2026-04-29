---
description: Initialize the project memory-bank/ directory and required files per CLAUDE.md
---

Read `CLAUDE.md` (project root) to identify the active memory-bank profile and its required file list. Then:

1. Resolve `PROJECT_ROOT` as the current git repo root, or the current working directory if there is no git root.
2. Create `PROJECT_ROOT/memory-bank/` if it does not exist.
3. For each required file listed in `CLAUDE.md`, create the file with its template skeleton if it does not already exist.
4. Do NOT overwrite any existing memory file.
5. Report a short summary: which files were created and which were already present.

If `CLAUDE.md` is missing or does not declare a profile, stop and ask which profile to bootstrap.
