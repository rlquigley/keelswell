#!/usr/bin/env python3
"""Tests for wave_status.py. Stdlib only; run with `python3 -m unittest`.

The three demonstrations Phase 2 has to make are test_routes_* (a record at
each status re-enters at the right stage), test_blocked_is_sticky_* (a blocked
wave halts on a second dispatch after its cause is fixed), and
test_hand_edit_clears_block (removing the status by hand lets it proceed).
"""

import contextlib
import json
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
            p.set("7A", "ready-for-dev")
            code, out, _ = p.route("7A")
            self.assertEqual(code, 0)
            self.assertEqual(out["stage"], "implement")
            self.assertEqual(out["reentry_step"], "6")

    def test_routes_in_progress_to_first_incomplete_step(self):
        with project() as p:
            p.set("7A", "in-progress")
            p.mark("7A", "1", "2", "3", "4", "4.5", "5", "6", "7")
            code, out, _ = p.route("7A")
            self.assertEqual(code, 0)
            self.assertEqual(out["stage"], "implement")
            self.assertEqual(out["reentry_step"], "8")

    def test_routes_in_review_to_review_stage(self):
        with project() as p:
            p.set("7A", "in-review")
            p.mark("7A", "10")
            code, out, _ = p.route("7A")
            self.assertEqual(code, 0)
            self.assertEqual(out["stage"], "review")
            self.assertEqual(out["reentry_step"], "11")

    def test_routes_done_to_a_fresh_followup_pass(self):
        """A done wave re-enters at step 10 whatever its markers say: the
        dispatch is a new review pass, not a resumption."""
        with project() as p:
            p.set("7A", "done")
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
            p.set("7A", "done")
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
            p.set("7A", "in-progress")
            p.set("7A", "blocked", reason="verify FAIL on tests/verify-fast.sh")
            code, out, err = p.route("7A")
            self.assertEqual(code, 1)
            self.assertEqual(out["status"], "blocked")
            self.assertIn("verify FAIL", err)

    def test_blocked_halts_again_after_the_cause_is_fixed(self):
        """The whole point. Fixing the cause changes nothing on disk that the
        gate reads, so the second dispatch refuses exactly as the first did."""
        with project() as p:
            p.set("7A", "in-progress")
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
            p.set("7A", "in-progress")
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
            p.set("7A", "in-review")
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
            _, out, _ = p.set("7A", "in-progress")
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


class Show(unittest.TestCase):

    def test_show_lists_every_wave(self):
        with project() as p:
            p.set("7A", "in-progress")
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


if __name__ == "__main__":
    unittest.main()
