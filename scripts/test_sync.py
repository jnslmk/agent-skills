"""Run with python3 -m unittest discover -s scripts -p 'test_sync.py'."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import sync


class ConservativeSyncTest(unittest.TestCase):
    def test_exact_materialization_refusal_and_read_only_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, upstream = Path(tmp) / "local", Path(tmp) / "upstream"
            for repo in (root, upstream):
                repo.mkdir()
                self.git(repo, "init", "-q", "-b", "main")
                self.git(repo, "config", "user.email", "sync-test@example.invalid")
                self.git(repo, "config", "user.name", "Sync test")
            skill = upstream / "skills" / "demo"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("old skill\n")
            (skill / "obsolete.txt").write_text("remove me\n")
            self.git(upstream, "add", ".")
            self.git(upstream, "commit", "-qm", "old")
            old = self.git(upstream, "rev-parse", "HEAD")
            (skill / "SKILL.md").write_text("new skill\n")
            (skill / "obsolete.txt").unlink()
            (skill / "run.sh").write_text("#!/bin/sh\nexit 99\n")
            (skill / "run.sh").chmod(0o755)
            self.git(upstream, "add", ".")
            self.git(upstream, "commit", "-qm", "new")
            new = self.git(upstream, "rev-parse", "HEAD")
            manifest = root / "upstream.json"
            baseline = {"skills": {
                "demo": {"source": "github:example/skills", "path": "skills/demo",
                         "rev": old, "rev_date": "2000-01-01"},
                "own": {"source": "own:"},
                "proprietary": {"source": "anthropic:example/skills"},
            }}
            local = root / "demo"
            local.mkdir()
            (local / "SKILL.md").write_text("old skill\n")
            (local / "obsolete.txt").write_text("remove me\n")
            manifest.write_text(json.dumps(baseline))
            self.git(root, "add", ".")
            self.git(root, "commit", "-qm", "baseline")

            def candidate(rev=new):
                value = json.loads(json.dumps(baseline))
                value["skills"]["demo"]["rev"] = rev
                manifest.write_text(json.dumps(value))

            with patch.multiple(sync, HERE=root, MANIFEST=manifest), \
                    patch.object(sync, "ensure_mirror", return_value=upstream), \
                    contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                unchanged = manifest.read_bytes()
                self.assertEqual(sync.main(["--renovate"]), 0)
                self.assertEqual(manifest.read_bytes(), unchanged)
                candidate()
                self.assertEqual(sync.main(["--check", "--base-ref", "HEAD"]), 1)
                self.assertEqual(sync.main(["--renovate"]), 0)
                self.assertEqual((local / "SKILL.md").read_text(), "new skill\n")
                self.assertFalse((local / "obsolete.txt").exists())
                self.assertEqual((local / "run.sh").read_text(), "#!/bin/sh\nexit 99\n")
                self.assertTrue((local / "run.sh").stat().st_mode & 0o100)
                value = json.loads(manifest.read_text())
                self.assertEqual(value["skills"]["demo"]["rev"], new)
                self.assertEqual(value["skills"]["demo"]["rev_date"],
                                 self.git(upstream, "show", "-s", "--format=%cs", new))
                self.assertEqual(value["skills"]["own"], baseline["skills"]["own"])
                snapshot = manifest.read_bytes(), sync.disk_tree(local)
                self.assertEqual(sync.main(["--check", "--base-ref", "HEAD"]), 0)
                self.assertEqual((manifest.read_bytes(), sync.disk_tree(local)), snapshot)

                # Reset only the disposable test checkout, never the real skill store.
                (local / "SKILL.md").write_text("old skill\n")
                (local / "run.sh").unlink()
                (local / "obsolete.txt").write_text("remove me\n")
                candidate()
                with patch.object(sync, "blob", side_effect=RuntimeError("missing blob")):
                    self.assertEqual(sync.main(["--renovate"]), 1)
                self.assertEqual((local / "SKILL.md").read_text(), "old skill\n")
                self.assertEqual((local / "obsolete.txt").read_text(), "remove me\n")
                self.assertFalse((local / "run.sh").exists())
                self.assertEqual(json.loads(manifest.read_text())["skills"]["demo"]["rev"], old)
                self.assertEqual(sync.main(["--check", "--base-ref", "HEAD"]), 1)

                (local / "SKILL.md").write_text("local fork\n")
                candidate()
                before = sync.disk_tree(local)
                self.assertEqual(sync.main(["--renovate"]), 1)
                self.assertEqual(sync.disk_tree(local), before)
                refused = json.loads(manifest.read_text())["skills"]["demo"]
                self.assertEqual(refused["rev"], old)
                self.assertEqual(refused["rev_date"], "2000-01-01")
                self.assertEqual(refused["candidate_rev"], new)
                self.assertEqual(sync.main(["--check", "--base-ref", "HEAD"]), 1)
                candidate("f" * 40)
                self.assertEqual(sync.main(["--renovate"]), 1)
                self.assertEqual(sync.disk_tree(local), before)
                self.assertEqual(json.loads(manifest.read_text())["skills"]["demo"]["rev"], old)
                for path in ("../escape", "/escape", "skill/.git/config", "skill\\escape"):
                    with self.assertRaises(ValueError):
                        sync.tree_at(upstream, new, path)

    @staticmethod
    def git(repo, *args):
        return subprocess.run(["git", "-c", "core.hooksPath=/dev/null",
                               "-c", "commit.gpgsign=false", "-C", str(repo), *args],
                              check=True, capture_output=True, text=True).stdout.strip()


if __name__ == "__main__":
    unittest.main()
