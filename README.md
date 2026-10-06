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

## Hooks

`prek install` once per clone. Gitleaks blocks secrets; baseline (2026-10-06)
was clean. New skills: add an `upstream.json` entry (or `own:`), commit.
