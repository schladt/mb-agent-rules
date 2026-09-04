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
| `sensitive/` | Operational inputs needed to perform project work | Owner-supplied credentials, keys, tokens, private configuration, and restricted datasets | Excluded by default |

## Profile Stores

No profile-specific stores.

## Additional Owner-Designated Stores

A completed row is explicit authorization to create and use that path for the stated purpose and data classes.

| Path | Purpose | Allowed data | Version control | Approved by |
|---|---|---|---|---|
|  |  |  | `excluded` / `permitted` / `external` |  |

## Handling Rules

- Memory files record classifications, owners, paths, hashes or fingerprints, validity, and rotation state; they do not reproduce secret values.
- `Memory-bank plaintext: synthetic-only` may be selected only with `private-lab` mode and explicit owner approval. Live production secrets remain prohibited in memory files.
- A compliant write to a declared store needs no repeated warning. Report only missing or ambiguous policy, an undeclared path or data class, version-control conflict, unsafe permissions, or another policy violation.
- New store directories use mode `0700` and newly written files use mode `0600` where the platform supports POSIX permissions.
- Directory existence alone does not designate a store. Standard and profile stores are authorized by the installed profile; additional stores are authorized only by a completed table row.

## Notes
