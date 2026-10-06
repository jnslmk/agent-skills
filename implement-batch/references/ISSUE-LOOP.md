# Issue loop

This is the inner loop run independently for every issue scheduled by
`/implement-batch`:

```text
fresh implementer -> two-axis review -> fix ladder -> verified issue commit
```

The batch orchestrator owns the loop, the ledger, Git, and tracker writes. The issue
implementer owns only its declared files. Reviewers own no files.

Apply the exact model and reasoning allocation in
[`MODEL-POLICY.md`](MODEL-POLICY.md) to every dispatch.

## 1. Dispatch a fresh implementer

By default, dispatch a fresh `batch-implementer` (MODEL-POLICY initial row:
primary `muse-spark-1.3-contributor` on the Go pot, `gpt-5.6-terra` as first
fallback). An issue touching authentication/authorization, cryptography, money,
irreversible migration, concurrency, or a compatibility-critical public API
dispatches `batch-implementer-hard` (Terra/high primary) instead. Apply the
dispatch table in [`MODEL-POLICY.md`](MODEL-POLICY.md); the harness applies each
agent's own model chain. Use no inherited
conversation history. Give it only:

- the issue text and comments verbatim;
- a pointer to the parent spec;
- the issue's hard write-set and worktree;
- interfaces, domain docs, ADRs, and pre-agreed test seams it must respect;
- targeted test, typecheck, lint, and full-suite commands;
- a path under the run directory for its report.

State uncertain diagnoses as claims it must verify. Do not send the batch plan, other
issues, prior agents' reasoning, or unrelated session history.

The implementer follows the `/implement` engineering contract:

1. Use `/tdd` at the pre-agreed public seams.
2. Work in vertical red -> green slices: one failing behavioural test, then the
   smallest implementation that passes it.
3. Run the relevant single test file and typechecking regularly.
4. After the slices, address review-driven refactoring rather than speculative cleanup.
5. Run lint and the full test suite once before asking for review.

It must not commit. Its report lists files changed, commands and results, deviations,
side effects, and relevant problems it deliberately left outside its boundary.

If implementation requires a file, interface, dependency, or decision outside the
brief, stop that issue and return the exact boundary change needed. The agent does not
expand its own scope.

## 2. Materialise the artifact

Verify that every changed and created path is inside the declared write-set. In the
isolated issue worktree, the orchestrator may use intent-to-add for new files so the
review diff includes them. Write the complete binary-safe diff against the issue's
pinned base SHA to the run directory, plus a pinned source-pack listing the exact
file paths and line ranges the reviewers must cite from (issue text, parent spec
excerpt, CONTEXT.md/ADR excerpts or paths). This diff plus source-pack is one shared
context bundle per issue loop; both reviewers receive the same bundle paths.

Never rely on the implementer's summary as the review artifact. Give reviewers the
bundle and repository. Include the report only for empirical work the diff cannot show,
such as a manual protocol check, and strip reasoning and secrets.

An out-of-bound write fails the issue loop. Record declared and actual write-sets and
return control to the batch scheduler.

## 3. Run independent two-axis review

Dispatch two fresh read-only reviewers in parallel with no inherited conversation
history: `batch-standards-reviewer` and `batch-spec-reviewer` (MODEL-POLICY
dispatch table). Their agent definitions carry no Edit/Write tools, so file edits
and Git writes are structurally impossible; their briefs still forbid commands
with side effects. Both apply the `/code-review` protocol to the materialised
diff:

- **Standards reviewer**: `batch-standards-reviewer` (Luna/high chain); repository
  standards plus `/code-review`'s smell baseline.
- **Spec reviewer**: `batch-spec-reviewer` (Terra/high chain); the issue, its
  parent spec, and acceptance criteria.

Neither reviewer sees the implementer's reasoning, the other review, or the batch
session. Both reviewers work from the shared bundle: cite `file:line` from its pinned
sources, and re-read the live repo only to confirm a cited line in its surrounding
context — never to rediscover inputs (no fresh `git diff`, no re-reading whole
CONTEXT.md/ADRs the bundle already pins). Same inputs, no shared reasoning.
Verification must be read-only and must disclose any accidental side effect. Initial
and re-review briefs must both forbid memory writes of any kind — no saved
observations, session summaries, or memory-context updates, whatever the harness names
them. Review context is ephemeral by design (fresh reviewers each round) and the ledger
is the durable memory; reviewer memory writes duplicate the ledger, leak one issue's
reasoning into unrelated future reviews, and cost dispatches. On
re-review, give each reviewer the refreshed shared bundle (current diff plus unchanged
source-pack) and anonymized open important findings from its own axis only.

Each finding needs a source `file:line` citation and one tier:

- `important`: incorrect behaviour, missing requirement, scope-breaking addition,
  failing test, resource/security problem, or documented-standard violation;
- `nit`: non-blocking cleanup or judgement-call smell;
- `pre-existing`: real but not introduced by this issue.

Keep the Standards and Spec reports separate. The issue passes only when both have no
important findings. Record nits and pre-existing findings even though they do not
block.

## 4. Climb the fix ladder

For every open important finding:

| Round | Action |
|---|---|
| 1-3 | Resume the same issue implementer at its original model and effort. |
| 4 | Dispatch a fresh `batch-escalator` (Sol/high chain) with the issue, current diff, and open findings. |
| 5 | Dispatch a fresh `batch-escalator-xhigh` (Sol/xhigh chain) with the issue, current diff, and open findings. |
| After 5 | Stop the issue, record a ruling for every open finding, and return it blocked to the batch loop. |

On round 1, the implementer may also fix nits. From round 2 onward, send and report
important findings only; preserve unfixed nits in the ledger.

The implementer must answer every supplied finding by either fixing it or rejecting it
with technical evidence and a `file:line` citation. A rejection goes to a fresh `batch-adjudicator` (Terra/high chain) that receives the
finding and rebuttal as anonymous peer artifacts. Dispatch `batch-escalator` (Sol/high
chain) instead for security, data-loss, or public-contract disputes.
The adjudicator reads the code and rules `finding stands`, `rebuttal stands`, or
`both partly right`; record the ruling before continuing.

**Quota failures are not ladder events.** If every entry of the dispatched model
chain fails with a usage/rate-limit error, stop that issue as `quota-paused`
(record `resumeAt` from the error hint when present and the chain index) and
return it to the batch loop. Do not escalate, do not burn a round, and never
redeem Codex usage-limit reset coupons to reopen the window — wait for it to
replenish. On resumption after the window opens: round 1 re-dispatches fresh;
rounds ≥2 revive
the previous implementer peer via `hub` (it holds the issue context) and continue
from its last report.

After every fix:

1. rerun affected focused tests and typechecking;
2. rerun lint and the full suite when the change can affect other seams;
3. rematerialise the complete diff;
4. dispatch fresh two-axis reviewers;
5. update every finding's disposition and the round counter.

A fresh review may report a new important finding only when the latest fix introduced
it or the previous review identifies a concrete omission. Late findings on unchanged
code require an explicit reviewer correction in the ledger.

## 5. Pass the issue back

When both review axes pass:

1. rerun the issue's promised verification if the last fix invalidated any result;
2. make one or more issue commits, each including the issue number; closure happens at land time, never in a commit message;
3. record the commit(s), final actual write-set, checks, review rounds, nits,
   pre-existing findings, and side effects;
4. return the issue branch to the batch loop for integration.

No finding disappears: each ends `fixed`, `rejected` with an adjudicated reason,
`escalated`, or `pre-existing`.
