#!/usr/bin/env python3
"""Tests for wave_gate.py. Stdlib only; run with `python3 -m unittest`."""

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
import zipfile
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
RECORD_HOOK = find_up(Path(".claude") / "hooks" / "wave-evaluator-record.sh")
EVALUATOR = find_up(Path(".claude") / "agents" / "keelswell-wave-evaluator.md")

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
        git(self.root, "symbolic-ref", "HEAD", "refs/heads/main")
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
        for wrapper in (HOOK, RECORD_HOOK):
            shutil.copy(wrapper, hooks / wrapper.name)
            (hooks / wrapper.name).chmod(0o755)
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

    def recorded_by(self, wave, session):
        """What the evaluator hook leaves: the session whose evaluator it recorded."""
        (self.bmad(wave) / "evaluation-session").write_text(session + "\n")


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


class TestRecord(Base):
    """R3: `record` is the evaluator hook's entry point, and no session calls it."""

    EW = "python3 .claude/skills/bmad-dev-wave/scripts/evaluate_wave.py"
    EVENT = '{"hook_event_name": "SubagentStop", "agent_type": "keelswell-wave-evaluator"}'

    def denied(self, command, tool="Bash"):
        code, _, err = self.p.pre(tool, command=command)
        self.assertEqual(code, 2, command)
        self.assertIn("DENIED (record)", err, command)
        return err

    def test_a_direct_call_is_denied_and_names_the_hook(self):
        err = self.denied(f"{self.EW} record --project-root . --wave 7A < out.txt")
        self.assertIn("evaluator hook's entry point", err)
        self.assertIn("evaluate_wave.py verdict", err)

    def test_a_forged_event_piped_in_is_denied(self):
        self.denied(f"echo '{self.EVENT}' | {self.EW} record")
        self.denied(f"{self.EW} record <<'EOF'\n{self.EVENT}\nEOF")

    def test_monitor_is_read_as_bash_is(self):
        self.denied(f"{self.EW} record", tool="Monitor")

    def test_shapes_the_gate_cannot_read_are_denied(self):
        for command in (
                f"V=record; {self.EW} $V",
                f'CMD="{self.EW} record"; eval "$CMD"',
                "cd .claude/skills/bmad-dev-wave/scripts && python3 evaluate_wave.py record",
                f"echo x\n{self.EW} record",
                'python3 -c "import evaluate_wave; evaluate_wave.record({})"',
                "python3 - <<'EOF'\nimport evaluate_wave\nevaluate_wave.record({})\nEOF",
                f"echo '{self.EVENT}' | bash -c '{self.EW} record'",
                f"{self.EW} 'rec''ord'"):
            self.denied(command)

    def test_the_other_verbs_are_allowed(self):
        for verb in ("check", "verify", "dispatch", "verdict", "opening-prompt"):
            code, _, err = self.p.pre("Bash", command=f"{self.EW} {verb} --project-root . --wave 7A")
            self.assertEqual(code, 0, err)

    def test_reading_and_printing_are_allowed(self):
        for command in (
                'echo "the hook runs evaluate_wave.py record"',
                "grep -n record .claude/skills/bmad-dev-wave/scripts/evaluate_wave.py",
                f"{self.EW} dispatch --project-root . --wave 7A | "
                "python3 -c \"import json, sys; print(json.load(sys.stdin)['record_to'])\"",
                'git commit -m "record the decision"'):
            code, _, err = self.p.pre("Bash", command=command)
            self.assertEqual(code, 0, command + "\n" + err)


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

    def test_done_denied_with_no_evaluation(self):
        """V2-01: done was the way into the review stage past the evaluator."""
        code, _, err = self.p.pre("Bash", command=self.SET + "done")
        self.assertEqual(code, 2)
        self.assertIn("DENIED (review)", err)
        self.assertIn("cannot be set done", err)

    def test_done_denied_on_needs_work(self):
        self.p.evaluation("7A", 1, "PASS")
        self.p.evaluation("7A", 2, "NEEDS_WORK")
        code, _, err = self.p.pre("Bash", command=self.SET + "done")
        self.assertEqual(code, 2)
        self.assertIn("NEEDS_WORK, not PASS", err)

    def test_done_allowed_on_a_pass_that_merged(self):
        """merge-wave's set: the worktree is gone and the records are on main."""
        self.p.evaluation("7A", 1, "NEEDS_WORK")
        self.p.evaluation("7A", 2, "PASS")
        self.p.land("7A")
        code, _, err = self.p.pre("Bash", command=self.SET + "done")
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
    def test_recording_session_cannot_edit_the_worktree_after_needs_work(self):
        wt = self.p.worktree("7A")
        self.p.recorded_by("7A", "s1")
        self.p.evaluation("7A", 1, "NEEDS_WORK")
        code, _, err = self.p.pre("Write", session="s1", file_path=str(wt / "src" / "x.py"))
        self.assertEqual(code, 2)
        self.assertIn("DENIED (in-place)", err)
        self.assertIn("bmad-resume-wave 7A", err)

    def test_a_later_session_can_edit_the_worktree(self):
        wt = self.p.worktree("7A")
        self.p.recorded_by("7A", "s1")
        self.p.evaluation("7A", 1, "NEEDS_WORK")
        code, _, err = self.p.pre("Write", session="s2", file_path=str(wt / "src" / "x.py"))
        self.assertEqual(code, 0, err)

    def test_recording_session_can_still_edit_outside_the_worktree(self):
        self.p.worktree("7A")
        self.p.recorded_by("7A", "s1")
        self.p.evaluation("7A", 1, "NEEDS_WORK")
        code, _, err = self.p.pre("Write", session="s1", file_path="HANDOFF.md")
        self.assertEqual(code, 0, err)

    def test_bash_writes_into_the_worktree_denied_reads_allowed(self):
        wt = self.p.worktree("7A")
        self.p.recorded_by("7A", "s1")
        self.p.evaluation("7A", 1, "NEEDS_WORK")
        code, _, err = self.p.pre("Bash", session="s1", command=f"sed -i '' 's/a/b/' {wt}/x.py")
        self.assertEqual(code, 2)
        code, _, err = self.p.pre("Bash", session="s1", command=f"git -C {wt} commit -m fix")
        self.assertEqual(code, 2)
        code, _, err = self.p.pre("Bash", session="s1", command=f"git -C {wt} status 2>/dev/null")
        self.assertEqual(code, 0, err)

    def test_pass_releases_the_session(self):
        wt = self.p.worktree("7A")
        self.p.recorded_by("7A", "s1")
        self.p.evaluation("7A", 1, "PASS")
        code, _, err = self.p.pre("Write", session="s1", file_path=str(wt / "src" / "x.py"))
        self.assertEqual(code, 0, err)

    def test_no_worktree_means_nothing_to_guard(self):
        self.p.recorded_by("7A", "s1")
        self.p.evaluation("7A", 1, "NEEDS_WORK")
        code, _, err = self.p.pre("Write", session="s1", file_path="src/x.py")
        self.assertEqual(code, 0, err)


class TestInPlaceWrapPath(Base):
    """ffbapp wave 5E: the session that recorded NEEDS_WORK was rooted in the
    wave's worktree, the desktop app's isolation refused it the main checkout,
    and the in-place rule refused it the worktree, so /bmad-wrap had nowhere
    to write its triage file. A wrap file is not wave work."""

    def setUp(self):
        super().setUp()
        self.wt = self.p.worktree("7A")
        self.p.recorded_by("7A", "s1")
        self.p.evaluation("7A", 1, "NEEDS_WORK")
        self.triage = self.wt / "_bmad-output" / "session-wrap" / "2026-10-08T21-29-00Z" / "triage.md"

    def write(self, path, cwd=None):
        return self.p.pre("Write", session="s1", cwd=cwd, file_path=str(path), content="x\n")

    def test_the_wrap_writes_its_triage_file_in_the_worktree(self):
        code, _, err = self.write(self.triage)
        self.assertEqual(code, 0, err)

    def test_a_relative_path_from_a_session_rooted_in_the_worktree(self):
        code, _, err = self.write("_bmad-output/session-wrap/2026-10-08T21-29-00Z/triage.md", cwd=self.wt)
        self.assertEqual(code, 0, err)

    def test_the_rest_of_the_wrap_stays_denied(self):
        # TODO.md and HANDOFF.md are the wave branch's files; the next
        # session reconciles them, as 5E's wrap left them.
        for name in ("TODO.md", "HANDOFF.md", "_bmad-output/session-wrap.md"):
            with self.subTest(name):
                code, _, err = self.write(self.wt / name)
                self.assertEqual(code, 2, name)
                self.assertIn("DENIED (in-place)", err)

    def test_a_path_that_only_starts_with_the_name_is_denied(self):
        code, _, _ = self.write(self.wt / "_bmad-output" / "session-wrap-x" / "triage.md")
        self.assertEqual(code, 2)

    def test_climbing_out_of_the_wrap_directory_is_denied(self):
        code, _, _ = self.write(f"{self.wt}/_bmad-output/session-wrap/../../src/x.py")
        self.assertEqual(code, 2)

    def test_the_exemption_is_for_file_tools_only(self):
        # /bmad-wrap writes with Write. A shell command into the directory is
        # still denied, so the exemption cannot carry a `git commit` or a
        # script that writes elsewhere too.
        code, _, _ = self.p.pre("Bash", session="s1",
                                command=f"echo x > {self.triage}")
        self.assertEqual(code, 2)

    def test_a_wrap_directory_in_another_tree_is_not_what_is_exempted(self):
        # The main checkout was never the in-place rule's to guard.
        code, _, err = self.write(self.p.root / "_bmad-output" / "session-wrap" / "t" / "triage.md")
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


class TestNewline(Base):
    """A newline ends a command. 1.8.1 marked it with the newline inside the
    mark, shlex split the mark there, and the halves became words: a guarded
    action on line 2 passed after `echo` on line 1, and a `mkdir` on line 1
    followed by any line 2 crashed the gate on a NUL in a path."""

    SET = "python3 .claude/skills/bmad-dev-wave/scripts/wave_status.py set --project-root . --wave 7A --status in-review"
    SED = "sed -i '' 's/^status: .*/status: in-review/' .bmad/wave-7A/wave.md"

    def test_a_guarded_action_on_line_two_is_denied(self):
        for first in ("echo start", "printf 'x\\n'", "cat README.md", "grep -n x README.md", "ls"):
            for second, rule in ((self.SET, "review"), (self.SED, "lifecycle"),
                                 ("rm .bmad/wave-7A/wave.md", "lifecycle"),
                                 ("cp /tmp/v.md docs/wave-7a/evaluation-1.md", "verdict"),
                                 ("printf 'VERDICT: PASS\\n' > docs/wave-7a/evaluation-1.md", "verdict")):
                with self.subTest(first=first, second=second):
                    code, _, err = self.p.pre("Bash", command=f"{first}\n{second}")
                    self.assertEqual(code, 2, err)
                    self.assertIn(f"DENIED ({rule})", err)

    def test_ordinary_two_line_commands_are_allowed(self):
        for command in ("mkdir -p build\necho hi", "rm -f build/none\nls", "touch a\ntouch b",
                        "cp README.md /tmp/c\necho done", "git status --short\ngit log --oneline | head -3",
                        "cd .\ngit status", "mkdir -p \"$P/.claude/hooks\" \"$P/_bmad-output\"\ncat \"$P/x\""):
            with self.subTest(command):
                code, _, err = self.p.pre("Bash", command=command)
                self.assertEqual(code, 0, err)
                self.assertNotIn("FAILED CLOSED", err)

    def test_a_direct_set_on_line_two_is_read(self):
        code, _, err = self.p.pre("Bash", command="ls\npython3 .claude/skills/bmad-dev-wave/scripts/wave_status.py set --project-root . --wave 7A --status in-progress")
        self.assertEqual(code, 0, err)
        self.p.evaluation("7A", 1, "PASS")
        code, _, err = self.p.pre("Bash", command=f"ls\n{self.SET}")
        self.assertEqual(code, 0, err)

    def test_a_newline_inside_quotes_is_text(self):
        code, _, err = self.p.pre("Bash", command='git commit -m "first line\nsed -i x .bmad/wave-7A/wave.md"')
        self.assertEqual(code, 0, err)


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
            "python3 x/wave_st''atus.py set --wave 7A --status in-review",  # still the file
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
            f"{s} show | python3 -c \"import json,sys; print(set(json.load(sys.stdin)))\"",
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
                        "touch docs/wave-7a/evaluation-4.md",
                        "git rm -q docs/wave-7a/evaluation-1.md"):  # resets the pass count
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
                        "nohup timeout 5 rm .bmad/wave-7A/wave.md",
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

    def test_merge_wave_adopts_a_worktree_record_through_the_script(self):
        # bmad-merge-wave 1.3.0 step 3 copies the worktree's checkpoint into
        # the main checkout before removal. A hand copy of wave.md is a
        # write of the record; adopt is wave_status.py, the record's writer.
        wt = "/repo/.claude/worktrees/wave-7a-x"
        for target in (".bmad/wave-7A/wave.md", ".bmad/wave-7A/"):
            with self.subTest(target):
                code, _, err = self.p.pre("Bash", command=f"cp {wt}/.bmad/wave-7A/wave.md {target}")
                self.assertEqual(code, 2, err)
                self.assertIn("DENIED (lifecycle)", err)
        code, _, err = self.p.pre("Bash", command=f"{TestParser.S} adopt --wave 7A --from {wt}")
        self.assertEqual(code, 0, err)

    def test_a_copy_into_its_directory_that_could_carry_it_is_denied(self):
        # ffbapp wave 6B's merge session: a copy whose target is the record's
        # directory names no record, so the file match alone let it through.
        self.p.bmad("7A")
        carried = self.p.root / "carried"
        carried.mkdir()
        (carried / "wave.md").write_text("status: done\n")
        wt = "/repo/.claude/worktrees/wave-7a-x"
        for command in (f"cp {wt}/.bmad/wave-7A/wave.md .bmad/wave-7A",
                        "cp -n src/* .bmad/wave-7A/",
                        "cp -n carried/* .bmad/wave-7A/",
                        "cp -n carried .bmad/wave-7A/",
                        f"cp -R {wt}/.bmad/wave-7A/ .bmad/wave-7A",
                        f"cp -r {wt}/.bmad/wave-7A .bmad/",
                        f"rsync -a {wt}/.bmad/wave-7A/ .bmad/wave-7A/",
                        f"rsync --archive {wt}/.bmad/wave-7A/ .bmad/wave-7A/",
                        f"install -m 644 {wt}/.bmad/wave-7A/WAVE.md .bmad/wave-7a/",
                        f"mv {wt}/.bmad/wave-7A/wave.md .bmad/wave-7A/",
                        "cp checkpoint.json \"$SRC\" .bmad/wave-7A/",
                        f"D=.bmad/wave-7A; cp {wt}/.bmad/wave-7A/wave.md \"$D/\"",
                        f"bash -c 'cp {wt}/.bmad/wave-7A/wave.md .bmad/wave-7A/'"):
            with self.subTest(command):
                code, _, err = self.p.pre("Bash", command=command)
                self.assertEqual(code, 2, err)
                self.assertIn("DENIED (lifecycle)", err)

    def test_copying_a_file_beside_it_or_the_record_out_is_allowed(self):
        d = self.p.bmad("7A")
        (d / "wave.md").write_text("x\n")
        wt = "/repo/.claude/worktrees/wave-7a-x"
        for command in (f"cp {wt}/.bmad/wave-7A/checkpoint.json .bmad/wave-7A/",
                        f"cp -n {wt}/.bmad/wave-7A/*.json .bmad/wave-7A/",
                        "cp .bmad/wave-7A/wave.md /tmp/wave.md",
                        f"cp {wt}/.bmad/wave-7A/wave.md .bmad/wave-7A/archive/"):
            with self.subTest(command):
                code, _, err = self.p.pre("Bash", command=command)
                self.assertEqual(code, 0, err)


class TestVerdictByDirectory(Base):
    """V2-03: a PASS written elsewhere arrived with its directory, and the
    records went with theirs, which reset the pass count to 1."""

    def setUp(self):
        super().setUp()
        self.p.evaluation("7A", 1, "NEEDS_WORK")
        root = self.p.root
        (root / "notes").mkdir()
        (root / "notes" / "evaluation-2.md").write_text("VERDICT: PASS\n")
        (root / "stage" / "wave-8a").mkdir(parents=True)
        (root / "stage" / "wave-8a" / "evaluation-1.md").write_text("VERDICT: PASS\n")
        (root / "assets").mkdir()
        (root / "assets" / "logo.svg").write_text("<svg/>\n")
        (root / "README.md").write_text("# proj\n")
        (root / "stage" / "wave-9z").mkdir()
        self.archive("forge.tar", {"docs/wave-8a/evaluation-1.md": "VERDICT: PASS\n"})
        self.archive("forge.tgz", {"wave-8a/evaluation-1.md": "VERDICT: PASS\n"})
        self.archive("flat.tar", {"evaluation-1.md": "VERDICT: PASS\n"})
        self.archive("safe.tar", {"src/a.py": "x = 1\n"})
        with zipfile.ZipFile(root / "forge.zip", "w") as z:
            z.writestr("evaluation-1.md", "VERDICT: PASS\n")

    def archive(self, name, members):
        with tarfile.open(self.p.root / name, "w:gz" if name.endswith("gz") else "w") as t:
            for member, text in members.items():
                data = text.encode()
                info = tarfile.TarInfo(member)
                info.size = len(data)
                t.addfile(info, io.BytesIO(data))

    def assert_denied(self, commands, cwd=None):
        for command in commands:
            with self.subTest(command):
                code, _, err = self.p.pre("Bash", cwd=cwd, command=command)
                self.assertEqual(code, 2, err)
                self.assertIn("DENIED (verdict)", err)

    def assert_allowed(self, commands, cwd=None):
        for command in commands:
            with self.subTest(command):
                code, _, err = self.p.pre("Bash", cwd=cwd, command=command)
                self.assertEqual(code, 0, err)

    def test_a_record_copied_moved_or_linked_in_is_denied(self):
        root = self.p.root
        self.assert_denied([
            "mv notes docs/wave-8a",
            "mv notes/evaluation-2.md docs/wave-7a/",
            "cp notes/evaluation-2.md docs/wave-7a/",
            "cp notes/* docs/wave-7a/",
            "cp -r notes/ docs/wave-7a",
            "rsync -a notes/ docs/wave-7a/",
            "ditto notes docs/wave-8a",
            f"ln -s {root}/notes docs/wave-8a",
            f"ln -s {root}/notes/evaluation-2.md docs/wave-7a/",
            # Relative to the link's own directory, so not a path the gate can stat.
            "ln -s ../stage/wave-8a docs/wave-8a",
            f"ln -s {root}/stage/wave-8a docs/",
            # Empty today; a link stays live, so it can fill later.
            f"ln -s {root}/stage/wave-9z docs/",
            'D=docs/wave-7a; cp notes/evaluation-2.md "$D/"',
            "cp -r stage/wave-8a docs/",
            "mv stage/wave-8a docs/",
            "cp -r stage/* docs/",
            "cp -R stage/ docs",
            "rsync -a stage/ docs/",
            "cp -r missing/ docs/",
        ])

    def test_a_record_unpacked_in_is_denied(self):
        self.assert_denied([
            "tar -xf forge.tar",
            "tar xf forge.tar",
            "tar -xzf forge.tgz -C docs",
            "tar --extract --file=forge.tgz --directory docs",
            "tar -xf flat.tar -C docs/wave-8a",
            "cd docs/wave-8a && tar -xf ../../flat.tar",
            "unzip forge.zip -d docs/wave-8a",
            "cat forge.tar | tar -x -C docs/wave-8a",
        ])

    def test_copies_and_archives_that_cannot_carry_a_record_are_allowed(self):
        self.assert_allowed([
            "cp README.md docs/wave-7a/notes.md",
            "cp notes/evaluation-2.md /tmp/elsewhere.md",
            "cp -r assets docs/",
            "rsync -a assets/ docs/",
            "cp -r assets/* docs/",
            "cp -R assets/ docs",
            "cp README.md docs/",
            "tar -xf safe.tar",
            "tar -czf out.tgz docs",
            "tar -tf forge.tar",
            "curl -sL https://example.com/tool.tgz | tar -xz",
        ])

    def test_removing_or_moving_the_records_away_is_denied(self):
        self.assert_denied([
            "rm -rf docs/wave-7a",
            "rm -r docs/wave-7a/",
            "rm -rf docs",
            "rm -rf docs/*",
            "rm -rf *",
            "rmdir docs/wave-7a",
            "mv docs/wave-7a /tmp/wave-7a",
            "mv docs docs.old",
            "rm -rf DOCS/Wave-7A",
            "find docs -delete",
            "find . -name 'evaluation-*' -delete",
            "find . -iname '*.md' -delete",
            "find docs/wave-7a -type f -exec rm {} +",
            "find . ! -name '*.py' -delete",
        ])

    def test_removals_that_reach_no_record_are_allowed(self):
        (self.p.root / "docs" / "wave-7a" / "scratch.txt").write_text("x\n")
        (self.p.root / "build").mkdir()
        self.assert_allowed([
            "rm -rf build",
            "rm -f docs/wave-7a/scratch.txt",
            "mv docs/wave-7a/scratch.txt /tmp/",
            "find . -name '*.pyc' -delete",
            "find docs -name '*.md'",
        ])

    def test_removal_is_allowed_where_there_is_no_record(self):
        (self.p.root / "docs" / "wave-7a" / "evaluation-1.md").unlink()
        self.assert_allowed(["rm -rf docs/wave-7a", "git clean -d -f", "git stash -u"])

    def test_git_clean_and_an_untracked_stash_are_denied_with_a_record_on_disk(self):
        wt = self.p.worktree("8A")
        self.p.evaluation("8A", 1, "NEEDS_WORK", where=wt)
        self.assert_denied([
            "git clean -d -f",
            "git clean -fdx",
            "git stash -u",
            "git stash push --include-untracked",
            "git stash save -a",
            "git stash push -ku -m wip",
            f"git -C {wt} clean -fd",
        ])
        self.assert_denied(["git stash --all"], cwd=wt)
        self.assert_allowed(["git stash", "git stash list", "git stash push -m wip",
                             "git status --short"])

    def merge_records(self):
        """The wave's records committed on main, as they are once its PR merges."""
        git(self.p.root, "add", "docs")
        git(self.p.root, "commit", "-q", "-m", "merge wave 7A", when=POST_RULE)

    def test_cleanup_is_allowed_once_the_records_are_on_main(self):
        self.merge_records()
        (self.p.root / "build").mkdir()
        self.assert_allowed([
            "git clean -d -f", "git clean -fdx", "git stash -u", "git stash push --all",
            "rm -rf docs/wave-7a", "rm -rf docs", "find docs -delete",
            "mv docs/wave-7a /tmp/wave-7a"])

    def test_a_record_not_on_main_still_stops_the_cleanup(self):
        self.merge_records()
        (self.p.root / "docs" / "wave-7a" / "evaluation-2.md").write_text("VERDICT: PASS\n")
        self.assert_denied(["git clean -d -f", "git stash -u", "rm -rf docs/wave-7a"])
        # The same path with other bytes is not the record main holds.
        (self.p.root / "docs" / "wave-7a" / "evaluation-2.md").unlink()
        (self.p.root / "docs" / "wave-7a" / "evaluation-1.md").write_text("VERDICT: PASS\n")
        self.assert_denied(["rm -rf docs/wave-7a"])

    def test_an_old_worktree_whose_records_are_on_main_can_go(self):
        self.merge_records()
        wt = self.p.worktree("7A")
        self.assert_allowed([f"rm -rf {wt}", f"git -C {wt} clean -fd"])

    def test_clean_reads_what_git_would_sweep(self):
        # Committed on the wave branch, not merged: clean and stash -u leave
        # tracked files alone, so they are not stopped; an rm still is.
        wt = self.p.worktree("8A")
        self.p.evaluation("8A", 1, "NEEDS_WORK", where=wt)
        git(wt, "add", "docs")
        git(wt, "commit", "-q", "-m", "wave 8A record", when=POST_RULE)
        self.assert_allowed([f"git -C {wt} clean -fd", f"git -C {wt} stash -u"])
        self.assert_denied([f"rm -rf {wt}/docs/wave-8a"])

    def test_removing_a_worktree_record_is_denied(self):
        wt = self.p.worktree("8A")
        self.p.evaluation("8A", 1, "PASS", where=wt)
        self.assert_denied([f"rm -rf {wt}/docs/wave-8a", f"rm -rf {wt}"])
        self.assert_denied(["rm -rf docs"], cwd=wt)


class TestRecordWrapperRun(Base):
    """V2-04: the record hook's wrapper, run from Bash with a crafted event,
    wrote a PASS under the hook's own header."""

    W = ".claude/hooks/wave-evaluator-record.sh"

    def test_running_the_wrapper_is_denied(self):
        w = self.W
        for tool, command in (
                ("Bash", f"echo E | {w}"),
                ("Bash", f"bash {w} < ev.json"),
                ("Bash", f"{w} <<< E"),
                ("Bash", f"sh -c '{w} < ev.json'"),
                ("Bash", f"W={w}; $W < ev.json"),
                ("Bash", f"cat ev.json | env FOO=1 {self.p.root}/{w}"),
                ("Bash", f"source {w}"),
                ("Bash", f"cat {w} | bash"),
                ("Bash", f"python3 -c \"import subprocess; subprocess.run(['{w}'])\""),
                ("Bash", f'{w} "unterminated'),
                ("Monitor", f"{w} < ev.json")):
            with self.subTest(command):
                code, _, err = self.p.pre(tool, command=command)
                self.assertEqual(code, 2, err)
                self.assertIn("DENIED (record)", err)

    def test_reading_or_staging_the_wrapper_is_allowed(self):
        w = self.W
        for command in (f"cat {w}", f"grep -n exec {w}", f"git add {w}",
                        "shasum .claude/hooks/wave-*.sh", f"diff {w} /tmp/{w.rsplit('/', 1)[-1]}"):
            with self.subTest(command):
                code, _, err = self.p.pre("Bash", command=command)
                self.assertEqual(code, 0, err)


class TestDashDash(Base):
    """V2-20: argparse reads `--` as the end of options and the next word as the verb."""

    def test_a_verb_after_dashdash_is_read(self):
        for tool, command, rule in (
                ("Bash", "python3 x/wave_status.py --wave 7A --status in-review -- set", "review"),
                ("Monitor", "python3 x/wave_status.py --wave 7A --status in-review -- set", "review"),
                ("Bash", "python3 x/evaluate_wave.py -- record < ev.json", "record"),
                ("Monitor", "python3 x/evaluate_wave.py -- record", "record")):
            with self.subTest(tool=tool, command=command):
                code, _, err = self.p.pre(tool, command=command)
                self.assertEqual(code, 2, err)
                self.assertIn(f"DENIED ({rule})", err)

    def test_other_verbs_after_dashdash_are_allowed(self):
        for command in ("python3 x/wave_status.py -- show --wave 7A",
                        "python3 x/evaluate_wave.py -- verdict --wave 7A"):
            code, _, err = self.p.pre("Bash", command=command)
            self.assertEqual(code, 0, err)


class TestInPlaceSwitches(Base):
    """V2-09 a and b: the in-place rule's own state, and a case-variant path."""

    def setUp(self):
        super().setUp()
        self.wt = self.p.worktree("7A")
        self.p.recorded_by("7A", "s1")
        self.p.evaluation("7A", 1, "NEEDS_WORK")
        (self.p.bmad("7A") / "evaluation-pending").write_text("{}\n")

    def test_the_markers_are_guarded_like_the_record(self):
        for name in ("evaluation-session", "evaluation-pending"):
            path = str(self.p.root / ".bmad" / "wave-7A" / name)
            for tool, extra in (("Write", {"content": "s2\n"}),
                                ("Edit", {"old_string": "s1", "new_string": "s2"})):
                with self.subTest(name=name, tool=tool):
                    code, _, err = self.p.pre(tool, file_path=path, **extra)
                    self.assertEqual(code, 2, err)
                    self.assertIn("DENIED (lifecycle)", err)
        for command in ("rm .bmad/wave-7A/evaluation-session",
                        "echo s2 > .bmad/wave-7A/evaluation-session",
                        "truncate -s 0 .bmad/wave-7a/EVALUATION-SESSION",
                        "mv .bmad/wave-7A/evaluation-pending /tmp/p",
                        "cp /tmp/s .bmad/wave-7A/evaluation-session",
                        "cp /tmp/evaluation-session .bmad/wave-7A/"):
            with self.subTest(command):
                code, _, err = self.p.pre("Bash", session="s2", command=command)
                self.assertEqual(code, 2, err)
                self.assertIn("DENIED (lifecycle)", err)

    def test_reading_the_markers_is_allowed(self):
        code, _, err = self.p.pre("Bash", command="cat .bmad/wave-7A/evaluation-session")
        self.assertEqual(code, 0, err)

    def test_a_case_variant_of_the_worktree_path_is_the_worktree(self):
        variant = str(self.wt).replace("wave-7a-fix", "WAVE-7A-FIX")
        code, _, err = self.p.pre("Write", session="s1", file_path=f"{variant}/src/x.py", content="x")
        self.assertEqual(code, 2, err)
        self.assertIn("DENIED (in-place)", err)
        for command in (f"echo x > {variant}/src.py",
                        f"python3 -c \"open('{variant}/src.py', 'w').write('x')\""):
            with self.subTest(command):
                code, _, err = self.p.pre("Bash", session="s1", command=command)
                self.assertEqual(code, 2, err)
                self.assertIn("DENIED (in-place)", err)


class TestInPlaceReRoll(Base):
    """V2-02's cheap fix: the session held after NEEDS_WORK may not re-dispatch
    or re-verify the wave until it says PASS."""

    EW = "python3 .claude/skills/bmad-dev-wave/scripts/evaluate_wave.py"

    def setUp(self):
        super().setUp()
        self.wt = self.p.worktree("7A")
        self.p.recorded_by("7A", "s1")
        self.p.evaluation("7A", 1, "NEEDS_WORK")

    def test_the_held_session_cannot_dispatch_or_verify(self):
        for tool, command in (
                ("Bash", f"{self.EW} dispatch --project-root {self.wt} --wave 7A"),
                ("Bash", f"{self.EW} verify --project-root {self.wt} --wave=7a"),
                ("Monitor", f"{self.EW} dispatch --project-root {self.wt} --wave 7A"),
                ("Bash", f"{self.EW} -- dispatch --wave 7A"),
                ("Bash", "python3 -c \"import evaluate_wave; evaluate_wave.dispatch('.', '7A', 's1')\""),
                ("Bash", f'{self.EW} dispatch --wave "7A'),
                ("Bash", f"echo '{self.EW} dispatch --wave 7A' | sh"),
                ("Bash", f"bash <<'EOF'\n{self.EW} verify --wave 7A\nEOF"),
                ("Bash", f"W={self.EW.split()[1]}; python3 $W dispatch --wave 7A")):
            with self.subTest(command):
                code, _, err = self.p.pre(tool, session="s1", command=command)
                self.assertEqual(code, 2, err)
                self.assertIn("DENIED (in-place)", err)

    def test_reading_the_verdict_and_other_waves_stay_open(self):
        for session, command in (
                ("s1", 'git commit -m "evaluate_wave.py dispatch is the next session\'s"'),
                ("s1", 'echo "next: evaluate_wave.py verify --wave 7A"'),
                ("s1", f"{self.EW} verdict --project-root {self.wt} --wave 7A"),
                ("s1", f"{self.EW} opening-prompt --wave 7A"),
                ("s1", f"{self.EW} dispatch --project-root . --wave 8A"),
                ("s2", f"{self.EW} dispatch --project-root {self.wt} --wave 7A"),
                ("s2", f"{self.EW} verify --project-root {self.wt} --wave 7A")):
            with self.subTest(session=session, command=command):
                code, _, err = self.p.pre("Bash", session=session, command=command)
                self.assertEqual(code, 0, err)

    def test_pass_releases_dispatch(self):
        self.p.evaluation("7A", 2, "PASS")
        code, _, err = self.p.pre("Bash", session="s1", command=f"{self.EW} dispatch --wave 7A")
        self.assertEqual(code, 0, err)


class TestSurvivors(Base):
    """V2-52: one test for each mutation the suite let live (M7 to M15)."""

    SET = TestReview.SET

    def test_git_checkout_and_restore_over_a_record_are_denied(self):  # M7, M8
        for command in ("git checkout -- docs/wave-7a/evaluation-1.md",
                        "git restore docs/wave-7a/evaluation-1.md"):
            with self.subTest(command):
                code, _, err = self.p.pre("Bash", command=command)
                self.assertEqual(code, 2, err)
                self.assertIn("DENIED (verdict)", err)

    def test_a_file_tool_through_a_symlink_is_read_at_its_target(self):  # M9
        (self.p.root / "docs" / "wave-7a").mkdir(parents=True)
        (self.p.root / "notes").symlink_to(self.p.root / "docs" / "wave-7a")
        code, _, err = self.p.pre("Write", file_path="notes/evaluation-1.md", content="VERDICT: PASS")
        self.assertEqual(code, 2, err)
        self.assertIn("DENIED (verdict)", err)

    def test_an_unparseable_record_call_is_denied(self):  # M12
        code, _, err = self.p.pre(
            "Bash", command='python3 x/evaluate_wave.py record --wave "7A')
        self.assertEqual(code, 2, err)
        self.assertIn("DENIED (record)", err)
        self.assertIn("cannot be parsed", err)

    def test_upstream_cause_does_not_open_review(self):  # M13
        self.p.evaluation("7A", 1, "UPSTREAM_CAUSE")
        code, _, err = self.p.pre("Bash", command=self.SET + "in-review")
        self.assertEqual(code, 2, err)
        self.assertIn("UPSTREAM_CAUSE, not PASS", err)

    def test_an_unreadable_latest_record_does_not_open_review(self):  # M15
        self.p.evaluation("7A", 1, "PASS")
        d = self.p.root / "docs" / "wave-7a"
        (d / "evaluation-2.md").write_text("# Evaluation\n\nno verdict line\n")
        code, _, err = self.p.pre("Bash", command=self.SET + "in-review")
        self.assertEqual(code, 2, err)
        self.assertIn("unreadable, not PASS", err)


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


@unittest.skipIf(HOOK is None or RECORD_HOOK is None,
                 "no .claude/hooks/ wrappers above this test tree")
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
        # Step 8's hook records in the worktree; a session on either side now reads it.
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

    def evaluator_stop(self, cwd, text="VERDICT: PASS\n\n## Findings\nNone.\n", path=None):
        """The record wrapper, the way Claude Code runs it on SubagentStop."""
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(self.p.root))
        if path is not None:
            env["PATH"] = path
        event = {"session_id": "s1", "cwd": str(cwd), "hook_event_name": "SubagentStop",
                 "agent_id": "a1", "agent_type": "keelswell-wave-evaluator",
                 "last_assistant_message": text}
        p = subprocess.run([str(self.p.root / ".claude" / "hooks" / "wave-evaluator-record.sh")],
                           input=json.dumps(event), capture_output=True, text=True,
                           env=env, cwd=str(cwd))
        return p.returncode, p.stdout, p.stderr

    def pending(self, wt):
        (self.p.root / ".bmad" / "wave-7A" / "evaluation-pending").write_text(json.dumps({
            "session_id": "s1", "wave": "7A", "pass_number": 1, "project_root": str(wt),
            "rounds": 0}))

    def test_the_record_wrapper_writes_in_the_worktree_from_either_side(self):
        wt = self.p.sibling("7A")
        for n, cwd in enumerate((self.p.root, wt), 1):
            self.pending(wt)
            (wt / "docs" / "wave-7a" / "evaluation-1.md").unlink(missing_ok=True)
            code, out, err = self.evaluator_stop(cwd)
            self.assertEqual((code, out), (0, ""), err)
            self.assertIn("Written by the evaluator hook",
                          (wt / "docs" / "wave-7a" / "evaluation-1.md").read_text())
            self.assertEqual((self.p.root / ".bmad" / "wave-7A" / "evaluation-session").read_text(),
                             "s1\n")
        # What the hook wrote is what opens the review stage.
        code, _, err = self.p.wrapped("Bash", self.p.root, wt, command=self.SET)
        self.assertEqual(code, 0, err)

    def test_the_record_wrapper_sends_back_a_report_with_no_verdict(self):
        self.pending(self.p.root)
        code, out, _ = self.evaluator_stop(self.p.root, text="looks fine\n")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["decision"], "block")

    def test_a_missing_script_or_python3_records_nothing_and_never_exits_two(self):
        self.pending(self.p.root)
        bin_dir = self.p.base / "bin"
        bin_dir.mkdir()
        (bin_dir / "bash").symlink_to("/bin/bash")
        (bin_dir / "git").symlink_to(shutil.which("git"))
        code, _, err = self.evaluator_stop(self.p.root, path=str(bin_dir))
        self.assertEqual(code, 1, err)
        self.assertIn("python3", err)
        (self.gate.parent / "evaluate_wave.py").unlink()
        code, _, err = self.evaluator_stop(self.p.root)
        self.assertEqual(code, 1, err)
        self.assertIn("install.sh --validate-only", err)
        self.assertFalse((self.p.root / "docs" / "wave-7a").exists())

    def evaluator_ready(self):
        """A wave worktree that `evaluate_wave.py dispatch` will accept."""
        if EVALUATOR is None:
            self.skipTest("no keelswell-wave-evaluator definition above this test tree")
        agents = self.p.root / ".claude" / "agents"
        agents.mkdir(parents=True, exist_ok=True)
        shutil.copy(EVALUATOR, agents / EVALUATOR.name)
        (self.p.root / "tests").mkdir()
        (self.p.root / "tests" / "verify-fast.sh").write_text("echo 3 passed\n")
        git(self.p.root, "add", "-A")
        git(self.p.root, "commit", "-q", "-m", "evaluator", when=POST_RULE)
        git(self.p.root, "branch", "-M", "main")
        wt = self.p.sibling("7A")
        (wt / "docs" / "wave-7a").mkdir(parents=True)
        (wt / "docs" / "wave-7a" / "test-design.md").write_text("# Test design\n")
        (wt / "src.py").write_text("x = 1\n")
        git(wt, "add", "-A")
        git(wt, "commit", "-q", "-m", "wave 7A", when=POST_RULE)
        return wt

    def step8(self, wt, session):
        """verify then dispatch, each gated through the wrapper first, as step 8 runs them."""
        ew = self.gate.parent / "evaluate_wave.py"
        for verb in ("verify", "dispatch"):
            command = f"python3 {ew} {verb} --project-root {wt} --wave 7A"
            code, _, err = self.p.wrapped("Bash", self.p.root, self.p.root, session=session,
                                          command=command)
            if code != 0:
                return code, err
            p = subprocess.run([sys.executable, str(ew), verb, "--project-root", str(wt),
                                "--wave", "7A"], capture_output=True, text=True,
                               env=dict(os.environ, CLAUDE_CODE_SESSION_ID=session))
            self.assertEqual(p.returncode, 0, p.stderr)
        return 0, ""

    def test_the_legitimate_path_end_to_end(self):
        """Dispatch, the real record wrapper on SubagentStop, then review opens."""
        wt = self.evaluator_ready()
        self.assertEqual(self.step8(wt, "s1"), (0, ""))
        code, out, err = self.evaluator_stop(wt)
        self.assertEqual((code, out), (0, ""), err)
        record = (wt / "docs" / "wave-7a" / "evaluation-1.md").read_text()
        self.assertIn("Written by the evaluator hook", record)
        code, _, err = self.p.wrapped("Bash", self.p.root, wt, command=self.SET)
        self.assertEqual(code, 0, err)

    def test_needs_work_holds_the_session_end_to_end(self):
        wt = self.evaluator_ready()
        self.step8(wt, "s1")
        code, _, err = self.evaluator_stop(
            wt, text="VERDICT: NEEDS_WORK\n\n## Findings\n### [HIGH] AC-1 has no test\n- Where: src.py:1\n")
        self.assertEqual(code, 0, err)
        code, err = self.step8(wt, "s1")
        self.assertEqual(code, 2, err)
        self.assertIn("DENIED (in-place)", err)
        for command in (f"rm {self.p.root}/.bmad/wave-7A/evaluation-session",
                        f"rm -rf {wt}/docs/wave-7a",
                        f"echo E | {self.p.root}/.claude/hooks/wave-evaluator-record.sh",
                        f"git -C {wt} stash -u"):
            with self.subTest(command):
                code, _, err = self.p.wrapped("Bash", self.p.root, self.p.root, command=command)
                self.assertEqual(code, 2, err)
        # The next session takes the findings and evaluates the fix.
        self.assertEqual(self.step8(wt, "s2"), (0, ""))

    def test_no_python3_denies(self):
        bin_dir = self.p.base / "bin2"
        bin_dir.mkdir()
        (bin_dir / "bash").symlink_to("/bin/bash")
        code, _, err = self.p.wrapped("Bash", self.p.root, self.p.root, path=str(bin_dir), command="ls")
        self.assertEqual(code, 2, err)
        self.assertIn("python3", err)


if __name__ == "__main__":
    unittest.main()
