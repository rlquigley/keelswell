#!/usr/bin/env python3
"""The reviewer-selection replay. Stdlib only; run with `python3 -m unittest`.

R5 of docs/reviews/harness-engineering-review-v1.md. Replay runs
select_reviewers.py over the eighteen waves the trigger table was tuned on and
compares what it returns with fixtures/replay-golden.json, by wave and by
role. It needs the fixture replay_fixture.py builds from a private instance,
which is not committed, so it SKIPS wherever that directory is absent -- a
hosted CI runner included. Run it here before any change to the table.

GoldenIsConsistent and Compare need no fixture and run everywhere: the first
checks the golden against the table that ships beside it, the second that a
difference is reported by wave and role.

A failure in Replay is a question, not a verdict: either the table regressed
or the golden is out of date. Read the lines it prints, decide which, and only
then run `replay_fixture.py golden --write`.
"""

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import replay_fixture as rf  # noqa: E402
import select_reviewers as sr  # noqa: E402

FIXTURE = rf.default_fixture_dir()


class GoldenIsConsistent(unittest.TestCase):
    def setUp(self):
        self.golden = rf.load_golden()
        self.rows, _ = sr.load_table(sr.DEFAULT_TABLE)

    def test_the_golden_covers_the_eighteen_waves(self):
        self.assertEqual([wave for wave, _ in rf.WAVES], list(self.golden["waves"]))

    def test_the_summary_is_the_sum_of_the_waves(self):
        self.assertEqual(rf.summarize(self.golden["waves"]), self.golden["summary"])

    def test_every_role_in_the_golden_is_a_row_that_can_fire(self):
        firing = {row["role"] for row in self.rows if not row.get("inert")}
        for wave, entry in self.golden["waves"].items():
            for role in entry["selected"]:
                self.assertIn(role, firing, f"wave {wave}: {role}")

    def test_the_fallback_fires_exactly_where_no_specialist_was_selected(self):
        generalists = {row["role"] for row in self.rows if row.get("generalist") == "yes"}
        for wave, entry in self.golden["waves"].items():
            specialists = [r for r in entry["selected"] if r not in generalists]
            self.assertEqual(not specialists, entry["fallback"], f"wave {wave}")


class Compare(unittest.TestCase):
    def setUp(self):
        self.golden = rf.load_golden()
        self.actual = copy.deepcopy(self.golden)

    def changed(self):
        self.actual["summary"] = rf.summarize(self.actual["waves"])
        return rf.compare(self.golden, self.actual)

    def test_an_unchanged_replay_reports_nothing(self):
        self.assertEqual([], self.changed())

    def test_a_row_that_stops_firing_is_named_by_wave_and_role(self):
        role = self.actual["waves"]["4B"]["selected"].pop(0)
        self.assertIn(f"wave 4B: {role} no longer selected", self.changed())

    def test_a_row_that_starts_firing_is_named_by_wave_and_role(self):
        self.actual["waves"]["3C"]["selected"].append("custom-legal")
        self.assertIn("wave 3C: custom-legal newly selected", self.changed())

    def test_a_fallback_that_stops_firing_is_named(self):
        self.actual["waves"]["3A"]["fallback"] = False
        self.assertIn("wave 3A: fallback no longer fires", self.changed())

    def test_a_stale_fixture_is_not_reported_as_a_table_change(self):
        self.actual["waves"]["2C"]["files"] += 1
        lines = [line for line in self.changed() if line.startswith("wave 2C")]
        self.assertEqual(1, len(lines))
        self.assertIn("Rebuild the fixture", lines[0])


@unittest.skipUnless(
    rf.fixture_present(FIXTURE),
    f"no replay fixture at {FIXTURE}: it is a private instance's paths and test "
    "designs and is not committed. Build it with `python3 replay_fixture.py "
    "build --repo <instance checkout>`",
)
class Replay(unittest.TestCase):
    def test_the_table_returns_what_the_golden_records(self):
        lines = rf.compare(rf.load_golden(), rf.replay(FIXTURE))
        if lines:
            self.fail("\n" + "\n".join(lines))


if __name__ == "__main__":
    unittest.main()
