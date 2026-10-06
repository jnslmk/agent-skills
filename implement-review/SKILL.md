---
name: implement-review
description: >-
  Use when given one task or a list of tasks to build - dispatches a fresh subagent to
  implement each task and a separate read-only subagent to review it, loops on findings
  with a capped fix ladder, and for multiple tasks picks the cheapest safe execution
  mode (sequential, parallel in-place, or isolated worktrees) after building a
  dependency DAG. Triggers on "implement and review", "build these tasks", "work
  through this plan", "implement with review", "orchestrate these tasks".
---

# Implement + Review

Given work to do, you orchestrate. You do not implement, and you do not review.
Implementation happens in a fresh subagent. Review happens in a different fresh
subagent that cannot write. You schedule, dispatch, adjudicate, and integrate.

**Core principle:** fresh subagent per task + review from an agent that never saw the
implementer's reasoning + a capped fix ladder that never silently drops a finding.

## Why the separation is strict

A reviewer that shares the implementer's context does not review — it ratifies. A
reviewer that can edit does not review — it becomes a second implementer, and the
quality signal disappears. Both boundaries are enforced mechanically where the harness
allows it (`ir-reviewer` has no write tools) and by this skill everywhere else.

---

## Phase 0 — Normalise the input

Detect which of three shapes you were given:

| Input | Detection | Action |
|---|---|---|
| A path to a markdown file | Argument resolves to an existing `.md` file | Parse task headings. Honour `[P]`, `[depends: N]`, and `writes:` annotations if present |
| An inline list | Prompt contains a bulleted or numbered list of 2+ items | One task per item |
| A single free-form task | Anything else | One-task run. Skip Phases 1 and 1b entirely; go to mode A |

Normalise to a task table. Keep it in the ledger, not just in context:

```
| id | description | write-set | deps | status | rounds |
|----|-------------|-----------|------|--------|--------|
| t1 | ...         | src/a/**  | —    | todo   | 0      |
```

Before dispatching, record the starting revision and any pre-existing local changes
in the ledger. Preserve the original request/spec alongside the task table; these
are the baseline for the final integrated review, not just the individual tasks.

**Write-set** is your prediction of which paths the task will touch, as globs. It
drives every scheduling decision below, and it gets verified before dispatch — you are
not trusted on it, and neither is the implementer.

To predict a write-set, read enough of the codebase to be specific. `src/**` is not a
write-set; it is a refusal to answer. If you genuinely cannot narrow it, that task is
not parallelisable and belongs in mode B.

---

## Phase 1 — Build the schedule (multi-task only)

Full rules in `references/scheduling.md`. The essentials:

**1. Edges are data dependencies, not vibes.** Add `A → B` only when B consumes an
artifact A produces: a symbol, a schema, a migration, a config key, a file. "B feels
like it should come after A" is not an edge. This is the single most common failure —
AI-built task graphs default to a serial chain and end up with zero parallelism.

**2. Foundational work is wave 0 alone.** Shared types, schema changes, migrations,
scaffolding, dependency additions. Never in the same wave as anything that consumes
them.

**3. Two tasks share a wave only if their write-sets are disjoint.**

**4. Sanity-check the graph before you trust it.** Compute the critical path. If it
equals the total work, every task is chained and the graph is wrong — go back and
challenge each edge for an actual data dependency.

**5. Verify disjointness, do not assume it.** Before dispatching a wave, expand every
write-set glob to concrete paths with `git ls-files` and intersect them. Overlap means
those tasks do not share a wave. This set computation is the only pre-flight available
at dispatch time — no branch exists yet, so there is nothing for git to merge.

Later, in mode D, `git merge-tree` gives you exact conflict detection **before
integration** without touching any working tree. Both are detailed in
`references/scheduling.md`.

---

## Phase 1b — Choose the execution mode

Pick the **cheapest mode that is safe**. Worktrees buy isolation and cost you missing
`.env` files, per-worktree dependency installs, port and database collisions, and
disk. Do not pay for isolation you do not need.

Walk the modes in order and take the first that fits:

### Mode A — Single, in-place
**When:** exactly one task.
**How:** current branch, no scheduling, no worktree. Implement → review → fix → commit.

### Mode B — Sequential, in-place
**When:** several tasks that overlap in write-set, are few, are small, or share build,
test, or database state.
**How:** current branch, one task at a time, each with its own full implement → review
→ fix → commit cycle. No worktrees, no integration phase, no conflicts by construction.

**This is the default for small task counts.** It is the lowest-variance path. Reach
past it only when concurrency buys something real.

### Mode C — Parallel, in-place
**When:** several tasks whose expanded write-sets provably do not intersect, **and**
none of them run migrations, start servers, bind ports, or mutate shared build caches.
**How:** current branch, concurrent implementer subagents editing disjoint paths in one
shared working tree.

Because the working tree is shared, these rules are non-negotiable:

- **You own git. Implementers do not.** Their brief forbids `git add`, `commit`,
  `checkout`, `stash`, `rebase`, and `merge`. They edit files and report.
- **Commits are serialised by you**, one per task after its review passes, using
  explicit pathspecs — `git commit -- <write-set>`, never `git add -A`. A blanket add
  in a shared tree captures another task's half-finished work.
- **Verification is serialised** if the test suite or build writes shared artifacts.
  Two concurrent `npm test` runs against one `.next/` or `target/` will produce
  garbage results and you will chase phantom failures.
- **A write outside a task's declared write-set aborts mode C for that wave.** Re-run
  the wave as mode B. Do not try to salvage it.

### Mode D — Worktrees
**When:** isolation is genuinely required — tasks whose writes overlap but must still
run concurrently, competing implementations of the same task, or tasks that each need
their own server, database, or build directory.
**How:** branch per task in `.worktrees/<branch>`, then Phase 4 integration. Setup and
failure modes in `references/integration.md`.

### Composition and bookkeeping

Waves always run sequentially. Each wave picks its own mode independently — a wave of
one is mode A regardless of what the other waves do.

**Before dispatching, write the chosen mode and a one-line reason into the ledger.**
A compacted or resumed run must not silently change modes mid-flight.

---

## Phase 2 — Per task: implement, then review

### Dispatch the implementer

Fresh subagent, no inherited session history. Use the `ir-implementer` agent if the
harness has it; otherwise a generic subagent with `references/implementer-brief.md`
pasted as its instructions.

Give it exactly this and nothing more:

- The task description, verbatim from the table
- Its declared write-set, stated as a hard boundary
- The working directory (worktree path in mode D, repo root otherwise)
- Interfaces it must conform to — signatures, schemas, types it consumes
- Global constraints: the project's conventions, its test command, its lint command
- A path to write its report to

Do **not** give it: your reasoning, the other tasks, prior review findings from a
different task, or the session history. Context it does not need is context that
lets it drift outside its slice.

### Provider failure fallback

Provider availability is separate from implementation quality. A provider rate
limit, quota exhaustion, outage, or transport failure is not a task failure and
does not consume a fix-ladder round.

When an implementer cannot start or complete because of a provider failure:

1. Classify the error from the provider response. Do not infer a rate limit from
   a generic agent timeout.
2. Honour `Retry-After` only when it is within the orchestrator's maximum wait
   (five minutes by default). A longer delay immediately selects the next
   fallback.
3. Dispatch one fresh implementer through the next available model/provider,
   using the original task description, write-set, interfaces, constraints, and
   report path. Do not pass the failed agent's reasoning.
4. Keep the task's implementation round unchanged and record the provider,
   classification, retry delay, and selected fallback in the ledger.
5. Never run two implementers for the same task concurrently. Before fallback
   dispatch, inspect the declared write-set for partial edits and make the new
   implementer continue safely from the current tree.

The fallback order is:

```
ir-implementer → alternate implementation model/provider → generic task agent
```

The generic agent receives the same implementer brief and hard write-set
boundary; it is not a reason to relax repository or git-state rules. If every
fallback is unavailable, mark the task `blocked: provider-unavailable` and
surface the provider evidence to the user. Do not silently retry for hours.

This execution fallback ends when an implementer produces an artifact. Review
then starts normally with a fresh read-only reviewer; provider fallback is not
part of the reviewer finding fix ladder below.

### Dispatch the reviewer

Fresh subagent, `ir-reviewer` where available, brief in
`references/reviewer-brief.md`. Two stages, in order:

1. **Spec compliance** — does it do what the task said, all of it, and nothing else?
2. **Code quality** — correctness, edge cases, error paths, resource handling.

Give the reviewer the **diff as a file** plus the task's stated requirements. Give it
the implementer's *report* only if the report claims something the diff cannot show
(a manual test performed, an external system checked).

**Never give the reviewer the implementer's reasoning or your session history.** This
is not stylistic caution. LLM judges are measurably swayed by an assertive framing
over a correct one — a bare confident claim outperforms a well-reasoned one at
changing a judge's verdict. A reviewer that sees the argument is reviewing the
argument. Give it the artifact.

### Your own premises are the most dangerous input

Everything you assert in a brief arrives as established fact. An agent that then
"confirms" it has confirmed nothing — you told it the answer and it found a way to
agree. **Two agents you briefed identically agreeing is not corroboration. It is one
claim, counted twice.**

The failure shape is specific: you state a diagnosis, dispatch on it, the work comes
back consistent with it, and the diagnosis is wrong. Nothing in the loop can catch
that, because every participant inherited the error from you.

So:

- Label diagnosis as a **claim to verify**, not as background — and mean it.
- When a finding depends on your premise, ask for the evidence, not the conclusion.
- **Treat an agent that challenges your premise as the loop working**, not as one that
  misread the brief. Re-derive it yourself before overruling.
- If a premise turns out wrong, fix it in the ledger *and* re-check everything already
  built on it. Downstream work inherited the error too.

### Verification is not free

"Read-only" is an instruction, not a property. Withholding Write/Edit leaves Bash, and
Bash reaches production hosts, container daemons, git state and secrets. When you ask
for empirical verification, say what it may touch and what it must not, and require
disclosure of any side effect.

Two real incidents in one session: a reviewer ran `docker run -v <name>:/path` — which
auto-creates the named volume — leaving a stray one on a production host that would
have silently broken the next deploy; and a reviewer's `PATH`-restriction test failed
to isolate what it believed it did, so the command ran against real state and printed
a live credential into the transcript, forcing a rotation.

Both surfaced only because the agents disclosed them. Make that disclosure an explicit
expectation, and treat an honest self-report as the system working — the alternative
is not fewer side effects, only unreported ones.

### Severity

| Marker | Tier | Meaning |
|---|---|---|
| 🔴 | Important | A bug that should be fixed before this lands |
| 🟡 | Nit | Minor, worth fixing, not blocking |
| 🟣 | Pre-existing | A real bug, but this change did not introduce it |

**Verification bar:** a claim about behaviour needs a `file:line` citation in the
source. An inference from a function's name is not a finding. Enforce this — false
positives cost a full round trip each, and they teach you to discount real findings.

🟣 findings are recorded in the ledger and reported at the end. They never block and
never enter the fix ladder; fixing them is scope creep unless the user asks.

---

## Phase 3 — The fix ladder

Full protocol in `references/adjudication.md`. Quality saturates after about three
feedback rounds, and the first correction captures most of the gain, so the ladder is
capped and escalating rather than open-ended:

| Round | Action |
|---|---|
| 1–3 | Resume the **same** implementer with the findings |
| 4–5 | Fresh implementer, **more capable model** |
| after 5 | **Stop.** Write a ruling for every open finding. Surface to the user |

Two rules that make the cap safe:

- **Suppress 🟡 from round 2 onward.** Only 🔴 re-enters the loop. This is what stops
  a one-line fix reaching round seven on style alone. Unfixed nits are recorded in
  the ledger and reported, not silently dropped.
- **No finding is ever silently discarded.** Every one ends in exactly one state:
  fixed, rejected with written technical reasoning, or escalated to the user.

**Disputes.** An implementer may reject a finding with evidence — that is legitimate,
and reviewers are wrong often enough that forbidding it would be worse. But the
dispute does not go back to the same reviewer as a follow-up turn; that is precisely
the framing judges cave to. Dispatch a **fresh adjudicator** with the finding and the
rebuttal presented as two peer artifacts, neither attributed as the incumbent. Record
its ruling in the ledger.

---

## Phase 4 — Integrate (mode D only)

Modes A, B, and C commit to the current branch as they go and skip this phase.

Full procedure and failure modes in `references/integration.md`. The shape:

```bash
git merge --ff-only task/t1
git rebase <base> task/t2      # t2 now sees t1
git merge --ff-only task/t2
git rebase <base> task/t3      # t3 sees t1 and t2
git merge --ff-only task/t3
```

Rebase then merge, one branch at a time, so each branch integrates against what
actually landed before it. **Do not cherry-pick** — it duplicates commits and discards
branch ancestry. Cherry-pick is correct in exactly one situation: you raced several
implementations of the *same* task and are keeping the winner.

**On a rebase conflict: stop and hand it to the user.** Do not auto-abort — a paused
rebase may be one the user is mid-way through resolving.

Remove each worktree immediately after its branch merges.

---

## Phase 5 — Final integrated review (multi-task runs, all modes)

After every task has passed its own review and all changes are in the target working
tree (after Phase 4 in mode D), run this gate before declaring the run complete.
Apply it to the whole run, even when each wave used mode A. A single-task run skips
this phase because its independent task review already covers the complete change.

### Review the combined artifact

Dispatch a **fresh `ir-reviewer`**, separate from every task's implementer and
reviewer, using `references/reviewer-brief.md`. Its task description is the original
request/spec plus the complete task table and shared interface contracts. Give it:

- A run-only aggregate diff from the recorded baseline, including integration edits
  and subsequent repairs; exclude unrelated and pre-existing local changes.
- The target working directory and the exact reviewed revision/tree snapshot.
- Verification evidence only for observations the diff cannot show, plus explicit
  permitted verification scope and side-effect disclosure requirements.

Keep implementer reasoning, prior reviewers' verdicts, and session history out of
the dispatch. The reviewer inspects the actual integrated code with the same
read-only boundaries, severity rules, and `file:line` evidence bar as task review.

The two review stages now cover **the complete spec and cross-task behaviour**:
trace producer/consumer contracts, shared state and configuration, migration/order
assumptions, error paths, and affected callers end to end. Check that the combined
implementation satisfies requirements that no individual task owned. Task-level
PASS verdicts do not prove integration. A defect exposed by composition is eligible
even when the implicated lines already passed task review.

### Resolve and re-review

Record findings under `final` in the same ledger. For blocking findings, create one
integration-repair task with an explicit write-set spanning the necessary owners
and dispatch a fresh implementer. Use Phase 3's fix ladder and dispute protocol with
one separate final-stage round counter: rounds 1–3 resume that repair implementer,
rounds 4–5 use fresh stronger implementers. New findings do not reset this counter.

After each repair, serialize integration and behavioural verification, regenerate
the aggregate diff, and dispatch a fresh final reviewer. Provide unresolved findings
to check resolution, but no rebuttals or earlier verdicts; suppress nits from round 2
onward. Re-review the complete combined artifact, not just the repair diff.

**Completion gate:** the latest integrated snapshot has a final `PASS`, every
finding has a disposition, and combined behavioural verification has passed with
evidence recorded. Any later code change invalidates that PASS and requires
re-review. Exhausted blocking findings or failed verification leave the run blocked,
even if its task commits have already landed locally; report that state to the user.

---

## The ledger

`.implement-review/<run-id>/ledger.md`, gitignored. It holds the task table, wave
assignments, the chosen mode and its justification, per-task round counters, and every
finding with its disposition.

This is what lets a run survive context compaction, and it is what makes "no silent
discards" an auditable claim rather than an intention. Update it after every state
change, not at the end.

Derive `<run-id>` from `git rev-parse --short HEAD` plus a slug of the first task —
**never a timestamp**, so that a resumed run addresses the same directory. Format in
`references/adjudication.md`.

Add `.implement-review/` to the repo's `.gitignore` if it is not already there.

---

## Stop and ask the user when

- A rebase or merge conflicts.
- Tests fail for a reason the implementer could not fix within the ladder.
- The fix ladder exhausts at round 5 with open 🔴 findings.
- A task's real write-set escapes its declared one in a way that invalidates the
  schedule.
- The work as described cannot be done without a decision you were not given —
  a schema change, a dependency addition, an API break.

Everything else runs unattended.

## Do not

- Implement or review anything yourself. You orchestrate.
- Let the reviewer edit files.
- Give the reviewer the implementer's reasoning.
- Use `git add -A` in mode C.
- Cherry-pick to integrate parallel slices.
- Drop a finding without recording its disposition.
- Create worktrees for tasks that do not need isolation.
