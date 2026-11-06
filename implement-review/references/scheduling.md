# Scheduling: ownership, dependencies, and verification

## Choose ownership

Main implements and owns integration by default. It may keep the implementation itself or delegate substantial independent slices with explicit, disjoint write-sets. Helpers are optional; retained implementers and reviewers are allowed when their work remains useful. Main can also implement a slice while helpers edit other paths.

Use a lightweight sequence for one owner. Do not build a task table or DAG unless multiple owners create real coordination needs. For multiple owners, name concrete files to create/edit, compare write-sets, and dispatch only independent work concurrently. Add a dependency only when one task consumes an artifact another produces; preserve real serial dependencies rather than forcing equal critical paths or inventing waves.

Use isolated worktrees only when actual concurrent isolation is needed, such as overlapping writes that must proceed concurrently or competing implementations. See [integration.md](integration.md). Otherwise, prefer sequential in-place edits or disjoint in-place helper work, according to main's baseline policy.

## Verification queue

Main owns one explicit queue for commands sharing locks, build caches, ports, databases, or browser resources. Wait for the current owner to finish before launching another command that would queue on the same resource. Genuinely independent read-only checks may run concurrently.

Do not run broad builds, full suites, or visual verification while helpers are still editing. Main integrates completed work, runs focused proof, obtains one independent review of the complete candidate, batches important repairs, reruns affected focused proof, and asks the same reviewer to close repairs. Run relevant broad regression checks once the candidate and review repairs are stable. A late material edit reopens only the affected proof and review.

One complete review of the integrated change is the default, including when helpers contributed. Do not require a review per slice plus a redundant final review. Specialist review is for a concrete independent high-risk boundary or explicit request; a new reviewer is warranted only when the retained reviewer is unavailable, independence is compromised, scope materially expands, progress stalls, or the user requests a fresh audit.

## Evidence

Tie each check to the production, test, configuration, toolchain, and generated-asset inputs it actually covers. A material input change invalidates relevant proof; unrelated changes do not. Respect runner validity flags and do not present drifted or invalid runs as valid. Existing repo fixtures and suites are allowed. For manual UI verification use Orca's embedded browser via its session-resolved CLI; follow the core skill and `skill://orca-cli` for setup, pinned-page ownership, and cleanup.

## Boundaries

No implicit commits or other git mutations. Commit, rebase, merge, branch/worktree cleanup, or other repository-state changes require user request/authorization. Protect existing dirty user state according to the main agent's explicit baseline policy; a dirty tree is not an unconditional stop.

Risk changes the expertise and focused checks selected, not the amount of orchestration by itself. Use full orchestration only for substantial independently-owned cross-system contracts requiring dedicated coordination, necessary competing implementations/isolation, or explicit user request. Preserve actual dependencies and shared-resource serialization; do not manufacture workflow stages for a single owner.
