---
name: git-workflow
description: Git workflow guidance with emphasis on committing pending changes in logical conventional-commit groups (feat/fix/chore with scopes). Use when committing work, splitting changes into commits, choosing merge vs rebase, or resolving conflicts.
---

# Git Workflow

Core recurring task: **commit pending changes in logical commit groups** using conventional commits (`feat(scope)`, `fix(scope)`, `chore(scope)`). Branching, merge/rebase, and conflict handling follow.

## Committing Pending Changes in Logical Groups

Before committing, run `git status` and `git diff` to see what's actually there. Group changes by *concern*, not by file count: each commit should be one reviewable, revertable unit.

**Process:**

1. **Inventory.** `git status --short` and skim diffs (`git diff`, `git diff --staged`).
2. **Partition.** Sort changes into groups that belong together: a new feature, a bug fix, dependency bumps, config/chore, docs, formatting. Unrelated changes never share a commit.
3. **Stage and commit each group separately.** Stage precisely, don't `git add .`:
   ```bash
   git add src/auth/login.ts src/auth/session.ts
   git commit -m "feat(auth): add session refresh on login"

   git add package.json package-lock.json
   git commit -m "chore(deps): bump zod to 3.23"
   ```
   Use `git add -p` to split hunks within a file when one file contains multiple concerns.
4. **Order matters.** Commit dependencies first: the type/interface change before the code using it, the fix before the test that covers it. Each commit should build and ideally pass on its own.
5. **Nothing left behind.** Afterward, `git status` should be clean or contain only intentionally uncommitted files (e.g. local `.env`).

**When in doubt about a group:** if you can't write one conventional-commit subject for it without "and", it's two commits.

## Conventional Commits

```
<type>(<scope>): <subject>

[optional body — explain why, not what]

[optional footer — Closes #123, BREAKING CHANGE: ...]
```

| Type | Use For | Example |
|------|---------|---------|
| `feat` | New feature | `feat(auth): add OAuth2 login` |
| `fix` | Bug fix | `fix(api): handle null response in user endpoint` |
| `docs` | Documentation | `docs(readme): update installation instructions` |
| `style` | Formatting, no code change | `style: fix indentation in login component` |
| `refactor` | Code refactoring | `refactor(db): extract connection pool to module` |
| `test` | Tests | `test(auth): add unit tests for token validation` |
| `chore` | Maintenance | `chore(deps): update dependencies` |
| `perf` | Performance | `perf(query): add index to users table` |
| `ci` | CI changes | `ci: add PostgreSQL service to test workflow` |
| `revert` | Revert | `revert: "feat(auth): add OAuth2 login"` |

Subject: imperative mood, no trailing period, ≤50 chars.

```bash
# BAD
git commit -m "fixed stuff"
git commit -m "updates"

# GOOD
git commit -m "fix(api): retry requests on 503 Service Unavailable

External API occasionally returns 503 during peak hours.
Added exponential backoff with max 3 attempts.

Closes #123"
```

## Merge vs Rebase

**Merge** — preserves exact history. Use for merging feature branches into `main`, or any branch others may have based work on.

**Rebase** — linear history. Use to update your *local, unpushed* feature branch onto latest `main`:

```bash
git checkout feature/user-auth
git fetch origin
git rebase origin/main        # resolve conflicts, tests must still pass
git push --force-with-lease origin feature/user-auth  # only if branch is yours
```

**Never rebase** pushed/shared branches, `main`, or merged branches — it rewrites history and breaks everyone else. Use `git revert` for public mistakes. Always prefer `--force-with-lease` over `--force`.

## Conflict Resolution

```bash
git status                          # see conflicted files
# Edit files: resolve <<<<<<< HEAD ... ======= ... >>>>>>> markers
git checkout --ours <file>          # or take one side wholesale
git checkout --theirs <file>
git add <file> && git commit        # complete the merge
```

Prevention: keep branches short-lived, rebase onto `main` frequently, coordinate before touching shared files.

## Branch Hygiene

```bash
git checkout -b feature/user-auth       # create from main
git branch --merged main | grep -v main | xargs -n 1 git branch -d   # cleanup merged
git fetch -p                            # prune deleted remote branches
```

Naming: `feature/<desc>`, `fix/<desc>`, `hotfix/<desc>`.

## Stash & Undo

```bash
git stash push -m "WIP: user auth"      # park work in progress
git stash pop                           # restore it

git reset --soft HEAD~1                 # undo last commit, keep changes staged
git commit --amend -m "fix(auth): corrected message"   # fix last message
git add forgotten-file && git commit --amend --no-edit # add forgotten file
git revert HEAD                         # undo a pushed commit safely
```

## Anti-Patterns

- Committing everything with `git add .` instead of logical groups
- `"update"` / `"WIP"` messages — every commit gets `type(scope): subject`
- Committing `.env`, secrets, or generated files (`dist/`, `node_modules/`)
- Committing directly to `main`; giant 1000+ line PRs
- `git push --force` on shared branches
