---
name: memory-bank-context
description: Load an existing project's AGENTS.md and .memory-bank into the current model or agent context without creating, modifying, auditing, or repairing files. Use for a fast, read-only context bootstrap when a session or harness starts without project memory.
---

# Read-Only Memory Bank Context Loader

Load an existing project memory bank into the current session. This skill builds
working context for a model or agent harness; it never initializes, updates,
migrates, audits, or repairs the project itself.

## Procedure

1. Resolve `PROJECT_ROOT` as the git repository root, or the current working
   directory when there is no git repository.
2. Read `PROJECT_ROOT/AGENTS.md` first. It defines the installed profile, the
   authority files, the required `.memory-bank/*.md` files, and the response
   contract. Never invent a schema or file list.
3. Read only the explicit required cognitive-file allowlist from AGENTS.md.
   Read authority files first, then `activeContext.md` and `project-status.md`,
   then remaining required records. Independent reads at the same authority
   level may run in parallel. Do not recursively read the bank, backups,
   incoming, references/datasets/raw, sensitive, artifacts or runtime stores.
   A referenced source is not automatic permission to load its contents.
4. If a required file is missing or unreadable, record its path and continue
   with the remaining files. Do not create, populate, or repair it.
5. Load the material into the current session or ephemeral harness context.
   Authority and explicit supersession control before recency; prefer newer
   dates only among equally authoritative compatible status entries. Load
   scoped confirmations and revocations from both relevant authority files and
   activeContext. An exception persists project-wide until revoked, only for
   its recorded action/risk scope. A revocation in either record ends it; do
   not let a stale duplicate or a newer working note revive permission. Flag
   conflicting records without editing them or treating ambiguity as approval.
   Do not warn again for an unchanged, valid confirmed scope.
6. Return a concise context brief containing:
   - project purpose and current objective;
   - controlling requirements, scope, and safety constraints;
   - current state, blockers, and next steps;
   - durable decisions, active scoped overrides/revocations, and risks relevant
     to the next action;
   - missing or unreadable required files.
7. End with the exact response status line required by `AGENTS.md`. Because this
   workflow changes no project files, use its read/no-update form when memory
   was consulted; if authority could not be loaded, report that truthfully.

## Read-Only Boundary

- Do not create, modify, move, rename, or delete any project file.
- Do not initialize a missing bank, migrate backups, audit freshness, repair
  contradictions, or update progress records.
- Do not scan `git log`, `git status`, README files, source trees, build or test
  configuration, or external sources merely to validate the bank.
- Do not run tests, linters, `check-memory-freshness`, `check-profile-drift`, or
  other verification commands.
- Do not invoke the full `memory-bank-maintenance` skill unless the user separately asks to
  initialize, migrate, audit, repair, or update project memory.
- Do not copy secrets, credentials, personal data, restricted payloads, or raw
  evidence into the response or tool-native persistent memory. State only the
  affected file and data class when such material is encountered.
- The ignored bank is local to this checkout, not automatically shared with
  clones, worktrees or cloud sessions; transfers require owner authorization.
- Tool-native memory may be local or service-shared. It is optional assistance, never the
  project store of record and never a substitute for `.memory-bank/`.

## Failure Mode

If `AGENTS.md` is absent or unreadable, stop the context load and report that the
authoritative profile and required file list cannot be determined. Do not guess
from directory contents. No project change is permitted.
