# Integration: isolated worktrees

Use this reference only when actual concurrent isolation requires worktrees. Worktrees do not authorize commits, rebases, merges, or cleanup: perform those repository mutations only when the user explicitly requested and authorized them.

## Baseline and isolation

Follow the main agent's explicit repository baseline policy, preserving existing user changes. Do not assume a dirty tree is a stop condition or stash/reset user work. Record the chosen base and its commit when worktree coordination requires it; do not guess on resume.

Keep worktree metadata and paths within the repository's established convention. Never copy real `.env` files, credentials, secrets, or live data into a worktree. Configure each isolated environment with non-secret settings, separate data stores, ports, and runtime identities as needed. Install dependencies locally when required; do not share mutable dependency directories or build caches across concurrent worktrees. If safe runtime isolation cannot be established, use sequential in-place work.

## Runtime resources

Concurrent tasks that start services need distinct ports and isolated databases/schemas and container identities. Shared migrations, databases, ports, browser sessions, or mutable build caches require serialization through the main agent's verification queue. Do not launch multiple commands merely to wait on the same lock.

## Integration and cleanup

Main owns integration. Inspect conflicts and preserve user state; do not automatically merge, rebase, cherry-pick, delete branches/worktrees, or prune worktree metadata. Ask for authorization if integration or cleanup requires an unrequested git mutation. Do not alter an in-progress user rebase or resolve conflicts by guessing.

When resuming, reconcile recorded ownership and worktree state with the repository before acting. Cleanup is a repository mutation and remains subject to the same explicit authorization.
