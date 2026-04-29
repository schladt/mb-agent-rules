# Contributing to Agent Rules Lab

This document covers development of this repo itself — adding profiles, modifying tool instructions, and verifying consistency. For end-user setup, see [README.md](README.md).

## Repository Layout

```
agent-rules/
├── bin/
│   ├── init-agent-rules        # bootstrap a profile in a target project
│   └── check-profile-drift     # verify the four tool variants of each profile agree
├── templates/
│   ├── pentest-memory-bank/
│   ├── academic-research-memory-bank/
│   ├── general-project-memory-bank/
│   └── memory-bank/                                    # legacy pentest alias
├── cursor/
│   ├── <profile>-memory-bank.mdc                       # project-scoped rule
│   └── cursor-global-<profile>-memory-bank-rule.md     # paste-able User Rule
├── github-copilot/.github/
│   ├── copilot-instructions.md                         # profile selector
│   └── instructions/<profile>-memory.instructions.md   # profile workflow
├── codex/
│   ├── AGENTS.<profile>.md
│   └── AGENTS.md                                       # legacy pentest alias
└── claude-code/
    ├── CLAUDE.<profile>.md
    └── .claude/
        ├── commands/{memory-bootstrap,memory-update}.md
        └── agents/memory-keeper.md
```

## Design Principles

- The lifecycle is shared, but the memory schema matches the project type. Pentest needs scope/findings/evidence; research needs questions/methodology/sources; general work needs requirements/decisions/risks.
- For each profile, all four tool variants must reference the same set of `memory-bank/*.md` required files. Drift breaks the "one memory bank, many agents" guarantee.
- File-format conventions follow the canonical, current format for each tool:
  - **Cursor**: `.cursor/rules/*.mdc` with frontmatter (`description`, `globs`, `alwaysApply`).
  - **GitHub Copilot**: `.github/copilot-instructions.md` plus `.github/instructions/*.instructions.md` with `applyTo:` frontmatter.
  - **Codex**: `AGENTS.md` at project root.
  - **Claude Code**: `CLAUDE.md` at project root; optional `.claude/commands/*.md` slash commands and `.claude/agents/*.md` subagents.
- Memory remains local to each project and version-controllable.

## Drift Check

After modifying any per-tool instruction file, run:

```bash
bin/check-profile-drift
```

For each profile, this extracts the set of `memory-bank/*.md` filenames declared as required across the Cursor `.mdc`, Copilot `.instructions.md`, Codex `AGENTS.<profile>.md`, and Claude Code `CLAUDE.<profile>.md` files, then reports any divergence. Exits 1 on drift. Honors `AGENT_RULES_ROOT`.

## Modifying an Existing Profile

When changing the required-file list or the workflow for a profile, update **all four** tool variants in lockstep:

- `cursor/<profile>-memory-bank.mdc`
- `cursor/cursor-global-<profile>-memory-bank-rule.md` (the paste-able User Rule)
- `github-copilot/.github/instructions/<profile>-memory.instructions.md`
- `codex/AGENTS.<profile>.md`
- `claude-code/CLAUDE.<profile>.md`

Then run `bin/check-profile-drift` and confirm it passes.

## Adding a New Profile

1. Pick a profile slug, e.g. `support-engineering`.
2. Create `templates/support-engineering-memory-bank/` with the file skeletons.
3. Create per-tool instruction files following the exact naming pattern:
   - `cursor/support-engineering-memory-bank.mdc`
   - `cursor/cursor-global-support-engineering-memory-bank-rule.md`
   - `github-copilot/.github/instructions/support-engineering-memory.instructions.md`
   - `codex/AGENTS.support-engineering.md`
   - `claude-code/CLAUDE.support-engineering.md`
4. Add the profile to the `case` block in `bin/init-agent-rules`.
5. Add the slug to the `profiles=( … )` array in `bin/check-profile-drift`.
6. Add a row to the Profiles table in `README.md`.
7. Run `bin/check-profile-drift` — it must pass.
8. Run `init-agent-rules <slug> --dry-run` from a temp directory to confirm the bootstrap works end-to-end.

## Legacy Aliases

Two legacy paths are kept for backwards compatibility:

- `templates/memory-bank/` — alias for `templates/pentest-memory-bank/`.
- `codex/AGENTS.md` — alias for `codex/AGENTS.pentest.md`.

When you change the canonical pentest files, mirror the change into these legacy copies. Do not introduce new profiles using these legacy names.

## Editing the Bootstrap Script

`bin/init-agent-rules` defaults to copying source files but supports `--dry-run` and `--force`. When adding new sources to be installed:

- Required-source presence is checked at startup via the `for required in ... do [ -e ] || die done` block — add new required files there if they should block the run.
- Use `copy_optional_dir` for new tree-shaped helpers (e.g. the Claude Code `.claude/commands/` and `.claude/agents/` trees) — it is a no-op when the source dir does not exist, which is the right behavior for optional add-ons.

## Style

- Markdown only in instruction and template files.
- Status labels used across profiles: `Planned`, `In Progress`, `Done`, `Blocked`, plus `Needs Verification` (research) and `Hypothesis`/`Validated`/`False Positive` (pentest findings).
- Append-only memory updates. Never delete historical notes; mark superseded items.
- Keep the response-contract footer line consistent: `Memory bank: consulted and updated`.
