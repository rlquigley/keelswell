"""pr_diagram_check.py against scratch repositories: a pull request on the
fork needs a Diagrams: line in its body, and one on any other repository
passes."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
HOOK = TOOLS / "pr_diagram_check.py"


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


class TestPrDiagramCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.fork = self.tmp / "keelswell"
        self.instance = self.tmp / "instance"
        for path, url in ((self.fork, "git@github.com:someone/keelswell.git"),
                          (self.instance, "https://github.com/someone/instance.git")):
            path.mkdir()
            git(path, "init", "-q")
            git(path, "remote", "add", "origin", url)

    def run_hook(self, command, cwd=None):
        event = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd or self.fork)}
        p = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(event), capture_output=True,
                           text=True, env=dict(os.environ, CLAUDE_PROJECT_DIR=str(self.fork)))
        return p.returncode, p.stderr

    def assertDenied(self, command, cwd=None):
        code, err = self.run_hook(command, cwd)
        self.assertEqual(code, 2, err)
        self.assertIn("`Diagrams:` line", err)

    def assertAllowed(self, command, cwd=None):
        code, err = self.run_hook(command, cwd)
        self.assertEqual(code, 0, err)

    def test_a_fork_pr_with_no_diagrams_line_is_denied(self):
        self.assertDenied('gh pr create --title "T" --body "Summary"')

    def test_a_fork_pr_that_says_what_it_did_passes(self):
        for line in ("Diagrams: updated -- the detailed flow's step 4.5",
                     "Diagrams: no change -- tests only",
                     "- **Diagrams:** no change -- docs only"):
            with self.subTest(line):
                self.assertAllowed(f"gh pr create --title T --body \"$(cat <<'EOF'\nSummary\n\n{line}\nEOF\n)\"")

    def test_an_empty_diagrams_line_is_denied(self):
        self.assertDenied("gh pr create --title T --body \"$(cat <<'EOF'\nSummary\nDiagrams:\nEOF\n)\"")

    def test_the_alias_in_a_chain_is_read(self):
        self.assertDenied("git push -u origin b && gh pr new --title T --body x")

    def test_a_body_file_is_read(self):
        (self.fork / "body.md").write_text("Summary\n\nDiagrams: no change -- tests only\n")
        (self.fork / "bare.md").write_text("Summary\n")
        self.assertAllowed("gh pr create --title T --body-file body.md")
        self.assertDenied("gh pr create --title T --body-file bare.md")

    def test_a_body_on_stdin_is_read(self):
        self.assertAllowed("gh pr create --title T --body-file - <<'EOF'\nDiagrams: updated -- both\nEOF")

    def test_a_pr_on_another_repository_passes(self):
        self.assertAllowed(f"cd {self.instance} && gh pr create --title T --body x")
        self.assertAllowed("gh pr create --title T --body x", cwd=self.instance)
        self.assertAllowed("gh pr create --repo someone/instance --title T --body x")

    def test_a_pr_on_the_fork_is_checked_from_anywhere(self):
        self.assertDenied("gh pr create --repo someone/keelswell --title T --body x", cwd=self.instance)
        self.assertDenied(f"cd {self.fork} && gh pr create --title T --body x", cwd=self.instance)

    def test_text_that_names_gh_pr_create_is_not_a_call(self):
        self.assertAllowed("git commit -m \"$(cat <<'EOF'\nhook: gh pr create needs a line\n\n"
                           "gh pr create --title x\nEOF\n)\"")
        self.assertAllowed("echo 'gh pr create --title T'")
        self.assertAllowed("gh pr view 12")

    def test_the_fork_settings_register_it(self):
        settings = json.loads((TOOLS.parent / ".claude" / "settings.json").read_text())
        hooks = [h for e in settings["hooks"]["PreToolUse"] if e["matcher"] == "Bash" for h in e["hooks"]]
        self.assertIn(["${CLAUDE_PROJECT_DIR}/tools/pr_diagram_check.py"], [h.get("args") for h in hooks])


if __name__ == "__main__":
    unittest.main()
