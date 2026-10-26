#!/usr/bin/env python3
"""Tests for wave_status.py. Stdlib only; run with `python3 -m unittest`.

The three demonstrations Phase 2 has to make are test_routes_* (a record at
each status re-enters at the right stage), test_blocked_is_sticky_* (a blocked
wave halts on a second dispatch after its cause is fixed), and
test_hand_edit_clears_block (removing the status by hand lets it proceed).
"""

import contextlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "wave_status.py"

WAVE_MAP = """# Wave Map

| Wave | Pattern | Stories | Branch suffix | Notes |
|---|---|---|---|---|
| 7A | serial | 7.1 | wave-7a-alpha | First. |
| 7B | parallel | 7.2, 7.3 | wave-7b-beta | Second. |
| 8A | serial | 8.1 | wave-8a-gamma | Another epic. |
"""

SUFFIX = {"7A": "wave-7a-alpha", "7B": "wave-7b-beta", "8A": "wave-8a-gamma"}

LIFECYCLE = ("draft", "ready-for-dev", "in-progress", "in-review", "done")


class Project:
    """A throwaway project tree with a wave map and a .bmad state directory."""

    def __init__(self, stack, wave_map=WAVE_MAP):
        self.root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        if wave_map is not None:
            d = self.root / "_bmad-output" / "planning-artifacts"
            d.mkdir(parents=True)
            (d / "waves.md").write_text(wave_map)

    def run(self, *args):
        out = subprocess.run(
            [sys.executable, str(SCRIPT), *args,
             "--project-root", str(self.root)],
            capture_output=True, text=True)
        payload = json.loads(out.stdout) if out.stdout.strip() else {}
        return out.returncode, payload, out.stderr

    def route(self, wave):
        return self.run("route", "--wave", wave)

    def set(self, wave, status, reason=None):
        args = ["set", "--wave", wave, "--status", status]
        if reason:
            args += ["--reason", reason]
        return self.run(*args)

    def show(self, wave=None):
        return self.run("show", *(["--wave", wave] if wave else []))

    def walk(self, wave, status):
        """Put the record at `status` the way the skills reach it: each legal
        set from draft, checked."""
        for step in LIFECYCLE[:LIFECYCLE.index(status) + 1]:
            code, _, err = self.set(wave, step)
            assert code == 0, err

    # -- fixtures ---------------------------------------------------------

    def wave_dir(self, wave):
        d = self.root / ".bmad" / f"wave-{wave}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def mark(self, wave, *steps):
        """Completion markers in the `step-N.done` convention."""
        d = self.wave_dir(wave)
        for step in steps:
            (d / f"step-{step}.done").write_text("")

    def mark_via_checkpoint(self, wave, **steps):
        """The other real convention: checkpoint.json's `steps` object."""
        d = self.wave_dir(wave)
        (d / "checkpoint.json").write_text(json.dumps({"wave": wave, "steps": steps}))

    def record_text(self, wave):
        return (self.root / ".bmad" / f"wave-{wave}" / "wave.md").read_text()

    def write_record(self, wave, text):
        d = self.wave_dir(wave)
        (d / "wave.md").write_text(text)

    # -- git fixtures -----------------------------------------------------

    def git(self, *args):
        subprocess.run(["git", "-C", str(self.root), *args],
                       check=True, capture_output=True)

    def init_git(self):
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")
        (self.root / "README.md").write_text("seed\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "seed")

    def write_wave_docs(self, wave):
        d = self.root / "docs" / f"wave-{wave.lower()}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "test-design.md").write_text("design\n")

    def land_docs_on_main(self, wave):
        """Docs written on the wave's branch and merged, as a real wave does."""
        self.git("checkout", "-q", "-b", f"wave-{wave.lower()}")
        self.write_wave_docs(wave)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", f"wave {wave} docs")
        self.git("checkout", "-q", "main")
        self.git("merge", "-q", "--no-ff", "-m", f"Merge wave {wave}",
                 f"wave-{wave.lower()}")

    def commit_docs_on_branch_only(self, wave):
        """Docs committed on the wave's own branch, never merged -- the shape
        of a wave still in flight inside its worktree."""
        self.git("checkout", "-q", "-b", f"wave-{wave.lower()}")
        self.write_wave_docs(wave)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", f"wave {wave} docs")


@contextlib.contextmanager
def project(**kw):
    with contextlib.ExitStack() as stack:
        yield Project(stack, **kw)


class RoutesEachStatus(unittest.TestCase):
    """Demonstration 1: a record at each status resumes at the correct stage."""

    def test_routes_draft_to_first_plan_step(self):
        with project() as p:
            p.set("7A", "draft")
            code, out, _ = p.route("7A")
            self.assertEqual(code, 0)
            self.assertEqual(out["stage"], "plan")
            self.assertEqual(out["reentry_step"], "1")

    def test_routes_draft_past_completed_plan_steps(self):
        with project() as p:
            p.set("7A", "draft")
            p.mark("7A", "1", "2", "3")
            _, out, _ = p.route("7A")
            self.assertEqual(out["reentry_step"], "4")

    def test_routes_draft_over_the_half_step(self):
        with project() as p:
            p.set("7A", "draft")
            p.mark("7A", "1", "2", "3", "4")
            _, out, _ = p.route("7A")
            self.assertEqual(out["reentry_step"], "4.5")

    def test_routes_ready_for_dev_to_implementation(self):
        with project() as p:
            p.walk("7A", "ready-for-dev")
            code, out, _ = p.route("7A")
            self.assertEqual(code, 0)
            self.assertEqual(out["stage"], "implement")
            self.assertEqual(out["reentry_step"], "6")

    def test_routes_in_progress_to_first_incomplete_step(self):
        with project() as p:
            p.walk("7A", "in-progress")
            p.mark("7A", "1", "2", "3", "4", "4.5", "5", "6", "7")
            code, out, _ = p.route("7A")
            self.assertEqual(code, 0)
            self.assertEqual(out["stage"], "implement")
            self.assertEqual(out["reentry_step"], "8")

    def test_routes_in_review_to_review_stage(self):
        with project() as p:
            p.walk("7A", "in-review")
            p.mark("7A", "10")
            code, out, _ = p.route("7A")
            self.assertEqual(code, 0)
            self.assertEqual(out["stage"], "review")
            self.assertEqual(out["reentry_step"], "11")

    def test_routes_done_to_a_fresh_followup_pass(self):
        """A done wave re-enters at step 10 whatever its markers say: the
        dispatch is a new review pass, not a resumption."""
        with project() as p:
            p.walk("7A", "done")
            p.mark("7A", *[str(n) for n in range(1, 13)])
            code, out, err = p.route("7A")
            self.assertEqual(code, 0)
            self.assertEqual(out["reentry_step"], "10")
            self.assertTrue(out["followup_pass"])
            self.assertIn("follow-up", err)

    def test_done_covers_exactly_one_step(self):
        """The follow-up pass is a fresh review, not a resumption, and that
        rests entirely on done's stage being the single step 10. Widening it
        would silently make a done wave resume mid-review."""
        with project() as p:
            p.walk("7A", "done")
            for marked in ([], ["10"], ["10", "11", "12"]):
                p.mark("7A", *marked)
                _, out, _ = p.route("7A")
                self.assertEqual(out["reentry_step"], "10", marked)

    def test_no_status_invents_a_stage(self):
        """Every status routes to a step bmad-dev-wave already has."""
        with project() as p:
            for status in ("draft", "ready-for-dev", "in-progress", "in-review", "done"):
                p.set("7A", status) if status == "draft" else None
                p.write_record("7A", f"---\nwave: 7A\nstatus: {status}\n---\n")
                _, out, _ = p.route("7A")
                self.assertIn(out["reentry_step"],
                              ["1", "2", "3", "4", "4.5", "5", "6", "7", "8", "9",
                               "10", "11", "12"], status)


class BlockedIsSticky(unittest.TestCase):
    """Demonstration 2: blocked halts every later dispatch."""

    def test_blocked_halts_dispatch(self):
        with project() as p:
            p.walk("7A", "in-progress")
            p.set("7A", "blocked", reason="verify FAIL on tests/verify-fast.sh")
            code, out, err = p.route("7A")
            self.assertEqual(code, 1)
            self.assertEqual(out["status"], "blocked")
            self.assertIn("verify FAIL", err)

    def test_blocked_halts_again_after_the_cause_is_fixed(self):
        """The whole point. Fixing the cause changes nothing on disk that the
        gate reads, so the second dispatch refuses exactly as the first did."""
        with project() as p:
            p.walk("7A", "in-progress")
            p.set("7A", "blocked", reason="verify FAIL on tests/verify-fast.sh")
            first, _, _ = p.route("7A")
            # The cause is fixed: the failing step now has its completion marker
            # and the whole implementation stage has finished.
            p.mark("7A", *[str(n) for n in range(1, 10)], "4.5")
            second, out, err = p.route("7A")
            self.assertEqual((first, second), (1, 1))
            self.assertEqual(out["status"], "blocked")
            self.assertIn("after", err)

    def test_a_skill_cannot_write_its_way_out_of_blocked(self):
        with project() as p:
            p.set("7A", "blocked", reason="open question unresolved")
            code, out, err = p.set("7A", "in-progress")
            self.assertEqual(code, 1)
            self.assertEqual(out["error"], "already_blocked")
            self.assertIn("open question unresolved", err)
            self.assertIn("status: blocked", p.record_text("7A"))

    def test_blocked_cannot_be_overwritten_by_blocked_either(self):
        with project() as p:
            p.set("7A", "blocked", reason="first cause")
            code, _, _ = p.set("7A", "blocked", reason="second cause")
            self.assertEqual(code, 1)
            self.assertIn("first cause", p.record_text("7A"))

    def test_blocked_record_records_when_and_why(self):
        with project() as p:
            p.set("7A", "blocked", reason="subagent returned an open question")
            _, out, _ = p.route("7A")
            self.assertTrue(out["blocked_at"])
            self.assertEqual(out["reason"], "subagent returned an open question")

    def test_reason_is_flattened_to_one_line(self):
        with project() as p:
            p.set("7A", "blocked", reason="line one\nline two")
            self.assertIn("reason: line one line two", p.record_text("7A"))


class ClearingABlock(unittest.TestCase):
    """Demonstration 3: a human clears it, and only a human."""

    def test_hand_edit_clears_block(self):
        with project() as p:
            p.walk("7A", "in-progress")
            p.set("7A", "blocked", reason="verify FAIL")
            self.assertEqual(p.route("7A")[0], 1)
            # The human edits the record: status blocked -> in-progress.
            text = p.record_text("7A").replace("status: blocked", "status: in-progress")
            p.write_record("7A", text)
            code, out, _ = p.route("7A")
            self.assertEqual(code, 0)
            self.assertEqual(out["status"], "in-progress")

    def test_deleting_the_record_starts_the_wave_over(self):
        with project() as p:
            p.set("7A", "blocked", reason="verify FAIL")
            (p.root / ".bmad" / "wave-7A" / "wave.md").unlink()
            code, out, err = p.route("7A")
            self.assertEqual(code, 0)
            self.assertEqual(out["status"], "draft")
            self.assertIn("UNMIGRATED", err)

    def test_deleting_the_status_line_is_not_a_way_out(self):
        """Removing `status:` looks like clearing the block and is not: a
        record that exists with no readable status refuses."""
        with project() as p:
            p.set("7A", "blocked", reason="verify FAIL")
            text = "\n".join(l for l in p.record_text("7A").splitlines()
                             if not l.startswith("status:"))
            p.write_record("7A", text)
            code, out, err = p.route("7A")
            self.assertEqual(code, 3)
            self.assertEqual(out["error"], "unrecognized_status")
            self.assertIn("quiet override", err)

    def test_a_nonsense_status_refuses(self):
        with project() as p:
            p.write_record("7A", "---\nwave: 7A\nstatus: unblocked\n---\n")
            code, out, _ = p.route("7A")
            self.assertEqual(code, 3)
            self.assertEqual(out["found"], "unblocked")

    def test_set_refuses_a_nonsense_status(self):
        with project() as p:
            code, _, err = p.set("7A", "nearly-done")
            self.assertEqual(code, 3)
            self.assertIn("not a wave status", err)


class Backfill(unittest.TestCase):
    """A wave with no record predates the field: inferred once, written down."""

    def test_unmigrated_wave_is_reported_not_defaulted_silently(self):
        with project() as p:
            code, out, err = p.route("7A")
            self.assertEqual(code, 0)
            self.assertIn("UNMIGRATED", err)
            self.assertIn("backfilled", out)

    def test_backfill_infers_from_checkpoint_markers(self):
        with project() as p:
            p.mark("7A", "1", "2", "3", "4", "4.5", "5", "6", "7")
            _, out, _ = p.route("7A")
            self.assertEqual(out["status"], "in-progress")
            self.assertEqual(out["reentry_step"], "8")

    def test_backfill_reads_the_checkpoint_json_convention_too(self):
        """ffbapp wave-5D records steps inside checkpoint.json; wave-2B uses
        marker files. A parser that knows one convention misreads the other."""
        with project() as p:
            p.mark_via_checkpoint("7A", **{"1_preflight": "done",
                                           "2_worktree": "done (existing, per ruling)"})
            _, out, _ = p.route("7A")
            self.assertEqual(out["status"], "draft")
            self.assertEqual(out["reentry_step"], "3")

    def test_backfill_infers_done_from_a_swept_archive(self):
        with project() as p:
            archive = p.wave_dir("7A") / "archive"
            archive.mkdir()
            (archive / "cleanup.done").write_text("")
            _, out, _ = p.route("7A")
            self.assertEqual(out["status"], "done")

    def test_backfill_infers_done_from_merged_docs(self):
        """The only evidence a wave swept before checkpoints were archived
        leaves behind. Sixteen of ffbapp's eighteen waves are this case."""
        with project() as p:
            p.init_git()
            p.land_docs_on_main("7A")
            _, out, _ = p.route("7A")
            self.assertEqual(out["status"], "done")
            self.assertIn("merged into main", out["backfilled"])

    def test_unmerged_wave_docs_are_not_evidence_of_done(self):
        """docs/wave-<id>/ also exists inside the wave's own worktree from
        step 3 onward. Presence alone would read every in-flight wave as
        finished; the ancestry test is what separates them."""
        with project() as p:
            p.init_git()
            p.commit_docs_on_branch_only("7A")
            p.mark("7A", "1", "2", "3")
            _, out, _ = p.route("7A")
            self.assertEqual(out["status"], "draft")
            self.assertEqual(out["reentry_step"], "4")

    def test_uncommitted_wave_docs_are_not_evidence_of_done(self):
        with project() as p:
            p.init_git()
            p.write_wave_docs("7A")
            _, out, _ = p.route("7A")
            self.assertEqual(out["status"], "draft")

    def test_backfill_resolves_ambiguity_toward_draft(self):
        """No marker at all: enter at step 1 rather than guess a wave forward
        past a test design and an ATDD scaffold that may never have run."""
        with project() as p:
            _, out, _ = p.route("7A")
            self.assertEqual(out["status"], "draft")
            self.assertEqual(out["reentry_step"], "1")

    def test_inference_runs_once(self):
        with project() as p:
            p.route("7A")
            first = p.record_text("7A")
            _, out, err = p.route("7A")
            self.assertNotIn("UNMIGRATED", err)
            self.assertNotIn("backfilled", out)
            self.assertEqual(p.record_text("7A"), first)

    def test_backfill_never_overwrites_an_existing_record(self):
        with project() as p:
            p.walk("7A", "in-review")
            p.mark("7A", "1")
            _, out, _ = p.route("7A")
            self.assertEqual(out["status"], "in-review")


class RecordShape(unittest.TestCase):

    def test_history_accumulates_across_writes(self):
        with project() as p:
            p.set("7A", "draft")
            p.set("7A", "ready-for-dev")
            p.set("7A", "in-progress")
            history = [l for l in p.record_text("7A").splitlines() if l.startswith("- 2")]
            self.assertEqual(len(history), 3)
            self.assertIn("draft -> ready-for-dev", history[1])

    def test_record_documents_how_to_clear_a_block(self):
        with project() as p:
            p.set("7A", "blocked", reason="verify FAIL")
            text = p.record_text("7A")
            self.assertIn("delete this file", text)
            self.assertIn("draft, ready-for-dev, in-progress, in-review, done, blocked",
                          text)

    def test_wave_directory_case_is_resolved_not_assumed(self):
        """The real instance spells .bmad/wave-5D/ while docs/wave-5d/ is
        lower-cased, so neither casing can be assumed.

        Asserted on the path the script reports rather than on what exists on
        disk: the developer filesystem here is case-insensitive, so a script
        that assumed the map's casing would still land in the pre-made
        directory and an existence check would pass vacuously.
        """
        with project() as p:
            (p.root / ".bmad" / "wave-7a").mkdir(parents=True)
            _, out, _ = p.set("7A", "draft")
            self.assertTrue(out["record"].endswith("wave-7a/wave.md"), out["record"])
            self.assertEqual([c.name for c in (p.root / ".bmad").iterdir()], ["wave-7a"])

    def test_wave_label_case_is_resolved_against_the_map(self):
        with project() as p:
            code, out, _ = p.set("7a", "draft")
            self.assertEqual(code, 0)
            self.assertEqual(out["wave"], "7A")


class Structural(unittest.TestCase):

    def test_no_wave_map_refuses(self):
        with project(wave_map=None) as p:
            code, out, err = p.route("7A")
            self.assertEqual(code, 2)
            self.assertEqual(out["error"], "no_wave_map")
            self.assertIn("bmad-create-wave", err)

    def test_wave_not_in_map_refuses(self):
        with project() as p:
            code, out, err = p.route("9Z")
            self.assertEqual(code, 2)
            self.assertEqual(out["error"], "wave_not_in_map")
            self.assertIn("7A, 7B, 8A", err)

    def test_set_refuses_a_wave_not_in_the_map(self):
        with project() as p:
            self.assertEqual(p.set("9Z", "draft")[0], 2)

    def test_prefix_options_do_not_bind(self):
        # The gate reads --status and --wave by their full names; a prefix
        # argparse would accept is a spelling the gate cannot see (R1).
        with project() as p:
            code, _, err = p.run("set", "--wav", "7A", "--stat", "in-review")
            self.assertEqual(code, 2)
            self.assertIn("unrecognized arguments", err)
            self.assertFalse((p.root / ".bmad" / "wave-7A" / "wave.md").exists())


class ClosurePending(unittest.TestCase):
    """V2-13: route refuses a draft wave while an earlier epic, every wave of
    which has landed, has no closure that covers them all."""

    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.p = Project(self.stack)
        self.p.init_git()

    def commit(self, rel, text, msg):
        f = self.p.root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)
        self.p.git("add", "-A")
        self.p.git("commit", "-q", "-m", msg)

    def close(self, epic):
        self.commit(f"_bmad-output/epic-closure/epic-{epic}/SUMMARY.md", "# Summary\n",
                    f"close epic {epic}")

    def defer(self, line):
        path = self.p.root / "_bmad-output" / "planning-artifacts" / "waves.md"
        self.commit("_bmad-output/planning-artifacts/waves.md",
                    path.read_text() + "\n" + line + "\n", "defer")

    def head(self):
        return subprocess.run(["git", "-C", str(self.p.root), "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()

    def test_an_unclosed_earlier_epic_refuses(self):
        self.p.land_docs_on_main("7A")
        self.p.land_docs_on_main("7B")
        code, out, err = self.p.route("8A")
        self.assertEqual(code, 5, err)
        self.assertEqual(out["error"], "closure_pending")
        self.assertEqual(out["pending"][0]["epic"], 7)
        self.assertIn("epic 7", err)
        self.assertIn("/bmad-close-epic 7", err)
        self.assertIn("Closure deferral: epic 7 -- ", err)

    def test_a_closed_earlier_epic_passes(self):
        self.p.land_docs_on_main("7A")
        self.p.land_docs_on_main("7B")
        self.close(7)
        code, out, err = self.p.route("8A")
        self.assertEqual(code, 0, err)

    def test_a_wave_merged_after_the_closure_makes_it_pending_again(self):
        self.p.land_docs_on_main("7A")
        self.close(7)
        self.p.land_docs_on_main("7B")
        code, out, err = self.p.route("8A")
        self.assertEqual(code, 5, err)
        self.assertEqual(out["pending"][0]["late"], ["7B"])
        self.assertIn("7B", err)

    def test_an_addendum_to_the_closure_covers_the_late_wave(self):
        self.p.land_docs_on_main("7A")
        self.close(7)
        self.p.land_docs_on_main("7B")
        self.commit("_bmad-output/epic-closure/epic-7/addendum-7b.md", "# 7B\n", "addendum")
        self.assertEqual(self.p.route("8A")[0], 0)

    def test_an_epic_still_mid_flight_is_not_pending(self):
        # The ruled 6A placement: a later epic's wave runs while an earlier
        # epic still has a wave to land.
        self.p.land_docs_on_main("7A")
        code, _, err = self.p.route("8A")
        self.assertEqual(code, 0, err)

    def test_a_valid_deferral_line_passes(self):
        self.p.land_docs_on_main("7A")
        self.p.land_docs_on_main("7B")
        self.defer("Closure deferral: epic 7 -- 2099-01-01 -- RQ ruled the closure waits for 8A.")
        code, out, err = self.p.route("8A")
        self.assertEqual(code, 0, err)

    def test_a_deferral_dated_before_a_landing_does_not_cover_it(self):
        self.p.land_docs_on_main("7A")
        self.p.land_docs_on_main("7B")
        self.defer("Closure deferral: epic 7 -- 2000-01-01 -- stale.")
        code, _, err = self.p.route("8A")
        self.assertEqual(code, 5, err)

    def test_a_deferral_for_another_epic_does_not_cover_it(self):
        self.p.land_docs_on_main("7A")
        self.p.land_docs_on_main("7B")
        self.defer("Closure deferral: epic 6 -- 2099-01-01 -- wrong epic.")
        self.assertEqual(self.p.route("8A")[0], 5)

    def test_an_uncommitted_deferral_does_not_count(self):
        self.p.land_docs_on_main("7A")
        self.p.land_docs_on_main("7B")
        path = self.p.root / "_bmad-output" / "planning-artifacts" / "waves.md"
        path.write_text(path.read_text() + "\nClosure deferral: epic 7 -- 2099-01-01 -- x.\n")
        self.assertEqual(self.p.route("8A")[0], 5)

    def test_a_deferral_off_origin_main_does_not_count(self):
        self.p.land_docs_on_main("7A")
        self.p.land_docs_on_main("7B")
        before = self.head()
        self.defer("Closure deferral: epic 7 -- 2099-01-01 -- local only.")
        self.p.git("update-ref", "refs/remotes/origin/main", before)
        self.assertEqual(self.p.route("8A")[0], 5)

    def test_a_malformed_deferral_line_is_quoted(self):
        self.p.land_docs_on_main("7A")
        self.p.land_docs_on_main("7B")
        self.defer("Closure deferral: epic seven, later")
        code, _, err = self.p.route("8A")
        self.assertEqual(code, 5, err)
        self.assertIn("Closure deferral: epic seven, later", err)

    def test_a_wave_past_draft_is_not_refused(self):
        self.p.land_docs_on_main("7A")
        self.p.land_docs_on_main("7B")
        self.p.walk("8A", "in-progress")
        code, out, err = self.p.route("8A")
        self.assertEqual(code, 0, err)
        self.assertEqual(out["status"], "in-progress")

    def test_a_wave_of_the_pending_epic_itself_is_not_refused(self):
        self.p.land_docs_on_main("7A")
        self.p.git("checkout", "-q", "-b", "side")  # 7B unlanded: 7 mid-flight anyway
        self.p.git("checkout", "-q", "main")
        self.assertEqual(self.p.route("7B")[0], 0)


class Show(unittest.TestCase):

    def test_show_lists_every_wave(self):
        with project() as p:
            p.walk("7A", "in-progress")
            code, out, _ = p.show()
            self.assertEqual(code, 0)
            self.assertEqual([w["wave"] for w in out["waves"]], ["7A", "7B", "8A"])

    def test_show_never_writes(self):
        """bmad-status-wave is read-only by charter, so its reader must not
        backfill the way route does."""
        with project() as p:
            p.show()
            self.assertFalse((p.root / ".bmad").exists())

    def test_show_renders_unmigrated_and_corrupt_as_rows(self):
        with project() as p:
            p.set("7A", "blocked", reason="verify FAIL")
            p.write_record("7B", "---\nwave: 7B\nstatus: nonsense\n---\n")
            code, out, _ = p.show()
            self.assertEqual(code, 0)
            states = {w["wave"]: (w["status"], w["state"]) for w in out["waves"]}
            self.assertEqual(states["7A"], ("blocked", "ok"))
            self.assertEqual(states["7B"], ("nonsense", "corrupt"))
            self.assertEqual(states["8A"], (None, "unmigrated"))


class AdoptFromWorktree(unittest.TestCase):
    """A session rooted in the wave's worktree writes .bmad/wave-<id>/ there,
    and bmad-merge-wave reads the main checkout's. ffbapp wave 6B's record
    would have gone with its worktree; it was copied out by hand."""

    def worktree(self, p, wave="7A"):
        p.init_git()  # commits the wave map, so the worktree has it too
        # ffbapp ignores .bmad/ through info/exclude, which every worktree shares.
        exclude = p.root / ".git" / "info" / "exclude"
        exclude.parent.mkdir(exist_ok=True)
        with exclude.open("a") as f:
            f.write(".bmad/\n")
        wt = p.root / ".claude" / "worktrees" / f"wave-{wave.lower()}-x"
        # The map's suffix with the hash a harness-created branch carries.
        p.git("worktree", "add", "-q", "-b", f"claude/{SUFFIX[wave]}-abc123", str(wt))
        return wt

    def in_tree(self, p, wt, *args):
        """Run the script against the worktree, as dev-wave does there."""
        out = subprocess.run([sys.executable, str(SCRIPT), *args,
                              "--project-root", str(wt)], capture_output=True, text=True)
        return out.returncode

    def walk_in_tree(self, p, wt, status):
        for step in LIFECYCLE[:LIFECYCLE.index(status) + 1]:
            code = self.in_tree(p, wt, "set", "--wave", "7A", "--status", step)
            if code:
                return code
        return 0

    def adopt(self, p, wt, wave="7A"):
        return p.run("adopt", "--wave", wave, "--from", str(wt))

    def test_a_checkpoint_written_in_the_worktree_survives_its_removal(self):
        with project() as p:
            wt = self.worktree(p)
            self.assertEqual(self.walk_in_tree(p, wt, "in-review"), 0)
            src = wt / ".bmad" / "wave-7A"
            for step in ("1", "4.5", "8", "12"):
                (src / f"step-{step}.done").write_text("")
            record = (src / "wave.md").read_bytes()

            code, out, _ = self.adopt(p, wt)
            self.assertEqual(code, 0)
            self.assertIn("wave.md", out["adopted"])

            p.git("worktree", "remove", str(wt))
            self.assertFalse(wt.exists())
            dst = p.root / ".bmad" / "wave-7A"
            self.assertEqual((dst / "wave.md").read_bytes(), record)
            for step in ("1", "4.5", "8", "12"):
                self.assertTrue((dst / f"step-{step}.done").is_file(), step)
            # merge-wave's step 5 then marks it done in the main checkout,
            # and the history the worktree wrote is still the record's.
            self.assertEqual(p.set("7A", "done")[0], 0)
            text = p.record_text("7A")
            self.assertIn("-> in-review", text)
            self.assertIn("in-review -> done", text)

    def test_adopting_twice_copies_nothing_the_second_time(self):
        with project() as p:
            wt = self.worktree(p)
            self.walk_in_tree(p, wt, "in-review")
            self.assertEqual(self.adopt(p, wt)[0], 0)
            code, out, _ = self.adopt(p, wt)
            self.assertEqual(code, 0)
            self.assertEqual(out["adopted"], [])
            self.assertIn("wave.md", out["identical"])

    def test_a_removed_worktree_is_nothing_to_adopt(self):
        with project() as p:
            code, out, _ = self.adopt(p, p.root / "gone")
            self.assertEqual(code, 0)
            self.assertEqual(out["adopted"], [])

    def test_the_main_checkouts_own_files_are_kept(self):
        # The evaluator hook writes evaluation-session beside the main
        # checkout's .bmad/ (ffbapp 6B: the only file there).
        with project() as p:
            wt = self.worktree(p)
            self.walk_in_tree(p, wt, "in-review")
            (p.wave_dir("7A") / "evaluation-session").write_text("abc\n")
            self.assertEqual(self.adopt(p, wt)[0], 0)
            self.assertEqual((p.root / ".bmad" / "wave-7A" / "evaluation-session").read_text(), "abc\n")

    def test_a_differing_record_in_the_main_checkout_refuses_and_writes_nothing(self):
        # ffbapp 5E: a hand copy left a stale wave.md in the main checkout.
        with project() as p:
            wt = self.worktree(p)
            self.walk_in_tree(p, wt, "in-review")
            (wt / ".bmad" / "wave-7A" / "step-8.done").write_text("")
            p.write_record("7A", "---\nwave: 7A\nstatus: in-progress\n---\n")
            code, out, err = self.adopt(p, wt)
            self.assertEqual(code, 1)
            self.assertEqual(out["conflicts"], ["wave.md"])
            self.assertIn("wave.md", err)
            self.assertFalse((p.root / ".bmad" / "wave-7A" / "step-8.done").exists())
            self.assertIn("status: in-progress", p.record_text("7A"))

    def test_subdirectories_keep_their_place(self):
        with project() as p:
            wt = self.worktree(p)
            self.walk_in_tree(p, wt, "in-review")
            (wt / ".bmad" / "wave-7A" / "archive").mkdir()
            (wt / ".bmad" / "wave-7A" / "archive" / "step-3.done").write_text("")
            self.assertEqual(self.adopt(p, wt)[0], 0)
            self.assertTrue((p.root / ".bmad" / "wave-7A" / "archive" / "step-3.done").is_file())

    def test_a_wave_not_in_the_map_refuses(self):
        with project() as p:
            self.assertEqual(self.adopt(p, p.root, wave="9Z")[0], 2)

    def test_adopt_needs_from(self):
        with project() as p:
            code, _, err = p.run("adopt", "--wave", "7A")
            self.assertEqual(code, 2)
            self.assertIn("--from", err)


# Every move `set` may make, written out here rather than read from the
# script, so a change to the script's table has to change this too.
# None is no record.
ALLOWED = {
    (None, "draft"), (None, "blocked"),
    ("draft", "draft"), ("draft", "ready-for-dev"), ("draft", "blocked"),
    ("ready-for-dev", "ready-for-dev"), ("ready-for-dev", "in-progress"),
    ("ready-for-dev", "blocked"),
    ("in-progress", "in-progress"), ("in-progress", "in-review"),
    ("in-progress", "blocked"),
    ("in-review", "in-review"), ("in-review", "in-progress"), ("in-review", "done"),
    ("in-review", "blocked"),
    ("done", "done"), ("done", "blocked"),
}
STATUSES = LIFECYCLE + ("blocked",)


class Transitions(unittest.TestCase):
    """V2-01: set accepted 25 of 25 ordered pairs, so done skipped review."""

    def test_every_ordered_pair(self):
        with project() as p:
            record = p.root / ".bmad" / "wave-7A" / "wave.md"
            start = {}
            for status in STATUSES:
                if record.exists():
                    record.unlink()
                if status == "blocked":
                    p.set("7A", "blocked", reason="r")
                else:
                    p.walk("7A", status)
                start[status] = record.read_bytes()
            for was in (None,) + STATUSES:
                for to in STATUSES:
                    with self.subTest(was=was, to=to):
                        if was is None:
                            if record.exists():
                                record.unlink()
                        else:
                            record.write_bytes(start[was])
                        code, out, err = p.set("7A", to)
                        if (was, to) in ALLOWED:
                            self.assertEqual(code, 0, err)
                            self.assertIn(f"status: {to}\n", record.read_text())
                            continue
                        self.assertEqual(code, 1 if was == "blocked" else 4, err)
                        if was is None:
                            self.assertFalse(record.exists())
                        else:
                            self.assertEqual(record.read_bytes(), start[was])
                        if code == 4:
                            self.assertEqual(out["error"], "illegal_transition")

    def test_done_from_in_progress_is_refused(self):
        with project() as p:
            p.walk("7A", "in-progress")
            code, out, err = p.set("7A", "done")
            self.assertEqual(code, 4)
            self.assertEqual(out["allowed"], ["in-progress", "in-review", "blocked"])
            self.assertIn("cannot move from in-progress to done", err)
            self.assertEqual(p.route("7A")[1]["status"], "in-progress")

    def test_a_wave_reviewed_without_step_10_re_enters_past_it(self):
        """V2-30: in-review is written at the end of step 9, so a wave that
        skips the party review still reaches the review stage and re-enters
        at 12 once step 11 is done, instead of capping at 9."""
        with project() as p:
            p.walk("7A", "in-review")
            p.mark("7A", "1", "2", "3", "4", "4.5", "5", "6", "7", "8", "9", "10", "11")
            _, out, _ = p.route("7A")
            self.assertEqual(out["reentry_step"], "12")


class CorruptRecords(unittest.TestCase):
    """V2-10: a record that could not be read read as absent, so set wrote
    over a blocked wave and route backfilled it."""

    def test_an_unreadable_blocked_record_is_not_written_over(self):
        with project() as p:
            p.set("7A", "blocked", reason="verify FAIL")
            record = p.root / ".bmad" / "wave-7A" / "wave.md"
            before = record.read_bytes()
            record.chmod(0o200)
            try:
                code, out, err = p.set("7A", "in-progress")
                route_code, _, _ = p.route("7A")
            finally:
                record.chmod(0o644)
            self.assertEqual(code, 3, err)
            self.assertEqual(out["error"], "corrupt_record")
            self.assertIn("cannot be read", err)
            self.assertEqual(route_code, 3)
            self.assertEqual(record.read_bytes(), before)

    def test_a_duplicated_status_line_refuses(self):
        with project() as p:
            p.set("7A", "blocked", reason="r")
            text = p.record_text("7A").replace(
                "status: blocked", "status: blocked\nstatus: in-progress", 1)
            p.write_record("7A", text)
            for code, out, err in (p.set("7A", "blocked"), p.route("7A")):
                self.assertEqual(code, 3, err)
                self.assertIn("'status' twice", err)
            self.assertEqual(p.record_text("7A"), text)
            self.assertEqual(p.show("7A")[1]["waves"][0]["state"], "corrupt")

    def test_set_does_not_write_over_a_missing_status(self):
        with project() as p:
            p.set("7A", "blocked", reason="r")
            text = "\n".join(l for l in p.record_text("7A").splitlines()
                             if not l.startswith("status:"))
            p.write_record("7A", text)
            code, out, _ = p.set("7A", "in-progress")
            self.assertEqual(code, 3)
            self.assertEqual(out["error"], "unrecognized_status")
            self.assertEqual(p.record_text("7A"), text)


class ConcurrentSets(unittest.TestCase):
    """V2-34: an unlocked read-modify-write kept 17 of 21 history lines."""

    def test_twenty_parallel_sets_keep_every_line(self):
        with project() as p:
            p.set("7A", "draft")
            procs = [subprocess.Popen(
                [sys.executable, str(SCRIPT), "set", "--project-root", str(p.root),
                 "--wave", "7A", "--status", "draft", "--reason", f"n{i}"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) for i in range(20)]
            self.assertEqual({proc.wait() for proc in procs}, {0})
            history = [l for l in p.record_text("7A").splitlines() if l.startswith("- 2")]
            self.assertEqual(len(history), 21)
            self.assertEqual(sorted(p.wave_dir("7A").iterdir()),
                             [p.wave_dir("7A") / "wave.md"])


class OneStateRoot(unittest.TestCase):
    """V2-07, V2-08 and V2-31 of the harness review v2: route and set answer
    "where is this wave's state" the same way from either checkout. The
    wave's own worktree holds it when it has a copy or main has none; two
    copies that disagree are refused."""

    def setUp(self):
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        self.p = Project(stack)
        self.p.init_git()
        exclude = self.p.root / ".git" / "info" / "exclude"
        exclude.parent.mkdir(exist_ok=True)
        with exclude.open("a") as f:
            f.write(".bmad/\n")

    def worktree(self, branch="claude/wave-7a-alpha-abc123", name=None):
        wt = self.p.root / ".claude" / "worktrees" / (name or branch.split("/")[-1])
        self.p.git("worktree", "add", "-q", "-b", branch, str(wt))
        return wt.resolve()

    def run_in(self, root, *args, cwd=None, env=None):
        out = subprocess.run([sys.executable, str(SCRIPT), *args, "--project-root", str(root)],
                             capture_output=True, text=True, cwd=cwd, env=env)
        return out.returncode, (json.loads(out.stdout) if out.stdout.strip() else {}), out.stderr

    def main_dir(self):
        return self.p.root.resolve() / ".bmad" / "wave-7A"

    def walk_in(self, root, status):
        for step in LIFECYCLE[:LIFECYCLE.index(status) + 1]:
            code, _, err = self.run_in(root, "set", "--wave", "7A", "--status", step)
            self.assertEqual(code, 0, err)

    def merge_docs_from(self, wt, branch="claude/wave-7a-alpha-abc123"):
        """The wave's docs committed on its branch and merged, worktree kept:
        ffbapp 5E's shape, merged on GitHub and not yet swept."""
        (wt / "docs" / "wave-7a").mkdir(parents=True)
        (wt / "docs" / "wave-7a" / "test-design.md").write_text("design\n")
        subprocess.run(["git", "-C", str(wt), "add", "docs"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(wt), "commit", "-q", "-m", "wave 7A docs"],
                       check=True, capture_output=True)
        self.p.git("merge", "-q", "--no-ff", "-m", "Merge wave 7A", branch)

    def test_a_block_in_main_holds_a_session_rooted_in_the_worktree(self):  # V2-07 a
        self.assertEqual(self.p.set("7A", "draft")[0], 0)
        self.assertEqual(self.p.set("7A", "blocked", reason="open question")[0], 0)
        wt = self.worktree()
        code, _, err = self.run_in(wt, "route", "--wave", "7A")
        self.assertEqual(code, 1, err)
        self.assertIn("blocked", err)
        code, _, _ = self.run_in(wt, "set", "--wave", "7A", "--status", "ready-for-dev")
        self.assertEqual(code, 1)
        self.assertFalse((wt / ".bmad").exists())

    def test_either_checkout_reads_and_writes_one_record(self):
        wt = self.worktree()
        code, out, err = self.run_in(wt, "route", "--wave", "7A")
        self.assertEqual(code, 0, err)
        record = wt / ".bmad" / "wave-7A" / "wave.md"
        self.assertEqual(Path(out["record"]).resolve(), record)
        code, _, err = self.p.set("7A", "ready-for-dev")
        self.assertEqual(code, 0, err)
        self.assertIn("draft -> ready-for-dev", record.read_text())
        self.assertFalse(self.main_dir().exists())
        self.assertEqual(Path(self.p.route("7A")[1]["record"]).resolve(), record)

    def test_a_new_record_starts_in_the_checkout_the_call_came_from(self):
        # A main-rooted session beside a sibling worktree (dev-wave step 2's
        # layout, and the evals') keeps its state in main, markers included.
        wt = self.worktree()
        code, out, err = self.p.route("7A")
        self.assertEqual(code, 0, err)
        self.assertEqual(Path(out["record"]).resolve(), self.main_dir() / "wave.md")
        code, out, err = self.run_in(wt, "route", "--wave", "7A")
        self.assertEqual(code, 0, err)
        self.assertEqual(Path(out["record"]).resolve(), self.main_dir() / "wave.md")
        self.assertFalse((wt / ".bmad").exists())

    def test_with_no_worktree_the_record_is_the_main_checkouts(self):
        code, out, err = self.p.route("7A")
        self.assertEqual(code, 0, err)
        self.assertEqual(Path(out["record"]).resolve(), self.main_dir() / "wave.md")

    def test_a_main_record_stays_where_it_is_when_the_worktree_is_made(self):
        self.assertEqual(self.p.route("7A")[0], 0)
        wt = self.worktree()
        code, _, err = self.run_in(wt, "set", "--wave", "7A", "--status", "ready-for-dev")
        self.assertEqual(code, 0, err)
        self.assertIn("status: ready-for-dev", self.p.record_text("7A"))
        self.assertFalse((wt / ".bmad").exists())

    def test_two_copies_that_disagree_are_refused_naming_both(self):  # ruling (b)
        wt = self.worktree()
        self.assertEqual(self.run_in(wt, "route", "--wave", "7A")[0], 0)
        record = (wt / ".bmad" / "wave-7A" / "wave.md").read_bytes()
        self.main_dir().mkdir(parents=True)
        (self.main_dir() / "evaluation-session").write_text("s1\n")
        for root in (self.p.root, wt):
            for args in (("route", "--wave", "7A"),
                         ("set", "--wave", "7A", "--status", "ready-for-dev")):
                code, out, err = self.run_in(root, *args)
                self.assertEqual(code, 3, f"{root} {args}: {err}")
                self.assertEqual(out["error"], "split_state")
                self.assertIn(str(self.main_dir()), err)
                self.assertIn(str(wt / ".bmad" / "wave-7A"), err)
                self.assertIn("evaluation-session", err)
        self.assertFalse((self.main_dir() / "wave.md").exists())
        self.assertEqual((wt / ".bmad" / "wave-7A" / "wave.md").read_bytes(), record)

    def test_a_record_in_main_that_differs_from_the_worktrees_is_a_split(self):
        wt = self.worktree()
        self.assertEqual(self.run_in(wt, "route", "--wave", "7A")[0], 0)
        self.main_dir().mkdir(parents=True)
        (self.main_dir() / "wave.md").write_text(
            (wt / ".bmad" / "wave-7A" / "wave.md").read_text().replace("draft", "in-progress"))
        code, out, err = self.p.route("7A")
        self.assertEqual(code, 3, err)
        self.assertEqual(out["files"], ["wave.md"])

    def test_a_copy_in_main_that_the_worktree_already_holds_is_not_a_split(self):
        wt = self.worktree()
        self.assertEqual(self.run_in(wt, "route", "--wave", "7A")[0], 0)
        (wt / ".bmad" / "wave-7A" / "step-1.done").write_text("")
        self.main_dir().mkdir(parents=True)
        (self.main_dir() / "step-1.done").write_text("")
        code, out, err = self.p.route("7A")
        self.assertEqual(code, 0, err)
        self.assertEqual(Path(out["record"]).resolve(), wt / ".bmad" / "wave-7A" / "wave.md")
        self.assertEqual(out["reentry_step"], "2")

    def test_merged_docs_do_not_make_a_wave_with_a_worktree_record_done(self):  # V2-31
        wt = self.worktree()
        self.walk_in(wt, "in-review")
        self.merge_docs_from(wt)
        code, out, err = self.p.route("7A")
        self.assertEqual(code, 0, err)
        self.assertEqual(out["status"], "in-review")
        self.assertNotIn("backfilled", out)
        self.assertFalse(self.main_dir().exists())

    def test_merged_docs_are_not_done_while_the_worktree_exists(self):  # ruling (d)
        wt = self.worktree()
        self.merge_docs_from(wt)
        code, out, err = self.p.route("7A")
        self.assertEqual(code, 0, err)
        self.assertEqual(out["status"], "draft")
        self.assertIn("worktree", out["backfilled"])

    def test_merged_docs_are_not_done_while_an_unmerged_wave_branch_exists(self):
        self.p.land_docs_on_main("7A")
        self.p.git("branch", "claude/wave-7a-alpha-abc123", "main")
        self.p.git("checkout", "-q", "claude/wave-7a-alpha-abc123")
        (self.p.root / "fix.txt").write_text("unmerged\n")
        self.p.git("add", "fix.txt")
        self.p.git("commit", "-q", "-m", "unmerged work")
        self.p.git("checkout", "-q", "main")
        code, out, err = self.p.route("7A")
        self.assertEqual(code, 0, err)
        self.assertEqual(out["status"], "draft")

    def test_a_merged_branch_left_behind_does_not_hold_back_done(self):
        # ffbapp keeps merged branches (claude/wave-4a-event-registry-825278):
        # they are not a wave in flight.
        self.p.git("checkout", "-q", "-b", "claude/wave-7a-alpha-abc123")
        self.p.write_wave_docs("7A")
        self.p.git("add", "-A")
        self.p.git("commit", "-q", "-m", "wave 7A docs")
        self.p.git("checkout", "-q", "main")
        self.p.git("merge", "-q", "--no-ff", "-m", "Merge", "claude/wave-7a-alpha-abc123")
        code, out, err = self.p.route("7A")
        self.assertEqual(code, 0, err)
        self.assertEqual(out["status"], "done")

    def test_a_lookalike_worktree_is_not_the_wave(self):  # V2-08
        # ffbapp: 6B's suffix is wave-6b-h1-harness, and the stale
        # claude/wave-6b-h1-eval-55aa75 matched the old segment test.
        stale = self.worktree("claude/wave-7a-h1-eval-55aa75", name="a-stale")
        wt = self.worktree()
        self.assertEqual(self.run_in(wt, "route", "--wave", "7A")[0], 0)
        record = wt / ".bmad" / "wave-7A" / "wave.md"
        for root in (self.p.root, stale, wt):
            code, out, err = self.run_in(root, "route", "--wave", "7A")
            self.assertEqual(code, 0, err)
            self.assertEqual(Path(out["record"]).resolve(), record)
        self.assertFalse((stale / ".bmad").exists())

    def test_two_worktrees_on_the_suffix_are_refused_by_name(self):  # ruling (a)
        one = self.worktree("wave-7a-alpha", name="one")
        two = self.worktree("claude/wave-7a-alpha-def456", name="two")
        code, out, err = self.p.route("7A")
        self.assertEqual(code, 3, err)
        self.assertEqual(out["error"], "ambiguous_worktree")
        self.assertIn(str(one), err)
        self.assertIn(str(two), err)
        self.assertFalse(self.main_dir().exists())

    def test_a_suffix_is_matched_whole(self):
        # wave-7a-alpha must not take wave-7a-alphabet or a non-hash tail.
        self.worktree("claude/wave-7a-alphabet", name="one")
        self.worktree("claude/wave-7a-alpha-fix", name="two")
        code, out, err = self.p.route("7A")
        self.assertEqual(code, 0, err)
        self.assertEqual(Path(out["record"]).resolve(), self.main_dir() / "wave.md")

    def test_the_checkout_list_read_from_git_files_matches_git(self):
        # checkouts() reads .git/worktrees/ itself, for the gate's speed.
        sys.path.insert(0, str(SCRIPT.parent))
        import wave_status
        self.worktree()
        self.worktree("claude/wave-7b-beta-abc123")
        root = self.p.root.resolve()
        self.p.git("worktree", "add", "-q", "--detach", str(root / ".claude" / "worktrees" / "det"))
        gone = self.worktree("wave-8a-gamma", name="gone")
        subprocess.run(["rm", "-rf", str(gone)], check=True)
        out = subprocess.run(["git", "-C", str(root), "worktree", "list", "--porcelain"],
                             capture_output=True, text=True, check=True).stdout
        listed, path = [], None
        for line in out.splitlines():
            if line.startswith("worktree "):
                path = Path(line[len("worktree "):]).resolve()
                listed.append([path, None])
            elif line.startswith("branch "):
                listed[-1][1] = line[len("branch refs/heads/"):]
        expected = sorted((p, b) for p, b in listed if p.is_dir())
        self.assertEqual(len(expected), 4)
        self.assertEqual(sorted(wave_status.checkouts(root)), expected)

    def test_adopt_refuses_from_inside_the_worktree_it_precedes(self):  # V2-15
        wt = self.worktree()
        self.assertEqual(self.run_in(wt, "route", "--wave", "7A")[0], 0)
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
        args = ("adopt", "--wave", "7A", "--from", str(wt))
        for cwd, extra in ((wt, {}),
                           (self.p.root, {"CLAUDE_PROJECT_DIR": str(wt)})):
            code, out, err = self.run_in(self.p.root, *args, cwd=cwd, env=dict(env, **extra))
            self.assertEqual(code, 1, err)
            self.assertEqual(out["error"], "inside_worktree")
            self.assertIn(str(self.p.root.resolve()), err)
            self.assertFalse(self.main_dir().exists())
        code, out, err = self.run_in(self.p.root, *args, cwd=self.p.root, env=env)
        self.assertEqual(code, 0, err)
        self.assertIn("wave.md", out["adopted"])


class Mark(unittest.TestCase):
    """`mark` writes a step's marker where route printed the record, from
    either checkout. A desktop session isolated to the worktree is refused
    the Write tool on main's `.bmad/` and told to write in the worktree; a
    marker there splits the state (2026-10-25)."""

    setUp = OneStateRoot.setUp
    worktree = OneStateRoot.worktree
    run_in = OneStateRoot.run_in
    main_dir = OneStateRoot.main_dir

    def mark_in(self, root, step, wave="7A"):
        return self.run_in(root, "mark", "--wave", wave, "--step", step)

    def test_a_worktree_rooted_session_marks_beside_a_main_record(self):
        self.assertEqual(self.p.route("7A")[0], 0)
        wt = self.worktree()
        code, out, err = self.mark_in(wt, "1")
        self.assertEqual(code, 0, err)
        self.assertEqual(Path(out["marker"]).resolve(), self.main_dir() / "step-1.done")
        self.assertTrue((self.main_dir() / "step-1.done").is_file())
        self.assertFalse((wt / ".bmad").exists())
        code, out, err = self.run_in(wt, "route", "--wave", "7A")
        self.assertEqual(code, 0, err)
        self.assertEqual(out["completed_steps"], ["1"])
        self.assertEqual(out["reentry_step"], "2")

    def test_a_main_rooted_session_marks_beside_a_worktree_record(self):
        wt = self.worktree()
        self.assertEqual(self.run_in(wt, "route", "--wave", "7A")[0], 0)
        code, out, err = self.mark_in(self.p.root, "4.5")
        self.assertEqual(code, 0, err)
        own = wt / ".bmad" / "wave-7A"
        self.assertEqual(Path(out["marker"]).resolve(), own / "step-4.5.done")
        self.assertEqual(Path(out["record"]).resolve(), own / "wave.md")
        self.assertFalse(self.main_dir().exists())

    def test_with_no_copy_the_marker_starts_where_route_starts_the_record(self):
        wt = self.worktree()
        code, out, err = self.mark_in(wt, "1")
        self.assertEqual(code, 0, err)
        own = wt / ".bmad" / "wave-7A"
        self.assertEqual(Path(out["marker"]).resolve(), own / "step-1.done")
        code, out, err = self.run_in(wt, "route", "--wave", "7A")
        self.assertEqual(code, 0, err)
        self.assertEqual(Path(out["record"]).resolve(), own / "wave.md")
        self.assertFalse(self.main_dir().exists())

    def test_marking_twice_keeps_one_empty_marker(self):
        self.assertEqual(self.p.route("7A")[0], 0)
        for _ in range(2):
            self.assertEqual(self.mark_in(self.p.root, "2")[0], 0)
        self.assertEqual((self.main_dir() / "step-2.done").read_bytes(), b"")

    def test_a_step_dev_wave_does_not_have_is_refused(self):
        self.assertEqual(self.p.route("7A")[0], 0)
        for step in ("13", "4.6", "0", "1.0", "../wave.md", ""):
            code, out, err = self.mark_in(self.p.root, step)
            self.assertEqual(code, 2, f"{step!r}: {err}")
            if step:
                self.assertEqual(out["error"], "unknown_step")
        self.assertEqual(sorted(p.name for p in self.main_dir().iterdir()), ["wave.md"])

    def test_a_split_is_refused_and_nothing_is_written(self):
        wt = self.worktree()
        self.assertEqual(self.run_in(wt, "route", "--wave", "7A")[0], 0)
        self.main_dir().mkdir(parents=True)
        (self.main_dir() / "evaluation-session").write_text("s1\n")
        for root in (self.p.root, wt):
            code, out, err = self.mark_in(root, "1")
            self.assertEqual(code, 3, err)
            self.assertEqual(out["error"], "split_state")
        self.assertFalse((self.main_dir() / "step-1.done").exists())
        self.assertFalse((wt / ".bmad" / "wave-7A" / "step-1.done").exists())

    def test_two_worktrees_on_the_suffix_are_refused_and_nothing_is_written(self):
        one = self.worktree("wave-7a-alpha", name="one")
        two = self.worktree("claude/wave-7a-alpha-def456", name="two")
        code, out, err = self.mark_in(one, "1")
        self.assertEqual(code, 3, err)
        self.assertEqual(out["error"], "ambiguous_worktree")
        for root in (self.p.root, one, two):
            self.assertFalse((root / ".bmad").exists(), root)

    def test_a_wave_not_in_the_map_is_refused(self):
        code, out, _ = self.mark_in(self.p.root, "1", wave="9Z")
        self.assertEqual(code, 2)
        self.assertEqual(out["error"], "wave_not_in_map")

    def test_mark_needs_step(self):
        out = subprocess.run([sys.executable, str(SCRIPT), "mark", "--wave", "7A",
                              "--project-root", str(self.p.root)],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 2)
        self.assertIn("mark needs --wave and --step", out.stderr)


class Pend(unittest.TestCase):
    """`pend` writes step 4.5's `step-4.5.pending` where route printed the
    record, and `pend --clear` removes it, from either checkout. The Write
    tool's refusal in an isolated session sends a hand-written one to the
    worktree, which splits the state (2026-10-25)."""

    GATE = SCRIPT.parent / "wave_gate.py"

    setUp = OneStateRoot.setUp
    worktree = OneStateRoot.worktree
    run_in = OneStateRoot.run_in
    main_dir = OneStateRoot.main_dir

    def questions(self, text="Q: which auth provider?\n"):
        f = self.p.root.parent / f"{self.p.root.name}-questions.md"
        f.write_text(text)
        self.addCleanup(f.unlink, missing_ok=True)
        return f

    def pend_in(self, root, *args, wave="7A"):
        return self.run_in(root, "pend", "--wave", wave, *args)

    def session_end(self, root):
        out = subprocess.run([sys.executable, str(self.GATE), "session-end",
                              "--project-root", str(root)],
                             input=json.dumps({"session_id": "s1", "cwd": str(root),
                                               "hook_event_name": "SessionEnd",
                                               "reason": "other"}),
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        return out.stdout

    def test_a_worktree_rooted_session_pends_beside_a_main_record(self):
        self.assertEqual(self.p.route("7A")[0], 0)
        wt = self.worktree()
        code, out, err = self.pend_in(wt, "--questions-file", str(self.questions()))
        self.assertEqual(code, 0, err)
        marker = self.main_dir() / "step-4.5.pending"
        self.assertEqual(Path(out["marker"]).resolve(), marker)
        self.assertEqual(marker.read_text(), "Q: which auth provider?\n")
        self.assertFalse((wt / ".bmad").exists())
        self.assertIn("wave 7A", self.session_end(wt))
        self.assertIn("status: blocked", self.p.record_text("7A"))

    def test_a_main_rooted_session_pends_beside_a_worktree_record(self):
        wt = self.worktree()
        self.assertEqual(self.run_in(wt, "route", "--wave", "7A")[0], 0)
        code, out, err = self.pend_in(self.p.root, "--questions-file", str(self.questions()))
        self.assertEqual(code, 0, err)
        own = wt / ".bmad" / "wave-7A"
        self.assertEqual(Path(out["marker"]).resolve(), own / "step-4.5.pending")
        self.assertEqual(Path(out["record"]).resolve(), own / "wave.md")
        self.assertFalse(self.main_dir().exists())
        self.assertIn("wave 7A", self.session_end(self.p.root))
        self.assertIn("status: blocked", (own / "wave.md").read_text())

    def test_with_no_copy_the_marker_starts_where_route_starts_the_record(self):
        wt = self.worktree()
        code, out, err = self.pend_in(wt, "--questions-file", str(self.questions()))
        self.assertEqual(code, 0, err)
        own = wt / ".bmad" / "wave-7A"
        self.assertEqual(Path(out["marker"]).resolve(), own / "step-4.5.pending")
        code, out, err = self.run_in(wt, "route", "--wave", "7A")
        self.assertEqual(code, 0, err)
        self.assertEqual(Path(out["record"]).resolve(), own / "wave.md")
        self.assertFalse(self.main_dir().exists())

    def test_clear_removes_the_marker_from_either_checkout(self):
        self.assertEqual(self.p.route("7A")[0], 0)
        wt = self.worktree()
        marker = self.main_dir() / "step-4.5.pending"
        for root in (wt, self.p.root):
            self.assertEqual(self.pend_in(root, "--questions-file", str(self.questions()))[0], 0)
            self.assertTrue(marker.is_file())
            code, out, err = self.pend_in(root, "--clear")
            self.assertEqual(code, 0, err)
            self.assertEqual(Path(out["marker"]).resolve(), marker)
            self.assertTrue(out["cleared"])
            self.assertFalse(marker.exists())
        self.assertNotIn("wave 7A", self.session_end(self.p.root))
        self.assertIn("status: draft", self.p.record_text("7A"))

    def test_clearing_with_no_marker_is_not_an_error(self):
        self.assertEqual(self.p.route("7A")[0], 0)
        code, out, err = self.pend_in(self.p.root, "--clear")
        self.assertEqual(code, 0, err)
        self.assertFalse(out["cleared"])

    def test_a_split_is_refused_and_nothing_is_written_or_removed(self):
        wt = self.worktree()
        self.assertEqual(self.run_in(wt, "route", "--wave", "7A")[0], 0)
        own = wt / ".bmad" / "wave-7A" / "step-4.5.pending"
        own.write_text("Q?\n")
        self.main_dir().mkdir(parents=True)
        (self.main_dir() / "evaluation-session").write_text("s1\n")
        for root in (self.p.root, wt):
            for args in (("--questions-file", str(self.questions())), ("--clear",)):
                code, out, err = self.pend_in(root, *args)
                self.assertEqual(code, 3, f"{root} {args}: {err}")
                self.assertEqual(out["error"], "split_state")
        self.assertFalse((self.main_dir() / "step-4.5.pending").exists())
        self.assertEqual(own.read_text(), "Q?\n")

    def test_two_worktrees_on_the_suffix_are_refused_and_nothing_is_written(self):
        one = self.worktree("wave-7a-alpha", name="one")
        two = self.worktree("claude/wave-7a-alpha-def456", name="two")
        code, out, err = self.pend_in(one, "--questions-file", str(self.questions()))
        self.assertEqual(code, 3, err)
        self.assertEqual(out["error"], "ambiguous_worktree")
        for root in (self.p.root, one, two):
            self.assertFalse((root / ".bmad").exists(), root)

    def test_a_missing_or_empty_questions_file_is_refused(self):
        self.assertEqual(self.p.route("7A")[0], 0)
        for f in (self.p.root.parent / "no-such-questions.md", self.questions(" \n")):
            code, out, err = self.pend_in(self.p.root, "--questions-file", str(f))
            self.assertEqual(code, 2, f"{f}: {err}")
            self.assertEqual(out["error"], "no_questions")
        self.assertFalse((self.main_dir() / "step-4.5.pending").exists())

    def test_a_wave_not_in_the_map_is_refused(self):
        code, out, _ = self.pend_in(self.p.root, "--clear", wave="9Z")
        self.assertEqual(code, 2)
        self.assertEqual(out["error"], "wave_not_in_map")

    def test_pend_needs_exactly_one_of_questions_file_and_clear(self):
        for extra in ([], ["--clear", "--questions-file", str(self.questions())]):
            out = subprocess.run([sys.executable, str(SCRIPT), "pend", "--wave", "7A", *extra,
                                  "--project-root", str(self.p.root)],
                                 capture_output=True, text=True)
            self.assertEqual(out.returncode, 2)
            self.assertIn("pend needs --wave and one of --questions-file or --clear", out.stderr)


class NoSkillWritesAMarkerItself(unittest.TestCase):
    """Every step marker goes through `wave_status.py mark`, and step 4.5's
    pending marker through `wave_status.py pend`: no skill tells the agent
    to write, touch, create or delete a `step-*.done` or `step-*.pending`
    path (or a checkpoint marker) itself. Version histories are left out;
    they describe what earlier versions did."""

    SKILLS = SCRIPT.parent.parent.parent
    WRITE = re.compile(r"\b(?:write|writes|writing|wrote|written|touch|touches|"
                       r"create|creates|creating|echo|delete|deletes|deleting|"
                       r"remove|removes|removing|rm)\b", re.I)
    MARKER = re.compile(r"step-[^\s`]*\.(?:done|pending)|checkpoint markers?", re.I)

    def offending(self, text):
        text = text.split("\n## Version history", 1)[0]
        sentences = re.split(r"(?<=[.:;])\s+|\n\s*\n", text)
        return [" ".join(s.split()) for s in sentences
                if self.WRITE.search(s) and self.MARKER.search(s)
                and "wave_status.py mark" not in s and "wave_status.py pend" not in s]

    def test_no_skill_md_writes_a_step_marker(self):
        skills = sorted(self.SKILLS.glob("*/SKILL.md"))
        self.assertTrue(any(p.parent.name == "bmad-dev-wave" for p in skills), self.SKILLS)
        found = {str(p.relative_to(self.SKILLS)): self.offending(p.read_text(encoding="utf-8"))
                 for p in skills}
        self.assertEqual({k: v for k, v in found.items() if v}, {})

    def test_the_check_catches_the_old_prose(self):
        self.assertTrue(self.offending(
            "When the answers are recorded, delete that marker and write step-4.5.done."))
        self.assertTrue(self.offending(
            "Each step writes a checkpoint marker in the wave's state directory."))
        self.assertTrue(self.offending("Run `touch .bmad/wave-7A/step-3.done`."))
        self.assertTrue(self.offending(
            "On any hit, write the questions to\n    .bmad/wave-<id>/step-4.5.pending "
            "and HALT for user input"))
        self.assertTrue(self.offending("Then rm .bmad/wave-7A/step-4.5.pending."))
        self.assertFalse(self.offending(
            "On any hit, write the questions to step-4.5.pending with "
            "`wave_status.py pend --questions-file <file>`."))
        self.assertFalse(self.offending(
            "Each step ends by writing its marker with `wave_status.py mark --step 3`, "
            "which puts step-3.done beside the record."))


if __name__ == "__main__":
    unittest.main()
