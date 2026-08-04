# Evidence Index

Chain of custody. Every artifact is hashed and timestamped on intake, before it
is copied into `artifacts/`. See the Artifact Intake procedure in `AGENTS.md`.

Never record a digest that was not computed. Use `PENDING HASH` if hashing was
not possible, and say so.

## Intake Commands

```bash
shasum -a 256 <file>          # macOS
sha256sum <file>              # Linux
date -u +%Y-%m-%dT%H:%M:%SZ   # ingest timestamp
```

Stored as: `artifacts/<ingest-utc>__<first-12-of-hash>__<original-name>`

## Artifact Template

- Artifact ID: `ART-####`
- Original name:
- Source path / system of origin:
- Provided by:
- Acquisition method: <!-- live acquisition, export, disk image, screenshot, analyst-supplied text, vendor report -->
- SHA-256:
- Copy verified: `Yes` / `No` — re-hash of the stored copy matched the source digest
- Size:
- Ingested (UTC):
- Stored path:
- Related timeline entries:
- Relevance:
- Handling notes: <!-- contains PII / credentials / malware sample / privileged material -->

## Entries

## Custody Transfers
<!-- Any movement of an artifact outside this project: to counsel, law
     enforcement, a vendor, or an insurer. Record who, when (UTC), what, and how
     integrity was verified on transfer. -->

| Artifact ID | Transferred to | Date (UTC) | Method | Hash verified | Notes |
|---|---|---|---|---|---|
|  |  |  |  |  |  |
