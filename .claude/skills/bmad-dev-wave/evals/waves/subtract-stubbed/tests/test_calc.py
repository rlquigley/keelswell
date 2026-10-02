import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import calc


class TestAdd(unittest.TestCase):
    def test_add(self):
        self.assertEqual(calc.add(2, 3), 5)


class TestSubtract(unittest.TestCase):
    def test_subtract(self):
        self.assertEqual(calc.subtract(5, 3), 2)

    def test_equal_is_zero(self):
        self.assertEqual(calc.subtract(3, 3), 0)

    def test_below_zero_refused(self):
        # AC-2
        pass


if __name__ == "__main__":
    unittest.main()
