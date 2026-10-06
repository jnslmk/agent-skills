# Adjudication: the fix ladder, disputes, and the ledger

## 1. The ladder

Review findings converge fast or not at all. Quality saturates after roughly three
feedback rounds, and the first correction captures most of the available gain, so the
loop is capped and escalates rather than repeating the same move.

| Round | Who implements the fix | Why |
|---|---|---|
| 1 | Same implementer, resumed | It has the context; most findings are fixed here |
| 2 | Same implementer, resumed | 🔴 only from here on |
| 3 | Same implementer, resumed | Last cheap attempt |
| 4 | **Fresh** implementer, stronger model | Three failures means the original agent has a wrong mental model; resuming it again just re-derives the same mistake |
| 5 | Fresh implementer, stronger model | Final attempt |
| — | **Stop.** Adjudicate, write rulings, surface to the user | |

Increment the round counter in the ledger **before** dispatching, not after. A run that
dies mid-round must not resume thinking it has a fresh budget.

### Nit suppression

**From round 2 onward, the reviewer reports 🔴 only.** 🟡 raised in round 1 that were
not fixed are recorded in the ledger and reported at the end; they do not re-enter the
loop.

This is the anti-loop mechanism, and it is severity-based rather than count-based on
purpose. A count-based cap stops the loop after N rounds regardless of what is left
open. Severity-based suppression stops the *cause* — a one-line fix reaching round
seven because each round found new style opinions about the same line.

### What "stop" means at round 5

Not "give up silently". For every finding still open:

1. Attempt adjudication (§2) if it is disputed.
2. Write a ruling into the ledger: what the finding is, why it is unresolved, and
   what you recommend.
3. Report all of them to the user together, with the diff as it stands.

The work is left in whatever state round 5 produced. Do not revert it, and do not
merge past open 🔴 in mode D — leave the branch unmerged and say so.

## 2. Disputes

An implementer may reject a finding with evidence. This is legitimate and necessary:
reviewers are wrong often enough that forbidding rejection would inject bugs rather
than prevent them. There is a documented failure mode where an implementer defers to
a confident-sounding but false critique and breaks working code to satisfy it.

A rejection is valid only if it states a technical reason and cites `file:line`.
"I disagree" or "this is intentional" is not a rejection.

### Routing a dispute

**Do not send the rebuttal back to the same reviewer.** That framing — an authority
being challenged by the party it just judged — is precisely the one LLM judges cave
to: a bare assertive counter-claim flips a judge's verdict more reliably than a
carefully reasoned one. The same reviewer will either capitulate to confidence or dig
in on pride, and neither is a ruling.

Instead dispatch a **fresh adjudicator** — the reviewer brief's adjudicator variant.
Give it:

- The finding, unattributed
- The rebuttal, unattributed
- The relevant code
- The task requirement

Present them as two peer claims. Do not label which came first, which is the
"original", or which came from the reviewer. Let it read the code and rule.

Record the ruling in the ledger. A `FINDING STANDS` ruling re-enters the ladder as a
🔴. A `REBUTTAL STANDS` ruling closes the finding as `rejected`.

Adjudication does not consume a ladder round.

## 3. Disposition — every finding ends somewhere

A finding may only exit in one of four states. There is no fifth, and there is no
silent drop:

| State | Meaning |
|---|---|
| `fixed` | The code changed and re-review confirmed it |
| `rejected` | Written technical reasoning, cited, and adjudicated if disputed |
| `parked` | Real but out of scope — usually 🟣, or 🟡 surviving nit suppression. Recorded and reported |
| `escalated` | Ladder exhausted or a decision is needed that you were not given |

The ledger is what makes this auditable. A finding that appears in the ledger without
a disposition is a bug in your orchestration, not a judgement call.

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

| wave | tasks  | mode | reason |
|------|--------|------|--------|
| 0    | t1     | A    | single foundational task (migration) |
| 1    | t2, t3 | C    | write-sets disjoint, no shared runtime state |

## Tasks

| id | description        | write-set          | deps | status   | rounds |
|----|--------------------|--------------------|------|----------|--------|
| t1 | add rate_limit col | migrations/**      | —    | merged   | 1      |
| t2 | enforce in API     | src/api/limit.ts   | t1   | reviewing| 2      |
| t3 | admin override UI  | src/admin/**       | t1   | todo     | 0      |

## Findings

| # | task | round | severity | finding                          | disposition |
|---|------|-------|----------|----------------------------------|-------------|
| 1 | t1   | 1     | 🔴       | migration not reversible         | fixed |
| 2 | t2   | 1     | 🟡       | `limit` shadows outer binding    | parked (nit suppression, round 2+) |
| 3 | t2   | 1     | 🔴       | window resets on every request   | disputed -> adjudicated: FINDING STANDS -> fixed |
| 4 | t2   | 2     | 🟣       | pre-existing: retry has no cap   | parked (pre-existing) |

## Final integrated review

status: pending
reviewed revision/tree snapshot: —
aggregate diff: —
repair rounds: 0
review report: —
combined behavioural verification: pending (command/scenario and evidence: —)

Use `final` in the findings table's task column for integrated-review findings.
For single-task runs, record `status: skipped (single-task review covers the run)`.

## Events

- wave 1 dispatched mode C; t3 wrote src/shared/types.ts (outside declared set)
  -> wave aborted, re-run as mode B
```

### Update points

Write to the ledger at every state change, not at the end:

- After normalising input — the task table
- After scheduling — waves, mode, and the critical-path check
- Before each dispatch — increment `rounds`, set `status`
- After each review — every finding, with severity
- After each disposition — the outcome
- After each merge — `status: merged`
- Before final review — record the aggregate diff and exact revision/tree snapshot
- After final review — record its report, status, and every finding under `final`
- Before each integration repair — increment final `repair rounds`
- After any later code change — invalidate the final PASS
- After combined verification — record the command/scenario, result, and evidence
- On any surprise — an `Events` line

The cost of over-writing the ledger is a few tokens. The cost of under-writing it is a
compaction that loses which findings were already dismissed and why, and then a run
that re-litigates them.

## 5. Reporting to the user at the end

```markdown
## Done
<n> tasks, <n> merged, <n> blocked

| task | status | rounds | 🔴 fixed | open |
|------|--------|--------|----------|------|

## Final integrated review
<PASS | BLOCKED | SKIPPED (single task)> — <reviewed revision/tree snapshot>
<Repair rounds; combined behavioural verification result and evidence>

## Open items
<Every finding with disposition `parked` or `escalated`, with its reasoning>

## Needs you
<Blockers, conflicts, decisions — or "nothing" >
```

Report honestly. If tests fail, say so and show the output. If a task was left
unmerged, say which and why. A summary claiming success over a blocked task is the
one failure mode that makes the entire skill worse than doing the work by hand.
