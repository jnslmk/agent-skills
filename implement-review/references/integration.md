# Integration: worktrees and getting the work back

Applies to **mode D only**. Modes A, B, and C commit to the current branch as they go.

## 1. Before you create anything

Confirm the repository is in a state worth branching from:

```bash
git status --porcelain          # must be clean, or you branch from a mess
git rev-parse --abbrev-ref HEAD # this is your base branch
git --version                   # need 2.38+ for merge-tree --write-tree
```

A dirty working tree at the start is a stop-and-ask. Do not stash the user's work.

Record the base branch and its SHA in the ledger. Every rebase target below refers to
it, and a resumed run must not guess.

## 2. Creating worktrees

Use `.worktrees/<branch>` inside the repository. This keeps git metadata writes inside
the workspace and matches the convention already recorded in `~/.codex/AGENTS.md`.

```bash
mkdir -p .worktrees
git worktree add .worktrees/task-t2 -b task/t2 <base>
```

Add both to `.gitignore` if absent:

```
.worktrees/
.implement-review/
```

### The setup step everyone forgets

A fresh worktree contains only tracked files. It does **not** have:

- `.env`, `.env.local`, or any gitignored config — the implementer will fail in ways
  that look like code bugs
- `node_modules`, `venv`, `vendor`, or any installed dependencies
- build caches, generated clients, compiled protos

**You must provision each worktree before dispatching into it.** Concretely:

```bash
# copy gitignored config the project needs
for f in .env .env.local; do
  [ -f "$f" ] && cp "$f" ".worktrees/task-t2/$f"
done

# install dependencies IN the worktree — never symlink or share node_modules,
# because branches can carry different lockfiles
(cd .worktrees/task-t2 && <install command>)
```

Detect the install command from the lockfile present: `pnpm-lock.yaml` → `pnpm i`,
`package-lock.json` → `npm ci`, `yarn.lock` → `yarn`, `uv.lock` → `uv sync`,
`poetry.lock` → `poetry install`, `Cargo.lock` → nothing needed, `go.sum` → nothing
needed.

If dependency installation is slow enough to dominate the run, that is an argument for
mode B rather than an argument for skipping it.

In Claude Code specifically, a `.worktreeinclude` file at the repository root (gitignore
syntax) makes the harness copy listed gitignored files into every worktree it creates.
Prefer it when running there; it does not exist in the other three harnesses.

### Runtime collisions

If two tasks each need a running service, they need more than file isolation:

- **Ports**: assign each worktree a distinct port via its own `.env.local`.
- **Databases**: a shared database is not isolated. Two concurrent migrations against
  one database corrupt each other. Give each worktree its own database or schema, or
  drop to mode B.
- **Docker**: distinct `COMPOSE_PROJECT_NAME` per worktree, or containers and volumes
  collide.

If you cannot cleanly separate these, mode D is not buying you isolation. Use mode B.

## 3. Integrating

One branch at a time, rebasing each remaining branch onto what actually landed:

```bash
# check before you act
git merge-tree --write-tree --name-only HEAD task/t1 >/dev/null || echo "t1 conflicts"

git merge --ff-only task/t1

git rebase <base> task/t2          # t2 now sees t1
git merge --ff-only task/t2

git rebase <base> task/t3          # t3 sees t1 and t2
git merge --ff-only task/t3
```

`--ff-only` is deliberate: after the rebase the merge must be a fast-forward. If it is
not, something moved underneath you and you should stop rather than create a merge
commit you did not intend.

### Why not cherry-pick

Cherry-picking each branch's commits onto the base duplicates them under new SHAs and
discards the ancestry link, so the branch no longer shows as merged and a later
`git log --graph` misrepresents what happened. It also surfaces conflicts one commit
at a time rather than once per branch.

Cherry-pick is correct in exactly one case: **you raced several implementations of the
same task and are keeping the winner.** There, ancestry to the losing branches is
noise and picking the winning commits is precisely the intent.

### On conflict

**Stop. Hand it to the user.** Report which branches conflict and in which files.

Do not run `git rebase --abort` reflexively — if a rebase is already in progress when
you arrive, it may be one the user is mid-way through resolving, and aborting destroys
their work. Check `git status` for an in-progress rebase before touching anything.

Do not attempt an automatic resolution. A conflict between two agent-written branches
is exactly the situation where a plausible-looking merge is most likely to be wrong.

## 4. Cleanup

Immediately after a branch merges:

```bash
git worktree remove .worktrees/task-t2
git branch -d task/t2
```

Do not defer this to the end of the run. Worktrees are expensive on disk — a reported
case reached 9.82 GB in twenty minutes on a 2 GB codebase — and removal is slow
because it unlinks every file individually.

`git worktree remove` refuses if the worktree has uncommitted changes. That refusal is
information: something was left behind. Investigate rather than forcing it with `-f`.

At the end of the run:

```bash
git worktree prune
```

## 5. If the run is interrupted

Worktrees and branches survive. On resume, read the ledger, then reconcile against
reality:

```bash
git worktree list
git branch --list 'task/*'
```

Any branch whose ledger status is `merged` but which still exists was interrupted
mid-cleanup — verify it is actually an ancestor of the base branch before deleting:

```bash
git merge-base --is-ancestor task/t2 <base> && git branch -d task/t2
```
