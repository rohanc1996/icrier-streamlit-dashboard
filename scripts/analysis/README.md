# Analysis scripts

One script, one question, re-runnable.

Use this directory for exploratory and one-off analyses that are worth keeping:
data reconciliation, coverage checks, sensitivity runs, comparisons against a
published figure. If a result matters enough to put in a report, it needs a
script here and a saved output.

Conventions:

- Name the file after the question: `gii_vintage_check.py`,
  `scaling_sensitivity.py`, `ncsi_coverage.py`.
- Read data through `SIDE_dashboard/core/loader.py` (add `SIDE_dashboard` to
  `sys.path`), never a private CSV reader.
- Write outputs to `deliverables/<task>/` (human-facing) or `data/derived/`
  (intermediate). Print a short summary of what was written.
- No hard-coded absolute paths. Resolve relative to the repository root.
- Run with `./.venv/bin/python scripts/analysis/<name>.py`.

If the analysis becomes a recurring check, move it to `scripts/tests/`.
