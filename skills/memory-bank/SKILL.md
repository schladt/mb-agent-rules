---
name: memory-bank
description: Initialize, migrate, audit, or repair a project-local memory bank (the memory-bank directory described in AGENTS.md). Use when the memory bank is missing, out of date, was just backed up to .old/, or when asked to re-initialize, migrate, audit, or verify project memory.
---

# Memory Bank Operations

Procedures for setting up and maintaining the project-local memory bank. The
always-on rules — what to read, when to update, the response status line — live
in `AGENTS.md` at the project root. This skill covers the occasional, multi-step
operations that do not belong in always-on context.

Read `AGENTS.md` first. It is the authority for which profile is installed and
which `memory-bank/*.md` files that profile requires. Never invent a file list.

## Initialize an existing project

Use when `AGENTS.md` exists but the memory bank is empty, partial, or has never
been filled in.

1. Resolve `PROJECT_ROOT` as the git repo root, or the working directory if
   there is no git root.
2. Read `AGENTS.md` and list the required `memory-bank/*.md` files for the
   installed profile. Create any that are missing.
3. Gather real evidence before writing: `git log`, `git status`, `README.md`,
   `CONTRIBUTING.md`, build and test configuration, and the top-level source
   layout. Do not describe intent you cannot verify.
4. Fill the authority files first (the profile's brief plus its scope,
   requirements, or methodology file), then the working files.
5. Record the initialization itself as the first dated entry in the progress
   file, including any verification commands you ran and their result.
6. Stop and ask the user when goals, scope, authorization, or ownership cannot
   be determined from the repository. Do not guess in an authority file.

## Migrate a backed-up memory bank

Use after `init-agent-rules` prints an ACTION REQUIRED notice, which means the
old bank was moved to `.old/memory-bank-<timestamp>/` and fresh scaffolding was
created.

1. Read every file in the backup directory and every file in the new
   `memory-bank/`.
2. Map old content onto the new schema by meaning, not by filename. Content that
   has no new home goes into the closest equivalent file under a clearly labeled
   heading rather than being dropped.
3. Preserve history. Append; never delete. Mark anything no longer true as
   superseded, with the date and a one-line reason.
4. Carry timestamps and status labels across unchanged.
5. Summarize the mapping (old file to new file) in the progress file so the
   migration is auditable.
6. Leave the backup directory in place. Deleting it is the user's decision.

## Audit and repair

Use when the memory bank may have fallen out of sync with the repository.

1. Verify structure: every required file for the installed profile exists and is
   non-empty.
2. Verify freshness: compare the newest dated entry in the progress file against
   recent commit history. Flag project changes that were never recorded.
3. Verify accuracy: check the authority files against the current repository.
   Statements that are no longer true get marked superseded, not deleted.
4. Verify hygiene: no secrets, credentials, private keys, payloads, or personal
   or restricted data in the memory files. Replace any found with a reference to
   a secure location and tell the user what was removed. A separate store the
   owner designated for sensitive data is out of scope for this audit — check
   only that the memory files reference it rather than reproduce its contents.
5. Verify consistency: resolve entries that contradict each other, keeping the
   newer one and marking the older superseded.
6. Report findings and the repairs made. Record the audit in the progress file.

## Verification

If `check-memory-freshness` is available on the path or in the repository, run
it to confirm that changed project files are accompanied by memory bank updates.
It is advisory tooling; it does not replace reading the files.

## Constraints

- Markdown only. No tool-specific syntax in any memory file.
- Append-only. Historical notes are never deleted, only marked superseded.
- Never write secrets, credentials, payloads, or restricted data to a memory
  file. They may go to a store the project owner explicitly designated for
  sensitive data; warn in your response when they do, and keep the memory file
  reference-only.
- The memory bank is the store of record. Do not rely on a tool's own automatic
  memory to carry project facts; it is machine-local and not shared.
- Finish with the response status line required by `AGENTS.md`.
