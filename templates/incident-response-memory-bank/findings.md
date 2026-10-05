# Findings

Analytical conclusions. Observations belong in `timeline.md`; this file is where
inference is recorded, explicitly labelled as such. Create each real entry under
`## Entries` with `### <descriptive title>`; retain legacy internal IDs when present.
Full report prose has one home in `findings/<workstream>/<slug>/finding.md`.

## Finding Template

- Finding ID:
- Title:
- Statement of fact (what was observed):
- Inference (what it means):
- Supporting artifacts (`ART-####`):
- Confidence: `Low` / `Medium` / `High` — and why it is not higher
- Alternative explanations considered:
- Affected assets:
- Status: `Suspected` / `Confirmed` / `Ruled Out`
- Recorded (UTC):
- Report path:
- Status / promotion history:

<!-- No attribution without supporting evidence. No assertions of intent, fault,
     negligence, or liability. Those belong with counsel, not in this file. -->

## Entries

Confirmed conclusions are report-eligible; Suspected conclusions require explicit
provisional selection. Ruled Out remains investigative history, not an accidental
report selection. Synchronize the report Status from this log. CVSS applies only
to actual vulnerability findings; never convert investigation certainty to severity.

## Gaps and Unanswered Questions
<!-- What is not known, and what evidence would answer it. Record what could not
     be determined and why: log retention expired, host rebuilt, no telemetry. -->
