#!/usr/bin/env python3
"""Tests for the subagent definitions dev-wave dispatches by name. Stdlib only.

R4 of docs/reviews/harness-engineering-review-v1.md: a subagent's model and
effort bind in its definition's frontmatter and nowhere else, so steps 6, 8
and 10 each dispatch a named definition under .claude/agents/. Whether a
definition matches the fork's tier table is `./install.sh --validate-only`'s
check, which reads core/config.yaml; what is pinned here holds in the fork
and in an instance alike: the files exist, each is the definition its name
says, each states a full model id and an effort, and the skill still
dispatches them by name.
"""

import re
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2] / "SKILL.md"
DEFINITIONS = ("keelswell-wave-coder", "keelswell-wave-reviewer", "keelswell-wave-evaluator")
EFFORTS = ("low", "medium", "high", "xhigh", "max")


def find_agents():
    """.claude/agents/, wherever this test tree sits: skills/, .claude/skills/, an instance."""
    for d in Path(__file__).resolve().parents:
        if (d / ".claude" / "agents").is_dir():
            return d / ".claude" / "agents"
    return None


def frontmatter(path):
    block = re.match(r"---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.S).group(1)
    return dict(re.findall(r"^([A-Za-z]+):[ \t]*(\S.*)?$", block, re.M))


class TestAgentDefinitions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agents = find_agents()

    def test_every_dispatched_definition_states_its_model_and_effort(self):
        self.assertIsNotNone(self.agents, "no .claude/agents/ above this test")
        for name in DEFINITIONS:
            with self.subTest(name):
                front = frontmatter(self.agents / f"{name}.md")
                self.assertEqual(front.get("name"), name)
                # A full id, not an alias: `opus` resolves to the session's own
                # model when the session is on Opus, and follows releases.
                self.assertRegex(front.get("model", ""), r"^claude-[a-z]+-\d")
                self.assertIn(front.get("effort"), EFFORTS)

    def test_coder_and_reviewer_inherit_their_tools(self):
        # A coder writes code, and a reviewer proves a finding by mutation and
        # execution (RQ, 2026-10-01). The evaluator's list is evaluate_wave.py
        # check's to guard, and stays Read, Glob, Grep.
        for name in ("keelswell-wave-coder", "keelswell-wave-reviewer"):
            with self.subTest(name):
                front = frontmatter(self.agents / f"{name}.md")
                self.assertNotIn("tools", front)
                self.assertNotIn("disallowedTools", front)

    def test_the_skill_dispatches_them_by_name(self):
        text = SKILL.read_text(encoding="utf-8")
        for name in DEFINITIONS:
            with self.subTest(name):
                self.assertIn(f"`{name}`", text)


class TestReviewerIsolation(unittest.TestCase):
    """What step 10's dispatch prompt gives each reviewer. ffbapp, 2026-10-07:
    reviewers in sibling detached worktrees could not use git or Edit there
    (the desktop app's worktree isolation), Tess overwrote the lead's script
    in a shared scratch directory, and concurrent verify lanes collided on one
    database. Wave 6B's reviewers bypassed gitleaks to commit a baseline."""

    @classmethod
    def setUpClass(cls):
        text = SKILL.read_text(encoding="utf-8")
        start = text.index("## The Reviewer Selection")
        cls.section = text[start:text.index("## The Review Record", start)]

    def test_each_reviewer_gets_its_own_copy_of_the_worktree(self):
        self.assertIn("rsync", self.section)
        self.assertIn("{scratch}/<name>/tree", self.section)

    def test_each_reviewer_gets_its_own_scratch_directory(self):
        self.assertIn("{scratch}/<name>/", self.section)
        self.assertIn("Name no other reviewer", self.section)

    def test_each_reviewer_gets_its_own_verify_database(self):
        self.assertIn("Its own verify database", self.section)

    def test_the_prompt_says_which_tools_work(self):
        self.assertIn("git worktree add --detach", self.section)
        self.assertIn("checksum", self.section)

    def test_no_reviewer_commits_past_the_secret_scan(self):
        self.assertIn("--no-verify", self.section)
        self.assertIn("core.hooksPath", self.section)

    def test_the_wave_worktree_is_checked_unchanged_afterwards(self):
        self.assertIn("git -C {worktree} status --porcelain", self.section)


if __name__ == "__main__":
    unittest.main()
