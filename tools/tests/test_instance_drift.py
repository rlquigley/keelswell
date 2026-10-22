"""instance_drift.py against a scratch fork with history and scratch instances."""
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import instance_drift as d  # noqa: E402

MANIFEST = "modules:\n  - name: core\n  - name: keelswell\n    version: 0.8.0\nides:\n  - claude-code\n"


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True,
                   env=dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                            GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t"))


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.fork = self.tmp / "fork"
        write(self.fork / "skills/bmad-dev-wave/SKILL.md", "v1\n")
        write(self.fork / "skills/bmad-dev-wave/scripts/gate.py", "gate v1\n")
        write(self.fork / "skills/agent-ml/SKILL.md", "ml v1\n")
        write(self.fork / ".claude/agents/reviewer.md", "reviewer v1\n")
        git(self.fork, "init", "-q")
        git(self.fork, "add", ".")
        git(self.fork, "commit", "-q", "--no-verify", "-m", "v1")
        write(self.fork / "skills/bmad-dev-wave/SKILL.md", "v2\n")
        (self.fork / "skills/bmad-dev-wave/scripts/gate.py").unlink()
        write(self.fork / "skills/bmad-dev-wave/scripts/gate2.py", "gate v2\n")
        git(self.fork, "add", "-A")
        git(self.fork, "commit", "-q", "--no-verify", "-m", "v2")

    def instance(self, name, trees=(".claude/skills",)):
        """An instance holding the fork's current files in each tree."""
        inst = self.tmp / "Projects" / "personal" / name
        write(inst / "_bmad/_config/manifest.yaml", MANIFEST)
        for tree in trees:
            for f in (self.fork / "skills").rglob("*"):
                if f.is_file():
                    write(inst / tree / f.relative_to(self.fork / "skills"), f.read_text())
        write(inst / ".claude/agents/reviewer.md", (self.fork / ".claude/agents/reviewer.md").read_text())
        return inst

    def rows(self, inst):
        return {(r.status, r.tree, r.unit) for r in d.check(self.fork, inst)}


class TestCheck(Base):
    def test_an_instance_matching_the_fork_has_no_rows(self):
        self.assertEqual(self.rows(self.instance("same")), set())

    def test_an_older_fork_version_is_behind(self):
        inst = self.instance("old")
        write(inst / ".claude/skills/bmad-dev-wave/SKILL.md", "v1\n")
        self.assertEqual(self.rows(inst), {("behind", ".claude/skills", "bmad-dev-wave")})

    def test_a_file_the_fork_has_since_deleted_is_behind(self):
        inst = self.instance("stale")
        write(inst / ".claude/skills/bmad-dev-wave/scripts/gate.py", "gate v1\n")
        self.assertEqual(self.rows(inst), {("behind", ".claude/skills", "bmad-dev-wave")})

    def test_content_the_fork_never_had_is_drift(self):
        inst = self.instance("edited")
        write(inst / ".claude/skills/agent-ml/SKILL.md", "ml, edited by hand\n")
        write(inst / ".claude/skills/agent-ml/notes.md", "an instance-only file\n")
        rows = d.check(self.fork, inst)
        self.assertEqual({(r.status, r.unit) for r in rows}, {("drift", "agent-ml")})
        self.assertEqual(sorted(rows[0].files), ["SKILL.md", "notes.md"])

    def test_drift_outranks_behind_within_one_skill(self):
        inst = self.instance("both")
        write(inst / ".claude/skills/bmad-dev-wave/SKILL.md", "v1\n")
        write(inst / ".claude/skills/bmad-dev-wave/scripts/gate2.py", "patched\n")
        self.assertEqual(self.rows(inst), {("drift", ".claude/skills", "bmad-dev-wave")})

    def test_a_missing_skill_or_file_is_reported(self):
        inst = self.instance("partial")
        for f in (inst / ".claude/skills/agent-ml").iterdir():
            f.unlink()
        (inst / ".claude/skills/agent-ml").rmdir()
        (inst / ".claude/skills/bmad-dev-wave/scripts/gate2.py").unlink()
        self.assertEqual(self.rows(inst), {("missing", ".claude/skills", "agent-ml"),
                                           ("behind", ".claude/skills", "bmad-dev-wave")})

    def test_every_keelswell_tree_is_checked_and_agents_too(self):
        inst = self.instance("two-trees", trees=(".claude/skills", ".agents/skills"))
        write(inst / ".agents/skills/agent-ml/SKILL.md", "ml v1, cursor copy edited\n")
        write(inst / ".claude/agents/reviewer.md", "reviewer, edited\n")
        self.assertEqual(self.rows(inst), {("drift", ".agents/skills", "agent-ml"),
                                           ("drift", ".claude/agents", "reviewer.md")})

    def test_a_tree_without_the_wave_skills_is_not_a_keelswell_tree(self):
        inst = self.instance("other-agents-tree")
        write(inst / ".agents/skills/some-skill/SKILL.md", "not ours\n")
        self.assertEqual(self.rows(inst), set())

    def test_caches_are_ignored(self):
        inst = self.instance("cached")
        write(inst / ".claude/skills/bmad-dev-wave/scripts/__pycache__/gate2.cpython-312.pyc", "x")
        write(inst / ".claude/skills/bmad-dev-wave/.DS_Store", "x")
        self.assertEqual(self.rows(inst), set())


class TestDiscovery(Base):
    def test_finds_instances_by_their_manifest_and_skips_the_rest(self):
        a = self.instance("a")
        nested = self.tmp / "Projects/clients/acme/app"
        write(nested / "_bmad/_config/manifest.yaml", MANIFEST)
        write(self.tmp / "Projects/learning/plain/_bmad/_config/manifest.yaml",
              "modules:\n  - name: core\n")
        write(self.tmp / "Projects/_archive/2026/old/_bmad/_config/manifest.yaml", MANIFEST)
        write(self.tmp / "Projects/personal/a/.claude/worktrees/w/_bmad/_config/manifest.yaml", MANIFEST)
        fork_link = self.tmp / "Projects/personal/fork"
        fork_link.symlink_to(self.fork)
        write(self.fork / "_bmad/_config/manifest.yaml", MANIFEST)
        other_checkout = self.tmp / "Projects/personal/fork-main"
        git(self.fork, "worktree", "add", "-q", "--detach", str(other_checkout))
        write(other_checkout / "_bmad/_config/manifest.yaml", MANIFEST)
        found = d.discover(self.tmp / "Projects", self.fork)
        self.assertEqual(found, sorted([a.resolve(), nested.resolve()]))


class TestMain(Base):
    def test_exit_codes(self):
        same, old = self.instance("same"), self.instance("old")
        write(old / ".claude/skills/bmad-dev-wave/SKILL.md", "v1\n")
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(d.main(["--fork", str(self.fork), str(same)]), 0)
            self.assertEqual(d.main(["--fork", str(self.fork), str(old)]), 1)
        self.assertIn("behind   .claude/skills/bmad-dev-wave: SKILL.md", out.getvalue())


if __name__ == "__main__":
    unittest.main()
