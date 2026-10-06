# Agent skills

The working skill store — installed copies live in `~/.agents/skills` and this
repo tracks them. OMP discovers them flat (`<name>/SKILL.md`); do not nest.

## Layout

- `<skill>/` — one directory per skill, `SKILL.md` at its root.
- `upstream.json` — provenance per skill: `source`, `path` and pinned `rev` in
  the upstream repo, plus `license`. `own:` entries are yours; the script never
  touches them. `anthropic:` entries exist on disk but are gitignored — see below.
- `scripts/sync.py` — conservative upstream sync. Fast-forwards a skill only
  when the local copy still matches the pinned `rev`; forks are reported, never
  overwritten. Run `python3 scripts/sync.py` (dry-run) / `--apply` to write.

## What is (not) here

| Origin | Skills | License | Notes |
|---|---|---|---|
| `mattpocock/skills` | 33 (`tdd`, `code-review`, …) | MIT | fork: `ask-matt` mentions `/implement-batch` |
| `vercel-labs/skills` | 1 (`find-skills`) | MIT | |
| `pbakaus/impeccable` | 1 (`impeccable`) | Apache-2.0 | local copy adapted for this setup |
| `nextlevelbuilder/ui-ux-pro-max-skill` | 1 (`ui-ux-pro-max`) | MIT | base = `.claude/skills/ui-ux-pro-max` |
| own (`jnslmk/…`) | 14 + `implement-batch`, `implement-review`, `rtk` | MIT | homelab-*, nas-ops, config-gc, canary-watch, … |
| `anthropics/skills` | `docx`, `pdf`, `xlsx`, `frontend-design`, `mcp-builder`, `webapp-testing` — **not committed** | proprietary, no redistribution | stay on disk, update via the plugin checkout |

## Scheduled upstream updates

The `Renovate` workflow runs weekly (Monday 04:17 UTC) and can be started with
`workflow_dispatch`. It uses GitHub-hosted Ubuntu, Node 24 and pinned self-hosted
Renovate, with the repository's `GITHUB_TOKEN`; no PAT is needed. GitHub Actions
must be allowed to create pull requests in the repository's Actions settings.

Renovate scans only `upstream.json`, the root pre-commit config and our workflows,
not vendored example configs. It tracks `main` for pinned `github:` entries;
`own:`, `anthropic:` and plugin skills remain untouched. Hook, Actions and Renovate
version updates are also supported. **Nothing automerges.**

Each skill has its own upstream PR so a local fork cannot block other pristine
skills from the same repository. After Renovate proposes a SHA, its allowlisted
`python3 scripts/sync.py --renovate` command reads the old pin from Git's `HEAD`
and materializes the exact candidate only when local files and executable bits
match that old upstream tree. All blobs are staged before replacing the directory;
Git errors, missing paths, symlinks and unsafe paths fail closed. No upstream
scripts are run. Successful PRs include skill files, `rev` and `rev_date`.

On refusal, the skill files stay untouched, `rev`/`rev_date` remain at their old
baseline, and `candidate_rev` records the proposed SHA for review. Renovate reports
a post-upgrade failure; `Skills checks` also fails until the candidate is resolved.
Do not merge a failed or pin-only update. The scheduled workflow explicitly
dispatches checks on Renovate PR heads because PRs created with `GITHUB_TOKEN`
do not trigger GitHub's normal `pull_request` event. Checks use trusted main-branch
automation with read-only content access and permission to publish the dispatched
result as a `Skills checks` commit status on the exact PR SHA (dispatch-run checks
alone do not satisfy PR required checks). Only the non-mutating secret scanner
hook runs in CI; existing local commit hooks are unchanged.

### Manually merging a fork

For a blocked PR, inspect the upstream diff between the original `rev` and
`candidate_rev` at the entry's `path` (the fetched repositories are in
`~/.cache/agent-skills-mirrors/<owner>__<repo>`). Port the relevant changes into
the local skill while preserving its local edits; neither `--apply` nor
`--renovate` will overwrite a fork.

Keep the original `rev`/`rev_date` as the fork's upstream baseline, record the
manually integrated candidate SHA in the entry's `note`, and remove
`candidate_rev` once review is complete. Only advance `rev` automatically when
the files exactly match upstream. Re-run `Skills checks` on the PR branch before
merging. A fork remains conservative/manual on subsequent upstream updates.

Focused local behavior check (temporary local Git repositories, no network):

```sh
python3 -m unittest discover -s scripts -p 'test_sync.py'
```

Read-only PR pin validation (fetch the base branch first):

```sh
python3 scripts/sync.py --check --base-ref origin/main
```

## Hooks

`prek install` once per clone. Gitleaks blocks secrets; baseline (2026-10-06)
was clean. New skills: add an `upstream.json` entry (or `own:`), commit.

The normal staged-files Gitleaks hook stays unchanged. CI uses the separate
manual-stage `gitleaks-dir` alias to scan the checked-out directory, including
files that are not staged. It ignores candidate `.gitleaksignore` files; CI loads
the trusted main-branch default rules rather than candidate scanner configuration:

```sh
GITLEAKS_CONFIG="$PWD/.github/gitleaks.toml" prek run gitleaks-dir --hook-stage manual --all-files
```
