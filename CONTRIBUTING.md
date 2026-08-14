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
│   ├── memory-bank/SKILL.md     # portable Agent Skill, profile-agnostic
│   ├── evidence-review/SKILL.md # post-intake IR analysis workflow
│   └── ir-dashboard/
│       ├── dashboard/           # local Flask application
│       ├── scripts/             # intake and semantic validator
│       └── sample-data/         # fictional event data
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
- The `memory-bank` skill stays profile-agnostic. It reads `AGENTS.md` for the required file list, so it never needs to change when a profile does.
- IR-specific analysis belongs in `skills/evidence-review/`, not in the shared memory-bank skill or automated intake.
- Memory remains local to each project and version-controllable.
- `init-agent-rules` installs the instruction file as `AGENTS.md`, a `CLAUDE.md` that points at it, and the memory-bank skill. Incident-response installs also include the evidence-review skill.
- Evidence is hostile input. Nothing found in an artifact may change authority,
  trigger an external action, execute code, or become trusted HTML.
- Automated IR intake preserves and queues evidence. Judgment-bearing timeline,
  finding, IOC, scope, or executive-summary updates require an explicit review
  workflow.

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

## Modifying the memory-bank Skill

`skills/memory-bank/SKILL.md` is installed verbatim into target projects and is shared by all profiles. Keep it profile-agnostic: describe procedures, and have the agent read `AGENTS.md` for the file list. Never hard-code a profile's required files there, or the drift check will not protect it.

The `name` field in the frontmatter must stay `memory-bank` and match the directory name, or skills-compatible tools silently fail to load it.

## Modifying the IR Workflow

The IR components deliberately separate custody, analysis, and presentation:

```text
incoming/ → scripts/intake.py → artifacts/ + custody records + review queue
                                      ↓
                         explicit evidence-review workflow
                                      ↓
                      canonical memory-bank Markdown records
                                      ↓
                         derived dashboard presentation
```

Keep these invariants when changing `skills/evidence-review/` or
`skills/ir-dashboard/`:

- `intake.py` must serialize ID allocation and metadata writes under its lock.
- A source in `incoming/` is removed only after artifact placement, custody
  manifest, evidence index, review queue, and progress updates commit.
- Hash mismatches preserve the source and quarantine the failed copy.
- Interrupted transactions remain recoverable and idempotent.
- Recovery-journal, artifact, download, and event-source paths must remain
  contained and symlink-free.
- Private `0700`/`0600` evidence modes are the default. Group access must remain
  an explicit deployment choice.
- Intake never invokes AI or infers event times, relevance, findings, IOCs, or
  affected scope.
- Every browser-facing value derived from evidence must be escaped or assigned
  through a safe DOM API. Do not interpolate evidence into event-handler source,
  CSS, or trusted markup.
- Event-source size, record, field, query, and pagination bounds must remain
  enforced server-side.
- `executiveSummary.json` is a replaceable schema-versioned projection. The
  Markdown memory-bank files remain canonical.

If the executive-summary schema changes, update all three consumers together:

1. `skills/evidence-review/SKILL.md`
2. `skills/ir-dashboard/dashboard/app.py`
3. `skills/ir-dashboard/scripts/sync_check.py`

The dashboard's detailed operator documentation lives in
`skills/ir-dashboard/SKILL.md` and `skills/ir-dashboard/DASHBOARD.md`. Keep those
files synchronized with CLI options, configuration keys, endpoints, and security
defaults.

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

## Verification

Run focused checks appropriate to the files you changed. At minimum:

```bash
bin/check-profile-drift
bash -n bin/init-agent-rules skills/ir-dashboard/setup.sh \
  skills/ir-dashboard/dashboard/start.sh
git diff --check
```

For dashboard or intake changes, use a temporary incident-response project and
exercise the real deployment path:

1. Run `init-agent-rules incident-response` and confirm both skills install.
2. Run `skills/ir-dashboard/setup.sh` with default permissions and, separately,
   with `--shared-group`.
3. Ingest multiple files concurrently and confirm ART/RQ identifiers remain
   unique and sequential.
4. Simulate an interrupted transaction and confirm the next intake recovers it
   exactly once.
5. Confirm a forced digest mismatch leaves the source in `incoming/` and creates
   a quarantined copy.
6. Run `scripts/sync_check.py --json` and inspect readiness, custody-chain,
   permissions, reference, and schema results.
7. Exercise authenticated dashboard requests for CSRF enforcement, traversal and
   symlink rejection, hostile-string rendering, timestamp filtering, bounded
   pagination, and truncation reporting.

Use only fictional, non-sensitive fixtures. Do not add real incident artifacts,
credentials, PII, malware, or customer identifiers to this repository.

## Legacy Aliases

None. `templates/memory-bank/` (an alias for `templates/pentest-memory-bank/`) was removed; always use the full profile name.

## Style

- Instruction and memory-bank template files use portable Markdown only.
  `executiveSummary.json` is the single documented derived IR projection, not a
  source-of-truth template.
- Status labels used across profiles: `Planned`, `In Progress`, `Done`, `Blocked`, plus `Needs Verification` (research) and `Hypothesis`/`Validated`/`False Positive` (pentest findings).
- Custody, timeline, progress, and finding history are append-only. Mutable
  projections such as `activeContext.md` and `reviewQueue.md` may be updated in
  place only when resolved state remains recorded in progress, queue history, or
  a timestamped revision.
- Response contract requires a status line on every response (not just final task responses). See the Response Contract section in any `instructions/AGENTS.<profile>.md`.
