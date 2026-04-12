# Cursor Rule: Local Academic Research Memory Bank (Global User Rule)

Paste the `BEGIN RULE` to `END RULE` block into Cursor `Settings -> Rules` as a User Rule.

## BEGIN RULE

Use a project-local memory bank for every academic research task.

Non-negotiable workflow:
1. Before each task: read memory bank.
2. During each task: keep sources, methodology, and research state synchronized.
3. After each task: update memory bank before final response.

### 1) Bootstrap and Load (required at task start)

- Resolve `PROJECT_ROOT` as the current repo root (`.git` directory). If no git repo is found, use current working directory.
- Use `MEMORY_DIR = PROJECT_ROOT/memory-bank`.
- If `MEMORY_DIR` does not exist, create it.
- Ensure these files exist (create if missing):
  - `memory-bank/researchBrief.md`
  - `memory-bank/researchQuestions.md`
  - `memory-bank/literatureNotes.md`
  - `memory-bank/methodology.md`
  - `memory-bank/sourcesIndex.md`
  - `memory-bank/activeContext.md`
  - `memory-bank/progress.md`
  - `memory-bank/openQuestions.md`
- If a required file is newly created, initialize it with the templates in this rule.
- Read all required memory files before planning or executing any task.

### 2) Research Integrity Gates

- Treat `researchBrief.md`, `researchQuestions.md`, and `methodology.md` as source of truth for research direction, scope, and analysis plan.
- If ethics, consent, data permissions, citation status, or methodology constraints are unclear, stop and ask before collecting data, analyzing restricted material, or asserting research conclusions.
- Do not fabricate citations, quotes, results, datasets, or methods.
- Keep sensitive participant data, private datasets, credentials, and restricted full-text materials out of memory files. Store references to secure locations instead.

### 3) Academic Recording Rules (during task)

- Track current research focus, hypotheses, blockers, and next steps in `activeContext.md`.
- Track completed and pending work in `progress.md`.
- Track literature themes, disagreements, gaps, and claims to verify in `literatureNotes.md`.
- Track methodology updates, analysis plan changes, validation checks, and limitations in `methodology.md`.
- Track citation metadata and artifact references in `sourcesIndex.md`.
- Track unresolved questions in `openQuestions.md`.

### 4) Completion Updates (required before final answer)

Update at least these files after completing each task:
- `activeContext.md`
- `progress.md`
- `sourcesIndex.md` (if no source was reviewed, explicitly state "No new sources reviewed")
- `openQuestions.md` (if no new question, explicitly state "No new open questions")

Also update `researchBrief.md`, `researchQuestions.md`, `literatureNotes.md`, or `methodology.md` when durable research understanding changes.

### 5) Update Style

- Markdown only.
- Use concise sections, timestamps, and clear status labels (`Planned`, `In Progress`, `Done`, `Blocked`, `Needs Verification`).
- Never delete historical notes; append updates and mark outdated items as superseded.
- Keep claims source-linked and label uncertainty clearly.

### 6) Required File Templates (for missing files)

When creating required files, use these minimum templates.

`researchBrief.md`
- Project title
- Research area
- Objective
- Motivation
- Expected contribution
- Deliverables
- Constraints
- Ethics / data permissions

`researchQuestions.md`
- Primary question
- Secondary questions
- Hypotheses
- Key constructs / variables
- Inclusion criteria
- Exclusion criteria
- Success criteria

`literatureNotes.md`
- Themes
- Key papers
- Disagreements / gaps
- Claims to verify

`methodology.md`
- Study design
- Data sources
- Sampling / selection plan
- Collection procedure
- Analysis plan
- Validation / robustness checks
- Reproducibility notes
- Known limitations

`sourcesIndex.md`
- Citation key
- Full citation
- DOI / URL
- Source type
- Status (`To Read` / `Read` / `Excluded` / `Needs Verification`)
- Relevance
- Notes
- Local artifact path

`activeContext.md`
- Current research focus
- Current claim / hypothesis
- Immediate next steps (1-3)
- Blockers / questions

`progress.md`
- Session/date
- Completed
- In progress
- Pending
- Validation/checks run

`openQuestions.md`
- Question
- Why it matters
- Current best answer
- Evidence/source references
- Owner
- Status (`Open` / `Investigating` / `Resolved` / `Deferred`)

### 7) Response Contract

In final task responses, include a short line:
- `Memory bank: consulted and updated`
- If skipped, explain exactly why.

## END RULE
