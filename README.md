# Agent Rules Lab

The Agent Rules Lab is a configuration repository that solves one specific problem: keeping a single, shared, project-local "memory bank" workflow consistent across four AI coding agents — **Cursor**, **GitHub Copilot**, **Codex**, and **Claude Code**.

The core model:

- **One memory bank, many agents** — all four tools read and update the same `memory-bank/` directory in the target project.
- **Three profiles** for different work types: `pentest`, `academic-research`, `general-project`. Each has its own file schema.
- **One bootstrap command** (`bin/init-agent-rules`) copies the right templates and tool-specific instruction files into the target project.
- **Shared lifecycle**: read memory → work → update memory → end the response with `Memory bank: consulted and updated`.

Do not maintain separate memory banks for the four tools. They should all read and update the same project-local `PROJECT_ROOT/memory-bank/` files.

## Install

```bash
mkdir -p ~/.local/bin
ln -sf "$HOME/projects/agent-rules/bin/init-agent-rules" ~/.local/bin/init-agent-rules
```

A symlink is recommended so updates from `git pull` propagate automatically.

If this repo lives somewhere other than `$HOME/projects/agent-rules`, either edit `DEFAULT_AGENT_RULES_ROOT` at the top of the script or set `AGENT_RULES_ROOT=/path/to/agent-rules` when running the command.

## Quick Start

From the target project root:

```bash
init-agent-rules general-project
```

Project type — pick exactly one:

- `pentest` (aliases: `hardware-pentest`, `software-pentest`)
- `academic-research` (aliases: `academic`, `research`)
- `general-project` (aliases: `general`, `project`)

Options:

- `--dry-run` — preview without writing.
- `--force` — overwrite existing profile-managed files.

This bootstraps `memory-bank/` plus instruction files for **all four** agentic environments at once. Each tool then reads/updates the same shared memory bank.

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

## Manual Setup (single tool)

If you only want to configure one tool, replace `<profile>` with `pentest`, `academic-research`, or `general-project`:

```bash
# Memory bank (always required first)
mkdir -p your-project/memory-bank
cp -R agent-rules/templates/<profile>-memory-bank/. your-project/memory-bank/

# Cursor
mkdir -p your-project/.cursor/rules
cp agent-rules/cursor/<profile>-memory-bank.mdc your-project/.cursor/rules/

# GitHub Copilot
mkdir -p your-project/.github/instructions
cp agent-rules/github-copilot/.github/copilot-instructions.md your-project/.github/
cp agent-rules/github-copilot/.github/instructions/<profile>-memory.instructions.md your-project/.github/instructions/

# Codex
cp agent-rules/codex/AGENTS.<profile>.md your-project/AGENTS.md

# Claude Code
cp agent-rules/claude-code/CLAUDE.<profile>.md your-project/CLAUDE.md
```

Do not place multiple Copilot profile instructions with `applyTo: "**"` in the same project — Copilot will ask which one governs the work.

## Optional Extras

**Cursor global rule** — paste-able User Rule for cross-project behavior:

1. Open `cursor/cursor-global-<profile>-memory-bank-rule.md`.
2. Copy the `BEGIN RULE` to `END RULE` block.
3. Paste into Cursor `Settings → Rules` as a User Rule.

**Codex global baseline** — keep personal defaults in `~/.codex/AGENTS.md`, project-specific behavior in the project `AGENTS.md`.

**Claude Code personal preferences** — keep in `~/.claude/CLAUDE.md` or `CLAUDE.local.md`, not in the shared project `CLAUDE.md`.

**Claude Code helpers** (auto-installed by `init-agent-rules`, profile-agnostic — they read `CLAUDE.md` to discover the active profile):

- `/memory-bootstrap` — slash command that creates `memory-bank/` and required files.
- `/memory-update` — slash command that runs the end-of-task update step.
- `memory-keeper` — subagent that consults and updates the memory bank in an isolated context.

## Operating Model

Every profile follows the same lifecycle:

1. Read the active profile's `memory-bank/*` files before planning or executing.
2. Treat the profile's authority files as source of truth.
3. Stop and ask when scope, authorization, ethics, data permissions, requirements, ownership, or production impact is unclear.
4. Keep sensitive data (secrets, credentials, payloads, PII, restricted datasets) out of memory files — store references to secure locations instead.
5. Update the profile-specific memory files before the final response.
6. Final responses include the line: `Memory bank: consulted and updated`.

When switching tools mid-project, tell the next tool to read `memory-bank/*` first and continue from the current active context.

## Switching Profiles

`init-agent-rules` does not delete instruction files from other profiles. If you change a project's profile, remove the old profile's files manually — the script warns about conflicts but won't touch them.

---

Developing or contributing to this repo? See [CONTRIBUTING.md](CONTRIBUTING.md).
