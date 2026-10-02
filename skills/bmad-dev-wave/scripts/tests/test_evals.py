#!/usr/bin/env python3
"""The eval pairs' fixtures and graders, checked with no model call.

R5 of docs/reviews/harness-engineering-review-v1.md. A trial costs money and
minutes, so everything about a task that can be wrong without a session is
checked here first: the reference end state passes its own grader, fails the
grader of the other half of its pair, the starting state passes neither, the
router re-enters at the step the task is about, and the two prompts of a pair
are the same bytes. A task that scores 0 after this is a finding about the
skill, not about the task.

Stdlib only; needs git, like the wave scripts' own tests.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

EVALS = Path(__file__).resolve().parent.parent.parent / "evals"
sys.path.insert(0, str(EVALS))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import graders  # noqa: E402
import run_evals  # noqa: E402
import select_reviewers as sr  # noqa: E402
import wave_status  # noqa: E402

PAIRS = (("a_fire", "a_pass"), ("b_fire", "b_none"), ("c_specialist", "c_generalist"))
NAMES = [name for pair in PAIRS for name in pair]


class EvalTasks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="keelswell-evals-"))
        cls.tasks = {name: run_evals.load_task(name) for name in NAMES}
        cls.start, cls.reference = {}, {}
        for name, task in cls.tasks.items():
            cls.start[name] = run_evals.scaffold(task, cls.tmp / "start" / name)
            cls.reference[name] = run_evals.apply_reference(
                task, run_evals.scaffold(task, cls.tmp / "reference" / name))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def grade(self, grader, trial):
        return graders.GRADERS[grader](graders.Trial(trial))

    def test_the_six_tasks_are_the_three_pairs(self):
        self.assertEqual(sorted(NAMES), run_evals.task_names())
        self.assertEqual(sorted(NAMES), sorted(graders.GRADERS))

    def test_a_reference_end_state_passes_its_own_grader(self):
        for name in NAMES:
            self.assertEqual([], self.grade(name, self.reference[name]), name)

    def test_a_grader_fails_the_other_half_of_its_pair(self):
        for one, other in PAIRS:
            self.assertTrue(self.grade(one, self.reference[other]), f"{one} on {other}")
            self.assertTrue(self.grade(other, self.reference[one]), f"{other} on {one}")

    def test_the_starting_state_passes_no_grader(self):
        for name in NAMES:
            self.assertTrue(self.grade(name, self.start[name]), name)

    def test_a_pair_shares_one_prompt(self):
        for one, other in PAIRS:
            self.assertEqual(self.tasks[one]["prompt"], self.tasks[other]["prompt"], one)

    def test_the_router_enters_at_the_step_under_test(self):
        for name, task in self.tasks.items():
            code, result, _ = wave_status.route(self.start[name] / graders.PROJECT, graders.WAVE)
            self.assertEqual(0, code, name)
            self.assertEqual(task["enters_at"], result["reentry_step"], name)

    def test_the_planted_defect_leaves_verify_green(self):
        # A red suite would halt a_fire at step 7, before the gate under test.
        stamp = (self.start["a_fire"] / graders.WORKTREE / "docs" / "wave-1a"
                 / "verify-output.txt").read_text(encoding="utf-8").splitlines()[0]
        self.assertIn(" exit=0 ", stamp)

    def test_no_fixture_carries_an_evaluation_record(self):
        # An eval reads the record the hook wrote; it never ships one.
        self.assertEqual([], [str(p) for p in EVALS.rglob("evaluation-*.md")])
        for name in NAMES:
            self.assertEqual([], graders.Trial(self.start[name]).evaluations(), name)

    def selection(self, name, with_files):
        """The selector over a C task's wave: its changes, or the committed
        diff alone, which is empty until step 11 commits."""
        worktree = self.start[name] / graders.WORKTREE
        files = []
        if with_files:
            out = subprocess.run(["git", "-C", str(worktree), "status", "--porcelain",
                                  "--untracked-files=all"], capture_output=True, text=True)
            files = [line[3:] for line in out.stdout.splitlines()]
        files = [f for f in files if not sr.is_ignored(f)]
        rows, fallback = sr.load_table(sr.DEFAULT_TABLE)
        spec = sr.read_spec_text([str(worktree / "docs" / "wave-1a" / "test-design.md")])
        selected, _, _, fb = sr.resolve(rows, fallback, files, spec)
        return {hit["role"] for hit in selected}, fb is not None

    def test_the_specialist_wave_fires_a_specialist(self):
        self.assertEqual(({"custom-ml", "bmm-dev"}, False),
                         self.selection("c_specialist", with_files=True))
        roles, fallback = self.selection("c_specialist", with_files=False)
        self.assertIn("custom-ml", roles)
        self.assertFalse(fallback)

    def test_the_generalist_wave_fires_the_fallback(self):
        self.assertEqual(({"bmm-dev"}, True), self.selection("c_generalist", with_files=True))
        self.assertEqual((set(), True), self.selection("c_generalist", with_files=False))

    def test_every_task_states_its_limits(self):
        for name, task in self.tasks.items():
            self.assertGreater(task["max_turns"], 0, name)
            self.assertGreater(task["max_budget_usd"], 0, name)
            json.dumps(task["reference"])


if __name__ == "__main__":
    unittest.main()
