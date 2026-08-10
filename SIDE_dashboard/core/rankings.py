"""Ranking, percentile and rank-stability helpers.

Ranks are always expressed the "intuitive" way: rank 1 = best country. For
indicators where a *lower* raw value is better (e.g. prices, waste), the scaled
scores are inverted so that 1.0 always means "best in the dataset".
"""
from __future__ import annotations

import pandas as pd

from . import scaling


def scaled_scores(
    data,
    indicator: str,
    lower: float = 0.05,
    upper: float = 0.95,
    invert_lower_is_better: bool = True,
) -> pd.DataFrame:
    """Return Country, raw value, and full/capped/log scores for an indicator.

    When ``invert_lower_is_better`` is True, scores for indicators where a low
    value is "good" (prices, waste, risk) are flipped to ``1 - score`` so that a
    score of 1.0 always means "best".
    """
    s = data.numeric_df[indicator]
    df = pd.DataFrame({"Country": data.numeric_df["Country"]})
    df["value"] = s
    for method in scaling.ALL_METHODS:
        df[method] = scaling.transform_series(s, method, lower, upper)
    if invert_lower_is_better and not data.higher_is_better.get(indicator, True):
        for method in scaling.ALL_METHODS:
            df[method] = 1.0 - df[method]
    return df


def rank_table(
    data,
    indicator: str,
    lower: float = 0.05,
    upper: float = 0.95,
) -> pd.DataFrame:
    """Leaderboard table: rank, country, value, percentile, and the three scores."""
    scores = scaled_scores(data, indicator, lower, upper).dropna(subset=["value"])
    n = len(scores)
    scores = scores.copy()
    # Rank by the capped score (monotonic, so it matches a raw-value ranking).
    scores["rank"] = scores[scaling.METHOD_CAPPED].rank(ascending=False, method="min").astype(int)
    scores["percentile"] = ((n - scores["rank"]) / (n - 1) * 100.0) if n > 1 else 100.0
    cols = ["rank", "Country", "value", "percentile",
            scaling.METHOD_FULL, scaling.METHOD_CAPPED, scaling.METHOD_LOG]
    return scores[cols].sort_values("rank").reset_index(drop=True)


def rank_stability_table(
    data,
    indicator: str,
    lower: float = 0.05,
    upper: float = 0.95,
) -> pd.DataFrame:
    """Rank of every country under each scaling method, plus max swing."""
    scores = scaled_scores(data, indicator, lower, upper).dropna(subset=["value"]).copy()
    for method in scaling.ALL_METHODS:
        scores[f"rank_{method}"] = (
            scores[method].rank(ascending=False, method="min").astype(int)
        )
    rank_cols = [f"rank_{m}" for m in scaling.ALL_METHODS]
    scores["max_swing"] = scores[rank_cols].max(axis=1) - scores[rank_cols].min(axis=1)
    cols = ["Country", "value"] + rank_cols + ["max_swing"]
    return scores[cols].sort_values("max_swing", ascending=False).reset_index(drop=True)


def profile_ranks(data, country: str) -> pd.DataFrame:
    """For one country: rank / total / percentile for every usable indicator."""
    rows = []
    for indicator in data.indicators:
        s = data.numeric_df[indicator].dropna()
        if len(s) < 2:
            continue
        matches = data.numeric_df.loc[data.numeric_df["Country"] == country, indicator]
        if matches.empty:
            continue
        value = matches.iloc[0]
        if pd.isna(value):
            continue
        higher = data.higher_is_better.get(indicator, True)
        rank = int((s > value).sum() + 1) if higher else int((s < value).sum() + 1)
        n = len(s)
        percentile = ((n - rank) / (n - 1) * 100.0) if n > 1 else 100.0
        rows.append({
            "indicator": indicator,
            "value": value,
            "rank": rank,
            "of": n,
            "percentile": percentile,
        })
    result = pd.DataFrame(rows)
    if len(result):
        result = result.sort_values("rank").reset_index(drop=True)
    return result
