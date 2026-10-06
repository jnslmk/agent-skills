---
name: implement-batch
description: "Implement an agent-ready issue graph as reviewed commits on main."
disable-model-invocation: true
---

# Implement Batch

Implement a spec and its agent-ready issues as reviewed commits landing directly on main — no pull request, no human gate.

This flow has two nested loops:

1. The **batch loop** advances the issue graph one frontier at a time.
2. Every issue runs an **issue loop**: TDD implementation, independent two-axis
   review, and the capped fix ladder in [`references/ISSUE-LOOP.md`](references/ISSUE-LOOP.md).

You are the batch orchestrator. You schedule, dispatch, integrate, and keep the
ledger. You do not write implementation code and you do not review it.

Use the explicit role allocation and dispatch table in
[`references/MODEL-POLICY.md`](references/MODEL-POLICY.md). The skill enforces its
subagent rows through the named `batch-*` agents listed there — dispatch by agent
name, never by raw model, so the harness applies each agent's own model chain. The
economical caller for the batch orchestrator is `gpt-5.6-luna` at
`medium`, but a skill cannot change the model that was already selected when it began.

Use `/implement` for one issue. Use this skill when several linked issues should land
as reviewed commits on main. The issues must already be agent-ready; incoming raw work
belongs in `/triage`, and an unsplit multi-session spec belongs in `/to-tickets`.

## Outcome

- Each issue lands as one or more reviewed commits, pushed to main as it passes.
- No pull request and no human gate: green review auto-lands.
- Each issue closes on land, with the commit SHA and proof in a comment.
- Reverts are routine: `git revert`, ledger-tracked, issue reopened with reason.
- Every review finding has a recorded disposition.

## 1. Pin the batch

Read `docs/agents/issue-tracker.md`. If it is absent, tell the user to run
`/setup-matt-pocock-skills` and stop.

Fetch the spec and every issue in the requested batch, including comments, labels,
assignees, and blocking relationships. Read the relevant domain docs named by
`docs/agents/domain.md` when it exists.

Require every implementation issue to be agent-ready. Preserve the issue graph's
native blocking edges; they are build dependencies, not suggestions about ordering.
An issue may also be held out of a wave because its predicted write-set overlaps
another issue's, but that scheduling constraint is not a new dependency edge.

Pin and record:

- the starting branch and SHA;
- the spec and issue numbers;
- test, typecheck, lint, and full-suite commands;
- the public test seams already agreed in the issues or spec;
- a predicted write-set for each issue.

If a required seam or product decision is absent, mark that issue `needs-decision` in
the ledger. Continue with independent issues; ask the user only when no frontier work
remains.

The starting working tree must be clean. Preserve user work in place and stop rather
than stashing it.

## 2. Create the durable run

No batch branch and no PR. Work lands directly on main, one issue at a time, as each
issue loop passes. Record the main head SHA as the moving integration target.

Keep the run ledger at:

```text
.codex-tmp/implement-batch/<base-sha>-<spec-slug>/ledger.md
```

Create `.codex-tmp/` first and add it to `.gitignore` when needed. Derive the run ID
from stable inputs, never a timestamp, so a resumed run finds the same ledger.

The ledger records:

```text
base branch and SHA
landed commits, push SHAs, revert SHAs, and issue-close comments
issue graph and predicted write-sets
issue status: todo | active | review | fix | passed | integrated | needs-decision | quota-paused | blocked
issue branch, worktree, base SHA, commit, and ladder round
pre-warmed worktree/branch/provision state prepared ahead of dispatch
every finding: open | fixed | rejected | escalated | pre-existing
verification results and disclosed side effects
model chain index, resolved model (with fallback flag), reasoning effort, and usage by dispatch
quota resumeAt and chain index when an issue is quota-paused
```

Update it after every transition. On resume, reconcile it with Git branches,
worktrees, commits, and tracker state before dispatching anything.

## 3. Run the batch loop

Repeat until every issue is landed or explicitly blocked:

1. Compute the **frontier** from the ledger. Blockers land before dependents, so an
   issue whose blockers are landed and closed is unblocked and the frontier follows
   merge order.
2. Split the frontier into safe waves. Only issues with disjoint predicted write-sets
   share a wave. Challenge unnecessary serialisation, but prefer a smaller safe wave
   over speculative concurrency.
3. For each issue in the wave, create a repository-local worktree and issue branch:
   `.worktrees/<batch-slug>-issue-<number>`. Ensure `.worktrees/` is ignored. Start
   every branch from the main head captured for that wave.
4. Provision each worktree independently: copy only required gitignored environment
   files, install dependencies from its lockfile, and isolate ports, databases,
   containers, and build caches. Fall back to a sequential wave when runtime state
   cannot be isolated.
5. Run the issue loop in [`references/ISSUE-LOOP.md`](references/ISSUE-LOOP.md).
   Independent issues may be in different issue-loop states concurrently. From the
   second issue on, the Spec reviewer receives the previously landed commits as
   integration context — the issue-level review is the land gate, so integration
   awareness lives there rather than in a separate final phase.
6. Land every passed issue one at a time. Verify its actual write-set, rebase its
   issue commit(s) onto the current main head, fast-forward main locally, then push.
   Each issue lands as one or more commits — never squash a reviewed issue into
   another's commit, never cherry-pick. Run the issue's affected checks plus the
   full test suite and typecheck/lint on the rebased result before pushing.
7. Remove the issue's worktree and branch immediately, mark it integrated, close it
   directly with a comment citing the landed SHA and the proof, and recompute the
   frontier.
8. A dispatch that fails with a usage/rate-limit error on every entry of its model
   chain is a quota failure, not a ladder event: mark the issue `quota-paused`,
   record `resumeAt` from the error's retry/reset hint when present and the chain
   index, and continue. Never spend a fix round or an escalation on a quota
   failure, and never redeem Codex usage-limit reset coupons to reopen a reached
   limit — wait for the usage windows to replenish and resume then.

Before each rebase, use `git merge-tree` when available. An unexpected conflict means
the schedule or issue boundary was wrong: record it and stop for the user rather than
guessing at intent. Other independent issue loops may finish first. If main moved
underneath a pending issue, rebase onto the new head and re-verify; a conflicting
rebase is a stop, not a guess.

**Lookahead.** While an issue loop is dispatched and not yet returned, the orchestrator SHOULD use the idle wait to pre-warm the next scheduled wave: create its worktree(s) and issue branch(es) from the current main head, provision them, pre-fetch the next issues' text and comments, and draft their implementer briefs. Pre-warmed work must not be landed or rebased until its wave is dispatched; re-validate it against the main head at dispatch time and rebase/re-provision if the head moved.

**Quota-paused runs.** When no frontier work remains because every remaining issue is
`quota-paused`, the run has no safe frontier. Default: park the run and report the
pauses with their `resumeAt` estimates — the ledger is durable and the run ID is
stable, so re-invoking the skill resumes once the windows replenish naturally
(never by redeeming reset coupons). With `--wait-for-quota`, the orchestrator
instead sleeps in ≤1h cycles and re-attempts the
paused dispatches; a failed attempt is a cheap probe (fresh contexts, nothing lost).
A round ≥2 issue resumes by reviving its previous implementer peer via `hub` when
that peer still holds useful context; round 1 always re-dispatches fresh.

## 4. Close out the batch

When every issue is landed:

1. Run typechecking, linting, and the full test suite on the main head.
2. Prune stale worktrees and issue branches. Keep the ledger as the run record.
3. A landed commit that must come out is routine, not exceptional: `git revert`
   (never reset or force-push — main is public), record the revert SHA against the
   issue, reopen the issue with the reason, and re-land only after a fresh review.

## Stop conditions

Continue unrelated frontier work when one issue blocks. Stop and ask the user when no
safe frontier remains because of any of these:

- a product, schema, dependency, API, or test-seam decision is missing;
- an issue exhausts five fix rounds with an open blocking finding;
- tests fail for a cause the ladder could not resolve;
- an actual write-set escapes its declared boundary and invalidates active parallel
  work;
- integration conflicts or main moved underneath a pending issue in a way rebase
  cannot resolve;
- every remaining frontier issue is `quota-paused` (a usage window closed; see
  Quota-paused runs in section 3).

Report all blocked issues together with their evidence and the smallest decisions
needed to resume.

## Guardrails

- Fresh issue implementer; fresh, read-only reviewers. Never let an implementer review
  its own work or a reviewer edit it.
- The orchestrator owns Git and tracker writes — including push, revert, and issue
  close/reopen. Issue agents may inspect Git but may
  not add, commit, checkout, stash, rebase, merge, or reset.
- Pass artifacts and context pointers, not the orchestrator's reasoning. Premises are
  claims to verify, not facts to inherit.
- Never expose secrets in diffs, logs, reports, fixtures, or reviewer prompts.
- Never silently drop a finding, skip a failed check, close an issue before its
  commit lands, or rewrite tracker text from a lossy read path.
