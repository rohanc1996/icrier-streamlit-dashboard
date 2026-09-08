"""50/50 Relative × Absolute blended CHIPS results.

The dashboard normally scores a single base dataset (Relative or Absolute).
"Combined" runs the *same* CHIPS pipeline once on each of the two canonical raw
frames and blends the two outcomes. Blending happens only at the aggregate
levels — sub-pillar, pillar and CHIPS — exactly the levels the CHIPS Index
Explorer surfaces as "combined".  Individual indicators are never averaged
between the two datasets; they keep the Relative run's values.

Presence policy: when both runs produced a score the blend is the arithmetic
mean (0.5/0.5); when only one run has the aggregate (the other dropped it) that
side's value is used and the node stays present; when neither has it the node is
missing, exactly as a single run would report it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Node kinds where the 50/50 blend is applied.  Indicators (and the INNOVATE · AI
# internal groups just above them) are intentionally left on the Relative run.
BLEND_KINDS = {"sub_pillar", "pillar", "chips"}


def blend_value(a: float | None, b: float | None) -> float | None:
    """50/50 of two scores with the presence fallback described above."""
    if a is None and b is None:
        return None
    if a is None:
        return float(b)
    if b is None:
        return float(a)
    return (float(a) + float(b)) / 2.0


def blended_chips_table(
    rel_table: pd.DataFrame,
    abs_table: pd.DataFrame,
) -> pd.DataFrame:
    """Blend two ``chips_table`` outputs (Relative and Absolute) into one.

    Pillar scores and the final CHIPS score are the 0.5/0.5 mean of the two
    runs (presence fallback: the present side is used when the other run dropped
    the level).  Coverage and indicator counts come from the Relative run.
    Ranks are re-derived from the blended CHIPS score exactly as the single-run
    engine does (2-dp rounding on the 0-100 scale, min rank).
    """
    metadata = {"Country", "chips_status", "coverage", "indicators_present",
                "indicators_total", "pillars_present", "rank"}
    cols = ["chips"] + [c for c in rel_table.columns
                        if c not in metadata and c != "chips"]
    merged = rel_table[["Country"]].copy()
    r = rel_table.set_index("Country")
    a = abs_table.set_index("Country")
    for col in cols:
        merged[col] = [
            blend_value(r.loc[c, col] if c in r.index else None,
                        a.loc[c, col] if c in a.index else None)
            for c in merged["Country"]
        ]
    # Round the blended CHIPS score to 2 dp on the 0-100 scale, matching the
    # published spreadsheet's CHIPS / rank precision.
    if "chips" in merged:
        merged["chips"] = (merged["chips"] * 100).round(2) / 100
    # Relative-run coverage bookkeeping travels with the blend.
    for col in ["coverage", "indicators_present", "indicators_total", "pillars_present"]:
        merged[col] = merged["Country"].map(r[col])
    merged["chips_status"] = merged["chips"].notna().map(
        lambda ok: "present" if ok else "dropped")
    scored = merged["chips"].notna()
    merged["rank"] = np.nan
    merged.loc[scored, "rank"] = (
        (merged.loc[scored, "chips"] * 100).round(2) / 100
    ).rank(ascending=False, method="min").astype(int)
    return merged


def blended_country_scores(rel_res, abs_res) -> dict[str, float | None]:
    """Blended sub-pillar and pillar scores for one country, keyed by
    ``"PILLAR"`` and ``"PILLAR · SUB-PILLAR"`` (used for metrics and sliders)."""
    out: dict[str, float | None] = {}
    for pr_rel, pr_abs in zip(rel_res.pillars, abs_res.pillars):
        out[pr_rel.name] = blend_value(pr_rel.score, pr_abs.score)
        for sp_rel, sp_abs in zip(pr_rel.children, pr_abs.children):
            key = f"{pr_rel.name} · {sp_rel.name}"
            out[key] = blend_value(sp_rel.score, sp_abs.score)
    return out


def blended_chips_score(rel_res, abs_res) -> float | None:
    return blend_value(rel_res.chips.score, abs_res.chips.score)


def _by_id(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.set_index("id")


def blend_treemap_rows(
    rel_rows: pd.DataFrame,
    abs_rows: pd.DataFrame,
) -> pd.DataFrame:
    """Merge two ``tree_to_frame`` outputs (Relative + Absolute) for the drill-down.

    Returns one row per node.  Aggregate nodes (sub-pillar/pillar/CHIPS) carry
    the blended score; indicators/internal groups keep the Relative run's score
    and status.  Every row also gains ``score_rel`` and ``score_abs`` so the
    treemap hover can show both base datasets alongside the blend.
    """
    r = _by_id(rel_rows)
    a = _by_id(abs_rows)
    merged = r.reset_index()
    merged["score_rel"] = merged["id"].map(r["score"])
    merged["score_abs"] = merged["id"].map(a["score"])
    blend = merged["kind"].isin(BLEND_KINDS)
    merged.loc[blend, "score"] = merged.loc[blend].apply(
        lambda row: blend_value(row["score_rel"], row["score_abs"]), axis=1)
    merged.loc[blend, "status"] = merged.loc[blend, "score"].notna().map(
        lambda ok: "present" if ok else "dropped")
    merged.loc[blend, "reason"] = ""
    return merged
