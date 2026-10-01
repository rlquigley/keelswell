#!/usr/bin/env python3
"""Tests for templates/settings.json.template. Stdlib only; run with `python3 -m unittest`.

R2 of docs/reviews/harness-engineering-review-v1.md: the merge halt, the
verdict rule and the lifecycle record get a permission-layer backing, so they
hold where the hook does not run (an untrusted workspace, disableAllHooks, a
checkout with no wrapper). Claude Code enforces these rules, not the model,
and nothing here can check that; what is pinned is that the template still
declares them, beside the hook registration R1 left.

The template is fork-only. An instance carries the resolved
.claude/settings.json instead, and `./install.sh --validate-only
--target-project <instance>` checks that file against the template, so these
skip there.
"""

import json
import unittest
from pathlib import Path


def find_up(rel):
    """A fork-only file, wherever this test tree sits: skills/, .claude/skills/, an instance."""
    for d in Path(__file__).resolve().parents:
        if (d / rel).is_file():
            return d / rel
    return None


TEMPLATE = find_up(Path("templates") / "settings.json.template")

# First match wins in the order deny, ask, allow, whatever a rule's position
# or specificity: a force push is denied although `git push *` would ask.
DENY = [
    "Bash(gh pr merge *)",
    "Bash(git push --force *)",
    "Bash(git push -f *)",
    "Bash(git reset --hard *)",
    "Bash(git clean -f*)",
    "Edit(/**/docs/wave-*/evaluation-*.md)",
    "Edit(/.bmad/**/wave.md)",
]
ASK = [
    "Bash(git push *)",
    "Bash(git branch -D *)",
    "Bash(git worktree remove *)",
    "Bash(gh auth token*)",
]


@unittest.skipIf(TEMPLATE is None, "templates/settings.json.template is fork-only; an instance's "
                 "settings.json is checked by ./install.sh --validate-only --target-project")
class TestSettingsTemplate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The placeholders sit inside string values, so the template parses as it stands.
        cls.settings = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        cls.permissions = cls.settings["permissions"]

    def test_every_deny_rule_is_present(self):
        for rule in DENY:
            with self.subTest(rule):
                self.assertIn(rule, self.permissions["deny"])

    def test_every_ask_rule_is_present(self):
        for rule in ASK:
            with self.subTest(rule):
                self.assertIn(rule, self.permissions["ask"])

    def test_file_rules_are_edit_rules_anchored_at_the_project_root(self):
        # Claude Code consults Edit(path) and Read(path) only: a Write(...) path
        # rule is accepted and never matched. A pattern with no leading slash
        # anchors at the session's current directory, which a `cd` moves.
        for rule in self.permissions["deny"] + self.permissions["ask"]:
            tool, _, spec = rule.partition("(")
            with self.subTest(rule):
                self.assertIn(tool, ("Bash", "Edit"))
                if tool == "Edit":
                    self.assertTrue(spec.startswith("/") and not spec.startswith("//"), rule)

    def test_the_lifecycle_rule_leaves_the_step_markers_writable(self):
        # dev-wave writes checkpoint.json, step-N.done and step-4.5.pending under
        # .bmad/wave-<id>/ with whichever tool the agent picks, and an Edit deny
        # also stops Write and a redirect. Only wave.md is locked (ruling d).
        for rule in self.permissions["deny"]:
            with self.subTest(rule):
                self.assertFalse(rule.startswith("Edit(") and ".bmad" in rule
                                 and not rule.endswith("/wave.md)"), rule)

    def test_bypass_is_locked_and_auto_is_not(self):
        self.assertEqual(self.permissions.get("disableBypassPermissionsMode"), "disable")
        self.assertNotIn("disableAutoMode", self.permissions)
        self.assertNotIn("disableAutoMode", self.settings)
        self.assertEqual(self.permissions.get("defaultMode"), "acceptEdits")

    def test_the_gate_registration_is_r1s(self):
        self.assertEqual(self.settings["hooks"]["PreToolUse"], [{
            "matcher": "Write|Edit|MultiEdit|NotebookEdit|Bash|Monitor",
            "hooks": [{"type": "command",
                       "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/wave-gate.sh",
                       "args": [], "timeout": 30}],
        }])
        ends = [h["command"] for entry in self.settings["hooks"]["SessionEnd"] for h in entry["hooks"]]
        self.assertIn(".claude/hooks/wave-session-end.sh", ends)


if __name__ == "__main__":
    unittest.main()
