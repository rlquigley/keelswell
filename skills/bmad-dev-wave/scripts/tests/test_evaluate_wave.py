#!/usr/bin/env python3
"""Tests for evaluate_wave.py. Stdlib only; run with `python3 -m unittest`."""

import contextlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "evaluate_wave.py"

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
---

# Wave evaluator
"""


class Project:
    """A throwaway project tree with a wave map and an evaluator definition."""

    def __init__(self, stack, definition=SAFE_DEFINITION, wave_map=WAVE_MAP):
        self.root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        if wave_map is not None:
            d = self.root / "_bmad-output" / "planning-artifacts"
            d.mkdir(parents=True)
            (d / "waves.md").write_text(wave_map)
        if definition is not None:
            d = self.root / ".claude" / "agents"
            d.mkdir(parents=True)
            (d / "keelswell-wave-evaluator.md").write_text(definition)

    def evaluation(self, wave, n, verdict):
        d = self.root / "docs" / f"wave-{wave.lower()}"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"evaluation-{n}.md").write_text(
            f"VERDICT: {verdict}\nWAVE: {wave}\nPASS: {n}\n\n"
            f"## Findings\nSomething about pass {n}.\n")

    def evidence(self, wave):
        d = self.root / "docs" / f"wave-{wave.lower()}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "test-design.md").write_text("# Test design\n")
        (d / "wave-diff.patch").write_text("diff --git a/x b/x\n")
        (d / "verify-output.txt").write_text("12 passed\n")

    def run(self, *args, stdin=None):
        p = subprocess.run(
            [sys.executable, str(SCRIPT), *args,
             "--project-root", str(self.root)],
            capture_output=True, text=True, input=stdin)
        out = json.loads(p.stdout) if p.stdout.strip() else {}
        return p.returncode, out, p.stderr


class Base(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)

    def project(self, **kw):
        return Project(self.stack, **kw)


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

    def test_write_is_refused(self):
        d = SAFE_DEFINITION.replace("  - Grep\n", "  - Grep\n  - Write\n")
        code, out, err = self.project(definition=d).run("check")
        self.assertEqual(code, 3)
        self.assertFalse(out["safe"])
        self.assertEqual(out["denied_tools"], ["Write"])
        self.assertIn("write, run or delegate", err)

    def test_edit_is_refused(self):
        d = SAFE_DEFINITION.replace("  - Grep\n", "  - Grep\n  - Edit\n")
        code, out, _ = self.project(definition=d).run("check")
        self.assertEqual(code, 3)
        self.assertEqual(out["denied_tools"], ["Edit"])

    def test_bash_is_refused(self):
        """RQ ruled no Bash: `bash -c 'cat > f'` is an edit."""
        d = SAFE_DEFINITION.replace("  - Grep\n", "  - Grep\n  - Bash\n")
        code, out, _ = self.project(definition=d).run("check")
        self.assertEqual(code, 3)
        self.assertEqual(out["denied_tools"], ["Bash"])

    def test_task_is_refused(self):
        """Delegation is the loophole: a spawned subagent inherits nothing."""
        d = SAFE_DEFINITION.replace("  - Grep\n", "  - Grep\n  - Task\n")
        code, out, _ = self.project(definition=d).run("check")
        self.assertEqual(code, 3)
        self.assertEqual(out["denied_tools"], ["Task"])

    def test_mcp_write_tool_is_refused(self):
        """A denied tool behind an MCP prefix is still that tool."""
        d = SAFE_DEFINITION.replace(
            "  - Grep\n", "  - Grep\n  - mcp__somewhere__write\n")
        code, out, _ = self.project(definition=d).run("check")
        self.assertEqual(code, 3)
        self.assertEqual(out["denied_tools"], ["mcp__somewhere__write"])

    def test_inline_tool_list_is_read(self):
        d = SAFE_DEFINITION.replace(
            "tools:\n  - Read\n  - Glob\n  - Grep\n", "tools: Read, Glob, Grep\n")
        code, out, _ = self.project(definition=d).run("check")
        self.assertEqual(code, 0)
        self.assertEqual(out["declared_tools"], ["Read", "Glob", "Grep"])

    def test_missing_tools_key_is_refused(self):
        """Absent is not empty: a subagent with no list inherits everything."""
        d = SAFE_DEFINITION.replace("tools:\n  - Read\n  - Glob\n  - Grep\n", "")
        code, out, err = self.project(definition=d).run("check")
        self.assertEqual(code, 3)
        self.assertFalse(out["safe"])
        self.assertIn("declares no tools", err)

    def test_wildcard_is_refused(self):
        d = SAFE_DEFINITION.replace(
            "tools:\n  - Read\n  - Glob\n  - Grep\n", "tools: '*'\n")
        code, _, err = self.project(definition=d).run("check")
        self.assertEqual(code, 3)
        self.assertIn("every tool", err)

    def test_no_frontmatter_is_refused(self):
        code, _, err = self.project(definition="# Wave evaluator\n").run("check")
        self.assertEqual(code, 3)
        self.assertIn("no frontmatter", err)

    def test_missing_definition_is_refused(self):
        code, out, err = self.project(definition=None).run("check")
        self.assertEqual(code, 3)
        self.assertFalse(out["safe"])
        self.assertIn("No evaluator definition", err)

    def test_unrecognized_tool_is_refused_not_allowed(self):
        """The default is refuse. A tool the check has never heard of is not
        evidence that it cannot edit."""
        d = SAFE_DEFINITION.replace("  - Grep\n", "  - Grep\n  - Teleport\n")
        code, out, err = self.project(definition=d).run("check")
        self.assertEqual(code, 3)
        self.assertEqual(out["unrecognized_tools"], ["Teleport"])
        self.assertIn("does not recognize", err)


# ------------------------------------------------------------ the dispatch

class TestDispatch(Base):
    def test_first_pass(self):
        p = self.project()
        p.evidence("5D")
        code, out, err = p.run("dispatch", "--wave", "5D")
        self.assertEqual(code, 0)
        self.assertEqual(out["pass_number"], 1)
        self.assertFalse(out["third_pass_rule"])
        self.assertEqual(out["evidence_missing"], [])
        self.assertIn("evaluation pass 1", err)

    def test_pass_number_counts_records_not_conversation(self):
        p = self.project()
        p.evaluation("5D", 1, "NEEDS_WORK")
        code, out, _ = p.run("dispatch", "--wave", "5D")
        self.assertEqual(out["pass_number"], 2)
        self.assertFalse(out["third_pass_rule"])
        self.assertEqual(out["prior_verdicts"], ["NEEDS_WORK"])

    def test_third_pass_rule_arms(self):
        """Done criterion (4): the rule fires from a count on disk."""
        p = self.project()
        p.evaluation("5D", 1, "NEEDS_WORK")
        p.evaluation("5D", 2, "NEEDS_WORK")
        code, out, err = p.run("dispatch", "--wave", "5D")
        self.assertEqual(code, 0)
        self.assertEqual(out["pass_number"], 3)
        self.assertTrue(out["third_pass_rule"])
        self.assertIn("THIRD-PASS RULE ARMED", err)
        self.assertIn("UPSTREAM_CAUSE", err)

    def test_unsafe_definition_blocks_dispatch(self):
        d = SAFE_DEFINITION.replace("  - Grep\n", "  - Grep\n  - Write\n")
        p = self.project(definition=d)
        code, out, _ = p.run("dispatch", "--wave", "5D")
        self.assertEqual(code, 3)
        self.assertEqual(out["wave"], "5D")

    def test_missing_evidence_is_named(self):
        code, out, err = self.project().run("dispatch", "--wave", "5D")
        self.assertEqual(code, 0)
        self.assertEqual(sorted(out["evidence_missing"]),
                         ["diff", "test_design", "verify_output"])
        self.assertIn("has no Bash", err)

    def test_case_insensitive_wave(self):
        p = self.project()
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


# ------------------------------------------------------------- the verdict

class TestRecord(Base):
    def test_pass_exits_zero_and_writes(self):
        p = self.project()
        code, out, err = p.run("record", "--wave", "5D",
                               stdin="VERDICT: PASS\nWAVE: 5D\n\n## Findings\nNone.\n")
        self.assertEqual(code, 0)
        self.assertEqual(out["verdict"], "PASS")
        self.assertEqual(out["recorded_to"], "docs/wave-5d/evaluation-1.md")
        self.assertTrue((p.root / out["recorded_to"]).is_file())
        self.assertIn("Continue at step 8", err)

    def test_needs_work_exits_one(self):
        p = self.project()
        code, out, err = p.run(
            "record", "--wave", "5D",
            stdin="VERDICT: NEEDS_WORK\n\n## Findings\n### [HIGH] x\n")
        self.assertEqual(code, 1)
        self.assertEqual(out["verdict"], "NEEDS_WORK")
        self.assertIn("Do not fix these findings in this session", err)

    def test_upstream_cause_exits_four(self):
        p = self.project()
        code, out, err = p.run("record", "--wave", "5D",
                               stdin="VERDICT: UPSTREAM_CAUSE\n\n## Upstream cause\n")
        self.assertEqual(code, 4)
        self.assertEqual(out["verdict"], "UPSTREAM_CAUSE")
        self.assertIn("do not run a fourth pass", err)

    def test_unparseable_verdict_is_refused(self):
        """The verdict is the evaluator's word or it is nothing."""
        p = self.project()
        code, _, err = p.run("record", "--wave", "5D",
                             stdin="I think this looks pretty good overall!\n")
        self.assertEqual(code, 3)
        self.assertIn("no readable VERDICT", err)
        self.assertFalse((p.root / "docs" / "wave-5d").exists())

    def test_records_do_not_overwrite(self):
        p = self.project()
        p.run("record", "--wave", "5D", stdin="VERDICT: NEEDS_WORK\n")
        code, out, _ = p.run("record", "--wave", "5D", stdin="VERDICT: PASS\n")
        self.assertEqual(out["pass_number"], 2)
        self.assertEqual(out["recorded_to"], "docs/wave-5d/evaluation-2.md")
        self.assertTrue((p.root / "docs/wave-5d/evaluation-1.md").is_file())

    def test_body_is_stored_verbatim(self):
        p = self.project()
        body = "VERDICT: NEEDS_WORK\n\n## Findings\n### [HIGH] no test for AC-3\n"
        _, out, _ = p.run("record", "--wave", "5D", stdin=body)
        written = (p.root / out["recorded_to"]).read_text()
        self.assertIn("### [HIGH] no test for AC-3", written)
        self.assertIn("unedited", written)


# ------------------------------------- the findings open the next session

class TestOpeningPrompt(Base):
    def test_needs_work_becomes_the_opening_prompt(self):
        """Done criterion (3), and it survives the session that built the wave."""
        p = self.project()
        p.run("record", "--wave", "5D",
              stdin="VERDICT: NEEDS_WORK\n\n## Findings\n"
                    "### [HIGH] AC-3 has no assertion\n- Where: src/pay.py:88\n")
        code, out, err = p.run("opening-prompt", "--wave", "5D")
        self.assertEqual(code, 1)
        self.assertTrue(out["open"])
        self.assertIn("AC-3 has no assertion", out["prompt"])
        self.assertIn("src/pay.py:88", err)
        self.assertIn("resuming wave 5D", out["prompt"])

    def test_pass_owes_nothing(self):
        p = self.project()
        p.run("record", "--wave", "5D", stdin="VERDICT: PASS\n")
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
        d = p.root / "docs" / "wave-5d"
        d.mkdir(parents=True)
        (d / "evaluation-1.md").write_text("the reviewer seemed happy\n")
        code, _, err = p.run("opening-prompt", "--wave", "5D")
        self.assertEqual(code, 3)
        self.assertIn("do not guess", err)


if __name__ == "__main__":
    unittest.main()
