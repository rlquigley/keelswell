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
        p.git("worktree", "add", "-q", "-b", f"claude/wave-{wave.lower()}-x", str(wt))
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


if __name__ == "__main__":
    unittest.main()
