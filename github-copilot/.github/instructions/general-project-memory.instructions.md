---
applyTo: "**"
---

# General Project Memory Bank Workflow

Apply these instructions for all general project tasks in this repository.

## 1) Bootstrap and Load (start of task)

- Resolve `PROJECT_ROOT` as git root (`.git`), else current working directory.
- Ensure `PROJECT_ROOT/memory-bank` exists.
- Ensure these files exist (create if missing):
  - `memory-bank/projectBrief.md`
  - `memory-bank/requirements.md`
  - `memory-bank/decisions.md`
  - `memory-bank/activeContext.md`
  - `memory-bank/progress.md`
  - `memory-bank/risks.md`
  - `memory-bank/handoff.md`
- Read all required memory files before planning or execution.

## 2) Project Gates

- Treat `projectBrief.md` and `requirements.md` as source of truth for goals, constraints, non-goals, and acceptance criteria.
- If requirements, ownership, privacy, or production-impacting behavior are unclear, stop and ask before irreversible or high-impact actions.
- Do not store plaintext secrets, credentials, private keys, or sensitive customer/user data in memory files.

## 3) Operating Rules During Work

- Keep current objective, approach, blockers, and next steps in `activeContext.md`.
- Keep execution status in `progress.md`.
- Track durable tradeoffs and decisions in `decisions.md`.
- Track meaningful risks, impacts, owners, and mitigations in `risks.md`.
- Keep `handoff.md` current enough that another contributor can resume the work.

## 4) Required Updates Before Final Response

Update all of the following:
- `activeContext.md`
- `progress.md`
- `handoff.md`
- `decisions.md` (if no new decision, write `No new decisions`)
- `risks.md` (if no new risk, write `No new risks`)

Also update `projectBrief.md` and `requirements.md` if new durable context was learned.

## 5) Output Contract

Final responses must include:
- `Memory bank: consulted and updated`
