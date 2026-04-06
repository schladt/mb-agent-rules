# Agent Rules Lab

Rule and template files for a local pentest memory-bank workflow across:

- Cursor
- GitHub Copilot (VS Code)
- Codex (VS Code)

## Repository Layout

- `cursor/cursor-global-pentest-memory-bank-rule.md`
- `cursor/pentest-memory-bank.mdc`
- `github-copilot/.github/copilot-instructions.md`
- `github-copilot/.github/instructions/pentest-memory.instructions.md`
- `codex/AGENTS.md`
- `templates/memory-bank/` (starter memory files)

## Shared Memory Bank Standard

Use the same local folder in every target project:

- `memory-bank/projectBrief.md`
- `memory-bank/scopeAuthorization.md`
- `memory-bank/targets.md`
- `memory-bank/activeContext.md`
- `memory-bank/findings.md`
- `memory-bank/progress.md`
- `memory-bank/evidenceIndex.md`

Recommended bootstrap for a new project:

```bash
cp -R /path/to/agent-rules/templates/memory-bank /path/to/your-project/
```

## 1) Cursor Setup

Use one or both:

1. Global behavior (applies to all projects):

- Open `cursor/cursor-global-pentest-memory-bank-rule.md`
- Copy the `BEGIN RULE` to `END RULE` block
- Paste into Cursor `Settings -> Rules` as a User Rule

2. Project-scoped behavior (recommended for reproducibility):

- Copy `cursor/pentest-memory-bank.mdc` into target project:
  - `/path/to/your-project/.cursor/rules/pentest-memory-bank.mdc`

Recommended: use both global + project rule together.

## 2) GitHub Copilot Setup (VS Code)

Copy these files into the target project:

1. Repository-wide instructions:

- Source: `github-copilot/.github/copilot-instructions.md`
- Destination: `/path/to/your-project/.github/copilot-instructions.md`

2. Path-specific instructions:

- Source: `github-copilot/.github/instructions/pentest-memory.instructions.md`
- Destination: `/path/to/your-project/.github/instructions/pentest-memory.instructions.md`

Result:

- Copilot gets persistent repo-wide behavior plus explicit path-scoped memory-bank workflow.

## 3) Codex Setup (VS Code)

Copy this file into the target project root:

- Source: `codex/AGENTS.md`
- Destination: `/path/to/your-project/AGENTS.md`

Optional global baseline for all projects:

- `~/.codex/AGENTS.md`

Recommended:

- Keep baseline personal defaults in `~/.codex/AGENTS.md`
- Keep project-specific pentest memory-bank behavior in repo `AGENTS.md`

## Operating Model (All 3 Environments)

Every task should follow this contract:

1. Read `memory-bank/*` before planning/execution.
2. Enforce scope from `scopeAuthorization.md`.
3. Update memory at completion:

- `activeContext.md`
- `progress.md`
- `findings.md` (or `No new validated findings`)
- `evidenceIndex.md` (or `No new evidence artifacts`)

4. Include final line in outputs:

- `Memory bank: consulted and updated`

## Why This Structure

- One shared memory format across tools prevents context drift.
- Cursor `.mdc`, Copilot `.github/*`, and Codex `AGENTS.md` map cleanly to each platform's native instruction system.
- Memory remains local to each project and version-controllable.
