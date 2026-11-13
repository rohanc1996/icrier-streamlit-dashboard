---
description: Run all tests and prove 2024–2026 outputs are unchanged
agent: data
---

Run the full regression check for this repository.

1. `cd SIDE_dashboard && ../.venv/bin/python -m tests.test_chips`
2. `./.venv/bin/python scripts/tests/test_gdp_reference.py`
3. `./.venv/bin/python scripts/tests/frozen_years.py`
4. `git status --short` and `git diff --stat`

Report pass/fail for each suite with the failing assertion text if any.

If the frozen-year check fails, do **not** regenerate the golden files. Instead:

- identify the country / indicator / score that moved,
- show the before and after values and the delta,
- trace it to the code or data change that caused it,
- tell me whether the change is intended. If it is, say so explicitly and wait
  for confirmation before updating the baseline.

Finish with one line: is the working tree safe to commit?
