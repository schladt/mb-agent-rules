<!-- TEMPLATE: explicitly author an incident conclusion; never promote this scaffold.
Retain investigation states Suspected / Confirmed / Ruled Out and evidence custody IDs.
Only Confirmed conclusions are selected by default. Never convert confidence into status.
An incident conclusion has NO CVSS. For an explicitly assessed vulnerability, change
Finding type to Vulnerability and deliberately add the canonical CVSSv3.1 Score and
Severity section BEFORE Affected Assets, including score, vector and all eight metric
values. Informational vulnerability observations use 0.0 / N/A without a metric grid.
Do not infer vulnerability scoring from incident severity or from the profile.
Review text/assets for sensitive material under project policy; remove instructions
only after supplying real prose. No unsupported attribution, intent or liability.
-->
# <Descriptive Incident Finding Title>

**Status:** `Suspected`
**Finding type:** Incident conclusion
**Workstream:** <Investigation workstream>
**Date:** YYYY-MM-DD
**Confidence:** <Low/Medium/High — basis and reason confidence is not higher>

## Affected Assets

**Origin:** <Evidence source or investigation workstream>

<Report-appropriate affected-system summary.>

## Description

<Concise analytical conclusion and scope; full narrative lives here once promoted.>

### Statement of fact

<What was actually observed, with supporting ART-#### custody references.>

### Inference

<What the observations support, explicitly separated from facts.>

### Alternative explanations considered

<Viable alternatives, disconfirming evidence and remaining uncertainty.>

### Affected assets

<Sanitized affected-asset list; distinguish confirmed scope from possible scope.>

### Steps to reproduce / observed behavior

1. <Observed sequence and evidence references; no invented reproduction.>
2. <Review limitations and missing telemetry.>

## Impact

**Technical.** <Observed technical effect versus possible effect.>

**Business.** <Supported operational consequence; identify uncertainty.>

## Remediation

1. <Evidence-preserving containment, corrective action or next investigative step, as applicable.>

## References

- <Relevant guidance and title-based cross-references.>

*Evidence source: <ART-#### identifiers, report-safe relative supporting assets, review provenance and limitations. Do not claim all raw evidence is safe for publication.>*
