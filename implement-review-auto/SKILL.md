---
name: implement-review-auto
description: "Use when choosing an implementation-and-review workflow: default to main-agent implementation and one independent review; select orchestration only for concrete multi-owner coordination or explicit requests."
---

# Automatic implementation and review

Use `skill://implement-review` as the workflow authority: main-agent implementation,
one independent complete-change review, retained repair closure, and final relevant
regression verification. Invoking either skill does not implicitly request full
orchestration.

## Choose ownership, not ceremony

Scope the affected flow, acceptance criteria, and existing checks; record
`route: standard|orchestrated — concrete reason` in compact session state.

**Standard is the default**, including authentication, concurrency, background sync,
shared state, sensitive data, migrations, and public APIs when one integration owner
can manage the change. Risk selects suitable implementation/review expertise and
boundary/error/race checks, not more review stages. Delegate a sensitive slice when
needed. Main-agent implementation and substantial independent helpers can coexist
under declared disjoint write-sets.

Choose **orchestrated** only for:
- Substantial independently owned cross-system contracts requiring dedicated coordination.
- Competing implementations or isolation that genuinely requires separate worktrees.
- An explicit request for full orchestration, not merely for review or this skill.

Several files, an endpoint, a background worker, or a task list alone do not justify
orchestration. Parallel helpers with fixed contracts can use the standard path.
Inspect unclear scope first; escalate on concrete ownership/integration evidence,
preserving findings, proof, and counters. Ask only for missing product decisions or
a policy stop.

## Same lean loop on either route

1. Follow repository ownership/baseline rules and preserve user drafts. Define complete
   acceptance criteria and permitted verification effects.
2. Implement in the main agent; delegate substantial independent slices only when
   useful. Load scheduling/worktree references only for those branches.
3. Run cheap checks and focused actual-behavior proof before independent review.
4. Review the actual combined change once. Retain the independent read-only reviewer
   for focused closure; replacement requires escalation, scope, independence,
   availability, or an explicit request. Additional audits need core-policy justification.
5. Queue shared verification resources. Settle review-driven repairs, then run the
   required broader regression set on the stable candidate. Reopen affected proof
   and review after changes, honoring actual runner validity and relevant inputs.
6. Reconcile final evidence without reviving a reviewer solely because a broad check
   finished. Completion still requires no Important blockers, current relevant proof,
   actual-surface smoke, documentation, and owned-resource cleanup.

## Verification defaults

Use **Orca's embedded worktree-scoped browser via the Orca CLI** for manual web
verification. Read `skill://orca-cli`, resolve the session executable once, and load
its version-matched browser reference. Follow the core skill's pinned-page ownership,
preview expiry, resource queue, cleanup, and unavailable-tool rules. Do not silently
use the generic Eval browser/Chrome relay or a bespoke CDP/Playwright launcher instead.
Existing repository automated browser suites remain allowed and complement Orca smoke.

Use canonical runners and relevant-input evidence, including generated assets for
browser proof. Test formatting or docs-only edits do not semantically require
unrelated asset rebuilds; never override an invalid/stale runner result. Launch
commands sharing a workstation lock sequentially, not simultaneously to queue on it.

## Repair policy and compatibility

The core skill owns dispatched-agent models; `references/adjudication.md` owns repair
limits, IDs, stagnation, disputes, and the one bounded launch correction. Read that
reference before repair instead of maintaining a second policy copy here. Preserve
run identity and counters across route changes/resumption. Commit only when requested.
Do not require DAGs, per-task ledgers, worktrees, or a second integrated audit merely
because this router was invoked.
