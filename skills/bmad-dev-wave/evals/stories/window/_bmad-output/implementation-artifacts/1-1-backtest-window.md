# Story 1.1: backtest window

As an analyst I can split dated rows into a training window and a holdout
window for a backtest.

## Acceptance criteria
- AC-1: `backtest.split(rows, cutoff)` returns `(train, holdout)`. A row is
  `(date, value)`. Rows dated before `cutoff` are train, the rest are holdout,
  and each list keeps the input order.
- AC-2: `backtest.split` raises `ValueError` when either window would be empty.

## Files
- src/backtest.py
- tests/test_backtest.py
