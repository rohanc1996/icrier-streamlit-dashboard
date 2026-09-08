"""Ranking, percentile and score-stability helpers.

Ranks are always expressed the "intuitive" way: rank 1 = best country. For
indicators where a *lower* raw value is better (e.g. prices, waste), the scaled
scores are inverted so that 1.0 always means "best in the dataset".
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import scaling


def scaled_scores(
    data,
    indicator: str,
    invert_lower_is_better: bool = True,
    methods: list[str] | None = None,
) -> pd.DataFrame:
    """Return Country, raw value, and the scaled scores for an indicator.

    When ``invert_lower_is_better`` is True, scores for indicators where a low
    value is "good" (prices, waste, risk) are flipped to ``1 - score`` so that a
    score of 1.0 always means "best".  ``methods`` restricts the scaling methods
    returned (defaults to all of them).
    """
    methods = methods or list(scaling.ALL_METHODS)
    s = data.numeric_df[indicator]
    df = pd.DataFrame({"Country": data.numeric_df["Country"]})
    df["value"] = s
    for method in methods:
        df[method] = scaling.transform_series(s, method)
    if invert_lower_is_better and not data.higher_is_better.get(indicator, True):
        for method in methods:
            df[method] = 1.0 - df[method]
    return df


def score_stability_table(
    data,
    indicator: str,
    methods: list[str] | None = None,
) -> pd.DataFrame:
    """Score of every country under each scaling method, plus the max swing.

    The scaling methods are all monotone transforms of the raw value, so
    they always produce the same ordering — the rank can never differ between
    them. What *does* differ is the 0-1 score itself: the swing between the
    highest and lowest score a country receives across the methods shows how
    sensitive that country is to the scaling choice.

    ``methods`` restricts which scalings are compared (defaults to all of them).
    """
    methods = methods or list(scaling.ALL_METHODS)
    score_cols = methods
    scores = scaled_scores(data, indicator, methods=methods).dropna(subset=["value"]).copy()
    # skipna: a method with no usable values for this indicator contributes
    # nothing to that country's swing.
    scores["score_swing"] = scores[score_cols].max(axis=1) - scores[score_cols].min(axis=1)
    cols = ["Country", "value"] + score_cols + ["score_swing"]
    return scores[cols].sort_values("score_swing", ascending=False).reset_index(drop=True)


def rank_delta_table(
    baseline: pd.DataFrame,
    custom: pd.DataFrame,
    pillar_names: list[str] | None = None,
) -> pd.DataFrame:
    """Side-by-side of two CHIPS leaderboards.

    Joins the ``chips.chips_table`` output of two frameworks on Country and
    reports each country's rank and CHIPS score under both, plus the deltas
    (Δrank > 0 means the country slipped down under the custom framework).
    Countries that only score under one framework keep a NaN on the other side
    and are sorted to the bottom.  ``pillar_names`` optionally carries the
    custom pillar score columns alongside the CHIPS columns.
    """
    b = baseline.set_index("Country")[["rank", "chips"]]
    c = custom.set_index("Country")[["rank", "chips"]]
    out = pd.DataFrame({
        "baseline_rank": b["rank"],
        "custom_rank": c["rank"],
        "baseline_chips": b["chips"],
        "custom_chips": c["chips"],
    })
    if pillar_names:
        for name in pillar_names:
            out[f"custom_{name}"] = custom.set_index("Country")[name]
    out["Δrank"] = out["custom_rank"] - out["baseline_rank"]
    out["Δchips"] = out["custom_chips"] - out["baseline_chips"]
    # Countries scored under both come first, best custom rank at the top;
    # countries that only score under one framework sink to the bottom.
    out["_both"] = out[["baseline_rank", "custom_rank"]].notna().all(axis=1)
    out = out.sort_values(["_both", "custom_rank"], ascending=[False, True], na_position="last")
    out = out.drop(columns="_both")
    return out[["baseline_rank", "custom_rank", "Δrank",
                "baseline_chips", "custom_chips", "Δchips"]
               + [f"custom_{n}" for n in (pillar_names or [])]]


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


PILLAR_COLUMNS = ["CONNECT", "HARNESS", "INNOVATE", "PROTECT", "SUSTAINABILITY"]


def composite_scaling_comparison(
    data,
    pillars,
    method_a: str,
    method_b: str,
) -> pd.DataFrame:
    """Full-minmax vs z-score comparison of the composite CHIPS index.

    Runs ``chips.chips_table`` under both scaling methods and joins the results
    per country, so every level (overall CHIPS plus the five pillars) carries
    both scores and both ranks, plus the deltas:

    - ``{level}_a`` / ``{level}_b``  — the 0-1 score under each method
    - ``{level}_dscore``             — ``abs(a - b)``
    - ``{level}_rank_a`` / ``{level}_rank_b`` — the rank *within that level*,
      using the published convention (score rounded to 2 dp on the 0-100 scale
      before ranking). So the CONNECT columns rank countries by their CONNECT
      pillar score, not by overall CHIPS.
    - ``{level}_drank``              — ``abs(rank_a - rank_b)``

    Unlike single indicators (where every scaling is a monotone transform and
    ranks never change), the composite aggregates many differently-shaped
    indicator transforms, so the two methods CAN produce different orderings.
    This frame is what the Scaling Comparator's scatter plots and diverger
    tables draw from.
    """
    from . import chips as chips_mod

    ta = chips_mod.chips_table(data, pillars=pillars, method=method_a)
    tb = chips_mod.chips_table(data, pillars=pillars, method=method_b)

    # Rank *within each level* (best = 1), using the published convention:
    # the score is rounded to 2 dp on the 0-100 scale before ranking, exactly
    # as the overall CHIPS rank is derived. For the "chips" level this
    # reproduces ``ta["rank"]``/``tb["rank"]``; for a pillar it ranks countries
    # by that pillar's own score. ``rank`` ignores NaN scores, so a country
    # only competes with others where that level survived.
    rank_a: dict[str, pd.Series] = {}
    rank_b: dict[str, pd.Series] = {}
    for level in ["chips"] + PILLAR_COLUMNS:
        ra_rounded = (ta[level] * 100).round(2) / 100
        rb_rounded = (tb[level] * 100).round(2) / 100
        rank_a[level] = ra_rounded.rank(ascending=False, method="min")
        rank_b[level] = rb_rounded.rank(ascending=False, method="min")
        rank_a[level].index = ta["Country"].values
        rank_b[level].index = tb["Country"].values

    rows = []
    for _, ra in ta.iterrows():
        c = ra["Country"]
        rb = tb.loc[tb["Country"] == c].iloc[0]
        row = {"Country": c}
        for level in ["chips"] + PILLAR_COLUMNS:
            a = ra[level]
            b = rb[level]
            ra_rank = rank_a[level].loc[c]
            rb_rank = rank_b[level].loc[c]
            if pd.isna(a) or pd.isna(b):
                row[f"{level}_a"] = np.nan
                row[f"{level}_b"] = np.nan
                row[f"{level}_dscore"] = np.nan
                row[f"{level}_rank_a"] = np.nan
                row[f"{level}_rank_b"] = np.nan
                row[f"{level}_drank"] = np.nan
                continue
            row[f"{level}_a"] = float(a)
            row[f"{level}_b"] = float(b)
            row[f"{level}_dscore"] = abs(float(a) - float(b))
            row[f"{level}_rank_a"] = int(ra_rank)
            row[f"{level}_rank_b"] = int(rb_rank)
            row[f"{level}_drank"] = abs(int(ra_rank) - int(rb_rank))
        rows.append(row)
    return pd.DataFrame(rows)
