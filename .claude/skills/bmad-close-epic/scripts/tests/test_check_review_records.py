#!/usr/bin/env python3
"""Tests for check_review_records.py. Stdlib only; run with `python3 -m unittest`."""

import os
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


def stamped(wave):
    """A record with the front matter bmad-dev-wave 1.5.0 requires."""
    return (f'---\ntitle: "Wave {wave} party-mode adversarial review"\nwave: {wave}\n'
            f"created: 2026-09-13\nmodel: claude-opus-5-5\neffort: high\n---\n\n"
            "# Party review\n\nNo findings.\n")


class Project:
    """A throwaway project tree with a wave map and a git history."""

    def __init__(self, stack):
        self.root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        (self.root / "_bmad-output" / "planning-artifacts").mkdir(parents=True)
        (self.root / "_bmad-output" / "planning-artifacts" / "waves.md").write_text(WAVE_MAP)
        git(self.root, "init", "-q")
        git(self.root, "symbolic-ref", "HEAD", "refs/heads/main")
        git(self.root, "config", "user.email", "t@example.com")
        git(self.root, "config", "user.name", "t")

    def seed(self):
        """A first commit on main, so a wave branch has somewhere to merge back."""
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "seed", when="2026-08-01T00:00:00Z")

    def land_via_merge(self, wave, committed, merged, record=None):
        """Land a wave on a side branch at `committed`, merge it at `merged`.

        The shape every real wave has: docs written on the wave's own branch,
        visible on the closing branch only once the merge lands. The two dates
        differ, and a wave can straddle the rule date between them.
        """
        git(self.root, "checkout", "-q", "-b", f"wave-{wave.lower()}")
        self.land(wave, committed, record=record)
        git(self.root, "checkout", "-q", "-")
        git(self.root, "merge", "-q", "--no-ff", "-m", f"Merge wave {wave}",
            f"wave-{wave.lower()}", when=merged)

    def land(self, wave, when, record=None):
        """Add docs/wave-<id>/ at `when`, optionally carrying a record."""
        d = self.root / "docs" / f"wave-{wave.lower()}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "test-design.md").write_text("design\n")
        if record == "canonical":
            (d / "review-party.md").write_text("# Party review\n")
        elif record == "stamped":
            (d / "review-party.md").write_text(stamped(wave))
        elif record == "empty":
            (d / "review-party.md").write_text("")
        elif record == "no-model":
            (d / "review-party.md").write_text(
                stamped(wave).replace("model: claude-opus-5-5\n", ""))
        elif record == "wrong-wave":
            (d / "review-party.md").write_text(stamped("9Z"))
        elif record == "amendments":
            (d / "api-surface.md").write_text("# API\n\n## Party-review amendments\n\nnone\n")
        elif record == "api-surface-only":
            (d / "api-surface.md").write_text("# API\n\nno review section here\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", f"wave {wave}", when=when)

    def run(self, epic, *extra, env=None, cwd=None):
        p = subprocess.run([sys.executable, str(SCRIPT), "--project-root", str(self.root),
                            "--epic", str(epic), *extra], capture_output=True, text=True,
                           env=env, cwd=cwd)
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

    def test_a_wave_is_dated_by_its_merge_not_its_branch_commit(self):
        """The straddle: committed before the rule, merged after it.

        Measured in a real instance at a 35-hour lag, with the two dates on
        opposite sides of the rule date. Dating by the branch commit passes
        this wave as pre-rule when its merge says refuse.
        """
        self.p.land("7A", "2026-09-01T09:00:00Z", record="canonical")
        self.p.land_via_merge("7B", "2026-09-09T03:00:00Z", "2026-09-10T14:42:00Z")
        code, out, err = self.p.run(7)
        self.assertEqual(code, 1, "a wave merged after the rule date must refuse")
        self.assertIn("2026-09-10", out)

    def test_a_wave_merged_before_the_rule_is_still_a_gap(self):
        self.p.land("7A", "2026-09-01T09:00:00Z", record="canonical")
        self.p.land_via_merge("7B", "2026-09-05T03:00:00Z", "2026-09-06T14:00:00Z")
        code, _, err = self.p.run(7)
        self.assertEqual(code, 0)
        self.assertIn("Pre-rule gaps", err)

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



# After dev-wave 1.5.0 made the front matter required (2026-09-12).
STAMPED = "2026-09-13T09:00:00Z"


class TestRecordProvenance(unittest.TestCase):
    """V2-12: a record counts only from the main line, non-empty, and, for a
    wave that landed from 2026-09-12 on, with its front matter."""

    def setUp(self):
        import contextlib
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.p = Project(self.stack)
        self.p.seed()

    def test_a_record_merged_with_its_wave_passes(self):
        self.p.land_via_merge("7A", STAMPED, STAMPED, record="stamped")
        self.p.land_via_merge("7B", STAMPED, STAMPED, record="stamped")
        code, _, err = self.p.run(7)
        self.assertEqual(code, 0, err)

    def test_an_untracked_record_fails(self):
        self.p.land("7A", STAMPED, record="stamped")
        self.p.land("7B", STAMPED)
        (self.p.root / "docs" / "wave-7b" / "review-party.md").write_text(stamped("7B"))
        code, _, err = self.p.run(7)
        self.assertEqual(code, 1, err)
        self.assertIn("7B", err)
        self.assertIn("not on main", err)

    def test_an_empty_record_fails(self):
        self.p.land("7A", STAMPED, record="stamped")
        self.p.land("7B", STAMPED, record="empty")
        code, _, err = self.p.run(7)
        self.assertEqual(code, 1, err)
        self.assertIn("empty", err)

    def test_a_record_with_no_front_matter_fails_from_the_stamp_date(self):
        self.p.land("7A", STAMPED, record="stamped")
        self.p.land("7B", STAMPED, record="canonical")
        code, _, err = self.p.run(7)
        self.assertEqual(code, 1, err)
        self.assertIn("front matter", err)

    def test_a_record_naming_another_wave_fails(self):
        self.p.land("7A", STAMPED, record="stamped")
        self.p.land("7B", STAMPED, record="wrong-wave")
        code, _, err = self.p.run(7)
        self.assertEqual(code, 1, err)
        self.assertIn("wave:", err)

    def test_a_record_missing_a_front_matter_key_fails(self):
        self.p.land("7A", STAMPED, record="stamped")
        self.p.land("7B", STAMPED, record="no-model")
        code, _, err = self.p.run(7)
        self.assertEqual(code, 1, err)
        self.assertIn("without model", err)

    def test_front_matter_is_not_required_before_the_stamp_date(self):
        self.p.land("7A", "2026-09-11T09:00:00Z", record="canonical")
        self.p.land("7B", "2026-09-11T23:59:00Z", record="canonical")
        self.assertEqual(self.p.run(7)[0], 0)

    def test_a_stub_committed_on_the_closure_branch_fails(self):
        self.p.land("7A", STAMPED, record="stamped")
        self.p.land("7B", STAMPED)
        git(self.p.root, "checkout", "-q", "-b", "claude/close-epic-7")
        (self.p.root / "docs" / "wave-7b" / "review-party.md").write_text(stamped("7B"))
        git(self.p.root, "add", "-A")
        git(self.p.root, "commit", "-q", "-m", "stub", when=STAMPED)
        code, _, err = self.p.run(7)
        self.assertEqual(code, 1, err)
        self.assertIn("not on main", err)

    def test_origin_main_is_the_main_line_when_it_exists(self):
        self.p.land("7A", STAMPED, record="stamped")
        self.p.land("7B", STAMPED)
        before = subprocess.run(["git", "-C", str(self.p.root), "rev-parse", "HEAD"],
                                capture_output=True, text=True).stdout.strip()
        (self.p.root / "docs" / "wave-7b" / "review-party.md").write_text(stamped("7B"))
        git(self.p.root, "add", "-A")
        git(self.p.root, "commit", "-q", "-m", "local only", when=STAMPED)
        git(self.p.root, "update-ref", "refs/remotes/origin/main", before)
        code, _, err = self.p.run(7)
        self.assertEqual(code, 1, err)
        self.assertIn("origin/main", err)


class TestCleanup(unittest.TestCase):
    """V2-12's preflight: a wave still checked out is not cleaned up."""

    def setUp(self):
        import contextlib
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.p = Project(self.stack)
        self.p.seed()
        self.p.land_via_merge("7A", STAMPED, STAMPED, record="stamped")
        self.p.land_via_merge("7B", STAMPED, STAMPED, record="stamped")

    def test_a_worktree_on_a_wave_branch_fails(self):
        wt = Path(self.stack.enter_context(tempfile.TemporaryDirectory())) / "wt"
        git(self.p.root, "worktree", "add", "-q", "-b", "claude/wave-7b-beta-abc123", str(wt))
        code, out, err = self.p.run(7)
        self.assertEqual(code, 4, err)
        self.assertIn("7B", err)
        self.assertIn("worktree", err)

    def test_a_worktree_on_another_branch_passes(self):
        wt = Path(self.stack.enter_context(tempfile.TemporaryDirectory())) / "wt"
        git(self.p.root, "worktree", "add", "-q", "-b", "claude/close-epic-7-abc123", str(wt))
        self.assertEqual(self.p.run(7)[0], 0)

    def fake_gh(self, prs, rc=0):
        bin_dir = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        gh = bin_dir / "gh"
        gh.write_text("#!/bin/sh\n" + (f"cat <<'EOF'\n{prs}\nEOF\n" if rc == 0
                                        else "echo 'gh: not logged in' >&2\n")
                      + f"exit {rc}\n")
        gh.chmod(0o755)
        return dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}")

    def test_preflight_passes_with_nothing_open(self):
        code, _, err = self.p.run(7, "--preflight", env=self.fake_gh("[]"))
        self.assertEqual(code, 0, err)

    def test_preflight_refuses_an_open_pull_request_for_a_wave(self):
        prs = '[{"number": 12, "headRefName": "claude/wave-7a-alpha-def456"}]'
        code, _, err = self.p.run(7, "--preflight", env=self.fake_gh(prs))
        self.assertEqual(code, 4, err)
        self.assertIn("#12", err)

    def test_preflight_refuses_an_existing_closure_branch(self):
        git(self.p.root, "branch", "claude/epic-7-closure-0a1b2c")
        code, _, err = self.p.run(7, "--preflight", env=self.fake_gh("[]"))
        self.assertEqual(code, 4, err)
        self.assertIn("claude/epic-7-closure-0a1b2c", err)

    def test_preflight_ignores_the_branch_it_runs_on(self):
        git(self.p.root, "checkout", "-q", "-b", "claude/close-epic-7-abc123")
        code, _, err = self.p.run(7, "--preflight", env=self.fake_gh("[]"))
        self.assertEqual(code, 0, err)

    def test_preflight_refuses_when_gh_fails(self):
        code, _, err = self.p.run(7, "--preflight", env=self.fake_gh("", rc=1))
        self.assertEqual(code, 4, err)
        self.assertIn("gh", err)

    def test_preflight_refuses_a_closure_branch_on_origin(self):
        origin = Path(self.stack.enter_context(tempfile.TemporaryDirectory())) / "origin.git"
        git(self.p.root, "init", "-q", "--bare", str(origin))
        git(self.p.root, "remote", "add", "origin", str(origin))
        git(self.p.root, "push", "-q", "origin", "main", "main:claude/close-epic-7-9f8e7d")
        code, _, err = self.p.run(7, "--preflight", env=self.fake_gh("[]"))
        self.assertEqual(code, 4, err)
        self.assertIn("claude/close-epic-7-9f8e7d", err)

    def test_preflight_refuses_when_origin_cannot_answer(self):
        git(self.p.root, "remote", "add", "origin", "/nonexistent/origin.git")
        code, _, err = self.p.run(7, "--preflight", env=self.fake_gh("[]"))
        self.assertEqual(code, 4, err)
        self.assertIn("origin", err)

    def test_without_wave_status_the_gate_is_structural(self):
        alone = Path(self.stack.enter_context(tempfile.TemporaryDirectory())) / "a" / "b" / "c"
        alone.mkdir(parents=True)
        import shutil
        shutil.copy(SCRIPT, alone / SCRIPT.name)
        p = subprocess.run([sys.executable, str(alone / SCRIPT.name), "--project-root",
                            str(self.p.root), "--epic", "7"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 2, p.stderr)
        self.assertIn("wave_status.py", p.stderr)

    def test_no_network_without_the_flag(self):
        code, _, err = self.p.run(7, env=self.fake_gh("", rc=1))
        self.assertEqual(code, 0, err)


if __name__ == "__main__":
    unittest.main()
