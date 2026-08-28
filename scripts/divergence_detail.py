"""Per-country divergence detail: published report vs dashboard.

For every country whose CHIPS score differs by more than 0.1 points, lists the
unit where the divergence appears (an indicator, or a sub-pillar when the
indicators reconcile but the aggregation differs), together with the published
vs dashboard scores at the indicator, sub-pillar, pillar and CHIPS levels.

Writes: min-max mismatch investigation/divergences_detail.csv
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "SIDE_dashboard"))

from core import chips, scaling  # noqa: E402
from core import chips_hierarchy as H  # noqa: E402
from core.loader import load_app_data  # noqa: E402

PUB_FILE = ROOT / "SIDE 2026 - Rohan - AI augmented Absolute Index 2026.csv"
OUT_FILE = ROOT / "min-max mismatch investigation" / "divergences_detail.csv"

CHIPS_ROW = 94
RANK_ROW = 96
IND_ROWS = range(0, 58)
SUB_ROWS = range(61, 77)
PIL_ROWS = range(79, 84)

NAME_MAP = {
    "United States of America": "USA",
    "United Arab Emirates": "UAE",
    "United Kingdom": "UK",
}
PIL_MAP = {"CONNECT": "C", "HARNESS": "H", "INNOVATE": "I", "PROTECT": "P", "SUSTAINABILITY": "S"}
# Dashboard sub-pillar name -> the name used in the published sub-pillar block.
SUBPILLAR_ALIASES = {
    "Apps and platform": "App and platform economy",
    "Fintech": "Fintech (change name)",
    "Sustainability": "",
}

# Thresholds: a country qualifies when its CHIPS score differs by more than this;
# an indicator is called out when its value differs by more than this, or when it
# is present on only one side inside a materially-diverging sub-pillar; a
# sub-pillar is called out when its score differs by more than this.
CHIPS_TOL = 0.1
SCORE_TOL = 0.5


def _tofloat(x: object) -> float:
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return np.nan


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def build_row_to_leaf(pub, pillars) -> dict[int, H.Leaf | None]:
    row_to_leaf: dict[int, H.Leaf | None] = {}
    for i in IND_ROWS:
        pname = str(pub.loc[i, "Indicator"]).strip()
        pn = _norm(pname)
        leaf = None
        for l in H.all_leaves(pillars):
            if _norm(l.name) == pn or _norm(l.column or "") == pn:
                leaf = l
                break
        if leaf is None:
            for k, v in H.COLUMN_ALIASES.items():
                if _norm(k) == pn or _norm(v) == pn:
                    leaf = next((l for l in H.all_leaves(pillars) if l.name == k), None)
                    break
        row_to_leaf[i] = leaf
    return row_to_leaf


def parent_sp(pillars, leaf_name: str) -> tuple[str, str] | None:
    for p in pillars:
        for sp in p.sub_pillars:
            groups = [g.leaves for g in sp.groups] if sp.groups else [sp.leaves]
            for group_leaves in groups:
                if any(lf.name == leaf_name for lf in group_leaves):
                    return p.name, sp.name
    return None


def main() -> None:
    pub = pd.read_csv(PUB_FILE, dtype=str, keep_default_na=False)
    countries = list(pub.columns[7:78])

    data = load_app_data()
    pillars, _ = H.resolve_hierarchy(data.numeric_df.columns)
    score_df = chips.score_matrix(data, pillars, method=scaling.METHOD_FULL)
    table = chips.chips_table(data, pillars=pillars, method=scaling.METHOD_FULL)
    rank_map = dict(zip(table["Country"], table["rank"]))
    row_to_leaf = build_row_to_leaf(pub, pillars)

    def db(n: str) -> str:
        return NAME_MAP.get(n, n)

    # Published blocks.
    pub_sub: dict[tuple[str, str], dict[str, float]] = {}
    pil = None
    for i in SUB_ROWS:
        pcell = str(pub.loc[i, "Pillar"]).strip()
        if pcell:
            pil = pcell
        pub_sub[(pil, str(pub.loc[i, "Sub -Pillar"]).strip())] = {
            c: _tofloat(pub.loc[i, db(c)]) for c in countries
        }
    pub_pil: dict[str, dict[str, float]] = {
        str(pub.loc[i, "Pillar"]).strip(): {c: _tofloat(pub.loc[i, db(c)]) for c in countries}
        for i in PIL_ROWS
    }
    pub_chips = {c: _tofloat(pub.loc[CHIPS_ROW, db(c)]) for c in countries}
    pub_rank = {c: _tofloat(pub.loc[RANK_ROW, db(c)]) for c in countries}

    def published_sub(pillar: str, sp_name: str, c: str) -> float:
        published_name = SUBPILLAR_ALIASES.get(sp_name, sp_name)
        return pub_sub.get((PIL_MAP[pillar], published_name), {}).get(db(c), np.nan)

    def published_pil(pillar: str, c: str) -> float:
        return pub_pil.get(PIL_MAP[pillar], {}).get(db(c), np.nan)

    def make_row(c, level, indicator, unit_pub, unit_dash, sp_key,
                 dash_sub, dash_pil, dash_chips) -> dict:
        pill = sp_key[0] if sp_key else ""
        sp_name = sp_key[1] if sp_key else ""
        return {
            "Country": c,
            "Divergence_level": level,
            "Indicator": indicator,
            "Published_Indicator": round(unit_pub, 2) if level == "indicator" and not np.isnan(unit_pub) else None,
            "Dashboard_Indicator": round(unit_dash, 2) if level == "indicator" and not np.isnan(unit_dash) else None,
            "Subpillar": f"{pill} · {sp_name}" if sp_name else pill,
            "Published_Subpillar": round(published_sub(pill, sp_name, c), 2) if sp_name else None,
            "Dashboard_Subpillar": round(dash_sub.get((pill, sp_name), np.nan), 2) if sp_name else None,
            "Pillar": pill,
            "Published_Pillar": round(published_pil(pill, c), 2) if pill else None,
            "Dashboard_Pillar": round(dash_pil.get(pill, np.nan), 2) if pill else None,
            "Published_CHIPS": round(pub_chips[c], 2),
            "Dashboard_CHIPS": round(dash_chips, 2),
            "Published_Rank": pub_rank.get(c, np.nan),
            "Dashboard_Rank": rank_map.get(c, np.nan),
        }

    rows: list[dict] = []
    for c in data.country_list:
        res = chips.aggregate_country(
            data, c, pillars=pillars, score_df=score_df, method=scaling.METHOD_FULL
        )
        dash_chips = res.chips.score * 100 if res.chips.score is not None else np.nan
        pub_c = pub_chips.get(c, np.nan)
        if np.isnan(pub_c) or np.isnan(dash_chips):
            continue
        if abs(pub_c - dash_chips) <= CHIPS_TOL:
            continue

        # Dashboard trees.
        dash_pil: dict[str, float] = {}
        dash_sub: dict[tuple[str, str], float] = {}
        dash_ind: dict[str, float] = {}   # rounded (displayed) indicator scores
        raw_ind: dict[str, float] = {}    # unrounded, for divergence detection
        row = score_df.loc[score_df["Country"] == c].iloc[0]
        for pr in res.pillars:
            dash_pil[pr.name] = pr.score * 100 if pr.score is not None else np.nan
            for sp in pr.children:
                dash_sub[(pr.name, sp.name)] = sp.score * 100 if sp.score is not None else np.nan
                for g in sp.children:
                    if g.kind == "internal_group":
                        for lf in g.children:
                            dash_ind[lf.name] = lf.score * 100 if lf.score is not None else np.nan
                            raw_ind[lf.name] = row.get(lf.name, np.nan) * 100
                    elif g.kind == "indicator":
                        dash_ind[g.name] = g.score * 100 if g.score is not None else np.nan
                        raw_ind[g.name] = row.get(g.name, np.nan) * 100

        # Material sub-pillar score differences.
        sub_scores: dict[tuple[str, str], tuple[float, float]] = {}
        for pr in res.pillars:
            for sp in pr.children:
                key = (pr.name, sp.name)
                pv = published_sub(pr.name, sp.name, c)
                dv = dash_sub.get(key, np.nan)
                if not np.isnan(pv) and not np.isnan(dv):
                    sub_scores[key] = (pv, dv)

        # Diverging indicators: different value on both sides, or present on only
        # one side inside a sub-pillar that itself diverges materially.
        ind_rows: list[tuple[str, float, float, tuple[str, str] | None]] = []
        for i in IND_ROWS:
            leaf = row_to_leaf.get(i)
            if leaf is None:
                continue
            pv = _tofloat(pub.loc[i, db(c)])
            dv_raw = raw_ind.get(leaf.name, np.nan)
            dv = dash_ind.get(leaf.name, np.nan)
            sp_key = parent_sp(pillars, leaf.name)
            both = not np.isnan(pv) and not np.isnan(dv_raw)
            if both and abs(pv - dv_raw) > SCORE_TOL:
                ind_rows.append((leaf.name, pv, dv, sp_key))
            elif np.isnan(pv) != np.isnan(dv_raw):
                # Present on only one side: report only when it sits inside a
                # sub-pillar that itself diverges materially.
                sub = sub_scores.get(sp_key, (np.nan, np.nan))
                if not np.isnan(sub[0]) and not np.isnan(sub[1]) and abs(sub[0] - sub[1]) > SCORE_TOL:
                    ind_rows.append((leaf.name, pv, dv, sp_key))

        explained = {sp_key for _n, _p, _d, sp_key in ind_rows}
        for name, pv, dv, sp_key in ind_rows:
            rows.append(make_row(c, "indicator", name, pv, dv, sp_key,
                                 dash_sub, dash_pil, dash_chips))

        # Sub-pillar divergences not explained by an indicator row.
        for key, (pv, dv) in sub_scores.items():
            if abs(pv - dv) <= SCORE_TOL or key in explained:
                continue
            rows.append(make_row(c, "sub-pillar", "", pv, dv, key,
                                 dash_sub, dash_pil, dash_chips))

    df = pd.DataFrame(rows).sort_values(["Country", "Divergence_level"], ignore_index=True)
    df.to_csv(OUT_FILE, index=False)
    print(f"Wrote {OUT_FILE} ({len(df)} rows, {df['Country'].nunique()} countries)")


if __name__ == "__main__":
    main()
