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
- `--force` — overwrite all profile-managed files in place, with no backup and no migration prompt (power-user escape hatch).

### Re-running on an existing project

`init-agent-rules` is safe to re-run. It detects what is already there and does the least destructive thing:

| Situation | What happens |
|---|---|
| Nothing exists yet | Fresh scaffolding is created. |
| Memory bank already matches the profile | Nothing is changed. |
| Same file schema, but `AGENTS.md`/`CLAUDE.md` are stale | Only the instruction files are refreshed; `memory-bank/` is left untouched. |
| File schema does **not** match (profile changed, or a newer profile added/removed files) | The old memory bank (plus `AGENTS.md`/`CLAUDE.md`) is moved to `.old/memory-bank-<timestamp>/`, fresh scaffolding is created, and you are told to ask your agent to migrate the old data. |

Migrating old data is a content-mapping task a bash script cannot do reliably, so after a schema-mismatch re-init, ask your agent, e.g.:

> "Migrate my memory bank from `.old/memory-bank-<timestamp>/` into the new `memory-bank/` scaffolding. Map old content to the new files, preserve history, and mark anything superseded."

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
5. **If the agent changes any file in the project, it MUST update the memory bank in the same response.** The only time an update is not required is when no files were changed. "Small" or "trivial" edits are not exempt — this is the rule that keeps the memory bank trustworthy.
6. **Every response** must end with a memory bank status line:

```
Memory bank: updated — activeContext.md, progress.md   # required whenever any file changed
Memory bank: read, no update needed                    # allowed only when no file changed
Memory bank: not consulted                             # only for unrelated requests
```

This is non-negotiable. The agent must report its memory bank interaction on every single response. The full contract — including the binary update rule and a pre-send self-check — lives in each profile's `instructions/AGENTS.<profile>.md`.

## Switching Profiles

Just re-run `init-agent-rules <new-profile>`. Because the new profile's file schema differs, the script detects the mismatch, backs up your existing memory bank to `.old/memory-bank-<timestamp>/`, and scaffolds the new profile. Then ask your agent to migrate the old data (see [Re-running on an existing project](#re-running-on-an-existing-project)).

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
