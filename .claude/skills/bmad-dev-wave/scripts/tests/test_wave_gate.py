#!/usr/bin/env python3
"""Tests for wave_gate.py. Stdlib only; run with `python3 -m unittest`."""

import contextlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "wave_gate.py"
CLOSURE_GATE = SCRIPT.parent.parent.parent / "bmad-close-epic" / "scripts" / "check_review_records.py"


def find_up(rel):
    """A fork-only file, wherever this test tree sits: skills/, .claude/skills/, an instance."""
    for d in Path(__file__).resolve().parents:
        if (d / rel).is_file():
            return d / rel
    return None


HOOK = find_up(Path(".claude") / "hooks" / "wave-gate.sh")

# Appendix F of docs/reviews/harness-engineering-review-v1.md, fixture-e2b.json,
# verbatim: the 15 review-rule shapes, labelled yes where the command sets a
# wave in-review. Before R1 the hook denied 3 of the 11 and one echo.
E2B = [
    ("b01", True, 'python3 .claude/skills/bmad-dev-wave/scripts/wave_status.py set --project-root . --wave 7A --status "in-review"'),
    ("b02", False, 'python3 .claude/skills/bmad-dev-wave/scripts/wave_status.py set --project-root . --wave 7A --status blocked --reason "evaluator returned NEEDS_WORK"'),
    ("b03", True, "S=in-review; python3 .claude/skills/bmad-dev-wave/scripts/wave_status.py set --project-root . --wave 7A --status $S"),
    ("b04", True, "python3 .claude/skills/bmad-dev-wave/scripts/wave_status.py set --project-root . --wave 7A --status in-review"),
    ("b05", True, "python3 .claude/skills/bmad-dev-wave/scripts/wave_status.py set --project-root . --wave=7A --status=in-review"),
    ("b06", False, "python3 .claude/skills/bmad-dev-wave/scripts/wave_status.py show --project-root . --wave 7A"),
    ("b07", True, 'python3 .claude/skills/bmad-dev-wave/scripts/wave_status.py set --project-root . --wave "7A" --status in-review'),
    ("b08", True, "python3 - <<'EOF'\nimport subprocess\nsubprocess.run(['python3', '.claude/skills/bmad-dev-wave/scripts/wave_status.py', 'set', '--project-root', '.', '--wave', '7A', '--status', 'in-review'], check=True)\nEOF"),
    ("b09", False, 'echo "after PASS run: wave_status.py set --wave 7A --status in-review then open the PR"'),
    ("b10", True, "cd .claude/skills/bmad-dev-wave/scripts && python3 wave_status.py set --project-root ../../../.. --wave 7A --status in-review"),
    ("b11", True, 'CMD="python3 .claude/skills/bmad-dev-wave/scripts/wave_status.py set --project-root . --wave 7A --status in-review"; eval "$CMD"'),
    ("b12", False, "python3 .claude/skills/bmad-dev-wave/scripts/wave_status.py route --project-root . --wave 7A"),
    ("b13", True, "python3 -c \"import subprocess; subprocess.run(['python3', '.claude/skills/bmad-dev-wave/scripts/wave_status.py', 'set', '--project-root', '.', '--wave', '7A', '--status', 'in-review'], check=True)\""),
    ("b14", True, "python3 .claude/skills/bmad-dev-wave/scripts/wave_status.py \\\n  set --project-root . --wave 7A --status in-review"),
    ("b15", True, "sed -i '' 's/^status: .*/status: in-review/' .bmad/wave-7A/wave.md"),
]

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
        # One level down, so a sibling worktree (../proj-wave-7a) is cleaned up too.
        self.base = Path(stack.enter_context(tempfile.TemporaryDirectory())).resolve()
        self.root = self.base / "proj"
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

    def evaluation(self, wave, n, verdict, where=None):
        d = (where or self.root) / "docs" / f"wave-{wave.lower()}"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"evaluation-{n}.md").write_text(f"# Evaluation\n\nVERDICT: {verdict}\n")

    def worktree(self, wave):
        """A checkout on a real-shaped wave branch, inside the project tree."""
        wt = self.root / ".claude" / "worktrees" / f"wave-{wave.lower()}-fix"
        wt.parent.mkdir(parents=True, exist_ok=True)
        git(self.root, "worktree", "add", "-q", "-b",
            f"claude/wave-{wave.lower()}-fix-abc123", str(wt))
        return wt.resolve()

    def sibling(self, wave):
        """The layout dev-wave step 2 makes by hand: ../<project>-wave-<id>."""
        wt = self.base / f"proj-wave-{wave.lower()}"
        git(self.root, "worktree", "add", "-q", "-b", f"wave-{wave.lower()}-alpha", str(wt))
        return wt.resolve()

    def bmad(self, wave):
        d = self.root / ".bmad" / f"wave-{wave}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def install_hook(self):
        """The wrapper and the scripts where an instance keeps them, committed so
        every worktree checks them out too."""
        scripts = self.root / ".claude" / "skills" / "bmad-dev-wave" / "scripts"
        scripts.mkdir(parents=True)
        for name in ("wave_gate.py", "wave_status.py", "evaluate_wave.py"):
            shutil.copy(SCRIPT.parent / name, scripts / name)
        closure = self.root / ".claude" / "skills" / "bmad-close-epic" / "scripts"
        closure.mkdir(parents=True)
        shutil.copy(CLOSURE_GATE, closure / CLOSURE_GATE.name)
        hooks = self.root / ".claude" / "hooks"
        hooks.mkdir(parents=True)
        shutil.copy(HOOK, hooks / "wave-gate.sh")
        (hooks / "wave-gate.sh").chmod(0o755)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "harness", when=POST_RULE)
        return scripts / "wave_gate.py"

    def payload(self, tool, session, cwd, tool_input):
        return {"session_id": session, "cwd": str(cwd or self.root),
                "hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input}

    def hook(self, event, payload, root=None):
        p = subprocess.run([sys.executable, str(SCRIPT), event,
                            "--project-root", str(root or self.root)],
                           input=json.dumps(payload), capture_output=True, text=True)
        return p.returncode, p.stdout, p.stderr

    def pre(self, tool, session="s1", cwd=None, **tool_input):
        return self.hook("pre-tool-use", self.payload(tool, session, cwd, tool_input))

    def wrapped(self, tool, project_dir, cwd, session="s1", path=None, **tool_input):
        """The .sh wrapper itself, the way Claude Code runs it: exec form, no
        --project-root, CLAUDE_PROJECT_DIR set, cwd wherever the session is."""
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(project_dir))
        if path is not None:
            env["PATH"] = path
        p = subprocess.run([str(project_dir / ".claude" / "hooks" / "wave-gate.sh")],
                           input=json.dumps(self.payload(tool, session, cwd, tool_input)),
                           capture_output=True, text=True, env=env, cwd=str(cwd))
        return p.returncode, p.stdout, p.stderr

    def end(self, session="s1", reason="other", root=None):
        return self.hook("session-end", {
            "session_id": session, "cwd": str(root or self.root),
            "hook_event_name": "SessionEnd", "reason": reason}, root=root)

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

    def test_a_worktree_rooted_session_blocks_the_main_record(self):
        wt = self.p.worktree("7A")
        self.pending("7A")
        code, _, err = self.p.end(root=wt)
        self.assertEqual(code, 0, err)
        self.assertIn("status: blocked", self.p.record("7A").read_text())


class TestE2bReplay(Base):
    """R1's check: every in-review shape denied; the echo, show, route and blocked calls allowed."""

    def test_every_in_review_shape_is_denied_and_nothing_else(self):
        for key, in_review, command in E2B:
            with self.subTest(key):
                code, _, err = self.p.pre("Bash", command=command)
                self.assertEqual(code, 2 if in_review else 0, f"{key}: {err}")

    def test_each_denial_names_its_rule(self):
        err = {key: self.p.pre("Bash", command=command)[2] for key, _, command in E2B}
        for key in ("b01", "b04", "b05", "b07", "b10", "b14"):
            self.assertIn("no evaluation on disk", err[key], key)
        self.assertIn("literal", err["b03"])
        for key in ("b08", "b11", "b13"):
            self.assertIn("cannot read", err[key], key)
        self.assertIn("DENIED (lifecycle)", err["b15"])

    def test_a_pass_opens_the_readable_shapes_only(self):
        self.p.evaluation("7A", 1, "PASS")
        for key, in_review, command in E2B:
            with self.subTest(key):
                code, _, err = self.p.pre("Bash", command=command)
                still = key in ("b03", "b08", "b11", "b13", "b15")
                self.assertEqual(code, 2 if still else 0, f"{key}: {err}")


class TestParser(Base):
    S = "python3 x/wave_status.py"

    def test_shapes_that_hide_a_set_are_refused(self):
        s = self.S
        for command in (
            f'{s} set --reason ";" --wave 7A --status in-review',  # a quoted ; is a word
            f"echo a#; {s} set --wave 7A --status in-review",  # a # inside a word is not a comment
            f"echo `{s} set --wave 7A --status in-review`",
            f'echo "$({s} set --wave 7A --status in-review)"',
            f'bash -c "{s} set --wave 7A --status in-review"',
            f"V=set; {s} $V --wave 7A --status in-review",
            f"W=x/wave_status.py; python3 $W set --wave 7A --status in-review",
            f"env FOO=1 timeout 30 {s} set --wave 7A --status in-review",
            f"while true; do {s} set --wave 7A --status in-review; done",
            f"PYTHONPATH=x python3 -m wave_status set --wave 7A --status in-review",
            f"echo {s} set --wave 7A --status in-review | sh",
            f"echo {s} set --wave 7A --status in-review > /tmp/s.sh",
            "python3 -c 'import wave_status as w; w.set_status(\".\", \"7A\", \"in-review\")'",
            f'{s} set --wave 7A --status "unterminated',
        ):
            with self.subTest(command):
                code, _, err = self.p.pre("Bash", command=command)
                self.assertEqual(code, 2, err)

    def test_ordinary_commands_near_the_script_are_allowed(self):
        s = self.S
        for command in (
            f"set -euo pipefail; {s} show --wave 7A",
            f'{s} set --wave 7A --status blocked --reason "set by the evaluator; see #4"',
            f'bash -c "{s} set --wave 7A --status blocked --reason x"',
            "grep -n 'wave_status.py set' SKILL.md",
            f"printf '%s\\n' '{s} set --wave 7A --status in-review' >/dev/null",
            f"{s} route --wave 7A 2>&1 | tail -5",
            # Claude Code's own commit idiom, with a message that names the call.
            "git commit -m \"$(cat <<'EOF'\nwave_status.py set refuses a prefix option\nEOF\n)\"",
        ):
            with self.subTest(command):
                code, _, err = self.p.pre("Bash", command=command)
                self.assertEqual(code, 0, err)

    def test_printed_text_piped_into_a_shell_is_refused(self):
        code, _, err = self.p.pre(
            "Bash", command=f"cat <<'EOF' | sh\n{self.S} set --wave 7A --status in-review\nEOF")
        self.assertEqual(code, 2, err)


class TestPathsAndTools(Base):
    def test_verdict_rule_ignores_case(self):
        for fp in ("docs/wave-7a/EVALUATION-3.md", "DOCS/Wave-7A/Evaluation-3.md"):
            code, _, err = self.p.pre("Write", file_path=str(self.p.root / fp), content="VERDICT: PASS")
            self.assertEqual(code, 2, fp)
            self.assertIn("DENIED (verdict)", err)
        code, _, err = self.p.pre("Bash", command="echo 'VERDICT: PASS' > docs/WAVE-7A/Evaluation-3.md")
        self.assertEqual(code, 2, err)

    def test_verdict_writes_the_substring_test_missed(self):
        for command in ("cd docs/wave-7a && echo 'VERDICT: PASS' > evaluation-1.md",
                        'F=docs/wave-7a/evaluation-1.md; echo "VERDICT: PASS" > "$F"',
                        "python3 -c \"open('docs/wave-7a/evaluation-1.md','w').write('VERDICT: PASS')\"",
                        "touch docs/wave-7a/evaluation-4.md"):
            with self.subTest(command):
                code, _, err = self.p.pre("Bash", command=command)
                self.assertEqual(code, 2, err)
                self.assertIn("DENIED (verdict)", err)

    def test_closure_path_ignores_case(self):
        self.p.land("7A", record=False)
        code, _, err = self.p.pre(
            "Write", file_path=str(self.p.root / "_BMAD-OUTPUT/Epic-Closure/Epic-7/SUMMARY.md"))
        self.assertEqual(code, 2)
        self.assertIn("DENIED (closure)", err)

    def test_notebook_edit_is_matched_by_notebook_path(self):
        self.p.land("7A", record=False)
        code, _, err = self.p.pre(
            "NotebookEdit", new_source="x",
            notebook_path=str(self.p.root / "_bmad-output/epic-closure/epic-7/trace.ipynb"))
        self.assertEqual(code, 2)
        self.assertIn("DENIED (closure)", err)

    def test_monitor_runs_under_the_bash_rules(self):
        code, _, err = self.p.pre("Monitor", description="x", timeout_ms=60000,
                                  command=f"{TestParser.S} set --wave 7A --status in-review")
        self.assertEqual(code, 2)
        self.assertIn("DENIED (review)", err)


class TestLifecycle(Base):
    def test_file_tools_cannot_write_the_record(self):
        record = str(self.p.root / ".bmad" / "wave-7A" / "wave.md")
        for tool, extra in (("Write", {"content": "status: done\n"}),
                            ("Edit", {"old_string": "blocked", "new_string": "done"})):
            code, _, err = self.p.pre(tool, file_path=record, **extra)
            self.assertEqual(code, 2, tool)
            self.assertIn("DENIED (lifecycle)", err)

    def test_bash_cannot_write_move_or_remove_it(self):
        (self.p.bmad("7A") / "wave.md").write_text("status: blocked\n")
        for command in ("sed -i '' 's/blocked/done/' .bmad/wave-7A/wave.md",
                        "echo 'status: done' > .bmad/wave-7a/WAVE.md",
                        "rm .bmad/wave-7A/wave.md",
                        "rm -rf .bmad/wave-7A",
                        "rm -rf .bmad",
                        "rm .bmad/wave-7A/*",
                        "if true; then rm .bmad/wave-7A/wave.md; fi",
                        "mv .bmad/wave-7A/wave.md /tmp/wave.md",
                        "python3 -c \"import pathlib; pathlib.Path('.bmad/wave-7A/wave.md').unlink()\""):
            with self.subTest(command):
                code, _, err = self.p.pre("Bash", command=command)
                self.assertEqual(code, 2, err)
                self.assertIn("DENIED (lifecycle)", err)

    def test_reading_it_and_writing_beside_it_are_allowed(self):
        d = self.p.bmad("7A")
        for name in ("wave.md", "checkpoint.json", "step-4.done"):
            (d / name).write_text("x\n")
        (d / "archive").mkdir()
        for command in ("cat .bmad/wave-7A/wave.md",
                        "touch .bmad/wave-7A/step-5.done",
                        "mv .bmad/wave-7A/checkpoint.json .bmad/wave-7A/step-*.done .bmad/wave-7A/archive/",
                        f"{TestParser.S} set --wave 7A --status blocked --reason r"):
            with self.subTest(command):
                code, _, err = self.p.pre("Bash", command=command)
                self.assertEqual(code, 0, err)


class TestFailsClosed(Base):
    def test_an_unreadable_event_is_denied(self):
        for payload in ("not json", "[]"):
            p = subprocess.run([sys.executable, str(SCRIPT), "pre-tool-use",
                                "--project-root", str(self.p.root)],
                               input=payload, capture_output=True, text=True)
            self.assertEqual(p.returncode, 2, payload)
            self.assertIn("FAILED CLOSED", p.stderr)

    def test_a_gate_that_runs_past_its_deadline_denies(self):
        slow = self.p.base / "slow_gate.py"
        slow.write_text("import time\ntime.sleep(30)\n")
        run = ("import sys; from pathlib import Path; sys.path.insert(0, sys.argv[1]); "
               "import wave_gate as g; g.DEADLINE = 1; g.CLOSURE_GATE = Path(sys.argv[2]); "
               "sys.argv = ['wave_gate.py', 'pre-tool-use', '--project-root', sys.argv[3]]; g.main()")
        payload = self.p.payload("Write", "s1", None, {
            "file_path": str(self.p.root / "_bmad-output/epic-closure/epic-7/SUMMARY.md")})
        start = time.monotonic()
        p = subprocess.run([sys.executable, "-c", run, str(SCRIPT.parent), str(slow), str(self.p.root)],
                           input=json.dumps(payload), capture_output=True, text=True)
        self.assertEqual(p.returncode, 2, p.stderr)
        self.assertIn("deadline", p.stderr)
        self.assertLess(time.monotonic() - start, 15)


@unittest.skipIf(HOOK is None, "no .claude/hooks/wave-gate.sh above this test tree")
class TestWrapper(Base):
    """R1's check: the .sh wrapper itself, from each checkout layout a wave runs in."""

    SET = ("python3 .claude/skills/bmad-dev-wave/scripts/wave_status.py set "
           "--project-root . --wave 7A --status in-review")

    def setUp(self):
        super().setUp()
        self.gate = self.p.install_hook()
        self.p.bmad("7A")

    def test_review_rule_reads_the_worktree_record_from_either_side(self):
        wt = self.p.sibling("7A")
        for cwd in (self.p.root, wt):
            code, _, err = self.p.wrapped("Bash", self.p.root, cwd, command=self.SET)
            self.assertEqual(code, 2, err)
            self.assertIn("no evaluation on disk", err)
        # Step 7 records in the worktree; a session on either side now reads it.
        self.p.evaluation("7A", 1, "PASS", where=wt)
        for cwd in (self.p.root, wt):
            code, _, err = self.p.wrapped("Bash", self.p.root, cwd, command=self.SET)
            self.assertEqual(code, 0, err)

    def test_a_session_rooted_in_a_claude_worktree_reads_the_main_bmad(self):
        wt = self.p.worktree("7A")
        (self.p.root / ".bmad" / "wave-7A" / "evaluation-session").write_text("s1\n")
        self.p.evaluation("7A", 1, "NEEDS_WORK", where=wt)
        # A --worktree session: CLAUDE_PROJECT_DIR and cwd are both the worktree,
        # which runs its own committed copy of the wrapper.
        code, _, err = self.p.wrapped("Bash", wt, wt, command="echo fix > src.py")
        self.assertEqual(code, 2, err)
        self.assertIn("DENIED (in-place)", err)
        code, _, err = self.p.wrapped("Bash", wt, wt, command=self.SET)
        self.assertEqual(code, 2, err)
        self.assertIn("NEEDS_WORK, not PASS", err)
        code, _, err = self.p.wrapped("Bash", wt, wt, command="git status --short")
        self.assertEqual(code, 0, err)

    def test_a_broken_gate_denies_every_matched_call(self):
        self.gate.write_text("def main(:\n")
        for tool, tool_input in (("Bash", {"command": "ls"}),
                                 ("Write", {"file_path": str(self.p.root / "x.md"), "content": "x"})):
            code, _, err = self.p.wrapped(tool, self.p.root, self.p.root, **tool_input)
            self.assertEqual(code, 2, tool)
            self.assertIn("could not be checked", err)
            self.assertIn("--help", err)

    def test_a_missing_gate_denies_and_names_the_fix(self):
        self.gate.unlink()
        code, _, err = self.p.wrapped("Bash", self.p.root, self.p.root, command="ls")
        self.assertEqual(code, 2)
        self.assertIn("install.sh --validate-only", err)

    def test_no_python3_denies(self):
        bin_dir = self.p.base / "bin"
        bin_dir.mkdir()
        (bin_dir / "bash").symlink_to("/bin/bash")
        code, _, err = self.p.wrapped("Bash", self.p.root, self.p.root, path=str(bin_dir), command="ls")
        self.assertEqual(code, 2, err)
        self.assertIn("python3", err)


if __name__ == "__main__":
    unittest.main()
