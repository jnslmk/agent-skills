#!/usr/bin/env python3
"""Conservative upstream sync: fast-forward pristine skills, never overwrite forks.

python3 scripts/sync.py                    # fetch + report, no writes
python3 scripts/sync.py --apply [skills]    # apply pristine updates
python3 scripts/sync.py --renovate          # materialize working manifest's pins
python3 scripts/sync.py --check --base-ref origin/main  # read-only PR pin gate

Renovate's old pins come from HEAD:upstream.json, not its modified working copy.
Failed candidates retain their old rev and record candidate_rev for manual review.
Mirrors are refetchable, under ~/.cache/agent-skills-mirrors/.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile

HERE = Path(os.environ.get("AGENT_SKILLS_ROOT", Path(__file__).resolve().parent.parent))
MIRRORS = Path.home() / ".cache" / "agent-skills-mirrors"
MANIFEST = HERE / "upstream.json"


def sh(*args, cwd=None):
    result = subprocess.run(args, capture_output=True, text=True, cwd=cwd)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"command failed: {args[0]}")
    return result.stdout.strip()


def safe_path(value):
    """Reject paths that can escape the selected upstream skill or local root."""
    if (not isinstance(value, str) or not value or "\\" in value or
            "\0" in value or value.startswith("/") or
            any(part in ("", ".", "..", ".git") for part in value.split("/"))):
        raise ValueError(f"unsafe path: {value!r}")
    return PurePosixPath(value)


def validate_entry(name, entry):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", name) or name == "scripts":
        raise ValueError(f"unsafe skill name: {name!r}")
    source = entry.get("source", "")
    if not re.fullmatch(r"github:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", source):
        raise ValueError(f"invalid GitHub source: {source!r}")
    if any(part in (".", "..") for part in source[7:].split("/")):
        raise ValueError(f"invalid GitHub source: {source!r}")
    safe_path(entry["path"])
    if not re.fullmatch(r"[0-9a-f]{40}", entry.get("rev", "")):
        raise ValueError(f"invalid commit pin for {name}")
    dest = HERE / name
    if dest.is_symlink():
        raise ValueError(f"symlinked skill directory: {name}")
    return dest


def ensure_mirror(url):
    MIRRORS.mkdir(parents=True, exist_ok=True)
    name = url.removesuffix(".git").rsplit("/", 2)[-2:]
    mirror = MIRRORS / "__".join(name)
    if not (mirror / ".git").exists():
        print(f"cloning {url} ...")
        sh("git", "clone", "-q", "--filter=blob:none", "--", url, str(mirror))
    sh("git", "-C", str(mirror), "fetch", "-q", "origin")
    return mirror


def head_rev(mirror):
    for ref in ("origin/HEAD", "origin/main", "origin/master"):
        try:
            return sh("git", "-C", str(mirror), "rev-parse", "--verify", f"{ref}^{{commit}}")
        except RuntimeError:
            continue
    raise RuntimeError("no upstream default branch found")


def tree_at(mirror, rev, sub):
    """Relative path -> (git mode, blob SHA); reject unsupported upstream entries."""
    safe_path(sub)
    if not re.fullmatch(r"[0-9a-f]{40}", rev):
        raise ValueError("expected full commit SHA")
    sh("git", "-C", str(mirror), "rev-parse", "--verify", f"{rev}^{{commit}}")
    tree = {}
    result = sh("git", "-C", str(mirror), "ls-tree", "-rz", rev, "--", sub)
    for line in result.split("\0"):
        if not line:
            continue
        meta, path = line.split("\t", 1)
        mode, kind, sha = meta.split()
        if not path.startswith(sub + "/"):
            raise ValueError(f"not a skill directory: {sub}")
        rel = path[len(sub) + 1:]
        safe_path(rel)
        if kind != "blob" or mode not in ("100644", "100755"):
            raise ValueError(f"unsupported upstream file mode {mode}: {path}")
        tree[rel] = (mode, sha)
    if "SKILL.md" not in tree:
        raise ValueError(f"missing upstream skill at {rev}:{sub}")
    return tree


def blob(mirror, sha):
    result = subprocess.run(["git", "-C", str(mirror), "cat-file", "blob", sha],
                            capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace").strip())
    return result.stdout


def disk_tree(dest):
    if not dest.is_dir() or dest.is_symlink():
        raise ValueError(f"missing or symlinked local skill: {dest.name}")
    tree = {}
    for path in dest.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"local symlink: {path.relative_to(dest)}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError(f"unsupported local file: {path.relative_to(dest)}")
        data = path.read_bytes()
        sha = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
        mode = "100755" if path.stat().st_mode & 0o100 else "100644"
        tree[path.relative_to(dest).as_posix()] = (mode, sha)
    return tree


def dump_tree(mirror, tree, dest):
    """Stage every blob before replacing; roll back if the final rename fails."""
    with tempfile.TemporaryDirectory(prefix=".sync-", dir=dest.parent) as tmp:
        candidate = Path(tmp) / "candidate"
        candidate.mkdir()
        for rel, (mode, sha) in tree.items():
            path = candidate / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(blob(mirror, sha))
            path.chmod(0o755 if mode == "100755" else 0o644)
        backup = Path(tmp) / "previous"
        dest.rename(backup)
        try:
            candidate.rename(dest)
        except OSError:
            backup.rename(dest)
            raise


def manifest_at(ref):
    if not ref or ref.startswith("-") or not re.fullmatch(r"[A-Za-z0-9_./-]+", ref):
        raise ValueError("invalid base ref")
    return json.loads(sh("git", "show", f"{ref}:upstream.json", cwd=HERE))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--renovate", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--base-ref", default="origin/main")
    parser.add_argument("skills", nargs="*")
    args = parser.parse_args(argv)
    try:
        man = json.loads(MANIFEST.read_text())
        old = manifest_at("HEAD" if args.renovate else args.base_ref) if (args.renovate or args.check) else man
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERR manifest: {exc}", file=sys.stderr)
        return 1
    mirrors, updated, failures = {}, [], []
    for name, entry in sorted(man["skills"].items()):
        if args.skills and name not in args.skills:
            continue
        if not entry.get("source", "").startswith("github:"):
            if not args.renovate and not args.check:
                print(f"SKIP {name}: own/proprietary/plugin")
            continue
        previous = old["skills"].get(name, {})
        target = entry.get("rev")
        changed = target != previous.get("rev")
        try:
            dest = validate_entry(name, entry)
            if args.check and entry.get("candidate_rev"):
                raise ValueError(f"blocked candidate {entry['candidate_rev']}; merge upstream into the fork manually")
            if (args.renovate or args.check) and not changed:
                continue
            if args.renovate and any(entry.get(key) != previous.get(key) for key in ("source", "path")):
                raise ValueError("Renovate may only change commit pins, not source/path")
            url = f"https://github.com/{entry['source'][7:]}.git"
            mirror = mirrors.get(url)
            if mirror is None:
                mirror = ensure_mirror(url)
                mirrors[url] = mirror
            if not args.renovate and not args.check:
                target = head_rev(mirror)
            theirs = tree_at(mirror, target, entry["path"])
            ours = disk_tree(dest)
            if args.check:
                if ours != theirs:
                    raise ValueError("changed pin does not match vendored files (pin-only update or unresolved fork)")
                print(f"OK {name}: files match {target}")
                continue
            base = tree_at(mirror, previous["rev"], entry["path"])
            if ours != base:
                different = sorted(k for k in set(ours) | set(base) if ours.get(k) != base.get(k))
                raise ValueError(f"locally diverged; refusing overwrite: {', '.join(different[:6])}")
            date = sh("git", "-C", str(mirror), "show", "-s", "--format=%cs", target)
            if args.apply or args.renovate:
                if ours != theirs:
                    dump_tree(mirror, theirs, dest)
                entry["rev"], entry["rev_date"] = target, date
                entry.pop("candidate_rev", None)
            updated.append(name)
            print(f"FF {name}: {'applied' if args.apply or args.renovate else 'would update'} {target}")
        except (OSError, ValueError, KeyError, RuntimeError) as exc:
            failures.append(name)
            if args.renovate and changed and previous.get("rev"):
                entry["rev"] = previous["rev"]
                if "rev_date" in previous:
                    entry["rev_date"] = previous["rev_date"]
                else:
                    entry.pop("rev_date", None)
                # ponytail: candidate data gives failed post tasks a truthful, reviewable PR.
                entry["candidate_rev"] = target
            print(f"KEEP {name}: {exc}", file=sys.stderr)
    if (args.apply and updated) or (args.renovate and (updated or failures)):
        MANIFEST.write_text(json.dumps(man, indent=2, sort_keys=True) + "\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
