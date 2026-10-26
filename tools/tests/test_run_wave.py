"""run_wave.py against a stand-in `claude` on PATH that records how it was called."""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_wave  # noqa: E402

FAKE = """#!/usr/bin/env python3
import json, os, sys
with open(os.environ["FAKE_CALL"], "w") as f:
    json.dump({"argv": sys.argv[1:], "cwd": os.getcwd()}, f)
print(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "working"}]}}))
print(json.dumps({"type": "result", "subtype": "success", "total_cost_usd": 1.25, "num_turns": 3,
                  "duration_ms": 60000, "result": "Halted at step 8: the evaluator returned NEEDS_WORK.",
                  "permission_denials": [{"tool_name": "Bash", "tool_input": {"command": "mkdir x"}}]}))
sys.exit(int(os.environ.get("FAKE_EXIT", "0")))
"""


class TestRunWave(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        (bin_dir / "claude").write_text(FAKE)
        (bin_dir / "claude").chmod(0o755)
        self.project = self.tmp / "ffbapp"
        self.project.mkdir()
        self.logs = self.tmp / "logs"
        self.call = self.tmp / "call.json"
        env = {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}", "FAKE_CALL": str(self.call)}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_it(self, *extra):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = run_wave.main([str(self.project), "7A", "--log-dir", str(self.logs), *extra])
        return code, out.getvalue(), json.loads(self.call.read_text())

    def opt(self, argv, name):
        return argv[argv.index(name) + 1]

    def test_runs_dev_wave_headless_in_the_project_and_stops_where_told(self):
        code, _, call = self.run_it("--through-step", "8")
        argv = call["argv"]
        self.assertEqual(code, 0)
        self.assertEqual(Path(call["cwd"]).resolve(), self.project.resolve())
        prompt = self.opt(argv, "-p")
        self.assertTrue(prompt.startswith("/bmad-dev-wave 7A\n"))
        self.assertIn("through step 8 and stop", prompt)
        self.assertIn("Do not merge", prompt)
        self.assertEqual(self.opt(argv, "--permission-mode"), "acceptEdits")
        self.assertEqual(self.opt(argv, "--output-format"), "stream-json")
        self.assertNotIn("--max-budget-usd", argv)

    def test_the_allowlist_covers_the_wave_and_takes_more(self):
        _, _, call = self.run_it("--allow", "Bash(npm *)")
        argv = call["argv"]
        allowed = argv[argv.index("--allowedTools") + 1:]
        for rule in ("Bash(python3 *)", "Bash(git *)", "Bash(gh *)", "Bash(rsync *)",
                     "Bash(npm *)"):
            self.assertIn(rule, allowed)

    def test_bash_is_not_allowed_and_merges_are_disallowed(self):  # V2-14
        _, _, call = self.run_it()
        argv = call["argv"]
        self.assertNotIn("Bash(bash *)", argv)
        flags = [j for j, a in enumerate(argv) if a.startswith("--")]
        start = argv.index("--disallowedTools") + 1
        end = min([j for j in flags if j >= start] or [len(argv)])
        self.assertEqual(argv[start:end], ["Bash(gh pr merge *)", "Bash(gh api *)"])

    def test_no_step_means_as_far_as_the_skill_goes(self):
        _, _, call = self.run_it()
        self.assertIn("as far as the skill goes", self.opt(call["argv"], "-p"))

    def test_resume_and_budget(self):
        _, _, call = self.run_it("--resume", "--max-budget-usd", "20")
        self.assertTrue(self.opt(call["argv"], "-p").startswith("/bmad-resume-wave 7A\n"))
        self.assertEqual(self.opt(call["argv"], "--max-budget-usd"), "20")

    def test_logs_the_stream_and_reports_where_it_stopped(self):
        _, out, _ = self.run_it("--through-step", "10")
        logs = list((self.logs / "ffbapp").glob("7A-*.jsonl"))
        self.assertEqual(len(logs), 1)
        self.assertIn('"type": "result"', logs[0].read_text())
        self.assertIn("Halted at step 8: the evaluator returned NEEDS_WORK.", out)
        self.assertIn("$1.25", out)
        self.assertIn("mkdir x", out)
        self.assertIn(str(logs[0]), out)

    def test_the_session_exit_code_passes_through(self):
        with mock.patch.dict(os.environ, {"FAKE_EXIT": "3"}):
            code, _, _ = self.run_it()
        self.assertEqual(code, 3)


if __name__ == "__main__":
    unittest.main()
