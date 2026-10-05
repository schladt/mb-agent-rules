# Memory Bank Agent Rules

Portable `AGENTS.md` instructions and complete Agent Skills for a shared, project-local memory bank. Four profiles cover pentesting, academic research, general projects, and incident response.

This repository distributes the framework; it does **not** use a memory bank or install project-specific agent instructions and skills for its own development. The `instructions/`, `templates/`, and `skills/` directories are product sources, not an active local installation. Installation commands below apply to a separate target project; development smoke checks use disposable target directories.

In an installed target project:

- **One instruction source:** native `AGENTS.md`, without a generated `CLAUDE.md` instruction bridge.
- **One local internal workspace:** `.memory-bank/`, the sole project-managed ignored root. Tools in the same checkout share it; clones, other worktrees, and cloud agents do not automatically receive it.
- **Explicit workflows:** read the profile's cognitive files, work, update the relevant memory, and report truthfully. Skills handle intake, planning, status, findings, and maintenance.
- **Trackable outputs:** skills, finding Markdown/assets, actual `deliverables/`, and enabled `team-status.md` remain eligible for Git. Generation is not permission to commit or publish.

## Install and quick start

```bash
mkdir -p ~/.local/bin
ln -sf "$HOME/projects/mb-agent-rules/bin/init-agent-rules" ~/.local/bin/init-agent-rules
ln -sf "$HOME/projects/mb-agent-rules/bin/check-memory-freshness" ~/.local/bin/check-memory-freshness
```

Symlinks keep these commands connected to repository updates. The installer requires Python 3 and resolves its source repository from its executable's real location; use `AGENT_RULES_ROOT=/path/to/mb-agent-rules` to override that source. The target is the current working directory.

From the target project root:

```bash
init-agent-rules general-project
# Optional security findings and team-facing status:
init-agent-rules general-project --findings --external-status
```

Choose one profile:

| Profile | Aliases | Findings by default | Team status by default |
|---|---|---|---|
| `pentest` | `hardware-pentest`, `software-pentest` | Yes, vulnerability findings | Yes |
| `academic-research` | `academic`, `research` | No | No |
| `general-project` | `general`, `project` | No | No |
| `incident-response` | `incident`, `dfir`, `ir` | Yes, adapted incident findings | Yes |

Installer options:

| Option | Purpose |
|---|---|
| `--migrate` | Explicit preservation-first migration of an existing layout; inspect a dry-run first. |
| `--findings` | Opt general projects into the security-finding workflow; pentest/IR already enable it. Not supported for `academic-research`, which retains research-specific records and outputs. |
| `--external-status` | Enable root `team-status.md` for research/general. “External” means outside the memory bank, not client-facing. |
| `--skills-dir=PATH` | Install complete skill packages at a project-relative location; default `.agents/skills`. Repeat this option on refresh for a custom location; recorded metadata does not replace the default. |
| `--no-skill` | Skip skill installation; instructions and memory can still be used, but bundled workflow commands require their scripts to be provisioned separately. |
| `--dry-run` | Preview without changing files. |
| `--force` | Back up before overwriting profile-managed scaffolding; not a substitute for preservation-aware content migration or a license to delete unrelated files. |

Normal refresh preserves populated memory and user content. Schema/layout changes require the migration flow rather than silently creating a second live bank. Conflicting user-owned files need a disposition; `--force` is not a general authorization to remove unrelated files.

Installation preflight rejects symlinked discovery ancestors and unrelated skill links before changing the target. A link is not installer-owned merely because it occupies a default package path; bundled-source links and independently recorded managed-package transitions remain supported.

During `--migrate`, an existing `memory-bank/` and legacy profile `AGENTS.md` also permit recognition of the previous installer's `.claude/skills/<name> -> ../../<skills-dir>/<name>` discovery links without `layout.json`. Targets must be real project-local packages with matching `SKILL.md` frontmatter names and no symlinked path components. Recognized packages must share one location outside the stores being moved. Default and custom legacy locations are supported; pass `--skills-dir` to retain a custom location, or omit it to move to `.agents/skills`. Replaced skill files are backed up, and packages retired by a location change are archived under `.memory-bank/backups/`. Do not delete valid legacy discovery links before migration.

## Installed layout

```text
your-project/
├── AGENTS.md
├── .gitignore                     # managed exclusion: /.memory-bank/
├── .agents/skills/                # complete packages, including scripts/resources
├── .claude/skills/                # discovery links where applicable, not instructions
├── .memory-bank/
│   ├── <profile cognitive files>.md
│   ├── project-status.md          # single execution-status source
│   ├── layout.json                # derived installer metadata, not memory prose
│   ├── planning/archive/
│   ├── incoming/
│   ├── references/
│   │   ├── reference.md           # consolidated synthesis and provenance
│   │   ├── datasets/
│   │   └── raw/                   # consented verbatim reference archives
│   ├── sensitive/                 # operational inputs
│   ├── artifacts/                 # acquired material, with provenance/custody
│   ├── backups/
│   └── runtime/
├── findings/                      # when enabled: README + _TEMPLATE + workstream/slug
├── deliverables/                  # actual reports, exports, and archives
└── team-status.md                 # when enabled: self-contained team coordination
```

There is **no `private/` intermediate directory**, duplicate private deliverables location, or second live `memory-bank/`. The bank is both cognitive memory and internal storage, but context loading uses explicit cognitive-file lists: it does not recursively read incoming, raw data, artifacts, runtime, or backups. Migration may inventory, hash, and copy raw bytes without loading their contents into session memory.

Only `/.memory-bank/` is added as the managed ignored root. Existing user exclusions are preserved. Ignore rules do not untrack files or remove Git history, prevent a tool from reading data, or provide confidentiality. Hidden names, POSIX permissions, indexing exclusions, model access, and Git tracking are separate controls.

## Profiles and authority

Required files below are `.memory-bank/*.md`; extensions are omitted in the table.

| Profile | Count | Required cognitive files |
|---|---:|---|
| `pentest` | 9 | `projectBrief`, `scopeAuthorization`, `sensitiveDataPolicy`, `targets`, `activeContext`, `findings`, `progress`, `evidenceIndex`, `project-status` |
| `academic-research` | 10 | `researchBrief`, `researchQuestions`, `literatureNotes`, `methodology`, `sensitiveDataPolicy`, `sourcesIndex`, `activeContext`, `progress`, `openQuestions`, `project-status` |
| `general-project` | 9 | `projectBrief`, `requirements`, `sensitiveDataPolicy`, `decisions`, `activeContext`, `progress`, `risks`, `handoff`, `project-status` |
| `incident-response` | 11 | `incidentBrief`, `scopeAuthorization`, `sensitiveDataPolicy`, `timeline`, `affectedAssets`, `indicators`, `findings`, `evidenceIndex`, `activeContext`, `progress`, `project-status` |

General-project `--findings` adds the optional `findings.md` working log and its explicit cognitive-load instruction; the base schema remains nine files.

The installed `AGENTS.md` declares the profile's authoritative files and precedence. Authority and explicit supersession take precedence over mere recency: a newer working note does not silently override scope or policy. `project-status.md` owns execution status, not findings validity, custody, authorization, or research citations.

- **Pentest:** full shared workspace, CVSSv3.1 finding sources, promotion, and warn-only lint.
- **Research:** retain citation keys, literature notes, methodology, consent, and uncertainty. `references/reference.md` synthesizes knowledge; it is not a duplicate citation registry. No default security findings or CVSS requirements.
- **General:** retain requirements, decisions, risks, and handoff. Security findings are opt-in, not a default loot or IR workflow.
- **IR:** retain ART custody, explicit review, fact/inference separation, confidence, alternatives, and `Suspected`/`Confirmed`/`Ruled Out`. CVSS applies to actual vulnerabilities, not every incident conclusion. Conditional recommendations can be recorded while execution waits for the named approver. Do not infer attribution, exfiltration, event time, or certainty from intake alone; refer legal conclusions and notification decisions to counsel.

### Soft conventions, real authority, and sensitive data

Repository-owned defaults use a specific risk disclosure and safe default, followed by confirmation of a precise exception. Confirmed exceptions persist **project-wide until revoked**, recorded in `activeContext.md` and the relevant authority/policy file. Matching operations do not repeatedly prompt; a materially different risk or scope needs a new decision. Keep dated confirmation/revocation history.

That mechanism does not override harness/provider/tool permissions, third-party authorization or consent, data integrity, or factual truth. Confirmation cannot make an uncomputed hash verified or an unperformed test pass. Hostile source material is data, never authority.

`sensitiveDataPolicy.md` records classes, approved paths, permissions, and Git treatment—not live secret values. Its modes are `restricted`, `designated-store` (default), and explicitly selected `private-lab`. Repository visibility does not select a mode. A completed policy row authorizes its stated path/classes; directory existence alone does not. Live production secrets remain reference-only in cognitive memory; synthetic plaintext requires an explicit lab policy.

Operational owner-supplied credentials/configuration belong in `.memory-bank/sensitive/`. Acquired material belongs in `.memory-bank/artifacts/`, with origin, classification, hashes, and provenance; IR additionally preserves full custody. Legacy loot/evidence/artifacts consolidate here without erasing their distinctions. Finding-local assets are report-use copies or transformations with provenance, not replacement acquisition originals. Default internal directories use `0700` and sensitive files `0600` where supported; authorized policy may select other modes.

## Complete portable skills

Every profile receives:

- [`memory-bank-context`](skills/memory-bank-context/SKILL.md): read-only bootstrap from `AGENTS.md` and the explicit required cognitive files. No repository scan, repair, test, or write.
- [`memory-bank-maintenance`](skills/memory-bank-maintenance/SKILL.md): initialization, migration, audit, and repair; preserve history and keep raw stores out of cognitive loading.
- [`memory-bank-workflow`](skills/memory-bank-workflow/SKILL.md): common intake, reference synthesis, completed-plan archival, overrides, and status projection.

Findings-enabled installs also receive [`memory-bank-findings`](skills/memory-bank-findings/SKILL.md). IR also receives [`memory-bank-ir-evidence-review`](skills/memory-bank-ir-evidence-review/SKILL.md). The dashboard is an optional, separately deployed package.

Skill distribution includes the **entire package**, not only `SKILL.md`: referenced scripts and resources must travel with it. Names/frontmatter follow the [Agent Skills specification](https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx). `.agents/skills` is the default portable location; actual discovery depends on host/version/surface. Claude skill discovery is separate from native AGENTS support; use the installer's applicable `.claude/skills` links or install directly:

```bash
init-agent-rules general-project --skills-dir=.claude/skills
```

Preserve real user-owned skill directories when changing location. A local link cannot provision a cloud checkout: track the required package and valid relative discovery links or explicitly provision them in the destination. This does not provision the ignored bank.

## Common workspace commands

The Python commands are standalone standard-library tools. Examples use the default installed skill location; substitute your configured `--skills-dir`. Put `--root PATH` **before** the subcommand. Without it, commands use the Git root or current directory.

Absolute workspace inputs may use the same root alias supplied to `--root` (including macOS `/var` aliases). Symlinks beneath that root and parent-traversal components are rejected rather than resolved away.

```bash
python3 .agents/skills/memory-bank-workflow/scripts/workspace.py --root . status
python3 .agents/skills/memory-bank-workflow/scripts/workspace.py --root . status --check
python3 .agents/skills/memory-bank-workflow/scripts/workspace.py --root . archive-plan \
  .memory-bank/planning/release.md --date 2026-10-04
python3 .agents/skills/memory-bank-workflow/scripts/workspace.py --root . intake \
  .memory-bank/incoming/vendor-guide.pdf --kind reference \
  --origin "Vendor documentation supplied by owner" --topic vendor-guide --retain
```

### Intake and references

`intake PATH --kind reference|operational|artifact --origin TEXT [--topic SLUG] [--archive|--delete|--retain] [--confirm]` makes classification, provenance, and disposition explicit. Classify origin and sensitivity before routing. Default/`--retain` leaves the source pending; `--archive` authorizes verified routing and source removal; `--delete` requires `--confirm` and agent-confirmed completed review/promotion. `intake-pending` reports metadata-only pending counts. The command can route/copy/hash material and record metadata; knowledge extraction and promotion into cognitive files, consolidated references, and status are agent-led—not fabricated automatic analysis.

Ask before optional verbatim reference archival to `.memory-bank/references/raw/`. If declined, ask whether to delete or retain. Deletion requires explicit approval and completed required preservation; unanswered requests and retained/failed/ambiguous items remain visibly pending in `incoming/`. Do not declare intake empty by ignoring hidden files or nested drops. One governed primary home plus references avoids uncontrolled copies.

IR artifact intake uses the installed `scripts/intake.py` custody path. If optional IR tooling is absent, automated intake reports that prerequisite rather than bypassing custody; use the documented manual profile custody process or install the tooling. Preserving/queuing evidence is not completed analysis and is independent of optional reference archival.

Retries validate retained acquisitions before source disposition. A missing or corrupted stored copy requires reconciliation; failed validation preserves the existing acquisition identity and receipt history instead of allowing the next retry to silently acquire a replacement.

### Plans and overrides

`archive-plan PATH [--date YYYY-MM-DD]` preserves completed plan content/history under `.memory-bank/planning/archive/YYYY-MM-DD-<name>.md`, records the move, and repairs active links without silently overwriting a collision. Link repair includes the optional general-project findings log when findings are enabled. Record completion before archival.

The workflow skill records or revokes scoped, confirmed project-default exceptions in active context and the named authority file:

```text
override record --id SLUG --policy .memory-bank/FILE.md --default TEXT --risk TEXT --action TEXT --scope TEXT --confirmed-by TEXT [--date YYYY-MM-DD] --confirm
override revoke --id SLUG --reason TEXT --confirmed-by TEXT [--date YYYY-MM-DD] --confirm
```

Pass these subcommands after `python3 .agents/skills/memory-bank-workflow/scripts/workspace.py --root .`. An optional global `--profile SLUG` supplies the domain when metadata is absent. Neither a record nor a confirmation bypasses actual runtime permission or integrity checks.

### Internal source and team-facing status

Root **`team-status.md`** is for teammates who do **not** have memory-bank access. It is not a client report or client update: client-facing reports/exports belong in `deliverables/`, and client communications belong in the project's separate client update file. The private source remains `.memory-bank/project-status.md`; generation uses it, but reading the team document must not require it.

The source `.memory-bank/project-status.md` has this explicit publication grammar:

```markdown
# Project Status
## Publishable
### Progress
- Not yet reported.
### Milestones
- Not yet reported.
### Blockers
- Not yet reported.
### Next Steps
- Not yet reported.
### Client Actions
- Not yet reported.
## Internal
Private working notes stay here.
```

Only the five `Publishable` sections flow to root `team-status.md`, headed `# Team Status`. Here “publishable” means approved for team readership, not approved for public or client delivery. Required source headings occur exactly once; organize detail within them using bold workstream labels, nested bullets, and tables rather than extra headings or code fences. This is positive selection, not arbitrary-prose redaction; do not place raw evidence, TTPs, secrets, or unapproved details in these fields. Heuristic warnings cannot prove sanitization.

Write a detailed coordination update, not a terse pointer into private notes:

- **Progress:** establish project context and scope, then describe workstreams, work completed, concrete results, coverage, and remaining gaps.
- **Milestones:** show deliverable/checkpoint status, known owners, and source-backed dates or target dates.
- **Blockers:** explain the problem, its impact, who can unblock it, and the next resolution step.
- **Next Steps:** prioritize specific actions with known owners, dependencies, and dates.
- **Client Actions:** describe requests or dependencies the team is tracking with the client; this is not a client-facing message.

State unknown owners, dates, and outcomes explicitly; do not manufacture completion or certainty. Explain results and references in ordinary language. Use only team-accessible links, resolved relative to root `team-status.md`; private memory-bank links, raw evidence, or unexplained IDs must not be required to understand the update. The generator selects prose, not facts: substantive synthesis belongs in the source fields.

When team status is enabled, run `status` after every agent edit to the source; manual editors run it explicitly. `status --check` detects stale/missing output without substituting generation time for source freshness. Internal source-hash receipts stay inside the bank. Malformed generation preserves the previous output and reports failure/staleness, not a supposedly safe current fallback. There is no watcher, host hook, background sync, upload, or guarantee of automatic regeneration after arbitrary manual edits. Local generation is not external publication authorization.

Existing installs switch on the next status generation or installer refresh. A legacy root `project-status.md` is backed up and removed in the same generation transaction only when its bytes match the previous output hash in the status receipt. Modified or unrecognized legacy files remain with a warning; an unrelated existing `team-status.md` blocks generation rather than being overwritten. `status --check` is read-only and reports a managed legacy output as needing migration. The private source filename and `--external-status`/`external_status` option and metadata names are unchanged.

## Tool-neutral findings and deliverables

Enabled profiles receive `findings/README.md` and `findings/_TEMPLATE/finding.md`. Full report prose lives once at `findings/<workstream>/<slug>/finding.md`, with optional relative `assets/`. Use descriptive title-only H1s and title-based crossreferences; folder/index identity and custody IDs remain available without adding report finding IDs to titles/body.

The working finding log is status truth; report Markdown is narrative truth. Promotion records backlinks/history; synchronization updates report Status headers. Pentest states are `Hypothesis`, `Validated`, `Informational`, and `False Positive`. Default report selection is Validated/Informational; hypotheses need explicit provisional selection. False positives stay in the log. IR retains its separate investigation states, confidence, and fact/inference structure rather than silently translating them into pentest states.

Canonical vulnerability findings include Status/Workstream/Date, CVSSv3.1 score/severity, affected assets and origin, description with affected assets and steps to reproduce / observed behavior, technical/business impact, remediation, references, and evidence provenance. Scored findings require consistent score/vector/metric table. Informational findings use **0.0 / N/A with no metric grid**.

```bash
python3 .agents/skills/memory-bank-findings/scripts/findings.py --root . lint
python3 .agents/skills/memory-bank-findings/scripts/findings.py --root . sync
python3 .agents/skills/memory-bank-findings/scripts/findings.py --root . list
```

The exact findings subcommands are:

```text
lint [PATH]
promote --title TITLE --workstream SLUG --slug SLUG --source PATH [--include-hypothesis | --include-suspected]
sync [PATH]
list [--include-hypothesis | --include-suspected]
```

An optional global `--profile pentest|incident-response|general-project` follows `--root PATH`; otherwise installed metadata selects the domain. Promotion requires an existing matching title/status in the working log and supplied full prose: it moves the draft (or registers an already canonical source), copies referenced local assets, and updates the log backlink and findings index. It does not generate a finding scaffold or invent evidence. Default IR selection is `Confirmed`; `list` excludes unregistered, stale, or status-mismatched reports.

The profile flag supplies missing metadata, not an override of an installed domain. Use `--include-hypothesis` for provisional pentest/general hypotheses or `--include-suspected` for provisional IR conclusions, on both promotion and selection. Neither flag admits False Positive/Ruled Out or converts IR confidence into severity.

Promotion rejects symlink components in the selected source and linked local asset paths before copying assets, updating records, or consuming the draft. This also applies when registering an already canonical report.

```bash
python3 .agents/skills/memory-bank-findings/scripts/findings.py --root . promote \
  --title "Example validated observation" --workstream application \
  --slug validated-observation --source .memory-bank/planning/finding-draft.md
```

Lint checks section/score/status consistency, relative asset resolution/containment, and obvious secret/PII indicators. Convention findings are warnings (exit 0); actual input/output/usage failures are nonzero. Diagnostics identify locations without echoing suspected values. Raw/unmodified finding assets are allowed by default, but suspected sensitive exposure triggers the scoped warn-confirm policy. Neither raw assets nor successful lint imply Git or external-delivery safety.

Actual final reports/exports/zips belong only in top-level `deliverables/`, with normal Git eligibility and no private duplicate. This project **does not compile reports**, generate DOCX/Google Docs, or integrate report-builder. A separately selected renderer must understand the source layout and approved selection; `list` is not a report engine.

## Optional IR dashboard

The dashboard is for **private local development and authorized investigation**, not a production/multi-tenant service. Setup follows profile installation:

```bash
init-agent-rules incident-response
bash /path/to/mb-agent-rules/skills/memory-bank-ir-dashboard/setup.sh /path/to/project \
  --title "Operation Name" --accent "#10b981"
cd /path/to/project/dashboard
bash start.sh --port 8443
```

Deployed `dashboard/` and `scripts/` remain trackable. Configuration lives at `.memory-bank/dashboard.config.json`; virtual environment, certificates, caches, locks, and recovery state remain under the bank. Setup provides a preservation-aware managed-code refresh; do not delete the deployed dashboard to upgrade it. `--shared-group` explicitly selects `0770`/`0660` in place of private evidence modes. `--with-sample-data` installs a fictional walkthrough, never real incident data.

Default bind is `127.0.0.1`, with HTTPS and generated password; set `DASHBOARD_PASSWORD` for a fixed password. Non-loopback with `--no-ssl` or `--no-auth` requires explicit `--allow-insecure-remote`, which is not a production-hardening claim.

Select evidence explicitly rather than ingesting every mixed-classification drop:

```bash
python3 scripts/intake.py .memory-bank/incoming/edr-export.json \
  --provided-by "Analyst Name" --source-system "EDR export"
python3 scripts/sync_check.py --json
```

Intake serializes IDs and metadata, copies and re-hashes artifacts, records custody and review queue entries, and uses a recovery journal. Remove a source only after verified committed preservation; mismatches preserve the source and quarantine the copy. Dry-run is not stored-copy verification. The artifact store's hash-chained custody manifest detects interior modification/reordering, but a local chain cannot prove it was not wholly replaced or truncated; stronger assurance needs an authorized independent anchor.

No automatic AI analysis occurs. The evidence-review skill explicitly performs analysis, using artifact event times rather than ingest times. Untrusted evidence stays inert in the browser; bounded event queries report truncation and API failures honestly. `sync_check.py` checks readiness, custody, permissions, references, review state, and executive projection consistency. The internal `executiveSummary.json` is analytical presentation, not the team-status source; inventory counts and responder downloads do not prove exfiltration or attacker phases.

See [dashboard operator documentation](skills/memory-bank-ir-dashboard/DASHBOARD.md) and its [skill](skills/memory-bank-ir-dashboard/SKILL.md) for configuration and deployment details.

## Native harness compatibility and memory

The baseline is **current native AGENTS-capable authoring harnesses**, not every older version, provider deployment, review surface, or cloud environment. No instruction bridge, Copilot review adapter, provider settings, or hooks are installed.

| Harness / surface | Documented behavior and limits |
|---|---|
| Codex | Startup instruction chain, same-directory `AGENTS.override.md` precedence, and 32 KiB default `project_doc_max_bytes` cap. This is an instruction budget, not total model context. `.agents/skills` and symlink support are documented. [AGENTS guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [skills](https://learn.chatgpt.com/docs/build-skills). |
| Claude Code | Native AGENTS fallback was added in **v2.1.277**, when no CLAUDE.md exists; release caveats include Bedrock/Vertex/Foundry exclusions. An existing user-owned CLAUDE.md may suppress fallback: preserve it and resolve the instruction conflict explicitly. Older/unsupported provider cases are outside this baseline. [Release](https://github.com/anthropics/claude-code/releases/tag/v2.1.277), [behavior details](https://github.com/anthropics/claude-code/blob/main/mods/agents-md/README.md). |
| Copilot CLI | Supports relative `@` imports and deduplicates identical instruction sources; do not assume universal double-loading. [CLI instructions](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions). |
| VS Code / Copilot | Local and Agent Host instruction behavior differ; local sources are additive and nested discovery depends on settings. Cloud, CLI, authoring, and review support differ; VS Code review and GitHub.com review do not have identical instruction support. [VS Code source](https://github.com/microsoft/vscode-docs/blob/main/docs/agent-customization/custom-instructions.md), [support matrix](https://docs.github.com/en/copilot/reference/custom-instructions-support), [skills](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills). |
| Cursor | Consult the current [rules](https://cursor.com/docs/rules), [skills](https://prod.cursor.com/docs/skills), and [ignore](https://cursor.com/docs/reference/ignore-file) documentation for the installed version. This review had official search-index evidence, but direct TLS reads failed; no newly dated change or runtime certification is claimed. |

These citations are documentation evidence, **not cross-harness runtime certification**. Claude skill watcher/account-sync behavior was not directly verified; do not rely on assumed synchronization. See [Claude skills](https://code.claude.com/docs/en/skills). For monorepos, use one root bank and narrowly scoped nested instructions only where the harness supports them; precedence/additivity is host-dependent.

Native memory is not universally machine-local: [Copilot repository memory](https://docs.github.com/en/copilot/concepts/agents/copilot-memory) is service-shared, in preview, with unused entries expiring after 28 days. [Codex local memories](https://learn.chatgpt.com/docs/customization/memories) and other hosts have their own storage/settings. Treat native memory as a convenience cache, not the project's authority, and review actual retention/confidentiality settings before placing information there. The installer changes no provider memory settings.

The ignored bank is local to a checkout. Fresh clones/worktrees/cloud sessions need owner-authorized provisioning; no automatic transfer, export/import service, or tracked duplicate bank is supplied. Git ignore/content exclusions are not access controls and exclusions do not apply uniformly across modes or symlink paths: see [GitHub exclusion limits](https://docs.github.com/en/copilot/concepts/security-governance-and-network-settings/content-exclusion).

## Completion contract and Git freshness limits

Changes anywhere in the project—including assets, incoming dispositions, references, archived plans, team status, and deliverables—require appropriate memory updates. Memory-only work counts as an update without recursive bookkeeping forever. Read-only work does not fabricate a write. Every response uses the installed profile's truthful status contract, for example:

```text
Memory bank: updated — activeContext.md, progress.md
Memory bank: read, no update needed
Memory bank: not consulted
```

The last form is for unrelated requests, not a substitute for required context. Preserve decision/custody/history records; prohibited values may be redacted for privacy repair with a non-sensitive correction record rather than perpetuated under an append-only slogan.

`check-memory-freshness` is Git-based and **cannot certify ignored-bank updates**. With the default local ignored bank, its skip/unavailable notice is not evidence of freshness. Where a bank is deliberately tracked under an explicit policy, its modes inspect Git-visible changes:

```bash
check-memory-freshness --staged
check-memory-freshness --worktree
check-memory-freshness --head
check-memory-freshness --range main..HEAD
```

`--head` uses the first-parent change set for an ordinary merge. Only root `.memory-bank/*.md` changes count as cognitive updates; copying raw artifacts or changing installer metadata is not sufficient. Git revisions/errors are validated before an untracked-bank skip and fail rather than masquerading as “no changes.” This repository installs no hooks and does not stage, untrack, or rewrite history automatically; do not claim that natural-language instructions enforce every editor event or that a Git skip validates private memory.

## Preservation-first migration

Preview from the target project, then explicitly migrate:

```bash
init-agent-rules general-project --migrate --dry-run
init-agent-rules general-project --migrate
```

Use the actual profile and any required opt-in feature flags. Profile changes also require content mapping, not just a new instruction file.

1. Inventory the installed managed paths and user customizations; identify already-tracked confidential material and unresolved destination collisions. Do not print private contents into the migration transcript.
2. Preserve backups under `.memory-bank/backups/`; retain cognitive history and hashes/custody for acquired originals. Migrate the legacy bank and stores to the flattened layout, including legacy `ref-docs` references and loot/evidence/artifact provenance. Do not keep alternate live stores or silently overwrite a collision.
3. The installer repairs Markdown links in current cognitive, active-plan, consolidated-reference, findings and root README documents, plus cognitive code-path references, retaining originals. It does not rewrite raw evidence, custody records or archived plan bytes. Use `memory-bank-maintenance` for authorized semantic mapping and references outside that set. Backups are not recursively loaded into session memory; scaffold creation is not completed semantic migration.
4. Remove **only positively identified obsolete managed files or links**. A known generated CLAUDE bridge may be removed for native AGENTS fallback; unrelated CLAUDE instructions must be preserved and their conflict explained. Never delete whole `.claude/commands`, `.claude/skills`, `.claude/agents`, `.github`, or `.cursor` directories. Inspect legacy per-tool rules individually; preserve user modifications and real skill directories.
5. Update only identified managed ignore entries; preserve user exclusions. Migration does not automatically untrack data or rewrite Git history. Review exposure separately before committing anything.
6. Refresh optional deployed IR tooling through its setup flow, preserving customizations/backups; confirm custody and reference paths rather than deleting a deployment and starting over.

Normal consumers use `.memory-bank/` only—there is no live old-name fallback. Migration records `.memory-bank/path-migrations.json` (`schema`, path `prefixes`, and prior `project_roots`) so immutable historical references can resolve without rewriting custody history; new records use canonical paths. `--force` backs up before overwriting managed scaffolding and is not a shortcut for semantic migration.

Each migration also retains a private `backups/<timestamp>/migration.json` inventory with original source/destination paths, metadata and verified hashes. Hashes describe preserved bytes before current-document reference repair; original cognitive snapshots and replaced documents remain in that backup.

For source development and verification guidance, see [CONTRIBUTING.md](CONTRIBUTING.md).
