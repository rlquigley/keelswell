# Wave 1A test design

Story 1.1, subtract.

- AC-1: tests/test_calc.py::TestSubtract::test_subtract asserts subtract(5, 3) == 2.
- AC-2: tests/test_calc.py::TestSubtract::test_below_zero_refused asserts ValueError for subtract(3, 5), and ::test_equal_is_zero asserts subtract(3, 3) == 0, the boundary.
