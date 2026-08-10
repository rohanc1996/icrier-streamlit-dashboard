"""Pairwise correlation machinery, including leave-one-out analysis.

Ports the ``compare_pair`` / ``run_theme`` logic from
``skewed_column_scaling_analysis.ipynb`` (cell 8) and adds a leave-one-out
helper for the outlier explorer.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import scaling


def prepare_pair(data, x_col: str, y_col: str):
    """Return (x, y, country names) for the countries with both values."""
    x = data.numeric_df[x_col]
    y = data.numeric_df[y_col]
    common_idx = x.dropna().index.intersection(y.dropna().index)
    x_common = x.loc[common_idx].astype(float)
    y_common = y.loc[common_idx].astype(float)
    countries = data.numeric_df["Country"].loc[common_idx].astype(str)
    return x_common, y_common, countries


def rank_corr(x: pd.Series, y: pd.Series) -> float:
    """Spearman's rho as Pearson correlation of the ranks (no scipy needed).

    pandas' ``Series.corr(method="spearman")`` lazily imports scipy, which is
    not in the dashboard requirements. Rank-then-Pearson is exactly what scipy's
    ``spearmanr`` does, so results are identical while staying dependency-free.
    """
    return float(x.rank().corr(y.rank(), method="pearson"))


def _corr(x: pd.Series, y: pd.Series, method: str) -> float:
    """Pearson or Spearman for a pair of aligned series (no scipy needed)."""
    if method == "spearman":
        return rank_corr(x, y)
    return float(x.corr(y, method="pearson"))


def compare_pair(
    data,
    x_col: str,
    y_col: str,
    lower: float = 0.05,
    upper: float = 0.95,
) -> pd.DataFrame:
    """Pearson and Spearman for each scaling method (mirrors the notebook)."""
    x_common, y_common, _ = prepare_pair(data, x_col, y_col)
    rows = []
    for method in scaling.ALL_METHODS:
        xs = scaling.transform_series(x_common, method, lower, upper).dropna()
        ys = scaling.transform_series(y_common, method, lower, upper).dropna()
        common = xs.index.intersection(ys.index)
        if len(common) < 3:
            pearson = spearman = np.nan
        else:
            xc, yc = xs.loc[common], ys.loc[common]
            pearson = float(xc.corr(yc, method="pearson"))
            spearman = rank_corr(xc, yc)
        rows.append({
            "method": method,
            "method_label": scaling.METHOD_LABELS[method],
            "n": int(len(common)),
            "pearson": pearson,
            "spearman": spearman,
        })
    return pd.DataFrame(rows)


def corr_with_exclusions(
    data,
    x_col: str,
    y_col: str,
    corr_method: str = "spearman",
    excluded: list[str] | None = None,
    scaling_method: str = scaling.METHOD_CAPPED,
    lower: float = 0.05,
    upper: float = 0.95,
):
    """Correlation after removing the given countries (uses capped scaling)."""
    x_common, y_common, countries = prepare_pair(data, x_col, y_col)
    keep = ~countries.isin(excluded or [])
    xs = scaling.transform_series(x_common[keep], scaling_method, lower, upper).dropna()
    ys = scaling.transform_series(y_common[keep], scaling_method, lower, upper).dropna()
    common = xs.index.intersection(ys.index)
    if len(common) < 3:
        return np.nan, int(len(common))
    return _corr(xs.loc[common], ys.loc[common], corr_method), int(len(common))


def leave_one_out(
    data,
    x_col: str,
    y_col: str,
    corr_method: str = "spearman",
    scaling_method: str = scaling.METHOD_CAPPED,
    lower: float = 0.05,
    upper: float = 0.95,
):
    """Correlation with each country removed one at a time.

    Returns ``(result_df, base_correlation)`` where ``result_df`` has columns
    ``country``, ``corr_without`` and ``delta`` (corr_without - base), sorted by
    the absolute change. Uses capped scaling (the robust default).
    """
    x_common, y_common, countries = prepare_pair(data, x_col, y_col)
    xs = scaling.transform_series(x_common, scaling_method, lower, upper)
    ys = scaling.transform_series(y_common, scaling_method, lower, upper)
    common = xs.index.intersection(ys.index)
    xs, ys, countries = xs.loc[common], ys.loc[common], countries.loc[common]

    if len(common) < 4:
        return pd.DataFrame(), np.nan

    base = _corr(xs, ys, corr_method)
    rows = []
    for country in countries.unique():
        mask = countries != country
        if mask.sum() < 3:
            continue
        without = _corr(xs[mask], ys[mask], corr_method)
        rows.append({
            "country": country,
            "n": int(mask.sum()),
            "corr_without": without,
            "delta": without - base,
        })
    out = pd.DataFrame(rows)
    if len(out):
        out["abs_delta"] = out["delta"].abs()
        out = out.sort_values("abs_delta", ascending=False).reset_index(drop=True)
    return out, base
