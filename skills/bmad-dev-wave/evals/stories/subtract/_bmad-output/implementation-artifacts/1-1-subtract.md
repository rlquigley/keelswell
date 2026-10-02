# Story 1.1: subtract

As a caller I can subtract one count from another without going below zero.

## Acceptance criteria
- AC-1: `calc.subtract(a, b)` returns `a - b`.
- AC-2: `calc.subtract` raises `ValueError` when `b` is greater than `a`.
  `calc.subtract(a, a)` returns 0.

## Files
- src/calc.py
- tests/test_calc.py
