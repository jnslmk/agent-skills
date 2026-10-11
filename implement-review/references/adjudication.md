# Adjudication: the fix ladder, disputes, and the ledger

## 1. Bounded repair policy

This file is authoritative for repair counters and gates. Apply it separately to
each task and to the integrated-review stage `final`.
These are local operating defaults, not an empirically universal iteration count.

### Counting and dispatch

Initial implementation and initial review are **round 0**. A product repair round
is one batched fix dispatch, verification, and fresh re-review. Increment the
stage's counter **before** dispatch. A subsequent source repair after feedback
uses another round; keeping the last round “open” does not extend the budget.
Provider-failure replacement continues the reserved round. Initial implementation,
provider faults, reviews, adjudication, and harness-only repairs do not add product
rounds. Persist counters across resumes, new finding IDs, and renamed repair tasks.

| Product round | Dispatch policy |
|---|---|
| 1–5 | Ordinary repair budget; resume the implementer only while the stagnation gate permits |
| 6–8 | Authorize each round individually through the extension gate |
| Beyond 8 | No automatic product repair |

Supply this policy explicitly to fresh agents whose profiles may contain older
briefs; do not assume their embedded instructions were regenerated.

### Progress, stagnation, and extension

**Verified progress** means closure or meaningful reduction of an existing blocker,
or new reproducible evidence materially narrowing its diagnosis. Rewording a
finding, moving its line, another opinion, or an unverified claim is not progress.

Apply stagnation **before** considering an extension:

- After the first unsuccessful approach to a finding, use a fresh implementer.
- After two materially distinct unsuccessful approaches with neither new diagnostic
  evidence nor meaningful reduction, escalate that finding.
- Two consecutive stage cycles without verified progress stop automatic repair.

For each extension, record a specific next repair and verification, and either
verified progress from the latest completed cycle or a genuinely new evidence-backed
material defect. Older progress cannot repeatedly fund extensions. Authorize only
if the stagnation gate permits; unused budget is not permission.

### Review and finding identity

Nits are reported only in the initial review; later reviews report 🔴 Important
findings only. Park surviving nits with reasons. Genuine newly discovered blockers
are allowed even on unchanged lines, with reproducible evidence and origin:
`newly introduced`, `newly exposed`, or `previously missed`.

Assign stable IDs such as `t1-F1` and `final-F1`. The same root cause and failing
behavior keep the same ID across line moves and rewordings. Reopen a fixed or
rejected finding only for changed code/reachability or genuinely new evidence;
record the reopening cause. Give fresh reviewers neutral pending findings to check,
not prior verdicts, rebuttals, implementer reasoning, or orchestrator diagnoses as
facts.

### Verification-harness repair

A harness-only failure invalidates evidence; it does not establish a product defect.
Preserve the bad run and identify the broken fixture, probe, or environment.
Allow at most **two harness-only repair attempts total per task or final stage**,
incremented before dispatch and never reset per incident. Smoke the repaired harness
minimally before the full rerun. Block the stage after two unsuccessful attempts,
or when a later harness defect would require a third attempt.

The exemption permits no production edits, weakened assertions, changed acceptance
criteria, or masking of failures. A mixed harness/product fix also consumes a product
round. Provider and verification retries are not unlimited: record failure,
next action, and retry bounds; block when valid evidence cannot be obtained.

### Stopping and completion

On stagnation, exhausted budget, or a missing decision, adjudicate eligible disputes,
dispose every unresolved finding, and report the current diff and blockers together.
Leave the work as it stands; in mode D leave blocked branches unmerged.

Merge or complete only with no open blockers, every finding disposed, valid required
behavioral proof, and a review PASS on the latest snapshot. Any subsequent code
change invalidates that PASS. Exhausting a counter is never a correctness verdict.

## 2. Disputes

An implementer may reject a finding with technical reasoning and cited `file:line`
evidence. “I disagree” or “this is intentional” alone is not a rejection.

### Routing a dispute

Dispatch a **fresh adjudicator**, using the reviewer brief's adjudicator variant.
Give it the finding and rebuttal as unattributed peer claims, the relevant code,
and the task requirement. Do not label either claim as original or identify its
author; do not route the rebuttal back to the same reviewer.

Record the ruling and its evidence in the ledger:

- `FINDING STANDS`: the finding remains open at its supported severity.
- `REBUTTAL STANDS`: close the finding as `rejected`.
- `BOTH PARTLY RIGHT`: record which claim parts stand and the remaining repair.

Use at most one adjudication for an unchanged finding/evidence pair. An evidence-only
dispute does not earn another product repair or another vote. Reconsider only when
code/reachability changes or genuinely new evidence warrants it; retain the finding
ID and record what changed. Adjudication itself consumes no product round.

## 3. Disposition — every finding ends somewhere

A finding may only exit in one of four states. There is no fifth, and there is no
silent drop:

| State | Meaning |
|---|---|
| `fixed` | The repair is verified and fresh re-review confirmed it |
| `rejected` | Written technical reasoning, cited, and adjudicated if disputed |
| `parked` | Real but out of scope, or a surviving nit; recorded and reported, never used to hide an in-scope blocker |
| `escalated` | Stagnation, exhausted budget, unavailable valid proof, or a required decision; blocks completion if material |

At completion, every ledger finding needs a disposition; an undisposed finding is
an orchestration error, not a judgment call.

## 4. The ledger

`.implement-review/<run-id>/ledger.md`, gitignored.

`<run-id>` is `<short-sha>-<slug-of-first-task>` — for example `a3f91c2-add-rate-limit`.
**Never a timestamp**: a resumed run must address the same directory, and timestamps
guarantee it will not.

### Format

```markdown
# Run a3f91c2-add-rate-limit

base branch: main @ a3f91c2
started from: /home/user/project
input shape: inline list (3 tasks)

## Schedule

critical path: 2   total tasks: 3   -> not over-serialised

| wave | tasks | mode | reason |
|------|-------|------|--------|
| 0 | t1 | A | foundational migration |
| 1 | t2, t3 | C | disjoint write-sets, no shared runtime state |

## Tasks

| id | description | acceptance criteria | write-set | deps | status |
|----|-------------|---------------------|-----------|------|--------|
| t1 | add rate_limit col | reversible migration preserves existing rows | migrations/** | — | merged |
| t2 | enforce in API | requests share a window; excess requests rejected | src/api/limit.ts | t1 | reviewing |
| t3 | admin override UI | authorized override persists and is enforced | src/admin/** | t1 | todo |

## Stage counters and proof

| stage | product rounds | harness attempts | consecutive no-progress cycles | status | latest snapshot | review | behavioral proof |
|-------|----------------|------------------|--------------------------------|--------|-----------------|--------|------------------|
| t1 | 1 | 0 | 0 | PASS | tree A | report path | migration up/down command, PASS, artifact path |
| t2 | 5 | 1 | 0 | reviewing | tree B | report path | window scenario, reduced failure, artifact path |
| t3 | 0 | 0 | 0 | todo | — | — | — |
| final | 0 | 0 | 0 | pending | — | — | combined scenario pending |

## Findings

| ID | stage | first/latest round | severity | root cause / failing behavior | origin | status | disposition |
|----|-------|--------------------|----------|-------------------------------|--------|--------|-------------|
| t1-F1 | t1 | 0/1 | 🔴 | down migration drops existing data | newly introduced | recurring | fixed |
| t2-F1 | t2 | 0/0 | 🟡 | local binding obscures outer limit | newly introduced | new | parked: nit |
| t2-F2 | t2 | 0/5 | 🔴 | request-local clock resets shared window | newly introduced | recurring | open |

### t2-F2 evidence and approaches

- Acceptance criterion: requests share a window; excess requests rejected.
- Approach A, round 1: move clock initialization; reproduction still fails
  (command, snapshot, artifact); unsuccessful -> fresh implementer.
- Approach B, rounds 2–5: persist window boundary; record each round's
  verified reduction/diagnostic evidence (command, snapshot, artifact).
  Latest reproduction isolates concurrent boundary rollover.
- Dispute: peer claim/rebuttal artifact paths; FINDING STANDS; ruling evidence.
- Reopening cause, if any: changed code/reachability or new evidence reference.

## Extension rulings

| stage | next round | stagnation gate | qualifying evidence | specific next repair / verification | ruling |
|-------|------------|-----------------|---------------------|-------------------------------------|--------|
| t2 | 6 | permits: latest cycle reduced failure | t2-F2 boundary reproduction artifact | correct persisted rollover / concurrent boundary scenario | authorized before dispatch |

## Harness repairs

| stage | attempt | bad-run evidence / diagnosis | harness-only change | minimal smoke / full rerun evidence |
|-------|---------|------------------------------|---------------------|------------------------------------|
| t2 | 1 | artifact: fixture clock not advanced | advance fixture clock, assertions unchanged | smoke PASS; full rerun exposes t2-F2 |

## Final integrated review

status: pending
aggregate diff: artifact path
acceptance criteria: all task criteria plus cross-task enforcement
review report: —
combined behavioral verification: command/scenario, snapshot, result, artifact

Use `final` for integrated-review findings and its separate counters above.
For single-task runs, record `status: skipped (single-task review covers the run)`.

## Events

- wave 1: t3 wrote outside declared write-set -> abort wave, re-run as mode B
```

`open` is an interim finding state, not a final disposition. Preserve approach and
evidence history instead of overwriting it with the latest verdict.

### Update points

Write at each state change:

- Normalize/schedule: task criteria, write-sets, dependencies, waves, and critical path.
- Before product repair: apply stagnation, record any extension ruling and next
  repair/verification, increment the stage counter, record approach and agent.
  Initial dispatch is round 0; a provider replacement retains the reserved round.
- Before harness repair: preserve bad-run evidence and diagnosis, increment the
  harness counter; afterward record smoke/full-rerun evidence and validity.
- After verification/review: record exact snapshot, command/scenario, result and
  artifacts; update progress/no-progress streak and stable findings with first/latest
  round, root cause, origin, new/recurring/reopened status, and reopening cause.
- After dispute/disposition: preserve peer artifacts, ruling, evidence changes, and
  outcome; after merge update task status.
- At final review: record aggregate diff, criteria, snapshot, report, proof, and
  findings under `final`; subsequent code changes invalidate PASS.
- On stop/surprise/resume: record reason and current state; resume existing counters
  and identities, not a fresh budget.

### Policy decision prompts

Use these concrete prompts for later smoke checks; each row states the expected decision.

| Prompt | Expected decision |
|---|---|
| Initial review finds a blocker; first fix dispatch crashes at the provider. Which round does replacement use? | Reserve round 1 before dispatch; replacement stays in round 1. |
| After round 5 a verified reproduction materially narrows the blocker and a specific next repair/probe is recorded. May repair continue? | Authorize round 6 only if stagnation permits; later extensions need their own rulings. |
| A finding moves lines and is reworded after two distinct failed approaches with no new evidence or reduction. Reset its ID and continue? | Keep its ID; escalate it under stagnation. |
| Two stage cycles make no verified progress, but unused rounds remain. Dispatch again? | Stop automatic repair; remaining budget does not override stagnation. |
| Round 8 re-review exposes a genuine blocker on unchanged code. Patch within the same round? | Record the evidence-backed origin and finding; escalate, not another source repair or PASS. |
| A rejected finding returns with the same evidence and a new reviewer opinion. Adjudicate again? | Retain its ID/disposition; no repeated vote. Changed reachability or new evidence is required to reopen. |
| Two harness repairs were used successfully; a later broken probe needs repair. Is its incident budget fresh? | No; block the stage rather than dispatch a third harness attempt. |
| A fixture repair also changes production behavior. Is it exempt from product counting? | No; increment both applicable counters and preserve acceptance/assertions. |

## 5. Reporting to the user at the end

```markdown
## Done
<n> tasks, <n> merged, <n> blocked

| task | status | product rounds | harness attempts | 🔴 fixed | open |
|------|--------|----------------|------------------|----------|------|

## Final integrated review
<PASS | BLOCKED | SKIPPED (single task)> — <reviewed revision/tree snapshot>
<Product rounds; harness attempts; combined behavioral verification result and evidence>

## Open items
<Every finding with disposition `parked` or `escalated`, with its reasoning>

## Needs you
<Blockers, conflicts, decisions — or "nothing" >
```

Report honestly. If tests fail, say so and show the output. If a task was left
unmerged, say which and why. A summary claiming success over a blocked task is the
one failure mode that makes the entire skill worse than doing the work by hand.
