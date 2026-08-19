"""Ranking, percentile and score-stability helpers.

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


def score_stability_table(
    data,
    indicator: str,
    lower: float = 0.05,
    upper: float = 0.95,
) -> pd.DataFrame:
    """Score of every country under each scaling method, plus the max swing.

    The four scaling methods are all monotone transforms of the raw value, so
    they always produce the same ordering — the rank can never differ between
    them. What *does* differ is the 0-1 score itself: the swing between the
    highest and lowest score a country receives across the methods shows how
    sensitive that country is to the scaling choice.
    """
    score_cols = list(scaling.ALL_METHODS)
    scores = scaled_scores(data, indicator, lower, upper).dropna(subset=["value"]).copy()
    # skipna: a method that is not applicable to an indicator (e.g. log on
    # negative-valued data) contributes nothing to that country's swing.
    scores["score_swing"] = scores[score_cols].max(axis=1) - scores[score_cols].min(axis=1)
    cols = ["Country", "value"] + score_cols + ["score_swing"]
    return scores[cols].sort_values("score_swing", ascending=False).reset_index(drop=True)


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
