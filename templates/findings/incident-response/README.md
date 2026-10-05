# Incident Findings

Author each incident conclusion once at
`findings/<workstream>/<descriptive-slug>/finding.md`, with optional relative
`assets/`. Explicitly start from [_TEMPLATE/finding.md](_TEMPLATE/finding.md);
commands do not silently select a template or invent analytical prose.
Cross-cutting findings have one primary home, linked by descriptive title.
Report titles/body do not carry finding IDs; preserve ART-#### evidence custody
identifiers and their reviewed provenance.

## Investigation semantics

`.memory-bank/findings.md` is the status truth: **Suspected / Confirmed /
Ruled Out**. Its lightweight entries retain factual/inferential summaries,
confidence and alternatives, evidence references, status history and report-path
backlinks; promoted full report prose lives once in the report source.

Only **Confirmed** is report-eligible by default. Explicitly promote and select
**Suspected** with `--include-suspected`; it remains visibly Provisional.
Suspected and Ruled Out are never mapped to pentest states;
`--include-hypothesis` is not an IR flag and Ruled Out is never selected.
Existing report sources can be retained and synchronized after a conclusion is
ruled out without rewriting investigative history. Confidence is not status.
Keep facts, inferences, alternatives, review limitations and confidence explicit;
preservation/intake alone is not analytical confirmation.

Incident conclusions do **not** use CVSS. An explicitly assessed vulnerability
must say `**Finding type:** Vulnerability` and deliberately adopt the canonical
CVSSv3.1 section before Affected Assets. Scored vulnerabilities require a
score/severity, vector and eight-metric grid; informational observations use
0.0 / N/A without a metric grid. Do not treat incident severity as vulnerability
severity or discard incident confidence/custody when scoring a vulnerability.

## Report safety

Findings and assets are Git-eligible, not automatically cleared for delivery.
Use reviewed relative links resolving within `findings/`; do not expose private
stores through traversal or symlinks. Raw assets remain subject to project data
policy and applicable warn/confirmation exceptions. Never echo suspected secret
or PII values into warnings or memory. Permission to store is not permission to
publish. The warning-only linter checks conventions, not analytical truth or
complete sanitization; actual I/O failures are nonzero errors.

No report engine, renderer, export or upload is integrated. Independently produced
actual deliverables belong in `deliverables/`.

## Report-source index

The command updates only this block with registered existing sources and current
working-log states. Use `list` for the eligible subset, and `sync` after state changes.

<!-- findings:index:start -->
| Finding | Status |
|---|---|
<!-- findings:index:end -->
