---
name: rtk
description: >
  Rust Token Killer — CLI proxy that filters/summarizes command output
  for 60-90% token savings. Rewrites bash commands transparently via
  the rtk OMP extension. Use `rtk gain` for savings stats, `rtk discover`
  for missed opportunities. Commands with rtk support include git, cargo,
  ls, find, grep, diff, test runners, linters, docker, kubectl, and more.
---

# RTK — Rust Token Killer

Token-optimized CLI proxy for LLM-invoked commands. All bash commands are transparently rewritten by the rtk extension — no manual `rtk` prefix needed.

## How it works

The rtk extension intercepts `bash` tool calls, runs `rtk rewrite <cmd>`, and replaces the command with the RTK-filtered version when a filter exists. The model sees the original intent; RTK compresses the output.

## Key commands (for the model — use directly, they'll be rewritten)

```
git status           → rtk git status      (compact diff stats)
ls -la               → rtk ls -la           (compact listing)
cat <file>           → rtk read <file>      (intelligent filtering)
find . -name "*.ts"  → rtk find <args>      (compact tree)
grep -r "foo" .      → rtk grep <args>      (grouped by file)
cargo test           → rtk cargo test       (failures only)
ruff check .         → rtk ruff check       (grouped rules)
docker ps            → rtk docker ps        (no ASCII art)
kubectl get pods     → rtk kubectl ...      (compact tables)
```

## Meta commands (use `rtk` directly — not rewritten)

- `rtk gain` — Show token savings analytics since last reset
- `rtk gain --graph` — ASCII graph of daily savings
- `rtk gain --history` — Recent command history with savings
- `rtk discover` — Analyze command history for missed RTK opportunities
- `rtk config` — Show or create configuration

## Configuration

Config file: `~/.config/rtk/config.toml`
RTK extension: `~/.omp/agent/extensions/rtk.ts` (auto-loaded by OMP)

Set `RTK_DISABLED=1` to temporarily disable rewriting.
