import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import backtest

ROWS = [("2024-01-01", 1), ("2024-02-01", 2), ("2024-03-01", 3)]


class TestSplit(unittest.TestCase):
    def test_split_at_cutoff(self):
        train, holdout = backtest.split(ROWS, "2024-02-01")
        self.assertEqual(train, [("2024-01-01", 1)])
        self.assertEqual(holdout, [("2024-02-01", 2), ("2024-03-01", 3)])

    def test_input_order_is_kept(self):
        rows = [("2024-03-01", 3), ("2024-01-01", 1), ("2024-02-15", 2), ("2024-01-15", 4)]
        train, holdout = backtest.split(rows, "2024-02-01")
        self.assertEqual(train, [("2024-01-01", 1), ("2024-01-15", 4)])
        self.assertEqual(holdout, [("2024-03-01", 3), ("2024-02-15", 2)])

    def test_empty_train_refused(self):
        with self.assertRaises(ValueError):
            backtest.split(ROWS, "2024-01-01")

    def test_empty_holdout_refused(self):
        with self.assertRaises(ValueError):
            backtest.split(ROWS, "2024-04-01")


if __name__ == "__main__":
    unittest.main()
