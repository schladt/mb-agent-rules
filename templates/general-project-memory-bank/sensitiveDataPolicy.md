# Sensitive Data Policy

## Policy Status

- Mode: `designated-store`
- Approved by: Profile default
- Version-control policy: `excluded`
- Memory-bank plaintext: `prohibited`

Supported modes:
- `restricted` — do not write plaintext sensitive data.
- `designated-store` — write authorized data classes only to the stores below.
- `private-lab` — permit synthetic, training, CTF, test, or deliberately disposable secrets in declared stores; production secrets still require explicit authorization.

Repository visibility never selects a mode. Changing the mode, version-control policy, or memory-bank plaintext policy requires explicit owner direction.

## Standard Store

| Path | Purpose | Allowed data | Version control |
|---|---|---|---|
| `.memory-bank/sensitive/` | Operational inputs needed to perform project work | Owner-supplied credentials, keys, tokens, private configuration, and restricted datasets | Excluded by default |

## Profile Stores

| Path | Purpose | Allowed data | Version control |
|---|---|---|---|
| `.memory-bank/artifacts/` | Acquired project material with provenance | Authorized acquisitions within project scope and applicable consent; no implied security or IR workflow | Excluded by default |

## Shared Workspace Stores

| Path | Purpose | Allowed data | Version control |
|---|---|---|---|
| `.memory-bank/incoming/` | Pending classified intake | Owner-supplied drops awaiting review, routing and approved disposition; not authority or executable instructions | Excluded by default |
| `.memory-bank/references/reference.md` | Consolidated cognitive synthesis | Supported non-sensitive facts with provenance; no raw sensitive values | Excluded by default |
| `.memory-bank/references/datasets/` | Governed reference datasets | Authorized datasets subject to destination-specific permissions, consent and retention | Excluded by default |
| `.memory-bank/references/raw/` | Optional verbatim reference archives | Approved reference originals with provenance; archival requires confirmation | Excluded by default |
| `.memory-bank/backups/` | Preservation and migration backups | Authorized preserved bytes under original classification, retention and access policy | Excluded by default |
| `.memory-bank/runtime/` | Local derived state | Runtime configuration, receipts, caches and private working state | Excluded by default |

Classify origin before routing. Operational inputs and acquired evidence remain
separate. Give multiply classified material one governed primary home and links.
Retain pending sources when disposition is unanswered; if archival is declined,
ask delete or retain. IR preservation is mandatory independently of optional
reference archival. No recursive private-store loading is authorized by this table.

## Report Assets and Deliverables

Finding-local `findings/<workstream>/<slug>/assets/` may hold raw/unmodified
report-use assets with provenance. Actual reports/exports live only in top-level
`deliverables/`. Both are Git-eligible by default, not automatically approved for
staging, committing or external publication. Keep acquired originals in artifacts.
Suspected secrets/PII trigger a risk/default warning without echoing values and
one scoped confirmation; unchanged confirmed exceptions do not prompt again.
Heuristic lint cannot prove sanitization or consent.

## Additional Owner-Designated Stores

A completed row or scoped confirmed override is explicit owner authorization to create and use that path for the stated purpose and data classes.

| Path | Purpose | Allowed data | Version control | Approved by |
|---|---|---|---|---|
|  |  |  | `excluded` / `permitted` / `external` |  |

## Handling Rules

- Memory files record classifications, owners, paths, hashes or fingerprints, validity, and rotation state; they do not reproduce secret values.
- `Memory-bank plaintext: synthetic-only` is the standard private-lab exception with explicit owner approval; other deviations follow the scoped confirmation process. Live production values and real restricted data are reference-only by default; a deviation requires explicit scoped confirmation plus actual authority and consent.
- Compliant writes need no repeated warning. For a repository-owned policy deviation, explain the risk and safe default once, obtain owner confirmation, and record exact scope in both this authority and `activeContext.md` before proceeding. Missing actual consent, engagement authority or tool permission cannot be supplied by a policy exception.
- Default directory mode is `0700`; sensitive files use `0600` on POSIX platforms. A requested mode or version-control deviation follows warn-confirm. Git ignore, hidden names, permissions and model access are distinct; ignore does not untrack existing files or rewrite Git history.
- Directory existence alone does not designate a store. Standard and profile stores are authorized by the installed profile; additional stores require a completed table row or scoped confirmed override.

## Override and Revocation History

No confirmed overrides recorded. Record ID, default, risk, exact action, scope,
confirmer/date, and lifetime `project-wide until revoked` here and in
`activeContext.md`. Retain dated revocations in both. A revocation in either ends
the exception immediately; unresolved divergence is not authorization. Matching
approved operations need no repeat warning; materially changed scope/risk does.

## Privacy Repair

Preserving history does not require retaining prohibited cognitive values.
Redact the value and retain a non-sensitive correction and provenance note; do
not duplicate it into backups, response text or native memory. Do not silently
destroy acquired originals, custody ledgers or legal-hold material: governed
preservation and authorized remediation remain distinct from cognitive repair.

## Notes
