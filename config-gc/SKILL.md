---
name: config-gc
description: Garbage collection for the omp config surface. Scans ~/.agents/skills/, ~/.omp/ (config leftovers, hooks, MCP entries, caches) and legacy ~/.config/opencode for redundant, stale, orphaned, or low-value items, then walks the user through a confirm-each-deletion cleanup. Use when the user says "clean up my config", "config GC", "too many skills", "audit my setup", "my config is bloated", or asks for a periodic config review.
---

# Config GC — Garbage Collection for the omp Setup

Borrowed from runtime garbage collection: periodically scan for objects that are no longer referenced, redundant, expired, or low-value, and reclaim the space. The critical difference: **here, collection requires a human in the loop. Never delete autonomously.** Until the user approves items one by one, a GC run is report-only.

## When to Activate

- The user asks to clean up, audit, or slim down their agent configuration
- The user complains about too many skills, noisy output, or slow session startup
- A monthly/periodic config review is due
- After installing a large skill pack, to reconcile overlaps with the existing setup

Do NOT activate for: cleaning project source code (that's refactoring), clearing chat history, or uninstalling omp itself.

## Design Philosophy

1. **Append-only configs leak.** Skills, MCP entries, and cache dirs only ever get added. Without periodic review they rot silently.
2. **Regular audits beat one-time purges.** Scan every ~30 days, propose a small batch of candidates each time.
3. **Per-channel strategies.** Each accumulation type (skills, MCP, caches, ...) has its own staleness signals — don't apply one rule everywhere.
4. **Soft-delete first.** Rename to `.disabled` > move to `~/.omp/_gc_trash/<date>/` > real deletion. Always keep an undo path.
5. **Forced human-in-the-loop.** Every candidate gets its own `[y/n/skip]` confirmation. No "yes to all" shortcut.
6. **Keep a log.** Every GC run appends to `~/.omp/gc_log.md`: what was touched, why, and how to undo it.

## Scan Channels

| # | Channel | Path | Staleness / redundancy signals |
|---|---------|------|--------------------------------|
| 1 | Skills (managed) | `~/.agents/skills/*/` | Overlapping names/descriptions (two skills firing on the same trigger); SKILL.md missing frontmatter, `name` ≠ directory name, or empty description; dead references (SKILL.md linking files that don't exist); empty or broken SKILL.md |
| 2 | Skills (harness copy) | `~/.omp/agent/skills/`, `~/.omp/agent/skills.disabled/` | Copies duplicating `~/.agents/skills/` entries; disabled leftovers already superseded by the managed set |
| 3 | Hooks | `~/.omp/hooks/pre/`, `~/.omp/hooks/post/` | Scripts on disk referenced by no config; config entries pointing at missing scripts; old versions superseded by rewrites |
| 4 | MCP servers | `~/.omp/agent/mcp.json` (`mcpServers`) | Servers that fail to connect; entries for servers no longer running/installed; functional duplicates |
| 5 | Legacy surface | `~/.config/opencode/`, `~/.cache/opencode/` | Anything remaining mid-migration to `~/.omp/` + `~/.agents/`; the cache (currently ~1.2 GB) is the single biggest reclaim candidate |
| 6 | Runtime caches | `~/.omp/logs/`, `~/.omp/agent/webcache/`, `~/.omp/agent/blobs/`, `~/.omp/cache/` | Sort by size and mtime; propose items >30 days old and large (logs past a few rotations, orphaned webcache/blob entries) |

## Workflow

1. **Dry-run scan** all channels (or the subset the user names). Collect candidates with: path, channel, signal that flagged it, size, last-modified. **No mutation in this step.**
2. **Rank** by confidence (broken/orphaned = high; merely old = low) and present as a numbered table. Cap each run at ~20 candidates — GC is periodic, not exhaustive. Still report-only.
3. **Confirm one by one.** For each candidate show the evidence, then ask `[y/n/skip]`. The user can stop at any point. Only now do deletions happen.
4. **Soft-delete confirmed items**: prefer `.disabled` rename for skills and `_gc_trash/<date>/` move for files. `mcp.json` is JSON (no comments possible): back up the file, record each removed server entry verbatim in `gc_log.md`, then remove it with `jq`. Only hard-delete when the user explicitly asks.
5. **Log** the run to `~/.omp/gc_log.md`: timestamp, items actioned, undo instructions.
6. **Report**: reclaimed size, channels still healthy, suggested next review date.

## Example Scan Commands

Frontmatter sweep (channel 1) — every skill needs frontmatter, `name` matching its directory, and a non-empty description:

```bash
for d in ~/.agents/skills/*/; do
  name=$(basename "$d"); f="$d/SKILL.md"
  [ -s "$f" ] || { echo "BROKEN: $f (missing/empty)"; continue; }
  grep -q '^---' "$f" || { echo "NO-FRONTMATTER: $f"; continue; }
  grep -q "^name: $name\$" "$f" || echo "NAME-MISMATCH: $f"
  grep -q '^description: .\+' "$f" || echo "EMPTY-DESCRIPTION: $f"
done
```

Overlapping skills (channel 1) — trigger phrases appearing in multiple descriptions:

```bash
grep -h '^description:' ~/.agents/skills/*/SKILL.md \
  | tr '[:upper:]' '[:lower:]' | grep -oE '"[^"]+"|[a-z]+ my [a-z]+' | sort | uniq -c | sort -rn | head
```

Orphaned hook scripts (channel 3) — scripts on disk that no config references:

```bash
for f in ~/.omp/hooks/pre/* ~/.omp/hooks/post/*; do
  [ -e "$f" ] || continue
  grep -rq "$(basename "$f")" ~/.omp/agent/config.yml ~/.omp/agent/*.yml 2>/dev/null \
    || echo "ORPHAN: $f"
done
```

Stale caches (channel 6):

```bash
du -sh ~/.omp/logs ~/.omp/agent/webcache ~/.omp/agent/blobs ~/.omp/cache 2>/dev/null
find ~/.omp/logs -type f -mtime +30 -exec du -k {} + 2>/dev/null | sort -rn | head -20
```

Soft-delete with undo path (capture the date once so the log can't disagree with the directory):

```bash
gc_date=$(date +%Y-%m-%d)
mkdir -p ~/.omp/_gc_trash/$gc_date
mv ~/.agents/skills/dead-skill ~/.omp/_gc_trash/$gc_date/
echo "$(date -Iseconds) moved skills/dead-skill -> _gc_trash/$gc_date/ (undo: mv back)" >> ~/.omp/gc_log.md
```

Removing a confirmed-dead MCP server (JSON has no comments — back up, log, then edit):

```bash
cp ~/.omp/agent/mcp.json ~/.omp/agent/mcp.json.bak
echo "$(date -Iseconds) removed mcpServers entry: <server> (undo: restore from .bak or re-add)" >> ~/.omp/gc_log.md
jq 'del(.mcpServers.<server>)' ~/.omp/agent/mcp.json.bak > ~/.omp/agent/mcp.json
```

## Anti-Patterns

- **Bulk approval.** Asking "delete all 15? [y/n]" defeats the design. One item, one decision.
- **Hard-deleting on first pass.** If there's no `_gc_trash/` copy or `.disabled` rename, you did it wrong.
- **Treating "old" as "dead".** A skill untouched for 60 days may be seasonal. Age is a signal, not a verdict — that's why a human confirms.
- **Touching anything outside the config surface.** GC covers `~/.agents/`, `~/.omp/`, `~/.config/opencode/`, `~/.cache/opencode/` — never project trees or dotfiles unrelated to the agent setup.
- **Deleting a duplicate skill copy without checking which one loads.** Confirm which skills directory omp actually reads for the entry in question before removing either copy.

## Best Practices

- Run after big additions, not just on a calendar: installing a 50-skill pack is exactly when overlap with existing skills appears.
- When two skills overlap, prefer disabling the one with the weaker trigger description — it's the one that was probably never firing anyway.
- The legacy cleanup (`~/.config/opencode`, `~/.cache/opencode`) is the highest-value channel per minute spent: 1+ GB reclaim and zero ambiguity once migration is confirmed complete.
- Keep `gc_log.md` forever. It's tiny, and "when did I disable that and why" comes up more often than you'd think.
