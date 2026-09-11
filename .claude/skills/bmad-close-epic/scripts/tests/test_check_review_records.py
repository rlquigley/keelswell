#!/usr/bin/env python3
"""Tests for check_review_records.py. Stdlib only; run with `python3 -m unittest`."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "check_review_records.py"

WAVE_MAP = """# Wave Map

| Wave | Pattern | Stories | Branch suffix | Notes |
|---|---|---|---|---|
| 7A | serial | 7.1 | wave-7a-alpha | First. |
| 7B | serial | 7.2 | wave-7b-beta | Second. |
| 8A | serial | 8.1 | wave-8a-gamma | Another epic. |
"""


def git(root, *args, when=None):
    env = None
    if when is not None:
        import os
        env = dict(os.environ, GIT_COMMITTER_DATE=when, GIT_AUTHOR_DATE=when)
    subprocess.run(["git", "-C", str(root), *args], check=True,
                   capture_output=True, env=env)


class Project:
    """A throwaway project tree with a wave map and a git history."""

    def __init__(self, stack):
        self.root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        (self.root / "_bmad-output" / "planning-artifacts").mkdir(parents=True)
        (self.root / "_bmad-output" / "planning-artifacts" / "waves.md").write_text(WAVE_MAP)
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "t@example.com")
        git(self.root, "config", "user.name", "t")

    def land(self, wave, when, record=None):
        """Add docs/wave-<id>/ at `when`, optionally carrying a record."""
        d = self.root / "docs" / f"wave-{wave.lower()}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "test-design.md").write_text("design\n")
        if record == "canonical":
            (d / "review-party.md").write_text("# Party review\n")
        elif record == "amendments":
            (d / "api-surface.md").write_text("# API\n\n## Party-review amendments\n\nnone\n")
        elif record == "api-surface-only":
            (d / "api-surface.md").write_text("# API\n\nno review section here\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", f"wave {wave}", when=when)

    def run(self, epic):
        p = subprocess.run([sys.executable, str(SCRIPT), "--project-root", str(self.root),
                            "--epic", str(epic)], capture_output=True, text=True)
        return p.returncode, p.stdout, p.stderr


class TestGate(unittest.TestCase):
    def setUp(self):
        import contextlib
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.p = Project(self.stack)

    def test_record_present_passes(self):
        self.p.land("7A", "2026-09-11T09:00:00Z", record="canonical")
        self.p.land("7B", "2026-09-11T10:00:00Z", record="canonical")
        code, _, _ = self.p.run(7)
        self.assertEqual(code, 0)

    def test_api_surface_amendments_count_as_a_record(self):
        self.p.land("7A", "2026-09-11T09:00:00Z", record="amendments")
        self.p.land("7B", "2026-09-11T10:00:00Z", record="canonical")
        self.assertEqual(self.p.run(7)[0], 0)

    def test_api_surface_without_the_section_is_not_a_record(self):
        self.p.land("7A", "2026-09-11T09:00:00Z", record="canonical")
        self.p.land("7B", "2026-09-11T10:00:00Z", record="api-surface-only")
        code, _, err = self.p.run(7)
        self.assertEqual(code, 1)
        self.assertIn("7B", err)

    def test_missing_record_after_the_rule_date_refuses(self):
        self.p.land("7A", "2026-09-11T09:00:00Z", record="canonical")
        self.p.land("7B", "2026-09-11T10:00:00Z")
        code, _, err = self.p.run(7)
        self.assertEqual(code, 1)
        self.assertIn("no review record", err)

    def test_missing_record_before_the_rule_date_is_a_gap_not_a_refusal(self):
        self.p.land("7A", "2026-09-01T09:00:00Z")
        self.p.land("7B", "2026-09-02T09:00:00Z", record="canonical")
        code, out, err = self.p.run(7)
        self.assertEqual(code, 0)
        self.assertIn("Pre-rule gaps", err)
        self.assertIn("7A", out)

    def test_the_rule_date_itself_is_on_the_refusing_side(self):
        self.p.land("7A", "2026-09-10T00:00:01Z")
        self.p.land("7B", "2026-09-10T01:00:00Z", record="canonical")
        self.assertEqual(self.p.run(7)[0], 1)

    def test_a_wave_that_never_landed_cannot_be_dated(self):
        self.p.land("7A", "2026-09-01T09:00:00Z", record="canonical")
        code, _, err = self.p.run(7)  # 7B has no docs directory at all
        self.assertEqual(code, 3)
        self.assertIn("cannot date", err)

    def test_epic_selection_ignores_other_epics(self):
        self.p.land("7A", "2026-09-11T09:00:00Z", record="canonical")
        self.p.land("7B", "2026-09-11T09:30:00Z", record="canonical")
        self.p.land("8A", "2026-09-11T10:00:00Z")  # epic 8 is broken, epic 7 is not
        self.assertEqual(self.p.run(7)[0], 0)
        self.assertEqual(self.p.run(8)[0], 1)

    def test_unknown_epic_is_structural(self):
        self.p.land("7A", "2026-09-11T09:00:00Z", record="canonical")
        code, _, err = self.p.run(9)
        self.assertEqual(code, 2)
        self.assertIn("no waves", err)

    def test_no_wave_map_is_structural(self):
        (self.p.root / "_bmad-output" / "planning-artifacts" / "waves.md").unlink()
        code, _, err = self.p.run(7)
        self.assertEqual(code, 2)
        self.assertIn("no wave map", err)


if __name__ == "__main__":
    unittest.main()
