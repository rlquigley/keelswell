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
import re
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


def table_rows():
    rows, _ = sr.load_table(TABLE)
    return rows


class TableIsWellFormed(unittest.TestCase):
    def test_check_passes_on_the_shipped_table(self):
        proc = subprocess.run([sys.executable, str(SCRIPT), "check"],
                              capture_output=True, text=True)
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertIn("ok", proc.stdout)

    def test_the_table_covers_the_whole_roster(self):
        roster = re.findall(r"^  - role: (\S+)",
                            (SCRIPT.parents[3] / "config" / "agent-names.yaml").read_text(), re.M)
        self.assertTrue(roster, "roster not found")
        table = {e["role"] for e in table_rows()}
        self.assertEqual(set(roster), table,
                         "every agent in config/agent-names.yaml gets a row, and no others")

    def test_every_row_names_where_its_trigger_came_from(self):
        for entry in table_rows():
            self.assertTrue(entry.get("source"), f"{entry['role']} has no source")

    def test_a_row_that_cannot_fire_must_say_why(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "t.yaml"
            bad.write_text(
                "version: 1\n"
                "fallback:\n  method: \"m\"\n  reviewers: \"2\"\n  source: \"s\"\n  brief: \"b\"\n  record_as: \"fallback\"\n"
                "reviewers:\n"
                "  - role: custom-x\n    skill: agent-x\n"
                "    display: \"X\"\n    source: \"none\"\n    trigger: \"t\"\n"
            )
            with self.assertRaises(sr.TableError) as ctx:
                sr.validate(*sr.load_table(bad))
            self.assertIn("visible", str(ctx.exception))

    def test_an_inert_row_cannot_also_carry_patterns(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "t.yaml"
            bad.write_text(
                "version: 1\n"
                "fallback:\n  method: \"m\"\n  reviewers: \"2\"\n  source: \"s\"\n  brief: \"b\"\n  record_as: \"fallback\"\n"
                "reviewers:\n"
                "  - role: custom-x\n    skill: agent-x\n"
                "    display: \"X\"\n    source: \"none\"\n    trigger: \"t\"\n"
                "    inert: \"because\"\n    paths:\n      - \"**/x*\"\n"
            )
            with self.assertRaises(sr.TableError):
                sr.validate(*sr.load_table(bad))


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

    def test_one_domain_returns_one_specialist(self):
        _, result = run(["src/engine/backtest.py"])
        specialists = {h["role"] for h in result["selected"] if not h["generalist"]}
        self.assertEqual({"custom-ml"}, specialists)

    def test_an_empty_selection_is_an_answer_not_an_error(self):
        proc, result = run(["assets/logo.png"])
        self.assertEqual(0, proc.returncode)


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
        self.assertNotIn("custom-appsec", roles(result))

    def test_django_models_py_is_not_an_ml_model(self):
        _, result = run(["src/platform/compute/models.py"])
        self.assertNotIn("custom-ml", roles(result))

    def test_bookkeeping_paths_are_counted_and_excluded(self):
        _, result = run(["TODO.md", "HANDOFF.md", "docs/wave-9a/test-design.md",
                         "src/engine/backtest.py"])
        self.assertEqual(3, result["ignored_file_count"])
        self.assertEqual(1, result["changed_file_count"])
        self.assertIn("custom-ml", roles(result))


class InertRows(unittest.TestCase):
    def test_the_three_inert_rows_never_appear_in_a_selection(self):
        _, result = run([
            "src/engine/backtest.py", "src/web/templates/page.html",
            "src/billing/webhook.py", ".github/workflows/ci.yml",
        ])
        inert = {row["role"] for row in result["inert"]}
        self.assertEqual(
            {"custom-bizops", "custom-web-designer", "core-bmad-master"}, inert)
        self.assertFalse(inert & roles(result))

    def test_every_inert_row_states_a_reason(self):
        _, result = run(["assets/logo.png"])
        for row in result["inert"]:
            self.assertTrue(row["reason"].strip(), row["role"])


class StructuralVocabulary(unittest.TestCase):
    """Rule 5: harness vocabulary appears in every spec and separates nothing."""

    def test_acceptance_criteria_prose_does_not_dispatch_the_qa_seat(self):
        spec = ("The acceptance criterion is quoted in full. A second acceptance "
                "criterion follows, and the acceptance criteria are Given/When/Then.")
        _, result = run(["src/engine/compiler.py"], spec)
        self.assertNotIn("bmm-qa", roles(result))

    def test_functional_requirement_prose_does_not_dispatch_the_pm_seat(self):
        spec = ("FR-8 is the functional requirement this wave serves. The "
                "functional requirement is quoted from the product requirement doc.")
        _, result = run(["src/engine/compiler.py"], spec)
        self.assertNotIn("bmm-pm", roles(result))

    def test_a_word_the_project_has_redefined_is_not_a_trigger(self):
        # ffbapp "prices" a touchdown and has a "presentation dial".
        _, result = run(["tests/unit/test_compiler_piece_pricing.py"])
        self.assertNotIn("custom-billing", roles(result))
        self.assertNotIn("custom-growth", roles(result))

    def test_a_fixture_readme_is_not_documentation(self):
        _, result = run(["tests/fixtures/wave3c/README.md"])
        self.assertNotIn("bmm-tech-writer", roles(result))


class Generalist(unittest.TestCase):
    """bmm-dev answers for no domain, so he never stands in for one."""

    def test_the_generalist_fires_on_any_implementation_diff(self):
        _, result = run(["src/contract/grammar.py"])
        self.assertIn("bmm-dev", roles(result))

    def test_the_generalist_does_not_fire_on_tests_alone(self):
        _, result = run(["tests/unit/test_grammar.py", "tests/db/conftest.py"])
        self.assertNotIn("bmm-dev", roles(result))

    def test_not_paths_removes_a_file_before_paths_is_tested(self):
        _, result = run(["src/app/models.py", "src/app/migrations/0001_initial.py"])
        hit = next(h for h in result["selected"] if h["role"] == "bmm-dev")
        matched = [f for m in hit["matched_paths"] for f in m["files"]]
        self.assertIn("src/app/models.py", matched)
        self.assertNotIn("src/app/migrations/0001_initial.py", matched)

    def test_a_generalist_only_selection_still_gets_the_fallback(self):
        # Wave 3A: production Python, no specialist domain in the diff.
        _, result = run(["src/contract/grammar.py", "src/contract/version.py"])
        self.assertEqual({"bmm-dev"}, roles(result))
        self.assertIsNotNone(result["fallback"])

    def test_one_specialist_retires_the_fallback(self):
        _, result = run(["src/engine/backtest.py"])
        self.assertIn("custom-ml", roles(result))
        self.assertIsNone(result["fallback"])

    def test_only_bmm_dev_is_a_generalist(self):
        generalists = [e["role"] for e in table_rows() if e.get("generalist")]
        self.assertEqual(["bmm-dev"], generalists)


class Fallback(unittest.TestCase):
    """A wave no specialist's trigger fires on still gets attacked."""

    def test_an_empty_selection_returns_the_fallback(self):
        proc, result = run(["assets/logo.png"])
        self.assertEqual(0, proc.returncode)
        self.assertIsNotNone(result["fallback"])
        self.assertTrue(result["fallback"]["brief"])
        self.assertEqual("fallback", result["fallback"]["record_as"])

    def test_a_non_empty_selection_returns_no_fallback(self):
        _, result = run(["src/engine/backtest.py"])
        self.assertTrue(result["selected"])
        self.assertIsNone(result["fallback"])

    def test_the_fallback_is_never_merged_into_selected(self):
        _, result = run(["src/contract/grammar.py"])
        self.assertNotIn("fallback", roles(result))
        self.assertNotIn("fallback", [h["skill"] for h in result["selected"]])

    def test_a_table_with_an_incomplete_fallback_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "t.yaml"
            bad.write_text(
                "version: 1\nfallback:\n  method: \"x\"\nreviewers:\n"
                "  - role: custom-x\n    skill: agent-x\n    display: \"X\"\n"
                "    source: \"none\"\n    trigger: \"t\"\n    paths:\n      - \"**/x*\"\n"
            )
            with self.assertRaises(sr.TableError) as ctx:
                sr.validate(*sr.load_table(bad))
            self.assertIn("reviewed", str(ctx.exception))


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
            proc, _ = run(["src/x.py"], table=bad)
            self.assertEqual(2, proc.returncode)
            self.assertIn("select_reviewers:", proc.stderr)


if __name__ == "__main__":
    unittest.main()
