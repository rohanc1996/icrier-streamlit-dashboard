"""Three scaling methods used across the dashboard.

Direct ports of the transformations in ``skewed_column_scaling_analysis.ipynb``
(cell 3):

- ``full_minmax``: simple min-max normalisation over the observed range.
- ``capped_minmax``: min-max over a chosen percentile window (default 5th to
  95th), so a handful of extreme values cannot dominate the scale.
- ``log_minmax``: log1p transform followed by min-max, which compresses the
  upper tail and highlights percentage-like differences.

All functions drop missing values and return a Series aligned to the input.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

METHOD_FULL = "full"
METHOD_CAPPED = "capped"
METHOD_LOG = "log"
ALL_METHODS = [METHOD_FULL, METHOD_CAPPED, METHOD_LOG]

METHOD_LABELS = {
    METHOD_FULL: "Full-range min-max",
    METHOD_CAPPED: "Capped min-max",
    METHOD_LOG: "Log-transformed min-max",
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


def log_minmax(series: pd.Series) -> pd.Series:
    s = series.dropna()
    logged = np.log1p(s)
    if logged.max() == logged.min():
        return pd.Series(0.0, index=s.index)
    return (logged - logged.min()) / (logged.max() - logged.min())


def transform_series(
    series: pd.Series,
    method: str,
    lower: float = 0.05,
    upper: float = 0.95,
) -> pd.Series:
    """Apply one of the three scalings to a raw series."""
    if method == METHOD_FULL:
        return full_minmax(series)
    if method == METHOD_CAPPED:
        return capped_minmax(series, lower, upper)
    if method == METHOD_LOG:
        return log_minmax(series)
    raise ValueError(f"Unknown scaling method: {method!r}")
