---
name: implement-review
description: >-
  Use when implementing and independently reviewing a task or task list. Default to
  main-agent implementation, one complete-change review, focused repair checks,
  and final regression verification; orchestrate multiple owners only when needed.
---

# Implement + Review

**Default: implement in the main agent, then get one independent review.** Keep the
implementation context through repairs. The reviewer stays read-only and independent
of the implementation, not fresh on every turn.

**Loop:** scope → implement → focused proof → independent review → repair and focused
closure → final relevant regression checks → handoff.

## 1. Scope and choose ownership

Read the affected flow and callers, the requested acceptance criteria, and existing
verification commands. Follow repository session/baseline rules before editing;
protect unrelated user drafts and select relevant drafts explicitly. Record the
starting revision, owner, scope, permitted runtime side effects, and required proof.
Use compact session state for one owner; a task table or DAG earns its place only
when scheduling multiple independent owners.

The main agent owns implementation and integration. Delegate substantial independent
slices when parallel work saves a real dependency path; define disjoint write-sets
and fixed contracts first. The main agent may implement its own slice while helpers
work. Small edits, cleanup, and already-open slices stay inline.

**Risk selects expertise and checks, not ceremony.** Authentication, concurrency,
background synchronization, money, migrations, and public contracts require suitable
expertise and targeted boundary/race/error checks. They do not automatically require
full orchestration. Delegate a sensitive slice if the main agent lacks the required
expertise; retain one integration owner and one complete-change review.

Use full orchestration only for:
- Substantial independently owned cross-system contracts needing dedicated coordination.
- Competing implementations or isolation that genuinely requires separate worktrees.
- An explicit user request for full orchestration.

For that branch, read [scheduling.md](references/scheduling.md). Read
[integration.md](references/integration.md) only when worktrees are needed. Full mode
still permits main-agent implementation; it does not imply per-slice reviews plus a
second mandatory final review. Repository policy can require stronger gates.

## 2. Implement

Trace the real path end to end, reuse existing patterns, and implement the requested
behavior without speculative scope. Update affected callers, tests, and existing
documentation. Keep useful behavior regressions, not source-text or mock-echo tests.

For a delegated slice, use [implementer-brief.md](references/implementer-brief.md).
Provide acceptance criteria, exact write-set, contracts, working directory, runtime
permissions, and proposed check commands. Helpers edit and hand off; the integration
owner queues shared builds, tests, and browser work after the affected source settles.
Helpers do not mutate git. Commit, merge, or remove worktrees only when requested or
otherwise explicitly authorized; this skill does not implicitly authorize commits.

### Dispatched-agent model policy

Use only `openai-codex/gpt-6-luna` or `openai-codex/gpt-6.1-sol` for implementation,
review, repair, and adjudication dispatches. This allowlist governs dispatched agents;
it is not a prohibition on the main agent implementing at its running model.

| Dispatched work | Profile | Model / effort |
|---|---|---|
| Clear, bounded implementation and ordinary repairs | `ir-implementer` | Luna / high |
| Ambiguous or cross-system implementation | `ir-implementer-sol` | Sol / medium |
| Sensitive boundaries, concurrency, irreversible changes, hard debugging | `ir-implementer-hard` | Sol / high |
| Independent review and retained repair closure | `ir-reviewer` | Sol / high |
| Stagnant repair or disputed finding | Fresh hard implementer or independent adjudicator | Sol / high |

Keep a retained reviewer on the same review model. Preserve a dispatched slice's Sol
selection across repairs. Ordinary Luna implementation can fall back to Sol on a
verified provider failure; Sol-required work has no Luna fallback. Honor a usable
Retry-After up to five minutes, then use an eligible available provider or report the
blocker. Provider failures do not consume product repair rounds or justify concurrent
implementers on the same files. Pin model/effort or use the matching configured
profile; unavailable required expertise blocks that dispatch. Raise effort only for
a specific evidenced need, not automatically on each round.

## 3. Focused proof before review

Run cheap syntax/lint/format/type checks at the affected scope, then the smallest
consumer-visible scenario covering the change. Exercise the actual changed surface;
tests alone do not replace a runtime smoke. Documentation-only changes need link,
consistency, and representative decision checks, not unrelated application suites.

For a bug, capture the reported failing path before repair when practical, then prove
it fixed. For a feature, cover its uncertain boundaries and the full user path. A
broken command, fixture, selector, or browser launcher is a harness failure, not a
product defect. Smoke a corrected harness minimally before a broad rerun.

### One verification queue

One owner queues commands sharing a lock, build cache, database, port, or browser
resource. Launch the next command after the current owner releases the resource;
do not submit parallel jobs merely to wait on the same `flock`. Independent cheap
read-only checks may run concurrently only when their resources are independent.

Reserve full suites, repeated builds, and broad visual passes until implementation
and review-driven repairs settle. During repairs, run the relevant regression and
cheap checks. After review closure, run the required broader regression set once on
the stable candidate. A late defect reopens affected proof and review; a passing
full suite from an earlier implementation is not proof of the repaired path.

### Orca browser is the default

For manual web verification use **Orca's embedded, worktree-scoped browser through
the Orca CLI**. Read `skill://orca-cli` first, resolve the session's executable once,
and load its version-matched guide and `references/browser.md`. Follow that resolver;
do not guess an executable or blindly invoke bare `orca` on Linux.

- Reuse the repository's supported disposable fixture or preview. Create an owned
  browser tab with the resolved CLI's `tab create --url ... --json`. Copy its
  `browserPageId` and pass `--page` on every page command; never retarget a user's tab.
- Use `snapshot`, typed interaction commands, state-based `wait`, and action effects.
  Read status/error text explicitly: interactive-only snapshots omit page text.
  Use `screenshot` for visual evidence and open its returned image. Close only the
  owned page with `tab close --page ... --json`. Follow the version-matched browser
  reference for flags, refs, viewport emulation, dialogs, and stale-ref recovery.
- Orca owns the browser. Do not build a bespoke Playwright/Puppeteer/CDP launcher
  or attach a competing automation client for manual inspection. Do not silently
  substitute the generic Eval browser/Chrome relay for the requested Orca surface.
- Existing repository Playwright/browser regression suites remain appropriate for
  automated regressions; they complement rather than replace Orca surface smoke.
- If the selected Orca executable or browser is unavailable, report the exact
  limitation. Do not switch Orca builds or claim unobserved Orca visual proof.
  Use an existing supported fallback only when user/project policy permits it.
- Before temporary previews or heavy browser work, record session owner, unique
  job, isolated process group/unit, finite expiry, purpose, and cleanup command.
  Follow workspace locking rules; absent a stricter rule, use a 15-minute expiry
  enforced independently of the agent. Close owned pages and stop owned preview
  descendants before releasing resources. Leave Orca's user-owned app/browser
  process and other user sessions running; do not give the persistent app an expiry.

### Relevant-input evidence

Use canonical repository runners and record each proof's actual production, test,
configuration, toolchain, and generated-asset inputs. Relevant input changes reopen
that proof. Formatting a test does not semantically require rebuilding assets;
documentation edits do not automatically invalidate unrelated runtime behavior.
Reuse evidence for unchanged scopes only when input independence is established and
the runner supports it. Respect the runner's validity flags: do not relabel a drifted
or invalid run as valid or weaken the runner as a side effect. If its coarse snapshot
requires a rerun, obey it and avoid starting expensive checks during active edits.

## 4. One independent complete-change review

After helpers are integrated and focused proof is available, dispatch one independent
read-only reviewer using [reviewer-brief.md](references/reviewer-brief.md). Supply the
original requirements, complete run-only diff, affected interfaces/callers, exact
candidate identity, exercised evidence, and remaining final check plan. Exclude the
implementer's reasoning and diagnoses presented as fact. The reviewer checks spec
compliance, then correctness, boundaries, errors, resources, and test relevance.

A blocker needs a file:line citation, reachable trigger, and concrete consumer impact.
Treat a proposed diagnosis as a claim to verify. Reviewers do not edit or run real
systems without an explicitly permitted verification scope; read-only tools do not
make shell/network effects safe. Never emit credentials or secret-bearing output.

One complete-change review of the actual combined candidate satisfies integration,
even with helpers or a task list. Add a specialist slice review only for a concrete
independent high-risk boundary or explicit requirement. A fresh final audit is needed
only when combined integration was not covered, scope materially broadened, review
independence was compromised, or the user explicitly requests one. Do not routinely
stack per-task, per-slice, and final audits on the same artifact.

## 5. Repair with retained context

Batch supported Important findings. Retain the implementation owner while making
verified progress, and retain the same independent reviewer for focused closure.
Send the repair diff, relevant original context, stable finding IDs, and focused
proof. Review changed paths and affected producer/consumer behavior; expand to the
whole artifact only for cross-cutting changes or evidenced wider impact. New genuine
blockers remain eligible, including previously missed defects on unchanged lines.

Use a fresh reviewer only for unavailability, compromised independence, materially
expanded scope/ownership, stagnation, or an explicit fresh-audit request. A retained
reviewer keeps its own findings; a fresh reviewer receives neutral pending claims,
not inherited verdicts, rebuttals, or author reasoning. Disputes use a fresh independent
adjudicator, not repeated votes from the same reviewer.

Before the first repair, read [adjudication.md](references/adjudication.md), the sole
authority for stable IDs, dispositions, repair/harness counters, invocation correction,
stagnation, extensions, and disputes. Preserve its five ordinary/eight maximum product
cycles and two harness-source attempts; reviewer replacement, renamed tasks, and
resumption do not reset budgets. Do not invent a stage per reviewer.

## 6. Final checks and handoff

Keep code review and verification as separate gates. A reviewer can finish code
inspection while broad checks are pending; the main agent holds completion until
all required relevant evidence passes. Collect final evidence once and reconcile it
without repeatedly waking reviewers just to change an evidence-only BLOCKED verdict.
Actual code changes or a newly exposed product defect reopen review and proof.

Finish when the complete requested behavior works, the independent review covers
the final semantic changes, every finding has a disposition, required checks and
actual-surface proof pass on relevant current inputs, and owned temporary resources
are released. Update documentation, remove throwaway scaffolds, release repository
session ownership, and commit only if requested. Report concise exercised evidence
and real remaining blockers, respecting the user's requested response format.
