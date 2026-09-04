# Sensitive Data Policy

## Policy Status

- Mode: `designated-store`
- Approved by: Profile default
- Version-control policy: `excluded`
- Memory-bank plaintext: `prohibited`

Supported modes:
- `restricted` — do not write plaintext sensitive data.
- `designated-store` — write authorized data classes only to the stores below.
- `private-lab` — permit synthetic, training, test, or deliberately disposable secrets in declared stores; production secrets and participant data still require explicit authorization and applicable consent.

Repository visibility never selects a mode. Changing the mode, version-control policy, or memory-bank plaintext policy requires explicit owner direction.

## Standard Store

| Path | Purpose | Allowed data | Version control |
|---|---|---|---|
| `sensitive/` | Restricted inputs needed to perform research | Owner-supplied credentials, private datasets, restricted sources, and participant data covered by consent and data permissions | Excluded by default |

## Profile Stores

No profile-specific stores.

## Additional Owner-Designated Stores

A completed row is explicit authorization to create and use that path for the stated purpose and data classes. Participant data also requires consent and data permissions covering the destination.

| Path | Purpose | Allowed data | Version control | Approved by |
|---|---|---|---|---|
|  |  |  | `excluded` / `permitted` / `external` |  |

## Handling Rules

- Memory files record classifications, owners, paths, hashes or fingerprints, consent or permission status, and retention state; they do not reproduce secret or participant-data values.
- `Memory-bank plaintext: synthetic-only` may be selected only with `private-lab` mode and explicit owner approval. Live production secrets and real participant data remain prohibited in memory files.
- A compliant write to a declared store needs no repeated warning. Report only missing or ambiguous policy, an undeclared path or data class, missing consent or permission, version-control conflict, unsafe permissions, or another policy violation.
- New store directories use mode `0700` and newly written files use mode `0600` where the platform supports POSIX permissions.
- Directory existence alone does not designate a store. Standard stores are authorized by the installed profile; additional stores are authorized only by a completed table row.

## Notes
