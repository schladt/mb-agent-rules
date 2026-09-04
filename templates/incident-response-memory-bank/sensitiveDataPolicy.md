# Sensitive Data Policy

## Policy Status

- Mode: `designated-store`
- Approved by: Profile default
- Version-control policy: `excluded`
- Memory-bank plaintext: `prohibited`

Supported modes:
- `restricted` — do not write plaintext sensitive data.
- `designated-store` — write authorized data classes only to the stores below.
- `private-lab` — permit synthetic, training, tabletop, test, or deliberately disposable secrets in declared stores; production credentials and real incident data still require explicit authorization.

Repository visibility never selects a mode. Changing the mode, version-control policy, or memory-bank plaintext policy requires explicit owner direction and must remain within `scopeAuthorization.md`.

## Standard Store

| Path | Purpose | Allowed data | Version control |
|---|---|---|---|
| `sensitive/` | Operational inputs needed to conduct the response | Responder credentials, API tokens, private keys, private configuration, and restricted coordination material | Excluded by default |

## Profile Stores

| Path | Purpose | Allowed data | Version control |
|---|---|---|---|
| `artifacts/` | Preserved incident evidence under chain of custody | Forensic acquisitions, logs, exports, recovered credentials, exfiltrated data, and defanged malware samples | Excluded by default |

Operational secrets belong in `sensitive/`; acquired evidence belongs in `artifacts/`.

## Additional Owner-Designated Stores

A completed row is explicit authorization to create and use that path for the stated purpose and data classes. It does not expand response authority in `scopeAuthorization.md`.

| Path | Purpose | Allowed data | Version control | Approved by |
|---|---|---|---|---|
|  |  |  | `excluded` / `permitted` / `external` |  |

## Handling Rules

- Memory files record classifications, affected assets or identities, paths, artifact IDs, hashes or fingerprints, validity, and rotation state; they do not reproduce secret values, exfiltrated data, or malware contents.
- `Memory-bank plaintext: synthetic-only` may be selected only with `private-lab` mode and explicit owner approval. Live production credentials and real incident data remain prohibited in memory files.
- A compliant write to a declared store needs no repeated warning. Report only missing or ambiguous policy, an undeclared path or data class, an authority conflict, version-control conflict, unsafe permissions, or another policy violation.
- New store directories use mode `0700` and newly written files use mode `0600` where the platform supports POSIX permissions.
- Directory existence alone does not designate a store. Standard and profile stores are authorized by the installed profile; additional stores are authorized only by a completed table row.
- Never execute malware or attacker tooling. Store such material defanged and contained in `artifacts/`.

## Notes
