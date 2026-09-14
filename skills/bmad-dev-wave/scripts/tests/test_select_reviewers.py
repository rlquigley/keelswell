#!/usr/bin/env python3
"""Tests for select_reviewers.py. Stdlib only; run with `python3 -m unittest`.

The demonstrations Phase 6.3 has to make are test_no_cap_* (necessity, not a
budget: eight domains in the diff return eight reviewers), test_fixed_three_*
(a wave touching no infrastructure returns no platform reviewer, and a wave
touching a webhook receiver returns the billing reviewer -- the plan's own
verify criterion), and the four precision tests, each of which is a real
ffbapp wave the first version of this script got wrong: test_word_boundary_*,
test_front_matter_*, test_negated_* and test_occurrence_threshold_*.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "select_reviewers.py"
TABLE = Path(__file__).resolve().parent.parent / "reviewer-triggers.yaml"

sys.path.insert(0, str(SCRIPT.parent))
import select_reviewers as sr  # noqa: E402


def run(changed, spec="", table=TABLE, extra=()):
    """Run the script over an inline file list and spec, return parsed JSON."""
    with tempfile.TemporaryDirectory() as tmp:
        files = Path(tmp) / "changed.txt"
        files.write_text("\n".join(changed) + "\n")
        argv = ["select", "--changed-files", str(files), "--json", *extra]
        if spec:
            spec_file = Path(tmp) / "spec.md"
            spec_file.write_text(spec)
            argv += ["--spec", str(spec_file)]
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--table", str(table), *argv],
            capture_output=True, text=True,
        )
        return proc, (json.loads(proc.stdout) if proc.returncode == 0 else None)


def roles(result):
    return {hit["role"] for hit in result["selected"]}


class TableIsWellFormed(unittest.TestCase):
    def test_check_passes_on_the_shipped_table(self):
        proc = subprocess.run([sys.executable, str(SCRIPT), "check"],
                              capture_output=True, text=True)
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertIn("ok", proc.stdout)

    def test_every_row_names_where_its_trigger_came_from(self):
        for entry in sr.load_table(TABLE):
            self.assertTrue(entry.get("source"), f"{entry['role']} has no source")

    def test_a_row_that_cannot_fire_must_say_why(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "t.yaml"
            bad.write_text(
                "version: 1\nreviewers:\n"
                "  - role: custom-x\n    skill: agent-x\n"
                "    display: \"X\"\n    source: \"none\"\n    trigger: \"t\"\n"
            )
            with self.assertRaises(sr.TableError) as ctx:
                sr.validate(sr.load_table(bad))
            self.assertIn("visible", str(ctx.exception))

    def test_an_inert_row_cannot_also_carry_patterns(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "t.yaml"
            bad.write_text(
                "version: 1\nreviewers:\n"
                "  - role: custom-x\n    skill: agent-x\n"
                "    display: \"X\"\n    source: \"none\"\n    trigger: \"t\"\n"
                "    inert: \"because\"\n    paths:\n      - \"**/x*\"\n"
            )
            with self.assertRaises(sr.TableError):
                sr.validate(sr.load_table(bad))


class NoCap(unittest.TestCase):
    """Necessity, not a budget. Nothing in the script limits the count."""

    def test_no_cap_returns_every_domain_that_is_genuinely_in_the_diff(self):
        _, result = run([
            "src/engine/backtest.py",            # ml
            "src/platform/run_manifest.py",      # sre
            "src/api/auth.py",                   # appsec
            "src/web/templates/page.html",       # accessibility + design-critic
            "src/billing/webhook.py",            # billing
            "src/analytics/events/api.py",       # analytics
            "src/cache/redis_pool.py",           # performance
            "src/legal/consent_flow.py",         # legal
            "src/prompts/answer.py",             # llm
            ".github/workflows/ci.yml",          # platform
        ])
        self.assertGreaterEqual(len(result["selected"]), 8)
        self.assertEqual(len(result["selected"]),
                         len({h["role"] for h in result["selected"]}))

    def test_one_domain_returns_one_reviewer(self):
        _, result = run(["src/engine/backtest.py"])
        self.assertEqual({"custom-ml"}, roles(result))

    def test_an_empty_selection_is_an_answer_not_an_error(self):
        proc, result = run(["README.md"])
        self.assertEqual(0, proc.returncode)
        self.assertEqual(set(), roles(result))


class FixedThreeLoseTheirExemption(unittest.TestCase):
    """The plan's verify criterion for 6.3, both halves."""

    def test_fixed_three_no_infrastructure_means_no_platform_reviewer(self):
        _, result = run(["src/engine/backtest.py", "tests/test_backtest.py"])
        self.assertNotIn("arch-platform-engineer", roles(result))

    def test_fixed_three_a_webhook_receiver_dispatches_the_billing_reviewer(self):
        _, result = run(["src/payments/webhook_receiver.py"])
        self.assertIn("custom-billing", roles(result))

    def test_fixed_three_infrastructure_still_dispatches_platform(self):
        _, result = run([".github/workflows/deploy.yml", "ops/Dockerfile"])
        self.assertIn("arch-platform-engineer", roles(result))


class SpecPrecision(unittest.TestCase):
    """Each test is a real ffbapp wave the naive matcher got wrong."""

    def test_word_boundary_constraint_does_not_fire_train(self):
        # Wave 4A: "train" appears three times, every one inside "constraint".
        spec = "A database check constraint refuses it. The constraint is a constraint."
        _, result = run(["src/contract/events.py"], spec)
        self.assertNotIn("custom-ml", roles(result))

    def test_word_boundary_still_matches_an_inflection(self):
        spec = "The training window is bounded. Training runs nightly."
        self.assertTrue(sr.spec_matches("train", spec))

    def test_front_matter_is_not_prose(self):
        # A test design's inputDocuments names what the wave READ.
        spec = (
            "---\ntitle: \"Wave 9A test design\"\ninputDocuments:\n"
            "  - planning/grounding-design.md\n  - planning/grounding-notes.md\n"
            "---\n\nThis wave changes the week clock.\n"
        )
        _, result = run(["src/clock.py"], spec)
        self.assertNotIn("custom-llm", roles(result))

    def test_negated_sentence_is_not_a_hit(self):
        # Waves 3D, 4B, 5C and 5D all say exactly this.
        spec = ("No rendered surface exists in this wave. "
                "Playwright: no rendered surface, so the lane is unchanged.")
        _, result = run(["src/engine/compiler.py"], spec)
        self.assertNotIn("custom-design-critic", roles(result))

    def test_negated_does_not_suppress_an_affirmative_mention(self):
        spec = ("No rendered surface existed before. "
                "This wave adds the rendered surface and its rendered surface tests.")
        self.assertTrue(sr.spec_matches("rendered surface", spec))

    def test_occurrence_threshold_one_mention_is_a_cross_reference(self):
        # Wave 3D quotes the architecture spine's component list once.
        spec = "engine holds event substrate, rule compiler, archetype engine, backtest harness."
        _, result = run(["src/engine/compiler.py"], spec)
        self.assertNotIn("custom-ml", roles(result))

    def test_occurrence_threshold_two_mentions_is_the_subject(self):
        spec = "The backtest window is bounded. Every backtest runs forward-only."
        _, result = run(["src/engine/compiler.py"], spec)
        self.assertIn("custom-ml", roles(result))


class PathPrecision(unittest.TestCase):
    def test_a_top_level_file_matches_a_starstar_pattern(self):
        _, result = run(["Dockerfile"])
        self.assertIn("arch-platform-engineer", roles(result))

    def test_regression_is_not_egress(self):
        # `**/*egress*` fired the cost reviewer on test_h2_regression.py.
        _, result = run(["tests/unit/test_h2_regression.py"])
        self.assertNotIn("arch-cost-optimizer", roles(result))

    def test_a_session_wrap_note_is_not_an_http_session(self):
        # `**/session*` fired the security reviewer on five of eighteen waves.
        _, result = run(["_bmad-output/session-wrap/2026-09-10T05-11-00Z/triage.md"])
        self.assertEqual(set(), roles(result))

    def test_django_models_py_is_not_an_ml_model(self):
        _, result = run(["src/platform/compute/models.py"])
        self.assertNotIn("custom-ml", roles(result))

    def test_bookkeeping_paths_are_counted_and_excluded(self):
        _, result = run(["TODO.md", "HANDOFF.md", "docs/wave-9a/test-design.md",
                         "src/engine/backtest.py"])
        self.assertEqual(3, result["ignored_file_count"])
        self.assertEqual(1, result["changed_file_count"])
        self.assertEqual({"custom-ml"}, roles(result))


class InertRows(unittest.TestCase):
    def test_the_three_inert_rows_never_appear_in_a_selection(self):
        _, result = run([
            "src/engine/backtest.py", "src/web/templates/page.html",
            "src/billing/webhook.py", ".github/workflows/ci.yml",
        ])
        inert = {row["role"] for row in result["inert"]}
        self.assertEqual({"custom-bizops", "custom-web-designer", "core-bmad-master"}, inert)
        self.assertFalse(inert & roles(result))

    def test_every_inert_row_states_a_reason(self):
        _, result = run(["README.md"])
        for row in result["inert"]:
            self.assertTrue(row["reason"].strip(), row["role"])


class Output(unittest.TestCase):
    def test_json_records_why_each_reviewer_was_selected(self):
        _, result = run(["src/engine/backtest.py"])
        hit = result["selected"][0]
        self.assertEqual("custom-ml", hit["role"])
        self.assertEqual("agent-ml", hit["skill"])
        self.assertTrue(hit["trigger"])
        self.assertTrue(hit["source"])
        self.assertTrue(hit["matched_paths"])

    def test_a_malformed_table_exits_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "t.yaml"
            bad.write_text("version: 1\nreviewers:\n  - role: x\n      bad: indent\n")
            proc, _ = run(["README.md"], table=bad)
            self.assertEqual(2, proc.returncode)
            self.assertIn("select_reviewers:", proc.stderr)


if __name__ == "__main__":
    unittest.main()
