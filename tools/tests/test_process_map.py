"""The process maps in docs/ are what tools/process_map.py draws."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import process_map as pm  # noqa: E402


class TestProcessMap(unittest.TestCase):
    def test_the_committed_maps_are_current(self):
        for m in pm.MAPS:
            with self.subTest(m["file"]):
                self.assertEqual((pm.DOCS / m["file"]).read_text(), pm.draw(m),
                                 "stale map: run python3 tools/process_map.py")

    def test_a_diagonal_link_is_refused(self):
        m = dict(pm.HIGH_LEVEL, links=[("start", "E", "plan", "W", "", [(0, 0.5)])])
        with self.assertRaisesRegex(ValueError, "not straight"):
            pm.draw(m)

    def test_two_steps_in_one_cell_are_refused(self):
        m = dict(pm.HIGH_LEVEL, steps=dict(pm.HIGH_LEVEL["steps"], twin=(0, 0, "step", "Twin")))
        with self.assertRaisesRegex(ValueError, "share a cell"):
            pm.draw(m)


if __name__ == "__main__":
    unittest.main()
