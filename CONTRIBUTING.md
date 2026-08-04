# Contributing to Memory Bank Agent Rules

This document covers development of this repo itself — adding profiles, modifying instructions, and verifying consistency. For end-user setup, see [README.md](README.md).

## Repository Layout

```
mb-agent-rules/
├── bin/
│   ├── init-agent-rules         # bootstrap a profile in a target project
│   ├── check-profile-drift      # verify instructions agree with templates
│   └── check-memory-freshness   # verify project changes come with memory updates
├── templates/
│   ├── pentest-memory-bank/
│   ├── academic-research-memory-bank/
│   ├── general-project-memory-bank/
│   └── incident-response-memory-bank/
├── skills/
│   └── memory-bank/SKILL.md     # portable Agent Skill, profile-agnostic
└── instructions/
    ├── AGENTS.pentest.md
    ├── AGENTS.academic-research.md
    ├── AGENTS.general-project.md
    └── AGENTS.incident-response.md
```

## Design Principles

- One instruction file per profile (`instructions/AGENTS.<profile>.md`), shared across all tools.
- No tool-specific features. No `.mdc` frontmatter, no Copilot `applyTo`, no per-tool hooks or subagents. If a feature only works in one tool, it does not belong here. Cross-tool open formats — `AGENTS.md` and Agent Skills (`SKILL.md`) — are in scope.
- Always-on context stays small: rules that must apply on every request live in the instruction files; multi-step procedures live in the skill.
- The instruction file and the template directory must agree on required `memory-bank/*.md` files. Drift breaks the guarantee.
- The skill stays profile-agnostic. It reads `AGENTS.md` for the required file list, so it never needs to change when a profile does.
- Memory remains local to each project and version-controllable.
- `init-agent-rules` installs the instruction file as `AGENTS.md`, a `CLAUDE.md` that points at it, and the skill.

## This Repo's Own Memory Bank

This repo dogfoods the `general-project` profile, but its own agent artifacts are **local-only working memory and must never be committed**. `.gitignore` anchors them to the repo root:

```
/memory-bank/   /AGENTS.md   /CLAUDE.md   /.agents/   /.old/
```

The unanchored source directories (`templates/`, `skills/`, `instructions/`) are the shipped artifacts and *are* committed. When adding anything that `init-agent-rules` writes into a target project, check whether it also needs an anchored `.gitignore` entry here.

## Drift Check

After modifying any instruction file or template directory, run:

```bash
bin/check-profile-drift
```

This extracts `memory-bank/*.md` references from `instructions/AGENTS.<profile>.md` and compares them against the actual files in `templates/<profile>-memory-bank/`. Exits 1 on drift.

## Modifying the Skill

`skills/memory-bank/SKILL.md` is installed verbatim into target projects and is shared by all profiles. Keep it profile-agnostic: describe procedures, and have the agent read `AGENTS.md` for the file list. Never hard-code a profile's required files there, or the drift check will not protect it.

The `name` field in the frontmatter must stay `memory-bank` and match the directory name, or skills-compatible tools silently fail to load it.

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

None. `templates/memory-bank/` (an alias for `templates/pentest-memory-bank/`) was removed; always use the full profile name.

## Style

- Markdown only in instruction and template files.
- Status labels used across profiles: `Planned`, `In Progress`, `Done`, `Blocked`, plus `Needs Verification` (research) and `Hypothesis`/`Validated`/`False Positive` (pentest findings).
- Append-only memory updates. Never delete historical notes; mark superseded items.
- Response contract requires a status line on every response (not just final task responses). See the Response Contract section in any `instructions/AGENTS.<profile>.md`.
