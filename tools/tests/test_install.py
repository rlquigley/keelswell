"""install.sh on a scratch copy of the fork, with a stand-in `npx` on PATH.

PR 5 of docs/reviews/harness-review-v2.md: a re-install is refused (V2-16),
validate stops reading the template in place of an instance's settings
(V2-17) and reads each registration by structure (V2-39), a fresh target gets
a verify stub and a scanning gitleaks config (V2-40, V2-41), and a failed
upstream install fails the run (V2-42).

The stand-in writes the one manifest line the refusal reads and exits
$FAKE_NPX_EXIT. Everything else is the real installer, run from a copy: phases
2 and 3 write into the fork tree they run from.
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

FORK = Path(__file__).resolve().parents[2]

FAKE_NPX = """#!/usr/bin/env python3
import os, pathlib, sys
argv = sys.argv[1:]
d = pathlib.Path(argv[argv.index("--directory") + 1]) / "_bmad" / "_config"
d.mkdir(parents=True, exist_ok=True)
(d / "manifest.yaml").write_text("modules:\\n  - name: bmm\\n  - name: keelswell\\n")
sys.exit(int(os.environ.get("FAKE_NPX_EXIT", "0")))
"""

KEPT = (".claude/settings.local.json", "CLAUDE.md", "TODO.md", "HANDOFF.md")


class TestInstall(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.fork = cls.tmp / "fork"
        files = subprocess.run(["git", "-C", str(FORK), "ls-files", "-z", "-co", "--exclude-standard"],
                               check=True, capture_output=True, text=True).stdout.split("\0")
        for rel in filter(None, files):
            src = FORK / rel
            if src.is_file():
                dst = cls.fork / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        subprocess.run(["git", "init", "-q", str(cls.fork)], check=True)
        bin_dir = cls.tmp / "bin"
        bin_dir.mkdir()
        (bin_dir / "npx").write_text(FAKE_NPX)
        (bin_dir / "npx").chmod(0o755)
        cls.env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
        cls.installed = cls.tmp / "installed"
        code, out = cls.install(cls.installed)
        assert code == 0, out

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    @classmethod
    def run_sh(cls, *args, npx_exit=0):
        p = subprocess.run([str(cls.fork / "install.sh"), *args], cwd=str(cls.fork),
                           env={**cls.env, "FAKE_NPX_EXIT": str(npx_exit)},
                           capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr

    @classmethod
    def install(cls, target, *extra, npx_exit=0):
        return cls.run_sh("--use-defaults", "--yes", "--user-name", "rq", "--skip-mcp-check",
                          "--target-project", str(target), *extra, npx_exit=npx_exit)

    def copy(self):
        dst = Path(tempfile.mkdtemp(dir=self.tmp)) / "instance"
        shutil.copytree(self.installed, dst, symlinks=True)
        return dst

    def validate(self, target):
        return self.run_sh("--validate-only", "--skip-mcp-check", "--target-project", str(target))

    def settings(self, target):
        return json.loads((target / ".claude" / "settings.json").read_text())

    def write_settings(self, target, settings):
        (target / ".claude" / "settings.json").write_text(json.dumps(settings, indent=2))

    # -- install --

    def test_a_fresh_target_validates_and_has_the_stub_and_a_scanning_config(self):
        code, out = self.validate(self.installed)
        self.assertEqual(code, 0, out)
        stub = self.installed / "tests" / "verify-fast.sh"
        self.assertTrue(os.access(stub, os.X_OK))
        p = subprocess.run(["bash", str(stub)], capture_output=True, text=True)
        self.assertEqual(p.returncode, 1)
        self.assertIn("wire your suite here", p.stderr)
        self.assertRegex((self.installed / ".gitleaks.toml").read_text(),
                         r"(?m)^\[extend\]\nuseDefault = true$")

    def test_a_reinstall_is_refused_and_writes_nothing(self):
        target = self.copy()
        (target / "TODO.md").write_text("sentinel\n")
        code, out = self.install(target)
        self.assertEqual(code, 3, out)
        self.assertIn("--force-reinstall", out)
        self.assertEqual((target / "TODO.md").read_text(), "sentinel\n")

    def test_a_forced_reinstall_keeps_the_four_project_files(self):
        target = self.copy()
        for rel in KEPT:
            (target / rel).write_text(f"sentinel {rel}\n")
        code, out = self.install(target, "--force-reinstall")
        self.assertEqual(code, 0, out)
        for rel in KEPT:
            with self.subTest(rel):
                self.assertEqual((target / rel).read_text(), f"sentinel {rel}\n")

    def test_the_refusal_covers_the_fork_root(self):
        # The scratch fork's manifest names keelswell, as the real one does.
        code, out = self.run_sh("--use-defaults", "--yes", "--user-name", "rq", "--skip-mcp-check")
        self.assertEqual(code, 3, out)

    def test_a_failed_upstream_install_fails_the_run(self):
        target = self.tmp / "npx-fails"
        code, out = self.install(target, npx_exit=1)
        self.assertNotEqual(code, 0, out)
        self.assertFalse((target / "CLAUDE.md").exists())

    # -- validate --

    def test_an_instance_with_no_settings_fails(self):
        target = self.copy()
        (target / ".claude" / "settings.json").unlink()
        code, out = self.validate(target)
        self.assertEqual(code, 7, out)
        # Both checks read the missing file, not the template.
        self.assertNotIn("registration: templates/settings.json.template", out)
        self.assertIn(f"Permission rules in {target}/.claude/settings.json", out)

    def test_a_local_allow_that_covers_a_merge_warns_and_passes(self):  # V2-14
        target = self.copy()
        (target / ".claude" / "settings.local.json").write_text(json.dumps(
            {"permissions": {"allow": ["Bash(gh api *)", "Bash(gh pr:*)", "Bash(gh pr view *)"]}}))
        code, out = self.validate(target)
        self.assertEqual(code, 0, out)
        self.assertIn("WARN: settings.local.json allows Bash(gh api *), which covers a merge", out)
        self.assertIn("WARN: settings.local.json allows Bash(gh pr:*)", out)
        self.assertNotIn("allows Bash(gh pr view *)", out)
        code, out = self.validate(self.installed)
        self.assertNotIn("WARN", out)

    def test_the_fork_root_reads_the_template_not_its_own_settings(self):
        # The fork's settings.json registers its sessions' PR hook, not the wave hooks.
        self.assertTrue((self.fork / ".claude" / "settings.json").is_file())
        code, out = self.run_sh("--validate-only", "--skip-mcp-check")
        self.assertEqual(code, 0, out)
        self.assertIn("(registration: templates/settings.json.template)", out)
        self.assertIn("Permission rules in templates/settings.json.template", out)

    def test_each_registration_mutation_fails(self):
        def comment_kept(s):
            entry = s["hooks"]["PreToolUse"].pop(0)
            s["$comment"] = entry["hooks"][0]["command"]

        def narrowed(s):
            s["hooks"]["PreToolUse"][0]["matcher"] = "NotebookEdit"

        def moved(s):
            s["hooks"]["PostToolUse"].append(s["hooks"]["PreToolUse"].pop(0))

        def replaced(s):
            hook = s["hooks"]["PreToolUse"][0]["hooks"][0]
            hook["command"] = "true # " + hook["command"]

        def session_end_gone(s):
            del s["hooks"]["SessionEnd"]

        for mutate in (comment_kept, narrowed, moved, replaced, session_end_gone):
            with self.subTest(mutate.__name__):
                target = self.copy()
                settings = self.settings(target)
                mutate(settings)
                self.write_settings(target, settings)
                code, out = self.validate(target)
                self.assertEqual(code, 7, out)

    def test_a_relative_session_end_registration_fails(self):
        target = self.copy()
        settings = self.settings(target)
        settings["hooks"]["SessionEnd"][0]["hooks"][1]["command"] = ".claude/hooks/wave-session-end.sh"
        self.write_settings(target, settings)
        code, out = self.validate(target)
        self.assertEqual(code, 7, out)
        self.assertIn("wave-session-end.sh registered on SessionEnd '' ... FAIL", out)

    def test_a_gitleaks_config_without_extend_fails(self):
        target = self.copy()
        path = target / ".gitleaks.toml"
        path.write_text(path.read_text().replace("[extend]\nuseDefault = true\n", ""))
        code, out = self.validate(target)
        self.assertEqual(code, 7, out)
        self.assertIn("no [extend] useDefault = true", out)

    def test_a_missing_verify_stub_is_named(self):
        target = self.copy()
        (target / "tests" / "verify-fast.sh").unlink()
        code, out = self.validate(target)
        self.assertEqual(code, 0, out)
        self.assertIn("tests/verify-fast.sh is missing", out)


if __name__ == "__main__":
    unittest.main()
