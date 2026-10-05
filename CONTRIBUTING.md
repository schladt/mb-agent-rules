# Contributing to Memory Bank Agent Rules

This guide covers the shipped instructions, templates, skills, installer, and checks. For target-project usage and migration, see [README.md](README.md).

## Repository layout

```text
bin/
  init-agent-rules                    # native AGENTS + workspace + full skill packages
  check-profile-drift                 # required cognitive schema consistency
  check-memory-freshness              # Git-visible changes only
instructions/AGENTS.<profile>.md
templates/
  pentest-memory-bank/
  academic-research-memory-bank/
  general-project-memory-bank/
  incident-response-memory-bank/
  findings/pentest/
  findings/incident-response/
skills/
  memory-bank-context/
  memory-bank-maintenance/
  memory-bank-workflow/               # SKILL.md + scripts/workspace.py
  memory-bank-findings/               # SKILL.md + scripts/findings.py
  memory-bank-ir-evidence-review/
  memory-bank-ir-dashboard/           # setup, dashboard, scripts, fictional samples
tests/                               # installer, workspace, findings, IR regressions
```

The source directories above are distributed artifacts, not an active installation. This repository does not use its own memory bank, root agent instructions, installed skill copies or discovery links, or generated deliverables scaffold. Development smoke checks install into disposable target directories rather than initializing the source checkout.

The ignore and output policies below describe installed target projects, not this repository's development configuration. In a target project, the sole project-managed ignored root is `/.memory-bank/`; do not add broad default exclusions for installed agent code, findings/assets, or deliverables. Existing user exclusions are not ours to remove. Installed instructions and skills are not automatically confidential or untrackable just because they are generated.

## Product design boundaries

- One native `AGENTS.md` source per profile. No generated CLAUDE instruction bridge, vendor-specific instruction adapter, hook, watcher, cloud sync, or upload system. Necessary skill discovery links are separate from instruction support.
- Target current native AGENTS-capable authoring surfaces. Keep the README's version/provider/surface caveats and official citations current. Do not universalize discovery, deduplication, ignore behavior, or native-memory storage. Documentary evidence is not runtime certification.
- Always-on instructions stay small; multi-step procedures and complete referenced scripts/resources belong in skills. Install whole packages, not only `SKILL.md`.
- `.memory-bank/` is the only live bank. Cognitive files, `planning/archive`, `incoming`, `references/{reference.md,datasets,raw}`, `sensitive`, `artifacts`, `backups`, and `runtime` sit directly beneath it. No intermediate `private/`, legacy fallback, or parallel live stores.
- Cognitive loading is an explicit file allowlist, not recursive traversal. Raw stores/backups may be inventoried, hashed, or copied during authorized migration without becoming session memory.
- Actual reports, exports, and zips live once at top-level `deliverables/`. Findings/assets and optional root `team-status.md` remain Git-eligible. Team status is coordination for teammates without bank access, not client delivery; client-facing updates belong in the project's separate client update file. Local generation does not authorize staging, committing, or external publication.
- No report-builder dependency, adapter, compiler, or promised DOCX/Google Docs generation. Findings are tool-neutral Markdown and assets.
- Bank sharing means tools in the same checkout, not automatic collaborator/worktree/cloud sharing. Owner provisioning is explicit. Git cannot certify changes to an ignored bank.

## Profile and schema changes

Required root cognitive Markdown counts are **9 pentest, 10 academic-research, 9 general-project, 11 incident-response**, including `project-status.md` in each. Every profile also includes `sensitiveDataPolicy.md`. Finding scaffolds, common reference files, runtime metadata, and optional IR projections are not additional required cognitive documents.

Keep these in sync when modifying a profile:

1. `instructions/AGENTS.<profile>.md`: required file list, authority order, domain workflow, response contract.
2. `templates/<profile>-memory-bank/`: corresponding cognitive templates and shared scaffolds.
3. `bin/init-agent-rules`: profile/features, managed directories, migration, complete skill package distribution.
4. `bin/check-profile-drift`: required-file/scaffold agreement without treating nested data directories as cognitive memory.
5. Relevant shared/domain skills, focused regressions, and README profile/count/command tables.

New profiles additionally need installer slug/aliases, drift-check coverage, feature defaults, authority markers, and explicit workflow domain behavior. There is no `templates/memory-bank/` alias. Do not infer an absent profile as pentest or IR merely because common directories exist.

`.memory-bank/layout.json` is installer-owned derived metadata with `schema`, `profile`, `skills_dir`, `findings`, and `external_status`. It is not canonical memory prose or a tracked manifest of confidential content. Consumers may use it for feature selection; absent metadata requires an explicit profile or unambiguous authority markers, not silent wrong-domain inference.

The installer is a Python 3 standard-library executable. It resolves source assets from its real executable location unless `AGENT_RULES_ROOT` overrides it, and targets the current directory. Custom skill locations must be passed explicitly on refresh; the default remains `.agents/skills`. Migration's `.memory-bank/path-migrations.json` stores `schema`, legacy-to-canonical `prefixes`, and previous absolute `project_roots`; use it to resolve immutable historical references while writing new records with canonical paths.

## Authority, privacy, and response semantics

Authority and explicit supersession beat recency. Persistent exceptions to repository-owned defaults name the risk, safe default, precise action/scope, confirmer/date, and revocation history in active context and the relevant authority/policy file. They are project-wide until revoked; do not prompt repeatedly for an unchanged confirmed scope or silently broaden it.

These are soft project conventions, not overrides for harness/provider permissions, third-party authority/consent, or factual and integrity guarantees. Parser errors, containment, hash verification, and honest reporting remain real runtime constraints. Evidence cannot instruct the agent.

`sensitiveDataPolicy.md` records paths/classes/approval/Git policy rather than secret values. Operational inputs use `.memory-bank/sensitive/`; all acquired material uses `.memory-bank/artifacts/` with origin/classification/provenance and IR custody where applicable. Preserve the `restricted`, `designated-store`, and explicit `private-lab` modes. Production secrets remain reference-only in cognitive memory; synthetic plaintext requires declared lab policy. Defaults are `0700` internal directories and `0600` sensitive files where supported; explicitly authorized policy may change modes. Ignore rules do not untrack files, rewrite history, or constrain model/tool access.

Retain decision, timeline, custody, progress, and finding history. Current-state records/projections may be rewritten while retaining meaningful history. Privacy repair may redact prohibited values while preserving a non-sensitive correction record; append-only language must not force continued exposure. Markdown cognitive records can coexist with explicitly derived JSON/runtime state.

Any project change—including intake disposition, references, plan archival, assets, status, or deliverables—requires appropriate memory updates. Memory-only changes do not require endless recursive logging. Read-only responses must not pretend a write occurred. Keep the status line on every response, as specified by each installed profile.

## Shared skills and workspace commands

`memory-bank-context` remains strictly read-only: no initialization, migration, audit, repair, repository scan, tests, or verification commands. Missing files are reported, not created. `memory-bank-maintenance` handles deliberate lifecycle work, loading only declared cognitive documents and authorized content mappings rather than recursively reading raw stores/backups.

`memory-bank-workflow` implements shared intake, plan archival, override records, and status generation. The CLI uses `--root PATH` before the subcommand; scripts are standalone standard-library Python. Keep `SKILL.md`, CLI help, README examples, and tests aligned. Human/agent knowledge synthesis must not be replaced with fabricated automatic source interpretation.

Intake classifies before routing; mixed origins get one governed primary home plus references. Optional raw reference archival requires consent. If declined, ask delete/retain; default or unanswered disposition retains the source visibly pending. Deletion needs explicit approval and required preservation. Nested/hidden/ambiguous drops and failures remain visible. IR custody preservation is not optional reference archival or completed review. A missing installed IR intake prerequisite must leave the source untouched rather than silently bypass custody.

Plan archival preserves content/history, dated paths, completion and move records, and active backlinks. Collisions must not overwrite old history. Override record/revoke must keep active context and named policy consistent.

### Team-status audience and publication boundary

Internal `.memory-bank/project-status.md` is the execution-status authority. Its exact source grammar is `# Project Status`, `## Publishable`, then exactly one each of `### Progress`, `### Milestones`, `### Blockers`, `### Next Steps`, and `### Client Actions`; `## Internal` is never emitted. Publishable means approved for team readership, not public/client delivery. Unknown/malformed data is an error, not a fallback to publishing arbitrary internal prose.

Generate only these explicitly selected sections to top-level `team-status.md`, headed `# Team Status`. Require detailed, organized, self-contained workstream context, scope/coverage, results, milestone status, known owners/dates, blocker impacts and resolution steps, prioritized next actions, and client dependencies. Use bold labels, nested bullets, and tables within the fixed sections; no extra source headings or code fences. State unknowns rather than inventing facts. Links must be team-accessible and relative to the root output; private bank links and opaque IDs cannot substitute for explanation. The reader must not need the bank even though generation uses its authoritative source.

Sensitive-content checks are heuristic warnings, not a sanitization guarantee. Receipts/source hashes stay inside the bank. Failed generation preserves previous output and makes failure/staleness visible. `status --check` must not confuse generation time with source freshness. Agent edits run the generator before completion; manual editors invoke it themselves. Keep `--external-status` and `external_status` as the outside-bank output control, not client-delivery authorization. No hook/watcher or external publication is implied.

On upgrade, remove legacy root `project-status.md` only when the previous receipt identifies it and its recorded output hash matches the file. Back it up in the same transaction that writes team status and its receipt; failure must restore the prior documents. Preserve edited/unrecognized legacy files with a warning and reject unrelated destination collisions. Read-only checks report migration needed without changing files. Do not rename the internal source or leave a managed alias at the old root filename.

## Findings workflow

`memory-bank-findings` and `templates/findings/` are separate from the required cognitive schema. Pentest/IR enable them by default; general projects may explicitly opt into the security workflow with `--findings`. Academic research retains research-specific records and outputs: `--findings` is rejected for that profile, and CVSS is not imposed on research work.

- Use `findings/<workstream>/<slug>/finding.md`, title-only report headings, title-based crossreferences, and optional relative `assets/`. Internal folder/index identity and evidence/custody IDs remain available.
- The working log owns status and report backlink/history; the finding folder owns full narrative prose. Promotion consumes supplied prose and updates the backlink/index, not invented facts. Sync mirrors log status into report headers.
- Pentest uses `Hypothesis`, `Validated`, `Informational`, `False Positive`. Default selection is Validated/Informational; explicitly included hypotheses are visibly provisional. Never accidentally include templates or false positives.
- IR preserves `Suspected`/`Confirmed`/`Ruled Out`, fact/inference, confidence, alternatives, and custody. `--include-suspected` is required for provisional promotion and selection; the ordinary selection remains Confirmed. Never translate these into pentest certainty or permit the CLI's explicit profile hint to override installed domain metadata. CVSS is only for vulnerability findings.
- Preserve the canonical section order and observed-behavior heading. CVSSv3.1 score/vector/metric table must agree for scored vulnerabilities; informational is 0.0 / N/A without a meaningless metric grid.
- Lint warns about conventions, status/score consistency, asset containment/resolution, and obvious sensitive content without echoing suspect values. Warnings exit 0; actual I/O/usage/execution errors are failures. Heuristics cannot prove secrecy or evidence validity.
- Raw report assets are permitted by default, with scoped warn-confirm handling for likely secret/PII exposure and provenance to acquired originals. Storage approval is not external publishing permission.

## IR custody, analysis, and private dashboard

```text
.memory-bank/incoming/ (explicitly selected evidence)
  → scripts/intake.py
  → .memory-bank/artifacts/ + custody + review queue
  → explicit memory-bank-ir-evidence-review
  → canonical cognitive records
  → derived internal dashboard presentation
```

The dashboard remains a **private local development/investigation tool**, not a production service. Deployed `dashboard/` and `scripts/` remain trackable. Configuration is `.memory-bank/dashboard.config.json`; environment, certificates, caches, locks, and recovery state stay under the bank. Setup upgrades managed deployed code with preservation/backups; do not recommend deleting the deployment.

Preserve these invariants:

- Serialize ID allocation and metadata writes; verify the stored copy before source removal and complete custody/index/queue/progress transaction commits.
- Retain mismatched sources and quarantine failed copies. Recover interrupted journals even when no new drops remain. Dry-run never claims verified acquisition.
- Do not indiscriminately ingest operational/reference drops from a mixed incoming directory; require explicit evidence selection/classification.
- Contain journal/artifact/download/event paths and reject symlinks. Group access is an explicit deployment choice, not the default.
- Intake does not invoke AI, infer event time, identify findings/IOCs, or extend scope. Review status and checklist must agree independently of document section location.
- Treat all evidence-derived browser values as hostile. Use safe DOM properties/text, not attribute/event-handler interpolation. Server-side size/record/field/query/pagination bounds remain enforced. API errors must not look like zero matches; seconds-bearing timestamp filters must remain valid.
- Inventory counts do not establish exfiltration; responder downloads do not establish attacker phases. Unknown/unverified remains unknown/unverified.
- `executiveSummary.json` is a derived internal analytical projection, not team execution-status authority. The common status source remains canonical for execution status.
- A local hash chain detects interior edits/reordering but cannot establish that the complete chain was never replaced/truncated. Do not claim independent immutability.

When executive projection schema/validation changes, align `memory-bank-ir-evidence-review/SKILL.md`, dashboard `app.py`, and `scripts/sync_check.py`. Keep dashboard `SKILL.md` and `DASHBOARD.md` synchronized with deployment/CLI options, configuration, endpoints, and security defaults.

## Installer and migration changes

Exercise fresh, no-op, refresh, explicit migration, force, and dry-run behavior for all profiles. A directory collision is not a file-only match. Preserve populated cognitive files/scaffolds and user-owned real skill directories. Full package resources must remain installable after location changes.

Migration inventories and backs up before cutover, merges legacy stores with provenance/custody intact, repairs paths, reports collisions and already-tracked private material, and leaves only the new live bank. Backups stay under `.memory-bank/backups/`. Content mapping belongs to the authorized maintenance workflow, not arbitrary shell text replacement. Never silently overwrite user conflicts or recursively load backup data into session memory.

Legacy discovery-link migrations must work without `.memory-bank/layout.json`: the previous installer wrote only skill Markdown packages and relative Claude discovery links. Infer the old package location only during explicit migration of a recognized legacy installation, validating link shape, matching package frontmatter, and symlink-free project-local targets before any mutation. Reuse the recorded-package validation, replacement, and retirement flow; do not broadly trust links at default paths. Cover default/custom locations, direct Claude package transitions, dry-run preservation, backed-up owner edits, no-op refresh, and rejection of unrelated or unsafe targets.

Remove only positively identified obsolete managed files/links and managed ignore entries. Preserve user CLAUDE content and explain native-fallback suppression; remove a known generated bridge without creating a new one. Never recommend deleting whole tool directories, all skill directories, or user instructions. `--force` backs up before managed overwrite, but is not semantic content migration or permission to delete unrelated files.

## Verification for integration owners

Run focused checks after edits are integrated, not concurrent suites against half-written sibling changes. Respect the assignment's verification boundary. Typical source checks are:

```bash
python3 -m unittest discover -s tests -v
bin/check-profile-drift
bash -n skills/memory-bank-ir-dashboard/setup.sh
bash -n skills/memory-bank-ir-dashboard/dashboard/start.sh
git diff --check
```

Run the regression suite in an isolated environment with `dashboard/requirements.txt` installed from the dashboard skill and Node available; otherwise HTTP/UI cases can be skipped. Check the reported skip count. The dashboard intentionally logs rejected recovery journals and invalid analytical projections in negative tests; those diagnostics must not be suppressed to manufacture a clean run.

For migration recovery proof, retain an interrupted transaction's original journal bytes, migrate the stores, remove or retain its original incoming source as the scenario requires, and invoke the deployed intake CLI with no new selections. Confirm custody identity/hash preservation and real journal clearance, not just a mocked recovery callback.

Then exercise actual temporary projects with **fictional non-sensitive fixtures**:

1. All four profile counts and shared directories; native AGENTS without bridge; complete skill packages and discovery links; findings/status defaults and explicit opt-ins.
2. Fresh/no-op/refresh/migrate/force/dry-run behavior, schema and file/directory collisions, real skill-directory location changes, user CLAUDE preservation, tracked-private warnings, managed-only cleanup, backup/history/hash preservation, and absence of extra default ignored roots.
3. Classified intake with pending/delete/archive/retain paths, hidden/nested items, failures, provenance, and missing IR prerequisite behavior; plan archival collisions/backlinks and persistent override/revocation authority.
4. Team-status regeneration/check, legacy output migration with backups, ownership/collision handling, read-only migration checks, rollback of failed cutover, internal-only content exclusion, malformed duplicate/missing headings, stale/failed receipts, previous-output retention, sensitive warnings without value disclosure, and no service calls.
5. Finding promotion from real source prose, log/backlink/header synchronization, default/provisional/IR selection, scored and informational CVSS, quoted/nested/missing assets, suspect content warnings, and genuine I/O errors.
6. IR setup refresh preserving customizations; private/group modes; concurrent intake IDs; interrupted and empty-incoming recovery; digest mismatch quarantine; dry-run honesty; review queue consistency; validator schema agreement.
7. Real authenticated dashboard requests/browser interaction for inert hostile strings, CSRF, traversal/symlink rejection, timestamp filtering, API-error display, bounded pagination/truncation, and no unsupported executive conclusions.
8. Freshness checker Git failures and first-parent merge semantics. With the default ignored bank, assert an unavailable/skip notice—not proof of a memory update.

Regression coverage must also exercise discovery-ancestor and unrelated-package symlinks before installer mutation; source/asset ancestor symlinks before promotion; repeated failed acquisition validation without losing prior custody identity; optional findings backlinks; absolute inputs through an explicitly declared root alias without permitting descendant symlinks; and equivalent freshness results from repository subdirectories. Invalid projection field types must produce structured checker errors and an available dashboard with the invalid analytical projection excluded.

Do not add real customer/incident data, credentials, PII, or malware. Report only checks actually exercised, separating source review, documentation evidence, and runtime results. Use the README's official harness citations as starting points; direct Cursor source access and Claude watcher/account-sync limits must not be silently promoted into verified claims.
