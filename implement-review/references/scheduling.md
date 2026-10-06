# Scheduling: task graph, waves, and mode selection

## 1. Predicting write-sets

Every scheduling decision rests on the write-set, so spend real effort here. For each
task, read enough of the codebase to name the files it will touch.

Good: `src/auth/session.ts`, `src/auth/*.test.ts`, `migrations/**`
Useless: `src/**`, `the auth code`, `probably a few files`

If you cannot narrow a task to a concrete set, that is your answer: it is not
schedulable in parallel. Put it in mode B.

Include files the task will **create**, not only those it will edit. A task that adds
`src/rate-limit/index.ts` owns that path even though it does not exist yet.

Expand globs to concrete paths before comparing:

```bash
git ls-files -- 'src/auth/*.ts'
```

Two tasks are disjoint when the expansion of their write-sets shares no path, **and**
neither creates a new path the other also creates.

## 2. Building the graph

### Edges

Add `A → B` only when B consumes an artifact A produces:

- B imports a symbol A defines
- B queries a column A's migration adds
- B reads a config key A introduces
- B extends a class or implements an interface A writes
- B's tests exercise behaviour A implements

That is the whole list. These are **not** edges:

- "A is more foundational in spirit"
- "It would be tidier to do A first"
- "A and B are both about authentication"
- "A is bigger so it should go first"

The default failure mode of a model building a task graph is to chain everything into
Setup → Implement → Test → Integrate, which produces a critical path equal to the
total work and therefore zero parallelism. Resist it. When you are unsure whether an
edge is real, ask: *if B ran first, what specifically would break?* If you cannot name
the breakage, there is no edge.

### Wave 0

Foundational work goes alone in wave 0 and never shares a wave with its consumers:

- Schema changes and migrations
- Shared types and interfaces
- New dependencies or package scaffolding
- Build or config changes that alter how everything else compiles

### Sanity check

```
critical path length  vs  total task count
```

If they are equal, every task is chained. That is almost always wrong — go back and
challenge each edge against the "what would break" test. Record the check in the
ledger so a resumed run does not silently accept an over-serialised graph.

Also check for cycles. A cycle means two tasks were split at the wrong seam; merge
them into one task rather than breaking the edge arbitrarily.

### Waves

Topologically sort, then group: a task belongs to wave *n* where *n* is the length of
the longest dependency chain ending at it. Within a wave, split further by write-set
overlap — two tasks in the same topological level that write the same file must not
run together.

## 3. Choosing the mode

Per wave, first match wins:

```
wave has 1 task
  → mode A (single, in-place)

any task in the wave writes a path another task in the wave writes
  → mode B (sequential, in-place)

wave has few small tasks and concurrency saves little
  → mode B

any task runs a migration, starts a server, binds a port,
  or writes a shared build cache (.next, target, dist, .turbo)
  → mode D (worktrees), or mode B if concurrency is not worth the setup

tasks are write-disjoint and share no runtime state
  → mode C (parallel, in-place)

isolation genuinely required — overlapping writes that must still be
concurrent, or racing several implementations of the same task
  → mode D (worktrees)
```

**Bias toward B.** Sequential in-place has no integration phase, no worktree setup, no
shared-tree hazards, and no way to produce a conflict. For three small tasks, the
wall-clock saved by concurrency rarely pays for a single worktree misconfiguration.

Mode D's costs are real and documented: a fresh worktree has no `.env`, no
`node_modules`, and no build cache; concurrent dev servers collide on ports; and
concurrent migrations against one shared database corrupt each other. See
`references/integration.md` before choosing it.

## 4. Conflict detection with `git merge-tree`

Be precise about when this is available.

**Before dispatch, there is nothing to merge.** No branch exists yet, so conflict
detection at this stage is the write-set disjointness computation in §1 — a set
operation, not a git operation. Do that one properly; it is the only pre-flight you
actually have.

**Before integration, `git merge-tree` is exact and free.** It performs a real
three-way merge in memory and touches no working tree, index, or ref:

```bash
# Will task/t2 merge cleanly into the current HEAD?
git merge-tree --write-tree --name-only HEAD task/t2
```

Exit status `0` means clean. Exit status `1` means conflict, and with `--name-only`
the output names the conflicting files. Requires git 2.38 or newer; check with
`git --version` and fall back to a throwaway-branch trial merge if older.

Use it in mode D at two points:

1. **Before merging each branch**, so you learn about a conflict before starting an
   operation you would have to abort.
2. **Between sibling branches in the same wave**, as a post-hoc audit of your
   write-set prediction. If two branches that you scheduled as disjoint conflict with
   each other, your prediction was wrong — record that in the ledger, because it means
   the same mistake will recur on the next wave unless you tighten how you predict.

## 5. Re-planning mid-run

If a task's real write-set escapes its declared one:

- **In mode B**: harmless. Update the table and carry on.
- **In mode C**: abort the wave, re-run it as mode B. Do not attempt to salvage a
  shared tree where an agent wrote somewhere unexpected.
- **In mode D**: the branch is isolated so nothing is corrupted, but the schedule is
  now wrong. Re-check the remaining waves for overlap against the *actual* write-set
  before dispatching further.

Record every escape in the ledger with the declared and actual sets. A pattern of
under-predicted write-sets is a signal to stop using modes C and D for this codebase.
