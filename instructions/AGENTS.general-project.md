# General Project Memory Bank Instructions

Use a project-local memory bank for general project work.

**Core rule: if you change any file in the project, you MUST update the memory bank in the same response. The only exception is when you change no files. See the Response Contract.**

## Required Workflow

### 1) Bootstrap and Load

- Resolve `PROJECT_ROOT` as the current git repo root. If no git root exists, use current working directory.
- Ensure `PROJECT_ROOT/memory-bank` exists.
- Ensure these files exist (create if missing):
  - `memory-bank/projectBrief.md`
  - `memory-bank/requirements.md`
  - `memory-bank/sensitiveDataPolicy.md`
  - `memory-bank/decisions.md`
  - `memory-bank/activeContext.md`
  - `memory-bank/progress.md`
  - `memory-bank/risks.md`
  - `memory-bank/handoff.md`
- Read all required memory files before planning or execution.

### 2) Authority and Safety Gates

- Treat `projectBrief.md`, `requirements.md`, and `sensitiveDataPolicy.md` as authority for goals, constraints, acceptance criteria, and sensitive-data handling.
- If requirements, ownership, privacy, or production-impacting behavior are unclear, stop and ask before irreversible or high-impact actions.
- Read `sensitiveDataPolicy.md` before writing credentials, private keys, tokens, restricted datasets, or other sensitive material. It defines the active mode, authorized data classes, storage paths, and version-control policy.
- Selecting this profile designates `sensitive/` as the standard store for authorized operational secrets and restricted inputs. Additional paths are authorized only when the owner records them in `sensitiveDataPolicy.md`; directory existence alone is not authorization.
- Memory files reference sensitive material rather than reproducing it. Synthetic values may appear there only when the policy explicitly sets `private-lab` mode and `Memory-bank plaintext: synthetic-only`; live production secrets remain prohibited.
- A compliant write to a declared store needs no repeated warning. Report and stop for missing or ambiguous policy, an undeclared path or data class, a version-control conflict, unsafe permissions, or another policy violation. Repository visibility never implies `private-lab`.
- New sensitive-store directories use mode `0700` and newly written files use mode `0600` where POSIX permissions are supported.
- The project `memory-bank` directory is the store of record. Some tools keep their own automatic memory outside the project. That memory is machine-local, tool-specific, and not shared with collaborators: never treat it as authoritative and never let it substitute for a memory bank update. Durable project facts belong in the memory bank.

### 3) Recording Rules

- Track current objective, approach, blockers, and next steps in `activeContext.md`.
- Track completed and pending work in `progress.md`.
- Track durable tradeoffs and decisions in `decisions.md`.
- Track meaningful risks, impacts, owners, and mitigations in `risks.md`.
- Keep `handoff.md` current enough that another contributor can resume the work.

### 4) Completion Updates

Before completing each task, update at least these files:
- `activeContext.md`
- `progress.md`
- `handoff.md`
- `decisions.md` (write `No new decisions` if none)
- `risks.md` (write `No new risks` if none)

Also update `projectBrief.md` or `requirements.md` if durable understanding changed.

### 5) Update Style

- Markdown only.
- Use concise entries with timestamps and status labels: `Planned`, `In Progress`, `Done`, `Blocked`.
- Never delete historical notes. Append and mark superseded content.

### 6) Response Contract

Two rules, both mandatory.

**Update rule (non-negotiable).** If you created, modified, or deleted ANY file in the project during this response — except files inside `memory-bank/` itself — you MUST update the memory bank in the SAME response. The only case where no update is required is when you changed zero project files. "Small", "trivial", or "obvious" changes are NOT exempt. When an update is required, update at minimum `activeContext.md` and `progress.md`, plus any other files named in Recording Rules and Completion Updates that apply.

**Status line.** End every response with exactly one of:

- `Memory bank: updated — <comma-separated list of files changed>`
  Required whenever you changed any project file (see the update rule).
- `Memory bank: read, no update needed`
  Allowed ONLY when you changed zero project files.
- `Memory bank: not consulted`
  Only for requests completely unrelated to this project.

Self-check before sending: if you changed any file outside `memory-bank/` and your status line is not `updated`, the contract is violated — stop and update the memory bank first. Never omit the status line. Never combine it with other output.
