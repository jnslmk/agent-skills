#!/usr/bin/env python3
"""Conservative upstream sync for the agent-skills repo.

For every entry in upstream.json with a pinned ``rev``:
  base            = upstream files at the pinned rev
  ours            = files on disk
  theirs          = upstream files at the newest fetched rev
  ours == base    -> fast-forward: copy theirs over, advance the pin
  otherwise       -> REFUSE, print the diff summary, leave the pin (fork)

Skills without a pinned rev (own:, anthropic:, plugin:) are reported, never touched.

Usage:
  python3 scripts/sync.py            # fetch + report (no changes)
  python3 scripts/sync.py --apply    # fast-forward pristine skills
  python3 scripts/sync.py --apply tdd retro  # only these skills

Mirrors live in ~/.cache/agent-skills-mirrors/ (gitignored, refetchable).
"""
import json, os, shutil, subprocess, sys, hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
MIRRORS = Path.home() / ".cache" / "agent-skills-mirrors"
MANIFEST = HERE / "upstream.json"


def sh(*a, cwd=None):
    return subprocess.run(a, capture_output=True, text=True, cwd=cwd).stdout.strip()


def ensure_mirror(url):
    MIRRORS.mkdir(parents=True, exist_ok=True)
    name = url.rstrip("/").rstrip(".git").rsplit("/", 2)[-2:]
    d = MIRRORS / "__".join(name)
    if not (d / ".git").exists():
        print(f"cloning {url} ...")
        sh("git", "clone", "-q", "--filter=blob:none", url, str(d))
    sh("git", "-C", str(d), "fetch", "-q", "origin")
    return d


def head_rev(d):
    return sh("git", "-C", str(d), "rev-parse", "origin/HEAD") or \
        sh("git", "-C", str(d), "rev-parse", "origin/main") or \
        sh("git", "-C", str(d), "rev-parse", "origin/master")


def tree_at(mirror, rev, sub):
    """relpath -> (git blob sha) for every file under sub at rev."""
    out, cur = {}, sub.rstrip("/")
    txt = sh("git", "-C", str(mirror), "ls-tree", "-r", rev, "--", cur)
    for line in txt.splitlines():
        meta, path = line.split("\t", 1)
        out[path[len(cur) + 1:]] = meta.split()[2]
    return out


def blob(mirror, rev, path):
    r = subprocess.run(["git", "-C", str(mirror), "show", f"{rev}:{path}"],
                       capture_output=True)
    return r.stdout if r.returncode == 0 else None


def dump_tree(mirror, rev, sub, dest):
    """Materialize upstream tree at rev/sub into dest/ (for fast-forward apply)."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for rel in tree_at(mirror, rev, sub):
        data = blob(mirror, rev, f"{sub.rstrip('/')}/{rel}")
        if data is None:
            continue
        p = dest / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)


def disk_files(d):
    return {str(p.relative_to(d)): p.read_bytes() for p in d.rglob("*") if p.is_file()}


def main():
    apply = "--apply" in sys.argv
    only = {a for a in sys.argv[1:] if not a.startswith("-")}
    man = json.loads(MANIFEST.read_text())
    mirrors = {}
    updated, refused, untouched, errors = [], [], [], []

    for name, e in sorted(man["skills"].items()):
        if only and name not in only:
            continue
        src = e.get("source", "")
        if not (src.startswith("github:") and e.get("rev")):
            untouched.append(name)
            continue
        owner_repo = src.split(":", 1)[1]
        url = f"https://github.com/{owner_repo}.git"
        try:
            m = mirrors.get(url) or ensure_mirror(url)
            mirrors[url] = m
            new = head_rev(m)
            base, theirs = tree_at(m, e["rev"], e["path"]), tree_at(m, new, e["path"])
            if not theirs:
                errors.append((name, f"path {e['path']} gone upstream"))
                continue
            local_dir = HERE / name
            ours = {k: hashlib.sha1(b"blob %d\0" % len(v) + v).hexdigest()
                    for k, v in disk_files(local_dir).items()}
            if set(ours) != set(base) or any(ours[k] != base[k] for k in base):
                changed = sorted(k for k in set(ours) | set(base)
                                 if ours.get(k) != base.get(k))[:6]
                refused.append((name, changed))
                continue
            if base == theirs:
                e["rev"], e["rev_date"] = new, sh(
                    "git", "-C", str(m), "log", "-1", "--format=%cs", new)
                man["skills"][name] = e
                updated.append((name, "rev-only (content identical)"))
                continue
            if apply:
                dump_tree(m, new, e["path"], local_dir)
                e["rev"], e["rev_date"] = new, sh(
                    "git", "-C", str(m), "log", "-1", "--format=%cs", new)
                man["skills"][name] = e
                updated.append((name, "fast-forwarded"))
            else:
                diff_n = len(set(theirs) ^ set(base)) + \
                    sum(1 for k in set(theirs) & set(base) if theirs[k] != base[k])
                updated.append((name, f"would fast-forward ({diff_n} files)"))
        except Exception as ex:  # noqa: BLE001 - report, keep going
            errors.append((name, str(ex)[:100]))

    if apply and updated:
        MANIFEST.write_text(json.dumps(man, indent=2, sort_keys=True) + "\n")

    print(f"{'DRY-RUN — use --apply to fast-forward' if not apply else 'APPLIED'}\n")
    for name, what in updated:
        print(f"  FF   {name:<32} {what}")
    for name, changed in refused:
        print(f"  KEEP {name:<32} locally diverged: {', '.join(changed)}")
    for name in untouched:
        print(f"  SKIP {name:<32} no upstream pin (own/proprietary/plugin)")
    for name, err in errors:
        print(f"  ERR  {name:<32} {err}")


if __name__ == "__main__":
    main()
