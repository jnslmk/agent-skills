---
name: implement-review-auto
description: "Implementation-and-review requests: choose lightweight main-agent implementation or full implement-review orchestration after scoping risk; use before selecting the review workflow, including single tasks and task lists."
---

# Automatic implementation and review

Select the route yourself after initial scoping and before implementation. Ordinary work uses lightweight review; material risk or substantial integration uses full orchestration. Asking for review or invoking this router is not a request for the full route. Honour an explicitly requested full workflow.

## Select once, escalate when evidence changes

Read the affected flow and callers, identify acceptance criteria, and inspect existing check commands. Classify the behavior being changed, not the directory name or number of files. Record one line in session state: `route: lightweight|full — concrete reason` and the starting revision/pre-existing changes. Tell the user the choice in one sentence; do not ask them to choose when repository evidence settles it.

Choose **full** when any of these applies:

- Authentication, authorization, credential/secret handling, or security-boundary behavior changes.
- Concurrency, synchronization, shared mutable-state ownership, or resource-lifecycle changes with material race risk.
- Money, irreversible migration, destructive data transformation, or compatibility-sensitive public API changes.
- Substantial multi-owner integration: separate slices must agree on changing producer/consumer contracts or shared state, and no single owner can reviewably implement the combined behavior. Parallel helpers with fixed contracts do not by themselves qualify.
- The user explicitly requires the full orchestration workflow.

Otherwise choose **lightweight**, including bounded bug fixes, ordinary features, cosmetic/accessibility UI changes, documentation, and small task lists. Several files or a server endpoint alone do not make work high-risk. A cosmetic change on a login page is not an authentication change.

If scope is initially unclear, inspect the relevant code before deciding. If material risk still cannot be bounded, choose full and state the concrete uncertainty. Escalate from lightweight when a newly discovered trigger applies or repairs fail to converge; preserve findings, evidence and counters. Ask only for missing product decisions or a policy stop, not routine routing permission.

## Startup and snapshot-bound proof

When the repository provides `scripts/work_session.py`, follow its startup/baseline policy before editing and consult its `--help` for the current interface. Record session ownership, the exact committed or explicitly selected draft baseline, and whether another writer requires an isolated worktree. Relevant unfinished changes require a baseline decision; unrelated dirty files do not require stashing. Check target state again before integration and verify the combined candidate. Without a repository helper, use existing ownership/worktree conventions rather than inventing a registry per run.

Use the repository's canonical check/build commands and verification runner. Where `scripts/verify.py` supports `--record`, record each required check against its real inputs, including generated assets for browser proof. Share arriving evidence with active reviewers; only evidence matching the latest relevant inputs can support completion. Keep counters and findings compact; derive execution times, cleanup and snapshot validity from the runner's evidence rather than repeatedly transcribing them.

## Lightweight

1. **Implement in the main agent.** Keep its exploration and implementation context. Delegate genuinely independent slices only when useful; the main agent remains integration owner. Define checkable acceptance criteria without expanding the request.
2. **Verify before review.** Use existing cheap syntax/lint/format/type checks at the affected scope, then focused consumer-visible behavioral proof. UI changes require the actual surface. Use the repository's supported verification runner and isolated runtime; obey existing process ownership, expiry and locking rules. A broken probe is not a product defect.
3. **Independent review.** Dispatch one fresh read-only `ir-reviewer` (Sol/high, retaining the existing review model policy). Give it the original requirements, complete run-only diff, affected interfaces/callers, exact candidate identity and exercised evidence. Exclude implementer reasoning, prior verdicts and session history. Request spec compliance followed by correctness, boundaries, errors, resources and test relevance. Require reachable consumer impact and file:line evidence for blocking findings. Prohibit edits and unapproved runtime effects.
4. **Repair with retained context.** The main agent fixes supported in-scope Important findings in one batch and records a disposition for each. Park unrelated defects and surviving nits with reasons. Prove the repaired behavior and run affected checks; reserve broader regression verification for cross-cutting changes and the final relevant integration boundary. Never weaken acceptance or label stale evidence current.
5. **Focused re-review.** Use a fresh read-only reviewer with the repair diff, original requirements, neutral pending IDs/root causes, evidence, and enough original-change context to trace affected callers. Check closure and newly affected producer/consumer paths. Expand to whole-artifact review for cross-cutting changes or new evidence of wider impact; bounded repair does not automatically require another full audit. Genuine evidenced blockers on unchanged lines remain eligible.
6. **Complete the latest candidate.** No open Important findings; each finding disposed; relevant checks and behavioral proof pass; independent review covers the final semantic changes. An integrated multi-owner change needs one fresh combined-spec/integration review unless the initial complete-change reviewer already reviewed the actual combined candidate. Reconcile any hook/source changes with proof and review before reporting completion. Preserve unrelated user work and commit only when requested.

### Same repair limits, less bookkeeping

Before the first repair, read sections 1–3 of `../implement-review/references/adjudication.md`. Reuse its finding identities, product/harness counting, stagnation, extension and dispute policy: five ordinary product cycles; individually gated cycles 6–8; eight automatic maximum; two harness-only attempts. Do not increase/reset limits on escalation or resume.

Track lightweight counters, findings/dispositions and snapshot-bound proof in compact session state; no scheduling DAG, per-task ledgers, attribution snapshots or worktrees merely to satisfy this route. Isolation required by concurrent work or runtime safety still applies. Resuming main-agent implementation is appropriate while making verified progress; an unsuccessful approach requires a fresh implementer under the existing stagnation policy. Evidence-backed disputes use a fresh read-only adjudicator, not repeated reviewer votes.

### Bounded launch correction — both routes

A failed invocation is distinct from repairing source, assertions or fixtures. If a build/verification command uses invalid syntax, wrong cwd, or prints help without producing the required artifact, preserve the failed evidence and correct the invocation **once** using the repository's known canonical command. Record the command/cwd correction and verify actual artifacts/minimal execution before a full rerun. It consumes neither a product round nor a harness-source repair; a second unsuccessful correction for that same invocation blocks automatic retry. Never use this allowance for changed assertions, fixture edits, production changes, weakened acceptance, or repeating an unchanged failure.

The existing five ordinary/eight maximum product cycles and two harness-source repairs remain unchanged. Preserve the per-invocation correction count across resumes and route changes. This specific distinction governs both router-selected routes; all other adjudication safeguards remain authoritative.

## Full

Read `../implement-review/SKILL.md` and follow its existing model policy, scheduling, implementer/reviewer separation, verification and final integration gates, with this router's bounded launch-correction distinction. Its prohibition on main-agent implementation applies only after choosing full. Preserve an active run's existing baseline, findings and counters; a route change is not a new budget.

## Scope

This router selects the workflow and the bounded launch-correction policy; the authored full skill remains unchanged. Use `/skill:implement-review-auto` for explicit automatic selection. A direct invocation of the authored `/skill:implement-review` still loads its original full-workflow instructions. Repository helpers and guidance own concurrency, execution evidence and CI behavior.
