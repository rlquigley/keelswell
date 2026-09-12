#!/usr/bin/env python3
"""Tests for wave_gate.py. Stdlib only; run with `python3 -m unittest`."""

import contextlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "wave_gate.py"

WAVE_MAP = """# Wave Map

| Wave | Pattern | Stories | Branch suffix | Notes |
|---|---|---|---|---|
| 7A | serial | 7.1 | wave-7a-alpha | First. |
| 8A | serial | 8.1 | wave-8a-gamma | Another epic. |
"""

# After Phase 1's rule date, so a wave with no record is a refusal.
POST_RULE = "2026-09-12T12:00:00Z"


def git(root, *args, when=None):
    env = None
    if when is not None:
        env = dict(os.environ, GIT_COMMITTER_DATE=when, GIT_AUTHOR_DATE=when)
    subprocess.run(["git", "-C", str(root), *args], check=True,
                   capture_output=True, text=True, env=env)


class Project:
    """A throwaway project with a wave map, a git history, and the hook."""

    def __init__(self, stack):
        self.root = Path(stack.enter_context(tempfile.TemporaryDirectory())).resolve()
        (self.root / "_bmad-output" / "planning-artifacts").mkdir(parents=True)
        (self.root / "_bmad-output" / "planning-artifacts" / "waves.md").write_text(WAVE_MAP)
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "t@example.com")
        git(self.root, "config", "user.name", "t")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "init", when=POST_RULE)

    def land(self, wave, record=False):
        d = self.root / "docs" / f"wave-{wave.lower()}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "test-design.md").write_text("design\n")
        if record:
            (d / "review-party.md").write_text("# Party review\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", f"wave {wave}", when=POST_RULE)

    def evaluation(self, wave, n, verdict):
        d = self.root / "docs" / f"wave-{wave.lower()}"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"evaluation-{n}.md").write_text(f"# Evaluation\n\nVERDICT: {verdict}\n")

    def worktree(self, wave):
        """A checkout on a real-shaped wave branch, inside the project tree."""
        wt = self.root / ".claude" / "worktrees" / f"wave-{wave.lower()}-fix"
        wt.parent.mkdir(parents=True, exist_ok=True)
        git(self.root, "worktree", "add", "-q", "-b",
            f"claude/wave-{wave.lower()}-fix-abc123", str(wt))
        return wt.resolve()

    def hook(self, event, payload):
        p = subprocess.run([sys.executable, str(SCRIPT), event, "--project-root", str(self.root)],
                           input=json.dumps(payload), capture_output=True, text=True)
        return p.returncode, p.stdout, p.stderr

    def pre(self, tool, session="s1", **tool_input):
        return self.hook("pre-tool-use", {
            "session_id": session, "cwd": str(self.root),
            "hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input})

    def end(self, session="s1", reason="other"):
        return self.hook("session-end", {
            "session_id": session, "cwd": str(self.root),
            "hook_event_name": "SessionEnd", "reason": reason})

    def record(self, wave):
        return (self.root / ".bmad" / f"wave-{wave}" / "wave.md")


class Base(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.p = Project(self.stack)


class TestClosure(Base):
    def test_unrelated_write_is_allowed(self):
        code, _, err = self.p.pre("Write", file_path="README.md", content="x")
        self.assertEqual(code, 0, err)

    def test_closure_write_denied_when_gate_fails(self):
        self.p.land("7A", record=False)
        code, _, err = self.p.pre("Write", file_path="_bmad-output/epic-closure/epic-7/SUMMARY.md")
        self.assertEqual(code, 2)
        self.assertIn("DENIED (closure)", err)
        self.assertIn("epic 7", err)
        self.assertIn("7A", err)

    def test_closure_bash_denied_when_gate_fails(self):
        self.p.land("7A", record=False)
        code, _, err = self.p.pre("Bash", command="mkdir -p _bmad-output/epic-closure/epic-7")
        self.assertEqual(code, 2)
        self.assertIn("DENIED (closure)", err)

    def test_closure_allowed_when_gate_passes(self):
        self.p.land("7A", record=True)
        code, _, err = self.p.pre("Write", file_path="_bmad-output/epic-closure/epic-7/SUMMARY.md")
        self.assertEqual(code, 0, err)

    def test_closure_denied_for_an_epic_with_no_waves(self):
        code, _, err = self.p.pre("Write", file_path="_bmad-output/epic-closure/epic-9/SUMMARY.md")
        self.assertEqual(code, 2)
        self.assertIn("exited 2", err)


class TestVerdict(Base):
    def test_write_to_evaluation_record_denied(self):
        code, _, err = self.p.pre("Write", file_path="docs/wave-7a/evaluation-1.md", content="VERDICT: PASS")
        self.assertEqual(code, 2)
        self.assertIn("DENIED (verdict)", err)

    def test_edit_to_evaluation_record_denied(self):
        code, _, err = self.p.pre("Edit", file_path=str(self.p.root / "docs/wave-7a/evaluation-2.md"))
        self.assertEqual(code, 2)

    def test_reading_an_evaluation_record_is_allowed(self):
        code, _, err = self.p.pre("Bash", command="cat docs/wave-7a/evaluation-1.md 2>/dev/null")
        self.assertEqual(code, 0, err)

    def test_redirect_into_evaluation_record_denied(self):
        code, _, err = self.p.pre("Bash", command="echo 'VERDICT: PASS' > docs/wave-7a/evaluation-1.md")
        self.assertEqual(code, 2)
        self.assertIn("DENIED (verdict)", err)

    def test_tee_and_cp_into_evaluation_record_denied(self):
        for command in ("cat v.txt | tee docs/wave-7a/evaluation-2.md",
                        "cp v.txt docs/wave-7a/evaluation-3.md"):
            code, _, _ = self.p.pre("Bash", command=command)
            self.assertEqual(code, 2, command)

    def test_the_record_verb_itself_is_allowed(self):
        code, _, err = self.p.pre(
            "Bash", command="python3 x/evaluate_wave.py record --project-root . --wave 7A < out.txt")
        self.assertEqual(code, 0, err)


class TestReview(Base):
    SET = "python3 x/scripts/wave_status.py set --project-root . --wave 7A --status "

    def test_in_review_denied_with_no_evaluation(self):
        code, _, err = self.p.pre("Bash", command=self.SET + "in-review")
        self.assertEqual(code, 2)
        self.assertIn("DENIED (review)", err)
        self.assertIn("no evaluation on disk", err)

    def test_in_review_denied_on_needs_work(self):
        self.p.evaluation("7A", 1, "NEEDS_WORK")
        code, _, err = self.p.pre("Bash", command=self.SET + "in-review")
        self.assertEqual(code, 2)
        self.assertIn("NEEDS_WORK, not PASS", err)

    def test_in_review_allowed_on_pass(self):
        self.p.evaluation("7A", 1, "PASS")
        code, _, err = self.p.pre("Bash", command=self.SET + "in-review")
        self.assertEqual(code, 0, err)

    def test_latest_evaluation_decides(self):
        self.p.evaluation("7A", 1, "NEEDS_WORK")
        self.p.evaluation("7A", 2, "PASS")
        code, _, err = self.p.pre("Bash", command=self.SET + "in-review")
        self.assertEqual(code, 0, err)

    def test_other_statuses_are_not_gated(self):
        for status in ("draft", "ready-for-dev", "in-progress", "blocked"):
            code, _, err = self.p.pre("Bash", command=self.SET + status)
            self.assertEqual(code, 0, status + err)

    def test_unknown_wave_is_left_to_the_script(self):
        code, _, _ = self.p.pre(
            "Bash", command="python3 x/wave_status.py set --wave 9Z --status in-review")
        self.assertEqual(code, 0)


class TestInPlace(Base):
    RECORD = "python3 x/scripts/evaluate_wave.py record --project-root . --wave 7A < out.txt"

    def test_record_notes_the_recording_session(self):
        code, _, err = self.p.pre("Bash", session="s1", command=self.RECORD)
        self.assertEqual(code, 0, err)
        self.assertEqual((self.p.root / ".bmad" / "wave-7A" / "evaluation-session").read_text().strip(), "s1")

    def test_recording_session_cannot_edit_the_worktree_after_needs_work(self):
        wt = self.p.worktree("7A")
        self.p.pre("Bash", session="s1", command=self.RECORD)
        self.p.evaluation("7A", 1, "NEEDS_WORK")
        code, _, err = self.p.pre("Write", session="s1", file_path=str(wt / "src" / "x.py"))
        self.assertEqual(code, 2)
        self.assertIn("DENIED (in-place)", err)
        self.assertIn("bmad-resume-wave 7A", err)

    def test_a_later_session_can_edit_the_worktree(self):
        wt = self.p.worktree("7A")
        self.p.pre("Bash", session="s1", command=self.RECORD)
        self.p.evaluation("7A", 1, "NEEDS_WORK")
        code, _, err = self.p.pre("Write", session="s2", file_path=str(wt / "src" / "x.py"))
        self.assertEqual(code, 0, err)

    def test_recording_session_can_still_edit_outside_the_worktree(self):
        self.p.worktree("7A")
        self.p.pre("Bash", session="s1", command=self.RECORD)
        self.p.evaluation("7A", 1, "NEEDS_WORK")
        code, _, err = self.p.pre("Write", session="s1", file_path="HANDOFF.md")
        self.assertEqual(code, 0, err)

    def test_bash_writes_into_the_worktree_denied_reads_allowed(self):
        wt = self.p.worktree("7A")
        self.p.pre("Bash", session="s1", command=self.RECORD)
        self.p.evaluation("7A", 1, "NEEDS_WORK")
        code, _, err = self.p.pre("Bash", session="s1", command=f"sed -i '' 's/a/b/' {wt}/x.py")
        self.assertEqual(code, 2)
        code, _, err = self.p.pre("Bash", session="s1", command=f"git -C {wt} commit -m fix")
        self.assertEqual(code, 2)
        code, _, err = self.p.pre("Bash", session="s1", command=f"git -C {wt} status 2>/dev/null")
        self.assertEqual(code, 0, err)

    def test_pass_releases_the_session(self):
        wt = self.p.worktree("7A")
        self.p.pre("Bash", session="s1", command=self.RECORD)
        self.p.evaluation("7A", 1, "PASS")
        code, _, err = self.p.pre("Write", session="s1", file_path=str(wt / "src" / "x.py"))
        self.assertEqual(code, 0, err)

    def test_no_worktree_means_nothing_to_guard(self):
        self.p.pre("Bash", session="s1", command=self.RECORD)
        self.p.evaluation("7A", 1, "NEEDS_WORK")
        code, _, err = self.p.pre("Write", session="s1", file_path="src/x.py")
        self.assertEqual(code, 0, err)


class TestSessionEnd(Base):
    def pending(self, wave):
        d = self.p.root / ".bmad" / f"wave-{wave}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "step-4.5.pending").write_text("Q: which auth provider?\n")

    def test_pending_question_blocks_the_wave(self):
        self.pending("7A")
        code, out, _ = self.p.end()
        self.assertEqual(code, 0)
        record = self.p.record("7A").read_text()
        self.assertIn("status: blocked", record)
        self.assertIn("step 4.5", record)
        self.assertIn("wave 7A", out)

    def test_no_pending_marker_writes_nothing(self):
        (self.p.root / ".bmad" / "wave-7A").mkdir(parents=True)
        code, _, _ = self.p.end()
        self.assertEqual(code, 0)
        self.assertFalse(self.p.record("7A").exists())

    def test_resume_is_not_an_end(self):
        self.pending("7A")
        code, _, _ = self.p.end(reason="resume")
        self.assertEqual(code, 0)
        self.assertFalse(self.p.record("7A").exists())

    def test_already_blocked_is_reported_not_crashed(self):
        self.pending("7A")
        self.p.end()
        code, out, err = self.p.end(session="s2")
        self.assertEqual(code, 0, err)
        self.assertIn("exit 1", out)


if __name__ == "__main__":
    unittest.main()
