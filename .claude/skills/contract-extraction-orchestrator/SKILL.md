---
name: contract-extraction-orchestrator
description: Orchestrates the contract field-extraction build — spawns contract-extraction-builder, has contract-extraction-grader verify and grade each round, feeds feedback back, and terminates within a bounded number of rounds. Use when asked to build or rebuild the contract field-extraction feature.
---

# Contract extraction build orchestrator

The main session orchestrates. It **never writes feature code itself** and it **never
grades** — it delegates via the Agent tool and enforces the loop rules below. Mirrors
`profile-build-orchestrator`, with a non-regression gate added.

## Roles & models

- **Orchestrator (you)** — the main session: sequencing, loop control, final report.
- **Builder** — `contract-extraction-builder`: implements/revises. Runs on **Opus**
  (set in its frontmatter — never pass a `model` override in the Agent call).
- **Grader** — `contract-extraction-grader`: read-only; returns `SCORE`, `VERDICT`
  (PASS/REVISE), and a `FEEDBACK` list. Runs on **Opus** (frontmatter — no override).

## Build order (phases, not one big drop)

The builder works in this order so each phase is independently verifiable. The grader
runs after every phase, not only at the end.

1. **Phase 1 — schema + JSON contract.** `catalogue.py` (the 10 fields: 5 fixed, 5
   optional), the 10-key assembler, normalizers, and their unit tests. No API, no DB
   yet.
2. **Phase 2 — DB.** SQLModel table + Alembic revision, `store.py`, round-trip tests,
   `alembic upgrade head` verified against the Docker DB.
3. **Phase 3 — extraction, outcome classification + API.** `extractor.py`,
   `grounding.py`, `verification.py`, `service.py`, the route including
   `PATCH /{id}/verify`, registration in `api/main.py`, API tests, client regeneration.
   The failure rule (any blank **requested** field → `needs_verification`) is graded
   here, including the unselected-optional case that must stay `complete`.
4. **Phase 4 — frontend.** Route, combobox, doc-left/JSON-right result, the
   non-dismissible failure banner, the verification view, table view with status
   filter, middleware and nav entries.

A phase that fails its grade is revised before the next phase starts.

## Autonomy & guardrails (no babysitting)

The loop runs hands-off; the user is not watching.

- Anything read-only, or executed/written **inside the project folder** or session
  scratchpad and reversible via git, is acceptable — decide and continue, never stop to
  ask mid-loop.
- Forbidden at every level: `sudo`, `rm -rf`, mutating `git` commands
  (commit/push/reset/checkout/clean), force flags, remote-script execution
  (`curl | sh`), destructive docker/db operations (dropping volumes, `docker compose
  down -v`, dropping existing tables), killing processes the agent didn't start,
  writing outside the project folder, editing `.env*` secrets.
- `alembic upgrade head` and `docker compose up -d db` against the local dev DB are
  allowed. Downgrades and data-destructive SQL are not.
- Editing any path the `contract-field-extraction` skill marks read-only is forbidden;
  an agent that believes it needs to reports **BLOCKED** instead.
- Nothing is committed: the loop ends with changes in the working tree for review.

## Loop

```
for phase in 1..4:
    round = 1
    spawn contract-extraction-builder  ->  "implement phase N per the skill"
    repeat:
        spawn contract-extraction-grader (fresh each round — no bias from prior rounds)
        if VERDICT == PASS                    -> next phase
        if round == MAX_ROUNDS (3)            -> stop: MAX ROUNDS REACHED
        if score <= previous round's score    -> stop: NO PROGRESS
        SendMessage FEEDBACK verbatim to the same builder agent (it keeps its context)
        round += 1
```

## Hard termination rules (no infinite loops)

1. **MAX_ROUNDS = 3** grade→revise cycles **per phase**. Never extend, even if "one
   more round would fix it". Track the round number explicitly each cycle.
2. **No-progress guard:** if a round's score is not strictly higher than the previous
   round's, stop immediately.
3. **Regression stop:** if the grader reports the existing `/document-extractions`
   pipeline changed in behaviour or its tests fail, stop the loop immediately and
   surface it — that outranks any score.
4. Builder and grader never spawn further agents and never invoke this skill. A
   subagent reporting BLOCKED stops the loop; surface the question to the user rather
   than retrying.

## Final report to the user

State per phase: rounds used, final score, verdict, and what remains. Name explicitly:
files added, the allowed shared files touched, the migration revision id, test results
(with real output — never claim a pass you did not see), and anything deferred.
