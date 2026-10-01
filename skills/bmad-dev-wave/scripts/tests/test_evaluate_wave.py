#!/usr/bin/env python3
"""Tests for evaluate_wave.py. Stdlib only; run with `python3 -m unittest`."""

import contextlib
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "evaluate_wave.py"
STATUS = SCRIPT.parent / "wave_status.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

# The definition this fork actually ships, so a test that passes here is a
# statement about the file bmad-dev-wave will really dispatch.
#
# Found by walking up rather than by a fixed depth. This file ships to three
# trees at two different depths -- the fork's skills/, the fork's
# .claude/skills/ mirror, and every instance's .claude/skills/ -- and a
# parents[4] that is right for the first builds ".claude/.claude/agents/" for
# the other two. That silently reduced this assertion to a failing test
# everywhere but one tree; install.sh's own `evaluate_wave.py check` is what
# actually held the invariant in the meantime.
def _find_shipped(start):
    for parent in start.parents:
        candidate = parent / ".claude" / "agents" / "keelswell-wave-evaluator.md"
        if candidate.is_file():
            return candidate
    return None


SHIPPED = _find_shipped(Path(__file__).resolve())

WAVE_MAP = """# Wave Map

| Wave | Pattern | Stories | Branch suffix | Notes |
|---|---|---|---|---|
| 5D | parallel | 5.4, 5.5 | wave-5d-delta | Load-bearing. |
| 6A | serial | 6.1 | wave-6a-alpha | Next epic. |
"""

SAFE_DEFINITION = """---
name: keelswell-wave-evaluator
description: Fresh-context evaluator.
tools:
  - Read
  - Glob
  - Grep
model: opus
effort: high
---

# Wave evaluator

- **CRITICAL** -- the work is wrong, unsafe, or loses data.
- **HIGH** -- an acceptance clause is not met.
- **MEDIUM** -- a real defect off the critical path.
- **LOW** -- worth fixing, would not hold the wave.

`LOW` findings alone are trivial.
"""

PASS_REPORT = "VERDICT: PASS\nWAVE: 5D\nPASS: 1\n\n## Findings\nNone.\n"
NEEDS_WORK_REPORT = ("VERDICT: NEEDS_WORK\nWAVE: 5D\n\n## Findings\n"
                     "### [HIGH] AC-3 has no assertion\n- Where: src/pay.py:88\n")


def git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


class Project:
    """A throwaway checkout on main with a wave map and an evaluator definition."""

    def __init__(self, stack, definition=SAFE_DEFINITION, wave_map=WAVE_MAP, repo=True):
        self.root = Path(stack.enter_context(tempfile.TemporaryDirectory())).resolve()
        if wave_map is not None:
            d = self.root / "_bmad-output" / "planning-artifacts"
            d.mkdir(parents=True)
            (d / "waves.md").write_text(wave_map)
        if definition is not None:
            d = self.root / ".claude" / "agents"
            d.mkdir(parents=True)
            (d / "keelswell-wave-evaluator.md").write_text(definition)
        (self.root / "src.py").write_text("x = 1\n")
        if repo:
            git(self.root, "init", "-q")
            git(self.root, "symbolic-ref", "HEAD", "refs/heads/main")
            git(self.root, "config", "user.email", "t@example.com")
            git(self.root, "config", "user.name", "t")
            self.commit("init")

    def commit(self, message):
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "--allow-empty", "-m", message)

    def docs(self, wave):
        d = self.root / "docs" / f"wave-{wave.lower()}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def evaluation(self, wave, n, verdict):
        (self.docs(wave) / f"evaluation-{n}.md").write_text(
            f"VERDICT: {verdict}\nWAVE: {wave}\nPASS: {n}\n\n"
            f"## Findings\nSomething about pass {n}.\n")

    def verify_script(self, body="echo 12 passed\n"):
        d = self.root / "tests"
        d.mkdir(exist_ok=True)
        (d / "verify-fast.sh").write_text(body)

    def verified(self, wave):
        """Verify script committed and run, so `dispatch` has fresh evidence."""
        self.verify_script()
        (self.docs(wave) / "test-design.md").write_text("# Test design\n")
        self.commit("tests")
        code, _, err = self.run("verify", "--wave", wave)
        assert code == 0, err

    def run(self, *args, script=SCRIPT, session="s1"):
        env = dict(os.environ)
        env.pop("CLAUDE_CODE_SESSION_ID", None)
        if session is not None:
            env["CLAUDE_CODE_SESSION_ID"] = session
        p = subprocess.run(
            [sys.executable, str(script), *args, "--project-root", str(self.root)],
            capture_output=True, text=True, env=env)
        out = json.loads(p.stdout) if p.stdout.strip() else {}
        return p.returncode, out, p.stderr

    def marker(self, wave):
        return self.root / ".bmad" / f"wave-{wave}" / "evaluation-pending"

    def event(self, name, text, session="s1", agent="keelswell-wave-evaluator"):
        e = {"session_id": session, "cwd": str(self.root), "hook_event_name": name,
             "agent_id": "a1", "agent_type": agent}
        if name == "SubagentStop":
            e.update(stop_hook_active=False, last_assistant_message=text)
        else:
            e.update(tool_name="SubagentHandback", tool_input={"message": text})
        return e

    def hook(self, event):
        """The `record` verb as the wrapper runs it: the event on stdin, no flags."""
        p = subprocess.run([sys.executable, str(SCRIPT), "record"],
                           input=event if isinstance(event, str) else json.dumps(event),
                           capture_output=True, text=True)
        return p.returncode, p.stdout, p.stderr

    def stop(self, text, **kw):
        return self.hook(self.event("SubagentStop", text, **kw))

    def records(self, wave):
        return sorted(p.name for p in self.docs(wave).glob("evaluation-*.md"))


class Base(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)

    def project(self, **kw):
        return Project(self.stack, **kw)

    def dispatched(self, wave="5D", **kw):
        p = self.project(**kw)
        p.verified(wave)
        code, out, err = p.run("dispatch", "--wave", wave)
        self.assertEqual(code, 0, err)
        return p


# ------------------------------------------------------- the tool-list gate

class TestCheck(Base):
    """The evaluator's inability to edit is a file this reads, not a promise."""

    def test_read_only_definition_is_safe(self):
        code, out, _ = self.project().run("check")
        self.assertEqual(code, 0)
        self.assertTrue(out["safe"])
        self.assertEqual(out["declared_tools"], ["Read", "Glob", "Grep"])

    def test_shipped_definition_is_safe(self):
        """The real file, not a fixture. Done criterion (1)."""
        if SHIPPED is None:
            self.skipTest("no .claude/agents/keelswell-wave-evaluator.md above this tree")
        p = subprocess.run(
            [sys.executable, str(SCRIPT), "check",
             "--project-root", str(SHIPPED.parents[2])],
            capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        out = json.loads(p.stdout)
        self.assertTrue(out["safe"])
        lowered = [t.lower() for t in out["declared_tools"]]
        for forbidden in ("write", "edit", "bash", "task"):
            self.assertNotIn(forbidden, lowered)
        self.assertEqual(out["effort"], "high")
        self.assertEqual(out["severities"], ["CRITICAL", "HIGH", "MEDIUM", "LOW"])
        self.assertEqual(out["trivial"], ["LOW"])

    def test_write_is_refused(self):
        d = SAFE_DEFINITION.replace("  - Grep\n", "  - Grep\n  - Write\n")
        code, out, err = self.project(definition=d).run("check")
        self.assertEqual(code, 3)
        self.assertFalse(out["safe"])
        self.assertEqual(out["denied_tools"], ["Write"])
        self.assertIn("Refusing to dispatch", err)

    def test_edit_is_refused(self):
        d = SAFE_DEFINITION.replace("  - Grep\n", "  - Grep\n  - Edit\n")
        code, out, _ = self.project(definition=d).run("check")
        self.assertEqual(code, 3)
        self.assertEqual(out["denied_tools"], ["Edit"])

    def test_bash_is_refused(self):
        """No Bash: `bash -c 'cat > f'` is an edit (RQ, 2026-09-11)."""
        d = SAFE_DEFINITION.replace("  - Grep\n", "  - Grep\n  - Bash\n")
        code, out, _ = self.project(definition=d).run("check")
        self.assertEqual(code, 3)
        self.assertEqual(out["denied_tools"], ["Bash"])

    def test_task_is_refused(self):
        """A spawned subagent inherits no restriction, so delegating is editing."""
        d = SAFE_DEFINITION.replace("  - Grep\n", "  - Grep\n  - Task\n")
        code, out, _ = self.project(definition=d).run("check")
        self.assertEqual(code, 3)
        self.assertEqual(out["denied_tools"], ["Task"])

    def test_mcp_write_tool_is_refused(self):
        d = SAFE_DEFINITION.replace("  - Grep\n", "  - Grep\n  - mcp__fs__Write\n")
        code, out, _ = self.project(definition=d).run("check")
        self.assertEqual(code, 3)
        self.assertEqual(out["denied_tools"], ["mcp__fs__Write"])

    def test_inline_tool_list_is_read(self):
        d = SAFE_DEFINITION.replace("tools:\n  - Read\n  - Glob\n  - Grep\n",
                                    "tools: Read, Glob, Edit\n")
        code, out, _ = self.project(definition=d).run("check")
        self.assertEqual(code, 3)
        self.assertEqual(out["denied_tools"], ["Edit"])

    def test_missing_tools_key_is_refused(self):
        """An absent list is not an empty list: the subagent inherits everything."""
        d = SAFE_DEFINITION.replace("tools:\n  - Read\n  - Glob\n  - Grep\n", "")
        code, out, err = self.project(definition=d).run("check")
        self.assertEqual(code, 3)
        self.assertFalse(out["safe"])
        self.assertIn("declares no tools", err)

    def test_wildcard_is_refused(self):
        d = SAFE_DEFINITION.replace("tools:\n  - Read\n  - Glob\n  - Grep\n",
                                    "tools:\n  - '*'\n")
        code, _, err = self.project(definition=d).run("check")
        self.assertEqual(code, 3)
        self.assertIn("every tool", err)

    def test_no_frontmatter_is_refused(self):
        code, _, err = self.project(definition="# just a heading\n").run("check")
        self.assertEqual(code, 3)
        self.assertIn("no frontmatter", err)

    def test_missing_definition_is_refused(self):
        code, out, err = self.project(definition=None).run("check")
        self.assertEqual(code, 3)
        self.assertFalse(out["safe"])
        self.assertIn("No evaluator definition", err)

    def test_unrecognized_tool_is_refused_not_allowed(self):
        """A tool the check has never heard of is not evidence it cannot edit."""
        d = SAFE_DEFINITION.replace("  - Grep\n", "  - Grep\n  - Teleport\n")
        code, out, err = self.project(definition=d).run("check")
        self.assertEqual(code, 3)
        self.assertEqual(out["unrecognized_tools"], ["Teleport"])
        self.assertIn("does not recognize", err)

    def test_effort_must_be_high(self):
        """Verdicts from sessions at different effort are not comparable (R3 d)."""
        for d in (SAFE_DEFINITION.replace("effort: high\n", ""),
                  SAFE_DEFINITION.replace("effort: high\n", "effort: medium\n")):
            code, out, err = self.project(definition=d).run("check")
            self.assertEqual(code, 3)
            self.assertFalse(out["safe"])
            self.assertIn("effort: high", err)

    def test_memory_is_refused(self):
        """`memory:` gives a subagent Write and Edit whatever its tool list says."""
        d = SAFE_DEFINITION.replace("effort: high\n", "effort: high\nmemory: project\n")
        code, out, err = self.project(definition=d).run("check")
        self.assertEqual(code, 3)
        self.assertFalse(out["safe"])
        self.assertIn("memory", err)

    def test_an_unreadable_severity_ladder_is_refused(self):
        for d in (SAFE_DEFINITION.replace("- **HIGH** -- ", "- HIGH: "
                                          ).replace("- **CRITICAL** -- ", "- CRITICAL: "
                                          ).replace("- **MEDIUM** -- ", "- MEDIUM: "),
                  SAFE_DEFINITION.replace("`LOW` findings alone are trivial.", "")):
            code, _, err = self.project(definition=d).run("check")
            self.assertEqual(code, 3)
            self.assertIn("severity ladder", err)


# -------------------------------------------------------------- the verify

class TestVerify(Base):
    def test_runs_the_script_and_stamps_its_output(self):
        p = self.project()
        p.verify_script("echo 12 passed\necho to-stderr >&2\n")
        p.commit("tests")
        code, out, err = p.run("verify", "--wave", "5D")
        self.assertEqual(code, 0, err)
        head = subprocess.run(["git", "-C", str(p.root), "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
        lines = (p.root / "docs/wave-5d/verify-output.txt").read_text().splitlines()
        self.assertRegex(lines[0], rf"^# verify-stamp command=bash tests/verify-fast\.sh "
                                   rf"exit=0 head={head} at=\S+$")
        self.assertEqual(lines[1:], ["12 passed", "to-stderr"])
        self.assertEqual(out["head"], head)
        self.assertEqual(out["verify_exit"], 0)

    def test_a_failing_script_exits_one_and_is_still_stamped(self):
        p = self.project()
        p.verify_script("echo 1 failed\nexit 7\n")
        p.commit("tests")
        code, out, err = p.run("verify", "--wave", "5D")
        self.assertEqual(code, 1)
        self.assertEqual(out["verify_exit"], 7)
        self.assertIn("exit=7 ", (p.root / "docs/wave-5d/verify-output.txt").read_text())
        self.assertIn("Verify FAIL", err)

    def test_a_missing_script_is_refused(self):
        p = self.project()
        code, _, err = p.run("verify", "--wave", "5D")
        self.assertEqual(code, 3)
        self.assertIn("tests/verify-fast.sh", err)
        self.assertFalse((p.root / "docs").exists())

    def test_outside_a_git_checkout_is_refused(self):
        p = self.project(repo=False)
        p.verify_script()
        code, _, err = p.run("verify", "--wave", "5D")
        self.assertEqual(code, 3)
        self.assertIn("not a git checkout", err)

    def test_wave_not_in_map(self):
        code, _, err = self.project().run("verify", "--wave", "9Z")
        self.assertEqual(code, 2)
        self.assertIn("not in", err)


# ------------------------------------------------------------ the dispatch

class TestDispatch(Base):
    def test_first_pass(self):
        p = self.project()
        p.verified("5D")
        code, out, err = p.run("dispatch", "--wave", "5D")
        self.assertEqual(code, 0, err)
        self.assertEqual(out["pass_number"], 1)
        self.assertEqual(out["rule_pass"], 1)
        self.assertFalse(out["third_pass_rule"])
        self.assertEqual(out["evidence_missing"], [])
        self.assertEqual(out["record_to"], "docs/wave-5d/evaluation-1.md")
        self.assertIn("evaluation pass 1", err)
        self.assertIn("keelswell-wave-evaluator", err)

    def test_it_leaves_a_marker_naming_the_session(self):
        p = self.project()
        p.verified("5D")
        p.run("dispatch", "--wave", "5D", session="sess-9")
        marker = json.loads(p.marker("5D").read_text())
        self.assertEqual(marker["session_id"], "sess-9")
        self.assertEqual(marker["wave"], "5D")
        self.assertEqual(marker["pass_number"], 1)
        self.assertEqual(marker["project_root"], str(p.root))

    def test_without_a_session_it_refuses(self):
        p = self.project()
        p.verified("5D")
        code, _, err = p.run("dispatch", "--wave", "5D", session=None)
        self.assertEqual(code, 3)
        self.assertIn("CLAUDE_CODE_SESSION_ID", err)
        self.assertFalse(p.marker("5D").exists())

    def test_missing_verify_output_is_refused(self):
        """Loop defect: it used to print a notice and exit 0 (R3 e)."""
        p = self.project()
        code, _, err = p.run("dispatch", "--wave", "5D")
        self.assertEqual(code, 3)
        self.assertIn("no verify output", err)
        self.assertIn("evaluate_wave.py verify", err)
        self.assertFalse(p.marker("5D").exists())

    def test_hand_written_verify_output_is_refused(self):
        p = self.project()
        (p.docs("5D") / "verify-output.txt").write_text("12 passed\n")
        code, _, err = p.run("dispatch", "--wave", "5D")
        self.assertEqual(code, 3)
        self.assertIn("no verify stamp", err)

    def test_verify_output_from_another_head_is_refused(self):
        p = self.project()
        p.verified("5D")
        (p.root / "src.py").write_text("x = 2\n")
        p.commit("a fix after verify")
        code, _, err = p.run("dispatch", "--wave", "5D")
        self.assertEqual(code, 3)
        self.assertIn("stale", err)

    def test_the_diff_is_written_from_the_merge_base(self):
        p = self.project()
        p.verify_script()
        p.commit("tests")
        git(p.root, "checkout", "-q", "-b", "wave-5d-delta")
        (p.root / "src.py").write_text("x = 2\n")
        p.commit("story 5.4")
        (p.root / "src.py").write_text("x = 3\n")           # not committed
        (p.root / "new_test.py").write_text("assert True\n")  # not tracked
        (p.root / ".bmad").mkdir()
        (p.root / ".bmad" / "note").write_text("harness state\n")
        self.assertEqual(p.run("verify", "--wave", "5D")[0], 0)
        (p.docs("5D") / "wave-diff.patch").write_text("typed by the builder\n")
        code, out, err = p.run("dispatch", "--wave", "5D")
        self.assertEqual(code, 0, err)
        patch = (p.root / out["evidence"]["diff"]).read_text()
        self.assertNotIn("typed by the builder", patch)
        self.assertIn("-x = 1", patch)
        self.assertIn("+x = 3", patch)
        self.assertIn("new_test.py", patch)
        self.assertIn("+assert True", patch)
        for absent in ("verify-stamp", "wave-diff.patch", "harness state"):
            self.assertNotIn(absent, patch)
        base = subprocess.run(["git", "-C", str(p.root), "rev-parse", "main"],
                              capture_output=True, text=True).stdout.strip()
        self.assertEqual(out["base"], base)

    def test_pass_number_counts_records_not_conversation(self):
        p = self.project()
        p.evaluation("5D", 1, "NEEDS_WORK")
        p.verified("5D")
        code, out, _ = p.run("dispatch", "--wave", "5D")
        self.assertEqual(out["pass_number"], 2)
        self.assertFalse(out["third_pass_rule"])
        self.assertEqual(out["prior_verdicts"], ["NEEDS_WORK"])

    def test_third_pass_rule_arms(self):
        """Done criterion (4): the rule fires from a count on disk."""
        p = self.project()
        p.evaluation("5D", 1, "NEEDS_WORK")
        p.evaluation("5D", 2, "NEEDS_WORK")
        p.verified("5D")
        code, out, err = p.run("dispatch", "--wave", "5D")
        self.assertEqual(code, 0)
        self.assertEqual(out["pass_number"], 3)
        self.assertTrue(out["third_pass_rule"])
        self.assertIn("THIRD-PASS RULE ARMED", err)
        self.assertIn("UPSTREAM_CAUSE", err)

    def upstream(self):
        p = self.project()
        p.evaluation("5D", 1, "NEEDS_WORK")
        p.evaluation("5D", 2, "NEEDS_WORK")
        p.evaluation("5D", 3, "UPSTREAM_CAUSE")
        p.verified("5D")
        return p

    def fix(self, p, reason="upstream fix: docs/stories/5.4.md"):
        code, _, err = p.run("set", "--wave", "5D", "--status", "in-progress",
                             "--reason", reason, script=STATUS)
        self.assertEqual(code, 0, err)

    def test_the_count_restarts_after_an_upstream_fix_on_record(self):
        """Loop defect: pass 4 was armed at once, so NEEDS_WORK was unreachable (R3 e)."""
        p = self.upstream()
        self.fix(p)
        code, out, err = p.run("dispatch", "--wave", "5D")
        self.assertEqual(code, 0, err)
        self.assertEqual(out["pass_number"], 4)
        self.assertEqual(out["rule_pass"], 1)
        self.assertFalse(out["third_pass_rule"])
        self.assertEqual(out["record_to"], "docs/wave-5d/evaluation-4.md")
        self.assertIn("Pass 1 since the upstream fix", err)

    def test_without_a_fix_on_record_the_count_does_not_restart(self):
        p = self.upstream()
        self.fix(p, reason="resuming after a break")
        _, out, _ = p.run("dispatch", "--wave", "5D")
        self.assertEqual(out["rule_pass"], 4)
        self.assertTrue(out["third_pass_rule"])

    def test_a_fix_recorded_before_the_upstream_cause_does_not_restart_it(self):
        """The reviewed party cannot bank a reset ahead of the verdict."""
        p = self.upstream()
        self.fix(p)
        later = time.time() + 60
        os.utime(p.root / "docs/wave-5d/evaluation-3.md", (later, later))
        _, out, _ = p.run("dispatch", "--wave", "5D")
        self.assertEqual(out["rule_pass"], 4)
        self.assertTrue(out["third_pass_rule"])

    def test_a_review_record_newer_than_the_evaluation_joins_the_evidence(self):
        """Loop defect: nothing re-checked a fix made at step 10 (R3 e)."""
        p = self.project()
        p.evaluation("5D", 1, "PASS")
        p.verified("5D")
        _, out, _ = p.run("dispatch", "--wave", "5D")
        self.assertNotIn("review_record", out["evidence"])
        (p.docs("5D") / "review-party.md").write_text(
            "---\ntitle: review\nwave: 5D\ncreated: 2999-01-01\n---\n\n### [HIGH] x\n")
        code, out, err = p.run("dispatch", "--wave", "5D")
        self.assertEqual(code, 0, err)
        self.assertEqual(out["evidence"]["review_record"], "docs/wave-5d/review-party.md")
        self.assertIn("after step 10's fixes", err)

    def test_unsafe_definition_blocks_dispatch(self):
        d = SAFE_DEFINITION.replace("  - Grep\n", "  - Grep\n  - Write\n")
        p = self.project(definition=d)
        code, out, _ = p.run("dispatch", "--wave", "5D")
        self.assertEqual(code, 3)
        self.assertEqual(out["wave"], "5D")

    def test_case_insensitive_wave(self):
        p = self.project()
        p.verified("5D")
        code, out, _ = p.run("dispatch", "--wave", "5d")
        self.assertEqual(code, 0)
        self.assertEqual(out["wave"], "5D")

    def test_wave_not_in_map(self):
        code, _, err = self.project().run("dispatch", "--wave", "9Z")
        self.assertEqual(code, 2)
        self.assertIn("not in", err)

    def test_no_wave_map(self):
        code, _, err = self.project(wave_map=None).run("dispatch", "--wave", "5D")
        self.assertEqual(code, 2)
        self.assertIn("no wave map", err)

    def test_prefix_options_do_not_bind(self):
        # The gate reads --wave by its full name (R1).
        code, _, err = self.project().run("dispatch", "--wav", "5D")
        self.assertEqual(code, 2)
        self.assertIn("unrecognized arguments", err)


# --------------------------------------------------- the hook-written record

class TestRecord(Base):
    """`record` is the evaluator hook's entry point. Nothing else writes a verdict."""

    def test_subagent_stop_writes_the_record(self):
        p = self.dispatched()
        code, out, err = p.stop(PASS_REPORT)
        self.assertEqual((code, out), (0, ""), err)
        written = (p.root / "docs/wave-5d/evaluation-1.md").read_text()
        self.assertIn("Written by the evaluator hook (SubagentStop)", written)
        self.assertIn("Session s1", written)
        self.assertIn("subagent a1", written)
        self.assertIn("unedited", written)
        self.assertTrue(written.endswith(PASS_REPORT))
        self.assertFalse(p.marker("5D").exists())
        self.assertEqual((p.root / ".bmad/wave-5D/evaluation-session").read_text(), "s1\n")

    def test_the_body_is_stored_verbatim(self):
        p = self.dispatched()
        p.stop(NEEDS_WORK_REPORT)
        self.assertIn("### [HIGH] AC-3 has no assertion\n- Where: src/pay.py:88\n",
                      (p.root / "docs/wave-5d/evaluation-1.md").read_text())

    def test_without_a_dispatch_nothing_is_written(self):
        p = self.project()
        code, out, err = p.stop(PASS_REPORT)
        self.assertEqual((code, out), (0, ""))
        self.assertIn("no dispatch is pending", err)
        self.assertFalse((p.root / "docs").exists())

    def test_another_sessions_dispatch_is_not_this_ones(self):
        p = self.dispatched()
        code, _, err = p.stop(PASS_REPORT, session="s2")
        self.assertEqual(code, 0)
        self.assertIn("no dispatch is pending", err)
        self.assertEqual(p.records("5D"), [])
        self.assertTrue(p.marker("5D").exists())

    def test_two_pending_dispatches_cannot_be_told_apart(self):
        p = self.dispatched()
        p.verified("6A")
        self.assertEqual(p.run("dispatch", "--wave", "6A")[0], 0)
        code, _, err = p.stop(PASS_REPORT)
        self.assertEqual(code, 0)
        self.assertIn("cannot be told apart", err)
        self.assertEqual(p.records("5D") + p.records("6A"), [])

    def test_another_subagents_events_are_ignored(self):
        p = self.dispatched()
        code, out, err = p.stop(PASS_REPORT, agent="Explore")
        self.assertEqual((code, out, err), (0, "", ""))
        self.assertEqual(p.records("5D"), [])

    def test_no_verdict_line_is_sent_back(self):
        p = self.dispatched()
        code, out, _ = p.stop("I think this looks pretty good overall!\n")
        self.assertEqual(code, 0)
        decision = json.loads(out)
        self.assertEqual(decision["decision"], "block")
        self.assertIn("no VERDICT line", decision["reason"])
        self.assertIn("exactly one VERDICT line", decision["reason"])
        self.assertEqual(p.records("5D"), [])
        self.assertEqual(json.loads(p.marker("5D").read_text())["rounds"], 1)

    def test_the_second_round_is_recorded(self):
        p = self.dispatched()
        p.stop("no verdict here\n")
        code, out, _ = p.stop(PASS_REPORT)
        self.assertEqual((code, out), (0, ""))
        self.assertEqual(p.records("5D"), ["evaluation-1.md"])

    def test_after_two_rounds_it_gives_up_and_writes_nothing(self):
        p = self.dispatched()
        for _ in range(2):
            self.assertTrue(p.stop("still no verdict\n")[1])
        code, out, err = p.stop("still no verdict\n")
        self.assertEqual((code, out), (0, ""))
        self.assertIn("not recorded", err)
        self.assertEqual(p.records("5D"), [])
        code, out, err = p.run("verdict", "--wave", "5D")
        self.assertEqual(code, 3)
        self.assertIn("no VERDICT line", err)

    def test_two_verdict_lines_are_refused(self):
        p = self.dispatched()
        _, out, _ = p.stop("VERDICT: PASS\n\n## Findings\nNone.\n\nVERDICT: NEEDS_WORK\n")
        self.assertIn("2 VERDICT lines", json.loads(out)["reason"])
        self.assertEqual(p.records("5D"), [])

    def test_a_verdict_outside_the_list_is_refused(self):
        p = self.dispatched()
        _, out, _ = p.stop("VERDICT: LGTM\n")
        self.assertIn("is not one of", json.loads(out)["reason"])

    def test_a_pass_carrying_a_real_finding_is_refused(self):
        """A parser's job, not a model's (R3 c)."""
        for severity in ("MEDIUM", "HIGH", "CRITICAL", "BLOCKER"):
            p = self.dispatched()
            _, out, _ = p.stop(f"VERDICT: PASS\n\n## Findings\n### [{severity}] AC-3 untested\n")
            self.assertIn(f"[{severity}]", json.loads(out)["reason"], severity)
            self.assertEqual(p.records("5D"), [])

    def test_a_pass_carrying_only_trivial_findings_is_recorded(self):
        p = self.dispatched()
        code, out, _ = p.stop("VERDICT: PASS\n\n## Findings\n### [LOW] a typo\n")
        self.assertEqual((code, out), (0, ""))
        self.assertEqual(p.records("5D"), ["evaluation-1.md"])

    def test_needs_work_may_carry_any_finding(self):
        p = self.dispatched()
        self.assertEqual(p.stop(NEEDS_WORK_REPORT)[:2], (0, ""))
        self.assertEqual(p.records("5D"), ["evaluation-1.md"])

    def test_records_changed_since_dispatch_write_nothing(self):
        p = self.dispatched()
        p.evaluation("5D", 2, "NEEDS_WORK")
        code, _, err = p.stop(PASS_REPORT)
        self.assertEqual(code, 0)
        self.assertIn("have changed since", err)
        self.assertEqual(p.records("5D"), ["evaluation-2.md"])

    def test_a_marker_naming_an_unknown_wave_writes_nothing(self):
        p = self.dispatched()
        marker = json.loads(p.marker("5D").read_text())
        marker["wave"] = "9Z"
        p.marker("5D").write_text(json.dumps(marker))
        code, _, err = p.stop(PASS_REPORT)
        self.assertEqual(code, 0)
        self.assertIn("cannot place", err)
        self.assertFalse((p.root / "docs/wave-9z").exists())

    def test_stdin_that_is_not_a_hook_event_is_refused(self):
        p = self.dispatched()
        for payload in (PASS_REPORT, "[]"):
            code, out, err = p.hook(payload)
            self.assertEqual((code, out), (3, ""))
            self.assertIn("run by the evaluator hook", err)
        self.assertEqual(p.records("5D"), [])

    def test_a_failure_never_exits_two(self):
        # Exit 2 on SubagentStop would hand the subagent a traceback as its instruction.
        p = self.dispatched()
        event = dict(p.event("PostToolUse", PASS_REPORT), tool_input="not an object")
        code, out, err = p.hook(event)
        self.assertEqual((code, out), (1, ""))
        self.assertIn("Nothing recorded", err)


class TestHandback(Base):
    """Auto mode: the report goes through SubagentHandback, and SubagentStop is empty."""

    def test_a_bad_report_is_denied_before_the_hand_over(self):
        p = self.dispatched()
        code, out, err = p.hook(p.event("PreToolUse", "looks fine to me\n"))
        self.assertEqual((code, out), (2, ""))
        self.assertIn("was not recorded: it carries no VERDICT line", err)
        self.assertEqual(json.loads(p.marker("5D").read_text())["rounds"], 1)

    def test_a_good_report_passes_pre_and_is_recorded_post(self):
        p = self.dispatched()
        self.assertEqual(p.hook(p.event("PreToolUse", PASS_REPORT)), (0, "", ""))
        self.assertEqual(p.records("5D"), [])
        code, out, _ = p.hook(p.event("PostToolUse", PASS_REPORT))
        self.assertEqual((code, out), (0, ""))
        written = (p.root / "docs/wave-5d/evaluation-1.md").read_text()
        self.assertIn("(PostToolUse on SubagentHandback)", written)
        self.assertFalse(p.marker("5D").exists())

    def test_one_pass_is_recorded_once_whichever_event_comes_after(self):
        p = self.dispatched()
        p.hook(p.event("PostToolUse", PASS_REPORT))
        before = (p.root / "docs/wave-5d/evaluation-1.md").read_text()
        stop = p.event("SubagentStop", None)
        del stop["last_assistant_message"]   # what auto mode sends, measured on 2.1.287
        self.assertEqual(p.hook(stop), (0, "", ""))
        self.assertEqual(p.stop(PASS_REPORT)[0], 0)
        self.assertEqual(p.records("5D"), ["evaluation-1.md"])
        self.assertEqual((p.root / "docs/wave-5d/evaluation-1.md").read_text(), before)

    def test_after_two_denials_the_hand_over_goes_through_unrecorded(self):
        p = self.dispatched()
        bad = p.event("PreToolUse", "VERDICT: PASS\n\n### [HIGH] AC-3 untested\n")
        self.assertEqual([p.hook(bad)[0] for _ in range(3)], [2, 2, 0])
        code, out, err = p.hook(dict(bad, hook_event_name="PostToolUse"))
        self.assertEqual((code, out), (0, ""))
        self.assertIn("not recorded", err)
        self.assertEqual(p.records("5D"), [])
        self.assertIn("[HIGH]", json.loads(p.marker("5D").read_text())["refused"])

    def test_a_handback_from_another_tool_or_agent_is_ignored(self):
        p = self.dispatched()
        other = dict(p.event("PostToolUse", PASS_REPORT), tool_name="Bash")
        self.assertEqual(p.hook(other), (0, "", ""))
        self.assertEqual(p.hook(p.event("PostToolUse", PASS_REPORT, agent="Explore")), (0, "", ""))
        self.assertEqual(p.records("5D"), [])


@unittest.skipUnless(FIXTURES.is_dir(), "no recorded hook events beside this test")
class TestRecordedEvents(Base):
    """Hook events as CLI 2.1.287 sent them, one per path, from a real dispatch.

    Only the paths in them were shortened. Replayed against a fresh dispatch
    under the event's own session id.
    """

    def replay(self, name):
        event = json.loads((FIXTURES / name).read_text())
        p = self.project()
        p.verified("5D")
        self.assertEqual(p.run("dispatch", "--wave", "5D", session=event["session_id"])[0], 0)
        event["cwd"] = str(p.root)
        return p, event

    def test_subagent_stop_outside_auto_mode(self):
        p, event = self.replay("subagent-stop.json")
        self.assertEqual(p.hook(event)[:2], (0, ""))
        self.assertIn("(SubagentStop)", (p.root / "docs/wave-5d/evaluation-1.md").read_text())

    def test_handback_in_auto_mode(self):
        p, event = self.replay("post-tool-use-handback.json")
        self.assertEqual(p.hook(dict(event, hook_event_name="PreToolUse"))[:2], (0, ""))
        self.assertEqual(p.hook(event)[:2], (0, ""))
        self.assertIn("(PostToolUse on SubagentHandback)",
                      (p.root / "docs/wave-5d/evaluation-1.md").read_text())

    def test_subagent_stop_after_a_handback_carries_no_report(self):
        p, event = self.replay("subagent-stop-after-handback.json")
        self.assertNotIn("last_assistant_message", event)
        self.assertEqual(p.hook(event), (0, "", ""))
        self.assertEqual(p.records("5D"), [])


# ------------------------------------------------------------- the verdict

class TestVerdict(Base):
    def recorded(self, report):
        p = self.dispatched()
        p.stop(report)
        return p

    def test_pass_exits_zero(self):
        code, out, err = self.recorded(PASS_REPORT).run("verdict", "--wave", "5D")
        self.assertEqual(code, 0)
        self.assertEqual(out["verdict"], "PASS")
        self.assertEqual(out["recorded_to"], "docs/wave-5d/evaluation-1.md")
        self.assertIn("Continue at step 9", err)

    def test_needs_work_exits_one(self):
        code, out, err = self.recorded(NEEDS_WORK_REPORT).run("verdict", "--wave", "5D")
        self.assertEqual(code, 1)
        self.assertEqual(out["verdict"], "NEEDS_WORK")
        self.assertIn("Do not fix these findings in this session", err)

    def test_upstream_cause_exits_four_and_names_the_fix_on_record(self):
        p = self.recorded("VERDICT: UPSTREAM_CAUSE\n\n## Upstream cause\n")
        code, out, err = p.run("verdict", "--wave", "5D")
        self.assertEqual(code, 4)
        self.assertEqual(out["verdict"], "UPSTREAM_CAUSE")
        self.assertIn("do not run a fourth pass", err)
        self.assertIn('--reason "upstream fix: <the artifact>"', err)

    def test_a_dispatch_with_nothing_recorded_is_refused(self):
        p = self.dispatched()
        code, out, err = p.run("verdict", "--wave", "5D")
        self.assertEqual(code, 3)
        self.assertEqual(out["pending_pass"], 1)
        self.assertIn("nothing is recorded", err)

    def test_an_earlier_pass_does_not_answer_for_a_pending_one(self):
        p = self.project()
        p.evaluation("5D", 1, "PASS")
        p.verified("5D")
        p.run("dispatch", "--wave", "5D")
        self.assertEqual(p.run("verdict", "--wave", "5D")[0], 3)

    def test_no_evaluation_is_refused(self):
        code, _, err = self.project().run("verdict", "--wave", "5D")
        self.assertEqual(code, 3)
        self.assertIn("no evaluation on disk", err)


# ------------------------------------- the findings open the next session

class TestOpeningPrompt(Base):
    def test_needs_work_becomes_the_opening_prompt(self):
        """Done criterion (3), and it survives the session that built the wave."""
        p = self.dispatched()
        p.stop(NEEDS_WORK_REPORT)
        code, out, err = p.run("opening-prompt", "--wave", "5D")
        self.assertEqual(code, 1)
        self.assertTrue(out["open"])
        self.assertIn("AC-3 has no assertion", out["prompt"])
        self.assertIn("src/pay.py:88", err)
        self.assertIn("resuming wave 5D", out["prompt"])

    def test_pass_owes_nothing(self):
        p = self.dispatched()
        p.stop(PASS_REPORT)
        code, out, err = p.run("opening-prompt", "--wave", "5D")
        self.assertEqual(code, 0)
        self.assertFalse(out["open"])
        self.assertIn("Nothing is owed", err)

    def test_latest_record_wins(self):
        p = self.project()
        p.evaluation("5D", 1, "NEEDS_WORK")
        p.evaluation("5D", 2, "PASS")
        code, out, _ = p.run("opening-prompt", "--wave", "5D")
        self.assertEqual(code, 0)
        self.assertFalse(out["open"])

    def test_prompt_warns_when_next_pass_is_the_third(self):
        p = self.project()
        p.evaluation("5D", 1, "NEEDS_WORK")
        p.evaluation("5D", 2, "NEEDS_WORK")
        _, out, _ = p.run("opening-prompt", "--wave", "5D")
        self.assertIn("third-pass rule is armed", out["prompt"])

    def test_no_evaluation_owes_nothing(self):
        code, out, err = self.project().run("opening-prompt", "--wave", "5D")
        self.assertEqual(code, 0)
        self.assertFalse(out["open"])
        self.assertIn("no evaluation on disk", err)

    def test_corrupt_record_is_refused_not_guessed(self):
        p = self.project()
        (p.docs("5D") / "evaluation-1.md").write_text("the reviewer seemed happy\n")
        code, _, err = p.run("opening-prompt", "--wave", "5D")
        self.assertEqual(code, 3)
        self.assertIn("do not guess", err)


if __name__ == "__main__":
    unittest.main()
