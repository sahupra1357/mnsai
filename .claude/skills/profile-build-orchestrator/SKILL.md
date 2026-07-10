---
name: profile-build-orchestrator
description: Orchestrates the profile homepage build — spawns the profile-page-builder subagent, has profile-page-grader verify and grade the result, feeds improvement suggestions back to the builder, and terminates within a bounded number of rounds. Use when asked to build/rebuild the profile page.
---

# Profile Build Orchestrator

The main session acts as orchestrator. It **never writes page code itself** and it
**never grades** — it delegates via the Agent tool and enforces the loop rules below.

## Roles & models

- **Orchestrator (you)** — the main session on **Fable 5**: sequencing, loop control,
  final report to the user. If the session is not on Fable 5, tell the user to switch
  via `/model` before starting; do not silently run on a lesser model.
- **Builder** — `profile-page-builder` agent: implements/revises the page. Runs on
  **Opus** (set in its frontmatter — never pass a `model` override in the Agent call).
- **Grader** — `profile-page-grader` agent: read-only; returns `SCORE`, `VERDICT`
  (PASS/REVISE), and a `FEEDBACK` list. Runs on **Opus** (frontmatter — no override).

## Autonomy & guardrails (no babysitting)

The whole loop runs hands-off; the user is not watching. Rules for you and (already
embedded in their definitions) for both subagents:

- Anything read-only, or executed/written **inside the project folder** or session
  scratchpad and reversible via git, is acceptable — decide and continue, never stop
  to ask the user mid-loop.
- Forbidden at every level: `sudo`, `rm -rf`, mutating `git` commands
  (commit/push/reset/checkout/clean), force flags, remote-script execution
  (`curl | sh`), destructive docker/db operations, killing processes the agent didn't
  start, or writing anything outside the project folder.
- A subagent that can't proceed within these rules reports BLOCKED; you stop the loop
  and surface it — nobody asks the user for permission mid-round.
- Nothing gets committed: the loop ends with changes in the working tree for the user
  to review.

## Loop

```
round = 1
spawn profile-page-builder  →  "initial build per skill + docs/profile-draft.md"
repeat:
    spawn profile-page-grader (fresh each round — no bias from prior rounds)
    if VERDICT == PASS                         → stop: SUCCESS
    if round == MAX_ROUNDS (3)                 → stop: MAX ROUNDS REACHED
    if score ≤ previous round's score          → stop: NO PROGRESS
    send FEEDBACK verbatim to the builder      (SendMessage to the same builder
    round += 1                                  agent — it keeps its context)
```

## Hard termination rules (no infinite loops)

1. **MAX_ROUNDS = 3** grade→revise cycles total. Never extend, even if "one more round
   would fix it". Track the round number explicitly in your notes each cycle.
2. **No-progress guard:** if a round's score is not strictly higher than the previous
   round's, stop immediately — repeated feedback isn't converging.
3. Builder and grader must never spawn further agents or invoke this skill; if a
   subagent reports it is blocked (missing info, conflicting spec), stop the loop and
   surface the question to the user instead of retrying.
4. One builder, one grader, sequential — never run them concurrently on the tree.

## Definition of done (the loop, not just a round)

The run is DONE only when all of these hold:

1. A terminal state was reached: `PASS`, `MAX ROUNDS REACHED`, or `NO PROGRESS` —
   never an open-ended pause.
2. The working tree typechecks and builds (`npx tsc --noEmit`, `npm run build` exit 0)
   as confirmed by the last grader run.
3. Protected paths are untouched: `frontend/app/_archive/product-landing.tsx`,
   `frontend/app/drafts/profile-v1/**`, `frontend/src/client/`, `middleware.ts`
   protected list, backend code.
4. No stray processes: any dev server started during the run is stopped.
5. Nothing was committed or pushed.
6. The final report below was delivered to the user.

If any box can't be ticked, the run is not done — say so explicitly (what's missing
and why) instead of declaring success.

## On stop — always report to the user

- Final score + verdict and the per-round score trajectory (e.g. 72 → 84 → 91).
- What shipped (files) and the backup location (`frontend/app/_archive/product-landing.tsx`).
- On non-PASS stop: the unresolved feedback items, verbatim, plus your recommendation
  (accept as-is / needs user input / needs spec change). Do not silently restart.

## Scope of this phase

Profile page only (chat UI stub included). The working chat agent
(`profile-chat-agent` skill, backend + streaming) is a separate later phase — run this
same loop pattern for it when asked, with its own grader criteria.

**Chat-agent phase (when run):** grading is security-gated. The grader's rubric must
weight the "Security" layers and red-team test suite from the `profile-chat-agent`
skill as a top category with an automatic cap: missing/failing red-team suite, a
client-suppliable `system` role, a privileged endpoint (tools/DB writes), or a
missing output guard → VERDICT cannot be PASS regardless of total score.
