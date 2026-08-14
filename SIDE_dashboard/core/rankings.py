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


def _tie_broken_ranks(scores: pd.DataFrame, score_col: str, higher_is_better: bool) -> pd.Series:
    """Competition ranks that break tied scores by the raw value.

    Countries pinned to the same scaled score (e.g. everyone at the upper cap)
    are ordered by their raw value, so the ranking mirrors the raw-value
    ranking. Countries with genuinely identical raw values keep the same rank.
    """
    base = scores[score_col].rank(ascending=False, method="min").astype(int)
    within = (
        scores.groupby(score_col)["value"]
        .rank(ascending=not higher_is_better, method="min")
        .astype(int)
    )
    return base + within - 1


def rank_table(
    data,
    indicator: str,
    lower: float = 0.05,
    upper: float = 0.95,
    rank_method: str = scaling.METHOD_CAPPED,
) -> pd.DataFrame:
    """Leaderboard table: rank, country, value, percentile, and all four scores.

    The headline ``rank`` column uses ``rank_method`` (capped by default),
    breaking any ties by the raw value; the per-method score columns follow.
    """
    scores = scaled_scores(data, indicator, lower, upper).dropna(subset=["value"])
    n = len(scores)
    scores = scores.copy()
    # Rank by the chosen method, breaking any ties by the raw value.
    scores["rank"] = _tie_broken_ranks(
        scores, rank_method, data.higher_is_better.get(indicator, True)
    )
    scores["percentile"] = ((n - scores["rank"]) / (n - 1) * 100.0) if n > 1 else 100.0
    cols = ["rank", "Country", "value", "percentile"] + list(scaling.ALL_METHODS)
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
        scores[f"rank_{method}"] = _tie_broken_ranks(
            scores, method, data.higher_is_better.get(indicator, True)
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
