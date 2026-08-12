"""CHIPS composite index — aggregation engine with missing-data transparency.

Scoring
-------
Every indicator is rescaled to 0-1 (capped 5-95 min-max, inverted where lower
is better) exactly as the rest of the dashboard does — the same maths behind
``rankings.scaled_scores`` and ``scaling.transform_series``.

Missing-data rules (from the CHIPS spec sheet)
----------------------------------------------
1. Components in a group are weighted equally unless a weight is given.
2. If a component is missing, redistribute its weight across the remaining
   present components in the same group.
3. If more than half of a group's components are missing, drop the group.
4. If a group has exactly 2 components and 1 is missing, drop the group.
5. The same logic applies at every level, so a dropped component counts as
   unavailable one level up (indicator -> sub-pillar -> pillar -> CHIPS).
6. CHIPS itself needs at least 3 of its 5 pillars (present/total > 0.5).

The INNOVATE -> AI sub-pillar nests one extra level: its two internal groups —
the research pair (AI Innovation - Research + AI R&D score) and the remaining
three AI indicators — are aggregated first with the same rules.  The research
pair follows the 2-of-2 rule (losing one member drops the pair as a unit), and
because the sub-pillar itself has only 2 groups it drops if either group is
lost (rule 4).  Inside the 3-indicator group the generic ">50% missing" rule
reproduces exactly the spec-sheet's "1 of 3 lost -> reweight, 2 of 3 lost -> drop".

Every node of the result tree records its status (present / missing / dropped),
the rule that dropped it, its nominal weight, the weight actually applied after
reweighting, and (for indicators) its underlying 0-1 score.  That tree is what
the explorer page turns into treemaps, weight-inflation bars and what-if
scenarios, so the effect of missing data is fully transparent.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import chips_hierarchy as H
from . import scaling


@dataclass
class NodeResult:
    """One node of the aggregation tree."""

    name: str
    kind: str  # "chips" | "pillar" | "sub_pillar" | "internal_group" | "indicator"
    status: str  # "present" | "missing" | "dropped"
    reason: str | None = None  # why it is missing/dropped
    score: float | None = None  # 0-1 aggregated score when present
    nominal_weight: float = 0.0  # weight within its parent (as specified)
    effective_weight: float = 0.0  # weight actually applied after reweighting
    children: list = field(default_factory=list)


@dataclass
class CountryResult:
    country: str
    chips: NodeResult
    coverage: dict
    pillars: list[NodeResult]


# ---------------------------------------------------------------------------
# Group-level rules
# ---------------------------------------------------------------------------

def _group_aggregate(
    flags: list[bool], scores: list[float], weights: list[float]
) -> tuple[float | None, str | None, list[float]]:
    """Apply the missingness rules to one group of children.

    Returns ``(score, reason, effective_weights)``.  ``score`` is None when the
    group is dropped; ``effective_weights`` is parallel to the children.
    """
    total = len(flags)
    present_idx = [i for i, f in enumerate(flags) if f]
    n = len(present_idx)
    if n == 0:
        return None, "no components have data", [0.0] * total
    if total == 2 and n == 1:
        return None, "2-of-2 rule: only 1 of 2 components has data", [0.0] * total
    if 2 * n < total:
        return None, ">50% of components are missing", [0.0] * total
    wsum = sum(weights[i] for i in present_idx)
    if wsum <= 0:
        return None, "no positive weight among the present components", [0.0] * total
    effective = [0.0] * total
    for i in present_idx:
        effective[i] = weights[i] / wsum
    score = sum(scores[i] * effective[i] for i in present_idx)
    return score, None, effective


def _aggregate_children(
    name: str, kind: str, children: list[NodeResult], nominal_weight: float
) -> NodeResult:
    """Aggregate a set of already-computed children into a parent node."""
    flags = [c.status == "present" for c in children]
    scores = [c.score for c in children]
    weights = [c.nominal_weight for c in children]
    score, reason, effective = _group_aggregate(flags, scores, weights)
    for c, e in zip(children, effective):
        c.effective_weight = e
    return NodeResult(
        name=name,
        kind=kind,
        status="present" if score is not None else "dropped",
        reason=reason,
        score=score,
        nominal_weight=nominal_weight,
        effective_weight=0.0,  # filled in by *this* node's parent
        children=children,
    )


def _indicator_results(row: pd.Series, leaves: list[H.Leaf]) -> list[NodeResult]:
    """Indicator nodes for one country; presence comes from the score matrix."""
    out = []
    for leaf in leaves:
        if leaf.column is None:
            out.append(NodeResult(
                name=leaf.name, kind="indicator", status="missing",
                reason="no dataset column for this indicator", score=None,
                nominal_weight=leaf.weight, effective_weight=0.0,
            ))
            continue
        value = row.get(leaf.name)
        present = bool(pd.notna(value))
        out.append(NodeResult(
            name=leaf.name, kind="indicator",
            status="present" if present else "missing",
            reason=None if present else "no data",
            score=None if not present else float(value),
            nominal_weight=leaf.weight, effective_weight=0.0,
        ))
    return out


def _build_subpillar_result(row: pd.Series, sp: H.SubPillar) -> NodeResult:
    if sp.groups:
        group_results = []
        for g in sp.groups:
            leaves = _indicator_results(row, g.leaves)
            group_results.append(_aggregate_children(g.name, "internal_group", leaves, g.weight))
        return _aggregate_children(sp.name, "sub_pillar", group_results, sp.weight)
    leaves = _indicator_results(row, sp.leaves)
    return _aggregate_children(sp.name, "sub_pillar", leaves, sp.weight)


def _build_pillar_result(
    row: pd.Series,
    pillar: H.Pillar,
    override: dict | None = None,
    fill_missing: float | None = None,
) -> NodeResult:
    """Build a pillar result, optionally with what-if overrides applied.

    ``override`` maps "PILLAR · SUB-PILLAR" to ``("present", score)`` or
    ``("absent", None)``.  ``fill_missing`` replaces *every* non-present
    sub-pillar with the given score (used by the fill-missing simulation).
    """
    results = []
    for sp in pillar.sub_pillars:
        sp_result = _build_subpillar_result(row, sp)
        key = f"{pillar.name} · {sp.name}"
        if override and key in override:
            action, value = override[key]
            if action == "present":
                sp_result.status = "present"
                sp_result.score = value
                sp_result.reason = "simulated present (what-if)"
            else:
                sp_result.status = "dropped"
                sp_result.score = None
                sp_result.reason = "simulated absent (what-if)"
        elif fill_missing is not None and sp_result.status != "present":
            sp_result.status = "present"
            sp_result.score = fill_missing
            sp_result.reason = f"simulated: missing data filled at {fill_missing:.2f}"
        results.append(sp_result)
    return _aggregate_children(pillar.name, "pillar", results, pillar.weight)


# ---------------------------------------------------------------------------
# Country-level aggregation
# ---------------------------------------------------------------------------

def score_matrix(data, pillars: list[H.Pillar], lower: float = 0.05, upper: float = 0.95) -> pd.DataFrame:
    """0-1 "goodness" score for every leaf, all countries.

    Columns are keyed by the indicator *name* and aligned to
    ``data.numeric_df`` rows (the Country column is first).  Missing raw values
    stay NaN so presence is readable straight off this frame.
    """
    base = data.numeric_df[["Country"]].copy()
    out = {}
    for leaf in H.all_leaves(pillars):
        if leaf.column is None:
            out[leaf.name] = np.nan
        else:
            raw = data.numeric_df[leaf.column]
            score = scaling.transform_series(raw, scaling.METHOD_CAPPED, lower, upper)
            if not data.higher_is_better.get(leaf.column, True):
                score = 1.0 - score
            # Assign the Series, not .values: transform_series drops NaN rows, so
            # pandas re-aligns by index and NaN-fills the missing countries.
            out[leaf.name] = score
    frame = pd.DataFrame(out, index=base.index)
    frame.insert(0, "Country", base["Country"].values)
    return frame


def _country_row(score_df: pd.DataFrame, country: str) -> pd.Series:
    match = score_df.loc[score_df["Country"] == country]
    if match.empty:
        raise ValueError(f"Country {country!r} not found in the score matrix")
    return match.iloc[0]


def leaf_global_weights(pillars: list[H.Pillar]) -> dict[str, float]:
    """Share of the whole CHIPS weight attached to each indicator."""
    out = {}
    for p in pillars:
        for sp in p.sub_pillars:
            if sp.groups:
                for g in sp.groups:
                    for leaf in g.leaves:
                        out[leaf.name] = p.weight * sp.weight * g.weight * leaf.weight
            else:
                for leaf in sp.leaves:
                    out[leaf.name] = p.weight * sp.weight * leaf.weight
    return out


def _coverage(row: pd.Series, pillars: list[H.Pillar]) -> dict:
    present_w = 0.0
    total_w = 0.0
    present_n = 0
    total_n = 0
    for name, w in leaf_global_weights(pillars).items():
        total_w += w
        total_n += 1
        if pd.notna(row.get(name)):
            present_w += w
            present_n += 1
    return {
        "coverage": present_w / total_w if total_w else 0.0,
        "indicators_present": present_n,
        "indicators_total": total_n,
    }


def aggregate_country(
    data,
    country: str,
    pillars: list[H.Pillar] | None = None,
    score_df: pd.DataFrame | None = None,
    override: dict | None = None,
    fill_missing: float | None = None,
) -> CountryResult:
    """Compute the full CHIPS result tree for one country.

    Pass ``pillars`` (from ``resolve_hierarchy``) and a precomputed
    ``score_df`` to avoid recomputing the scaling for every call.  ``override``
    and ``fill_missing`` implement the what-if simulations (see
    ``_build_pillar_result``).
    """
    if pillars is None:
        pillars, _ = H.resolve_hierarchy(data.numeric_df.columns)
    if score_df is None:
        score_df = score_matrix(data, pillars)
    row = _country_row(score_df, country)
    pillar_results = [_build_pillar_result(row, p, override, fill_missing) for p in pillars]
    chips_node = _aggregate_children("CHIPS composite", "chips", pillar_results, 1.0)
    coverage = _coverage(row, pillars)
    coverage["pillars_present"] = sum(1 for pr in pillar_results if pr.status == "present")
    return CountryResult(country=country, chips=chips_node, coverage=coverage, pillars=pillar_results)


# ---------------------------------------------------------------------------
# Cross-country tables
# ---------------------------------------------------------------------------

def chips_table(
    data,
    pillars: list[H.Pillar] | None = None,
    override: dict | None = None,
    fill_missing: float | None = None,
) -> pd.DataFrame:
    """One row per country: CHIPS score, rank, pillar scores and coverage.

    Countries that score (at least 3 pillars survived) get a rank; the others
    keep a NaN score/rank so the page can call them out as data-insufficient.
    """
    if pillars is None:
        pillars, _ = H.resolve_hierarchy(data.numeric_df.columns)
    score_df = score_matrix(data, pillars)
    rows = []
    for country in data.country_list:
        res = aggregate_country(
            data, country, pillars=pillars, score_df=score_df,
            override=override, fill_missing=fill_missing,
        )
        row = {
            "Country": country,
            "chips": res.chips.score,
            "chips_status": "present" if res.chips.status == "present" else "dropped",
            "coverage": res.coverage["coverage"],
            "indicators_present": res.coverage["indicators_present"],
            "indicators_total": res.coverage["indicators_total"],
            "pillars_present": res.coverage["pillars_present"],
        }
        for pr in res.pillars:
            row[pr.name] = pr.score
        rows.append(row)
    df = pd.DataFrame(rows)
    scored = df["chips"].notna()
    df["rank"] = np.nan
    df.loc[scored, "rank"] = df.loc[scored, "chips"].rank(ascending=False, method="min").astype(int)
    return df


def subpillar_status_matrix(
    data, pillars: list[H.Pillar] | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per-country sub-pillar status codes (0=present, 1=no data, 2=dropped)
    plus the reason for every non-present cell."""
    if pillars is None:
        pillars, _ = H.resolve_hierarchy(data.numeric_df.columns)
    score_df = score_matrix(data, pillars)
    labels = H.sub_pillar_keys(pillars)
    codes: dict[str, list[int]] = {}
    reasons: dict[str, list[str]] = {}
    for country in data.country_list:
        res = aggregate_country(data, country, pillars=pillars, score_df=score_df)
        row_codes, row_reasons = [], []
        for pr in res.pillars:
            for sp in pr.children:
                if sp.status == "present":
                    row_codes.append(0)
                    row_reasons.append("present")
                elif sp.reason and sp.reason.startswith("no components"):
                    row_codes.append(1)
                    row_reasons.append("no data at all")
                else:
                    row_codes.append(2)
                    row_reasons.append(sp.reason or "dropped")
        codes[country] = row_codes
        reasons[country] = row_reasons
    return (
        pd.DataFrame.from_dict(codes, orient="index", columns=labels),
        pd.DataFrame.from_dict(reasons, orient="index", columns=labels),
    )


def _subtree_weight(node: NodeResult, leaf_weights: dict[str, float]) -> float:
    if node.kind == "indicator":
        return leaf_weights.get(node.name, 0.0)
    return sum(_subtree_weight(c, leaf_weights) for c in node.children)


def tree_to_frame(chips_node: NodeResult, leaf_weights: dict[str, float]) -> pd.DataFrame:
    """Flatten the result tree into rows for the treemap.

    ``weight`` is the node's share of the whole CHIPS weight (branchvalues
    total, so parents equal the sum of their children).  ``pillar`` carries the
    top-level pillar name down the tree so the treemap can colour every level
    of a pillar with the same hue.
    """
    rows = []

    def walk(node: NodeResult, parent: str, path: list[str], pillar: str) -> None:
        node_id = "/".join(path)
        rows.append({
            "id": node_id,
            "parent": parent,
            "label": node.name,
            "kind": node.kind,
            "status": node.status,
            "reason": node.reason or "",
            "score": node.score,
            "weight": _subtree_weight(node, leaf_weights),
            "nominal": node.nominal_weight,
            "effective": node.effective_weight,
            "pillar": pillar,
        })
        for i, child in enumerate(node.children):
            walk(child, node_id, path + [str(i)], pillar or child.name)

    walk(chips_node, "", ["root"], "")
    return pd.DataFrame(rows)


def reweight_frame(res: CountryResult) -> pd.DataFrame:
    """Nominal vs effective sub-pillar weights for the weight-inflation bars."""
    rows = []
    for pr in res.pillars:
        for sp in pr.children:
            rows.append({
                "pillar": pr.name,
                "sub_pillar": sp.name,
                "label": f"{pr.name} · {sp.name}",
                "nominal": sp.nominal_weight,
                "effective": sp.effective_weight,
                "status": sp.status,
                "score": sp.score,
                "reason": sp.reason or "",
            })
    return pd.DataFrame(rows)

