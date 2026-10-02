# Wave 1A test design

Story 1.1, backtest window. The backtest splits dated rows at a cutoff into a
training window and a holdout window.

- AC-1: tests/test_backtest.py::TestSplit::test_split_at_cutoff asserts rows before the cutoff are train and the rest are holdout, with a row dated at the cutoff in holdout. ::test_input_order_is_kept passes rows out of date order and asserts each window keeps the input order.
- AC-2: tests/test_backtest.py::TestSplit::test_empty_train_refused and ::test_empty_holdout_refused assert ValueError when the backtest cutoff leaves either window empty.
