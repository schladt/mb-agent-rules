# Contributing to Memory Bank Agent Rules

This document covers development of this repo itself — adding profiles, modifying instructions, and verifying consistency. For end-user setup, see [README.md](README.md).

## Repository Layout

```
mb-agent-rules/
├── bin/
│   ├── init-agent-rules        # bootstrap a profile in a target project
│   └── check-profile-drift     # verify instructions agree with templates
├── templates/
│   ├── pentest-memory-bank/
│   ├── academic-research-memory-bank/
│   ├── general-project-memory-bank/
│   └── memory-bank/            # legacy pentest alias
└── instructions/
    ├── AGENTS.pentest.md
    ├── AGENTS.academic-research.md
    └── AGENTS.general-project.md
```

## Design Principles

- One instruction file per profile (`instructions/AGENTS.<profile>.md`), shared across all tools.
- No tool-specific features. No `.mdc` frontmatter, no Copilot `applyTo`, no Claude Code skills/subagents. If a feature only works in one tool, it does not belong here.
- The instruction file and the template directory must agree on required `memory-bank/*.md` files. Drift breaks the guarantee.
- Memory remains local to each project and version-controllable.
- `init-agent-rules` copies the instruction file as both `AGENTS.md` (Cursor, Copilot, Codex) and `CLAUDE.md` (Claude Code) in the target project.

## Drift Check

After modifying any instruction file or template directory, run:

```bash
bin/check-profile-drift
```

This extracts `memory-bank/*.md` references from `instructions/AGENTS.<profile>.md` and compares them against the actual files in `templates/<profile>-memory-bank/`. Exits 1 on drift.

## Modifying an Existing Profile

When changing the required-file list or the workflow for a profile:

1. Edit `instructions/AGENTS.<profile>.md`.
2. Add or remove template files in `templates/<profile>-memory-bank/` to match.
3. Run `bin/check-profile-drift` — it must pass.
4. Run `init-agent-rules <profile> --dry-run` from a temp directory to confirm the bootstrap works.

## Adding a New Profile

1. Pick a profile slug, e.g. `support-engineering`.
2. Create `templates/support-engineering-memory-bank/` with the file skeletons.
3. Create `instructions/AGENTS.support-engineering.md` following the structure of existing profiles.
4. Add the profile to the `case` block in `bin/init-agent-rules`.
5. Add the slug to the `profiles=( … )` array in `bin/check-profile-drift`.
6. Add a row to the Profiles table in `README.md`.
7. Run `bin/check-profile-drift` — it must pass.
8. Run `init-agent-rules <slug> --dry-run` from a temp directory to confirm the bootstrap works.

## Legacy Aliases

One legacy path is kept for backwards compatibility:

- `templates/memory-bank/` — alias for `templates/pentest-memory-bank/`.

When you change the canonical pentest template files, mirror the change into this legacy copy. Do not introduce new profiles using this legacy name.

## Style

- Markdown only in instruction and template files.
- Status labels used across profiles: `Planned`, `In Progress`, `Done`, `Blocked`, plus `Needs Verification` (research) and `Hypothesis`/`Validated`/`False Positive` (pentest findings).
- Append-only memory updates. Never delete historical notes; mark superseded items.
- Response contract requires a status line on every response (not just final task responses). See the Response Contract section in any `instructions/AGENTS.<profile>.md`.
