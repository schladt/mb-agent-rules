---
name: memory-bank-findings
description: Author and promote report-facing findings from an explicit working-log entry and supplied prose, synchronize status/backlinks, list eligible reports and run warning-only convention preflight. Supports pentest and incident-response semantics without a report engine.
---

# Tool-neutral findings workflow

Read project `AGENTS.md`, its authority/data-policy files and the relevant
`.memory-bank/findings.md` entry. Do not recursively load incoming, references,
sensitive, artifacts, backups or runtime stores. Findings and assets are tracked
report sources, not automatically approved external publications. Use the installed
profile from `.memory-bank/layout.json`; absent metadata, explicitly supply
`--profile pentest` or `--profile incident-response`. General projects require the
installer's explicit findings opt-in (`layout.json` findings true); never impose a
security schema on ordinary project records. Do not use a report-builder skill or
render/export integration as part of this workflow.

## Commands

Use Python 3.10+ and the installed package path (commonly `.agents/skills`):

```sh
python3 .agents/skills/memory-bank-findings/scripts/findings.py --root . lint
python3 .agents/skills/memory-bank-findings/scripts/findings.py --root . promote --title 'Descriptive title' --workstream application --slug descriptive-title --source .memory-bank/planning/draft/finding.md
python3 .agents/skills/memory-bank-findings/scripts/findings.py --root . sync
python3 .agents/skills/memory-bank-findings/scripts/findings.py --root . list
```

`--root PATH` and optional `--profile pentest|incident-response|general-project`
precede the subcommand. Root defaults to the Git root, otherwise cwd. Paths are
relative to project root unless explicitly absolute; report selections must stay
inside `findings/`. `lint [PATH]` and `sync [PATH]` accept a report file or subtree.
Template folders are excluded and cannot be selected directly. `list` prints
working-log status, title and canonical path separated by tabs; it performs no
rendering or publication. Actual generated deliverables belong in `deliverables/`.

## Authoring and promotion

1. Identify the existing working-log entry by descriptive title under `## Entries`:

   ```markdown
   ### Descriptive title
   - Status: Validated
   - Evidence references: reviewed evidence summary
   - Report path:
   - Status history: retain dated state changes here
   ```

   Exact pentest states are Hypothesis, Validated, Informational, False Positive.
   IR states are Suspected, Confirmed, Ruled Out; legacy `### F-001: Title` entry
   headings remain readable without carrying the finding ID into the report.
   `- Report path:` is a root-relative plain path (a Markdown link is also read).
   Duplicate titles/status/backlink fields are ambiguous input errors.
2. Explicitly choose and complete the installed `findings/_TEMPLATE/finding.md`.
   Never select a template automatically or fabricate facts, scores or impact.
   Pentest keeps canonical CVSSv3.1 sections and the exact
   `### Steps to reproduce / observed behavior` heading. Scored vulnerabilities
   need the score/severity, base vector and all eight metric values. Informational
   uses 0.0 (Informational), Vector: N/A, and **no metric grid**. Impact and
   Remediation remain meaningful, including supported assurance observations.
   IR keeps fact/inference/alternatives, confidence, ART custody references and
   investigation status. Incident conclusions have no CVSS. Only explicitly
   labeled `**Finding type:** Vulnerability` adopts CVSS, while retaining IR
   confidence and evidence semantics; deliberately add that section, do not guess.
3. Supply completed Markdown with exactly `# Descriptive title` via required
   `--source PATH`. Source is an explicitly chosen project file, not a template or
   symlink. `promote` consumes the draft prose file after writing the canonical
   report and backlink/index; it does not leave a second authoring copy. It can
   also register an already canonical file by using that file as `--source`.
   Existing different canonical sources/assets are never overwritten.
   First promotion appends a UTC promotion receipt to the entry without replacing
   existing status history; registering an already linked source adds no duplicate receipt.
4. Default promotion and `list` eligibility: pentest **Validated/Informational**;
   IR **Confirmed**. Pentest/general Hypothesis requires `--include-hypothesis`;
   IR Suspected requires `--include-suspected`, on both promotion and selection.
   Each receives an explicit Provisional header without changing its domain state.
   Neither flag selects false positives or ruled-out conclusions.
   Promotion takes status from the working log, not the draft header. Approval of
   promotion/selection is not authorization for external sharing.
5. Canonical path is `findings/<workstream>/<slug>/finding.md`. Slugs use Unicode
   alphanumeric words separated by hyphens. One primary home per finding;
   cross-reference by descriptive title. Place reviewed draft attachments under
   its sibling `assets/` directory. Promotion copies only linked assets from
   that directory, including nested filenames, and rewrites links with URL-safe
   relative paths. Source attachments are retained; the prose draft is consumed.
   Other links within findings are rebased; missing/unsafe links warn and require
   author review, not a false claim that an attachment was copied. Do not link
   private stores into a report or use symlinks to evade containment. Asset
   copying never traverses or ingests an unselected private store.
6. Inspect warnings and the resulting report. Update appropriate working memory
   under the project response contract. Do not duplicate the full narrative into
   the log: retain concise supported summaries, evidence and history there.

## Status synchronization and index

After changing status in the working log, run `sync` to apply it to existing
report Status headers, add any absent backlink and regenerate only the marked
index block in `findings/README.md`. Existing false-positive/ruled-out report
sources remain synchronized but are excluded from `list`. Provisional labels are
removed when a hypothesis changes state. The command does not rewrite dated log
history or infer a new state. A conflicting backlink, duplicate report title or
invalid domain status is an input error, not permission to overwrite history.
`list` excludes stale/mismatched report headers until synchronized. The README
index shows registered sources including ineligible states, not a report manifest.

## Warning-only preflight and failures

`lint` checks canonical section presence/order, title-based identity, score/
severity/vector/metric consistency, informational exception, applicable IR
fields, log/header/backlink agreement and relative links/assets. It recognizes
inline Markdown, angle-bracket/quoted-title links, balanced parentheses, reference
definitions and HTML src/href. It checks containment after symlink resolution.
It scans report Markdown and linked report-owned text assets for obvious
credential/private-key/email/identifier indicators, reporting path, line and data
class **without echoing suspect values**. Binary files are checked for existence
and readability, not claimed to be sanitized. Heuristics do not establish
analytical correctness, complete sanitization or publication approval.

Convention warnings exit **0**; missing/unreadable command inputs, malformed
working-log identity, invalid invocation and write failures exit nonzero. Missing
linked assets are convention warnings, not missing command inputs. Raw assets may
be retained under project policy; warn-confirm and persist any applicable
exception through the project's approved override workflow. Never silently strip
content, block solely on a convention warning, or claim a secret-free footer when
an approved exception makes that assertion untrue. Report failures truthfully;
do not claim generation, synchronization or external delivery that did not occur.
