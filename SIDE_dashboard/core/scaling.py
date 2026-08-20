"""Three scaling methods used across the dashboard.

Direct ports of the transformations in ``skewed_column_scaling_analysis.ipynb``
(cell 3), plus the z-score method:

- ``full_minmax``: simple min-max normalisation over the observed range.
- ``capped_minmax``: min-max over a chosen percentile window (default 5th to
  95th), so a handful of extreme values cannot dominate the scale.
- ``z_score``: standardise each column to ``(x - mean) / std`` (population
  standard deviation), then map to 0-1 with the logistic curve
  ``1 / (1 + exp(-z))``.  The logistic transform is monotone, so ranks match a
  literal z-score ranking, while the output stays on the same 0-1 scale as the
  other methods.  A constant column (zero variance) maps every country to the
  neutral point 0.5.

All functions drop missing values and return a Series aligned to the input.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

METHOD_FULL = "full"
METHOD_CAPPED = "capped"
METHOD_Z = "z"
ALL_METHODS = [METHOD_FULL, METHOD_CAPPED, METHOD_Z]

METHOD_LABELS = {
    METHOD_FULL: "Full-range min-max",
    METHOD_CAPPED: "Capped min-max",
    METHOD_Z: "Z-score (standardized)",
}

# Compact names for column headers, radio options and short captions.
METHOD_SHORT_LABELS = {
    METHOD_FULL: "Full",
    METHOD_CAPPED: "Capped",
    METHOD_Z: "Z-score",
}


def full_minmax(series: pd.Series) -> pd.Series:
    s = series.dropna()
    if s.max() == s.min():
        return pd.Series(0.0, index=s.index)
    return (s - s.min()) / (s.max() - s.min())


def capped_minmax(series: pd.Series, lower: float = 0.05, upper: float = 0.95) -> pd.Series:
    s = series.dropna()
    low = s.quantile(lower)
    high = s.quantile(upper)
    if high == low:
        return pd.Series(0.0, index=s.index)
    clipped = s.clip(lower=low, upper=high)
    return (clipped - low) / (high - low)


def z_score(series: pd.Series) -> pd.Series:
    """Standardise to z-scores, then map to 0-1 via the logistic curve.

    ``z = (x - mean) / std`` (population std) followed by ``1 / (1 + exp(-z))``.
    The logistic transform is monotone, so the ranking is identical to a literal
    z-score ranking, while the values stay on the same 0-1 scale as the other
    three methods.  A constant column (zero variance) has no spread to measure,
    so every country maps to the neutral point 0.5.
    """
    s = series.dropna()
    if len(s) == 0:
        return pd.Series(dtype=float, index=s.index)
    std = s.std(ddof=0)
    if std == 0:
        return pd.Series(0.5, index=s.index)
    z = (s - s.mean()) / std
    return 1.0 / (1.0 + np.exp(-z))


def transform_series(
    series: pd.Series,
    method: str,
    lower: float = 0.05,
    upper: float = 0.95,
) -> pd.Series:
    """Apply one of the scalings to a raw series."""
    if method == METHOD_FULL:
        return full_minmax(series)
    if method == METHOD_CAPPED:
        return capped_minmax(series, lower, upper)
    if method == METHOD_Z:
        return z_score(series)
    raise ValueError(f"Unknown scaling method: {method!r}")
