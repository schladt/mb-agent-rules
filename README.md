# Agent Rules Lab

Rule and template files for local memory-bank workflows across:

- Cursor
- GitHub Copilot (VS Code)
- Codex (VS Code)

The core model is:

1. Choose one project memory-bank profile.
2. Bootstrap one shared `memory-bank/` directory in the target project.
3. Configure any or all supported agentic environments to use that same directory.

Do not create separate memory banks for Cursor, Copilot, and Codex. They should all read and update the same project-local `PROJECT_ROOT/memory-bank/` files.

## Quick Start

Install the helper command:

```bash
mkdir -p ~/.local/bin
install -m 0755 "$HOME/projects/agent-rules/bin/init-agent-rules" ~/.local/bin/init-agent-rules
```

From the target project root, initialize one profile and all three agentic environments:

```bash
init-agent-rules general-project
```

Use one of these project type arguments:

- `pentest`
- `academic-research`
- `general-project`

Preview before writing files:

```bash
init-agent-rules general-project --dry-run
```

If this repository is not at `$HOME/projects/agent-rules`, either edit `DEFAULT_AGENT_RULES_ROOT` at the top of `bin/init-agent-rules` or run with:

```bash
AGENT_RULES_ROOT=/path/to/agent-rules init-agent-rules general-project
```

The helper configures `memory-bank/`, Cursor, GitHub Copilot, and Codex. For manual setup or single-agent setup, use the detailed sections below.

## Supported Profiles

- Pentest: hardware/software pentest engagement memory with scope, targets, findings, and evidence.
- Academic research: research project memory with questions, methodology, literature notes, sources, and open questions.
- General project: broad project memory with requirements, decisions, risks, progress, and handoff context.

Choose exactly one profile per target project unless you intentionally maintain separate memory banks for separate streams of work.

## Project Memory Bank Template Setup

This is the project-state setup. Do this once per target project, and choose exactly one project type.

### Pentest

```bash
mkdir -p /path/to/your-project/memory-bank
cp -R /path/to/agent-rules/templates/pentest-memory-bank/. /path/to/your-project/memory-bank/
```

### Academic Research

```bash
mkdir -p /path/to/your-project/memory-bank
cp -R /path/to/agent-rules/templates/academic-research-memory-bank/. /path/to/your-project/memory-bank/
```

### General Project

```bash
mkdir -p /path/to/your-project/memory-bank
cp -R /path/to/agent-rules/templates/general-project-memory-bank/. /path/to/your-project/memory-bank/
```

### Profile File Sets

Pentest memory bank:

- `memory-bank/projectBrief.md`
- `memory-bank/scopeAuthorization.md`
- `memory-bank/targets.md`
- `memory-bank/activeContext.md`
- `memory-bank/findings.md`
- `memory-bank/progress.md`
- `memory-bank/evidenceIndex.md`

Academic research memory bank:

- `memory-bank/researchBrief.md`
- `memory-bank/researchQuestions.md`
- `memory-bank/literatureNotes.md`
- `memory-bank/methodology.md`
- `memory-bank/sourcesIndex.md`
- `memory-bank/activeContext.md`
- `memory-bank/progress.md`
- `memory-bank/openQuestions.md`

General project memory bank:

- `memory-bank/projectBrief.md`
- `memory-bank/requirements.md`
- `memory-bank/decisions.md`
- `memory-bank/activeContext.md`
- `memory-bank/progress.md`
- `memory-bank/risks.md`
- `memory-bank/handoff.md`

## Agentic Environment Setup

This is the tool-instruction setup. It is separate from template setup.

After bootstrapping exactly one project memory-bank profile, you may configure Cursor, GitHub Copilot, Codex, or all three. When configuring multiple environments in the same project, always use the matching profile instructions for the memory-bank profile you chose.

### Automated All-Environment Setup

Use `bin/init-agent-rules` when you want to bootstrap the selected project memory-bank profile and configure Cursor, GitHub Copilot, and Codex in one step.

Install it somewhere on your `PATH`:

```bash
mkdir -p ~/.local/bin
install -m 0755 "$HOME/projects/agent-rules/bin/init-agent-rules" ~/.local/bin/init-agent-rules
```

Run it from the target project root:

```bash
init-agent-rules general-project
```

Supported project type arguments:

- `pentest`
- `academic-research`
- `general-project`

Useful options:

- `--dry-run`: print the files that would be created or skipped.
- `--force`: overwrite existing profile-managed files.

The script defaults to `$HOME/projects/agent-rules`. If this repository lives somewhere else, edit `DEFAULT_AGENT_RULES_ROOT` at the top of the script or override it at runtime:

```bash
AGENT_RULES_ROOT=/path/to/agent-rules init-agent-rules general-project
```

The script does not remove other profile instruction files. If it finds profile files that may conflict, it prints a warning so you can remove them intentionally.

### Cursor

Use one project-scoped Cursor rule:

```bash
mkdir -p /path/to/your-project/.cursor/rules
cp /path/to/agent-rules/cursor/pentest-memory-bank.mdc /path/to/your-project/.cursor/rules/pentest-memory-bank.mdc
```

Swap the source file for another profile when needed:

- Academic research: `cursor/academic-research-memory-bank.mdc`
- General project: `cursor/general-project-memory-bank.mdc`

Optional global behavior:

1. Open the matching `cursor/cursor-global-*-memory-bank-rule.md` file.
2. Copy the `BEGIN RULE` to `END RULE` block.
3. Paste it into Cursor `Settings -> Rules` as a User Rule.

### GitHub Copilot

```bash
mkdir -p /path/to/your-project/.github/instructions
cp /path/to/agent-rules/github-copilot/.github/copilot-instructions.md /path/to/your-project/.github/copilot-instructions.md
cp /path/to/agent-rules/github-copilot/.github/instructions/pentest-memory.instructions.md /path/to/your-project/.github/instructions/pentest-memory.instructions.md
```

Copy the shared profile selector plus exactly one profile instruction file.

Swap the second source file for another profile when needed:

- Academic research: `github-copilot/.github/instructions/academic-research-memory.instructions.md`
- General project: `github-copilot/.github/instructions/general-project-memory.instructions.md`

Do not copy multiple Copilot profile instruction files with `applyTo: "**"` into the same project unless you intentionally want Copilot to ask which profile governs the work.

### Codex

```bash
cp /path/to/agent-rules/codex/AGENTS.pentest.md /path/to/your-project/AGENTS.md
```

Copy exactly one profile file into the target project root as `AGENTS.md`.

Swap the source file for another profile when needed:

- Academic research: `codex/AGENTS.academic-research.md`
- General project: `codex/AGENTS.general-project.md`

Optional global baseline for all projects:

- `~/.codex/AGENTS.md`

Recommended:

- Keep baseline personal defaults in `~/.codex/AGENTS.md`.
- Keep project-specific memory-bank behavior in the target repo `AGENTS.md`.

## Using All Three Environments Together

This is supported. Bootstrap the memory bank once, then install the matching rule/instruction files for each agentic environment.

Example general project layout after configuring all three:

```text
your-project/
  memory-bank/
    projectBrief.md
    requirements.md
    decisions.md
    activeContext.md
    progress.md
    risks.md
    handoff.md
  .cursor/
    rules/
      general-project-memory-bank.mdc
  .github/
    copilot-instructions.md
    instructions/
      general-project-memory.instructions.md
  AGENTS.md
```

Example setup for a general project using all three environments:

```bash
mkdir -p /path/to/your-project/memory-bank
cp -R /path/to/agent-rules/templates/general-project-memory-bank/. /path/to/your-project/memory-bank/

mkdir -p /path/to/your-project/.cursor/rules
cp /path/to/agent-rules/cursor/general-project-memory-bank.mdc /path/to/your-project/.cursor/rules/general-project-memory-bank.mdc

mkdir -p /path/to/your-project/.github/instructions
cp /path/to/agent-rules/github-copilot/.github/copilot-instructions.md /path/to/your-project/.github/copilot-instructions.md
cp /path/to/agent-rules/github-copilot/.github/instructions/general-project-memory.instructions.md /path/to/your-project/.github/instructions/general-project-memory.instructions.md

cp /path/to/agent-rules/codex/AGENTS.general-project.md /path/to/your-project/AGENTS.md
```

## Operating Model

Every profile follows the same lifecycle:

1. Read the active profile's `memory-bank/*` files before planning or execution.
2. Treat the profile's authority files as source of truth.
3. Stop and ask when scope, authorization, ethics, data permissions, requirements, ownership, or production impact is unclear.
4. Keep sensitive data out of memory files.
5. Update profile-specific memory files before the final response.
6. Include this line in final outputs:

- `Memory bank: consulted and updated`

When switching between Cursor, Copilot, and Codex, start the next tool by telling it to read `memory-bank/*` first and continue from the current active context.

## Repository Layout

Command and templates:

- `bin/init-agent-rules`
- `templates/pentest-memory-bank/`
- `templates/academic-research-memory-bank/`
- `templates/general-project-memory-bank/`
- `templates/memory-bank/` legacy pentest alias retained for backwards compatibility

Cursor rules:

- `cursor/cursor-global-pentest-memory-bank-rule.md`
- `cursor/cursor-global-academic-research-memory-bank-rule.md`
- `cursor/cursor-global-general-project-memory-bank-rule.md`
- `cursor/pentest-memory-bank.mdc`
- `cursor/academic-research-memory-bank.mdc`
- `cursor/general-project-memory-bank.mdc`

GitHub Copilot instructions:

- `github-copilot/.github/copilot-instructions.md`
- `github-copilot/.github/instructions/pentest-memory.instructions.md`
- `github-copilot/.github/instructions/academic-research-memory.instructions.md`
- `github-copilot/.github/instructions/general-project-memory.instructions.md`

Codex instructions:

- `codex/AGENTS.md` legacy pentest profile
- `codex/AGENTS.pentest.md`
- `codex/AGENTS.academic-research.md`
- `codex/AGENTS.general-project.md`

## Why This Structure

- The lifecycle is shared, but the memory schema matches the project type.
- Pentest projects need scope, targets, findings, and evidence.
- Academic research projects need research questions, methodology, source tracking, and literature notes.
- General projects need requirements, decisions, risks, and handoff context.
- Cursor `.mdc`, Copilot `.github/*`, and Codex `AGENTS.md` map cleanly to each platform's native instruction system.
- Memory remains local to each project and version-controllable.
