# Memory Bank Agent Rules

Memory Bank Agent Rules keeps a single, shared, project-local "memory bank" consistent across AI coding agents — **Cursor**, **GitHub Copilot**, **Codex**, and **Claude Code**.

The core model:

- **One memory bank, one instruction file** — all tools read `AGENTS.md` (or `CLAUDE.md` for Claude Code) and update the same `memory-bank/` directory.
- **Three profiles** for different work types: `pentest`, `academic-research`, `general-project`. Each has its own file schema.
- **One bootstrap command** (`bin/init-agent-rules`) copies the right templates and a universal `AGENTS.md` into the target project.
- **Shared lifecycle**: read memory → work → update memory → report status on every response.

## Install

```bash
mkdir -p ~/.local/bin
ln -sf "$HOME/projects/mb-agent-rules/bin/init-agent-rules" ~/.local/bin/init-agent-rules
```

A symlink is recommended so updates from `git pull` propagate automatically.

If this repo lives somewhere other than `$HOME/projects/mb-agent-rules`, either edit `DEFAULT_AGENT_RULES_ROOT` at the top of the script or set `AGENT_RULES_ROOT=/path/to/mb-agent-rules` when running the command.

## Quick Start

From the target project root:

```bash
init-agent-rules general-project
```

This creates:

```
your-project/
├── AGENTS.md          # universal agent instructions (read by Cursor, Copilot, Codex)
├── CLAUDE.md          # identical mirror (read by Claude Code)
└── memory-bank/
    ├── projectBrief.md
    ├── requirements.md
    ├── decisions.md
    ├── activeContext.md
    ├── progress.md
    ├── risks.md
    └── handoff.md
```

Project type — pick exactly one:

- `pentest` (aliases: `hardware-pentest`, `software-pentest`)
- `academic-research` (aliases: `academic`, `research`)
- `general-project` (aliases: `general`, `project`)

Options:

- `--dry-run` — preview without writing.
- `--force` — overwrite existing profile-managed files.

## How It Works

`AGENTS.md` is the [universal standard](https://agents.md/) for AI coding agent instructions (Agentic AI Foundation, Linux Foundation). It is read natively by:

- **Cursor** — reads `AGENTS.md` and `CLAUDE.md` from project root, always applied.
- **GitHub Copilot** — reads `AGENTS.md` as agent instructions.
- **Codex** — reads `AGENTS.md` as its primary instruction file.
- **Claude Code** — reads `CLAUDE.md` from project root.

`init-agent-rules` copies the same instructions as both `AGENTS.md` and `CLAUDE.md` so all four tools are covered with zero configuration.

## Profiles

| Profile | Use for | Required `memory-bank/*.md` files |
|---|---|---|
| `pentest` | Hardware/software pentest engagements | `projectBrief`, `scopeAuthorization`, `targets`, `activeContext`, `findings`, `progress`, `evidenceIndex` |
| `academic-research` | Research projects | `researchBrief`, `researchQuestions`, `literatureNotes`, `methodology`, `sourcesIndex`, `activeContext`, `progress`, `openQuestions` |
| `general-project` | Software / general work | `projectBrief`, `requirements`, `decisions`, `activeContext`, `progress`, `risks`, `handoff` |

Authority files (treated as source of truth; agents stop and ask when these are unclear):

- Pentest: `scopeAuthorization.md`, `targets.md`, `projectBrief.md`
- Research: `researchBrief.md`, `researchQuestions.md`, `methodology.md`
- General: `projectBrief.md`, `requirements.md`

## Operating Model

Every profile follows the same lifecycle:

1. Read the active profile's `memory-bank/*` files before planning or executing.
2. Treat the profile's authority files as source of truth.
3. Stop and ask when scope, authorization, ethics, data permissions, requirements, ownership, or production impact is unclear.
4. Keep sensitive data (secrets, credentials, payloads, PII, restricted datasets) out of memory files — store references to secure locations instead.
5. Update the profile-specific memory files when significant progress is made.
6. **Every response** must end with a memory bank status line:

```
Memory bank: updated — activeContext.md, progress.md
Memory bank: read, no update needed
Memory bank: not consulted
```

This is non-negotiable. The agent must report its memory bank interaction on every single response.

## Switching Profiles

`init-agent-rules` does not delete files from other profiles. If you change a project's profile, remove the old `memory-bank/` files manually.

## Migration from Previous Versions

If you used an earlier version of this project that installed tool-specific files, you can safely delete:

- `.cursor/rules/*-memory-bank.mdc`
- `.github/copilot-instructions.md`
- `.github/instructions/*-memory.instructions.md`
- `.claude/commands/`, `.claude/skills/`, `.claude/agents/`
- `CLAUDE.md` (will be re-created by `init-agent-rules`)

Then re-run `init-agent-rules <profile>` to install the simplified `AGENTS.md` + `CLAUDE.md`.

---

Developing or contributing to this repo? See [CONTRIBUTING.md](CONTRIBUTING.md).
