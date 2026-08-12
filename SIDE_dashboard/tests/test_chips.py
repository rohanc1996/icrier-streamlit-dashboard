"""Unit and integration tests for the CHIPS engine.

Run from the SIDE_dashboard directory (no pytest needed):

    ../.venv/bin/python -m tests.test_chips

The rule-level tests are self-contained.  The integration tests load the real
dataset through ``core.loader`` and are skipped automatically if the data file
is unavailable.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from core import chips, chips_hierarchy as H

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ok  {name}")
    else:
        FAILURES.append(name)
        print(f"FAIL  {name} {detail}")


# ---------------------------------------------------------------------------
# Rule-level tests
# ---------------------------------------------------------------------------

def test_group_rules() -> None:
    print("\nGroup-level missingness rules")
    # 2-of-2 rule: 1 of 2 present -> drop
    score, reason, eff = chips._group_aggregate([True, False], [0.9, None], [0.5, 0.5])
    check("2-of-2: drops the pair", score is None and "2-of-2" in (reason or ""))
    # 2-of-2: both present -> equal 0.5/0.5
    score, reason, eff = chips._group_aggregate([True, True], [0.8, 0.6], [0.5, 0.5])
    check("2-of-2: both present keeps score", score is not None and abs(score - 0.7) < 1e-9)
    check("2-of-2: weights stay 0.5/0.5", np.allclose(eff, [0.5, 0.5]))
    # >50% missing: 4 components, 1 present -> drop
    score, reason, eff = chips._group_aggregate(
        [True, False, False, False], [0.9, None, None, None], [0.25] * 4)
    check(">50%: 1 of 4 drops", score is None and ">50%" in (reason or ""))
    # exactly half missing: 4 components, 2 present -> keep, reweight to 0.5 each
    score, reason, eff = chips._group_aggregate(
        [True, False, True, False], [0.8, None, 0.4, None], [0.25] * 4)
    check("exactly half keeps with reweight", score is not None and abs(score - 0.6) < 1e-9)
    check("exactly half effective 0.5", np.allclose(eff, [0.5, 0.0, 0.5, 0.0]))
    # reweight by nominal weights: [0.2, 0.3, 0.5] with the last missing
    score, reason, eff = chips._group_aggregate([True, True, False], [0.0, 1.0, None], [0.2, 0.3, 0.5])
    check("reweight uses nominal weights", abs(score - 0.6) < 1e-9)
    check("reweight effective = 0.4/0.6", np.allclose(eff[:2], [0.4, 0.6]))
    # all missing
    score, reason, eff = chips._group_aggregate([False, False], [None, None], [0.5, 0.5])
    check("all missing drops", score is None and "no components" in (reason or ""))
    # a present component with score exactly 0 is not "missing"
    score, reason, eff = chips._group_aggregate([True, True], [0.0, 1.0], [0.5, 0.5])
    check("zero score is present, not missing", score is not None and abs(score - 0.5) < 1e-9)


# ---------------------------------------------------------------------------
# Synthetic end-to-end tests
# ---------------------------------------------------------------------------

class _FakeData:
    def __init__(self, frame: pd.DataFrame, higher_is_better: dict | None = None):
        self.numeric_df = frame
        self.country_list = frame["Country"].tolist()
        self.higher_is_better = higher_is_better or {}


def _fake(columns: list[str], countries: list[str] | None = None) -> _FakeData:
    """A small synthetic dataset where higher values are always better."""
    countries = countries or ["A", "B", "C", "D"]
    rng = pd.DataFrame({"Country": countries})
    for i, col in enumerate(columns, start=1):
        rng[col] = [float(i * (j + 1)) for j in range(len(countries))]
    return _FakeData(rng)


def _ai_pillar() -> H.Pillar:
    return H.Pillar("INNOVATE", 1.0, [
        H.SubPillar("AI", 1.0, groups=[
            H.Group("Research", 1 / 2, [
                H.Leaf("P1A1", "P1A1", 0.5),
                H.Leaf("P1A2", "P1A2", 0.5),
            ]),
            H.Group("Investment & commercial", 1 / 2, [
                H.Leaf("P1B", "P1B", 1 / 3),
                H.Leaf("P1C1", "P1C1", 1 / 3),
                H.Leaf("P1C2", "P1C2", 1 / 3),
            ]),
        ]),
    ])


def _set_nan(data: _FakeData, country: str, column: str) -> None:
    data.numeric_df.loc[data.numeric_df["Country"] == country, column] = np.nan


def test_ai_subpillar() -> None:
    print("\nINNOVATE AI sub-pillar (internal groups)")
    data = _fake(["P1A1", "P1A2", "P1B", "P1C1", "P1C2"])
    pillars = [_ai_pillar()]

    res = chips.aggregate_country(data, "D", pillars=pillars)
    sp = res.pillars[0].children[0]
    check("all data present", sp.status == "present")
    check("all data score near top", sp.score is not None and sp.score > 0.9)
    check("2 internal groups present", sum(1 for g in sp.children if g.status == "present") == 2)

    # One member of the research pair missing -> the pair drops (2-of-2 rule)
    # and, with only 2 groups in the sub-pillar, the sub-pillar drops too.
    data2 = _fake(["P1A1", "P1A2", "P1B", "P1C1", "P1C2"])
    _set_nan(data2, "D", "P1A2")
    res = chips.aggregate_country(data2, "D", pillars=pillars)
    sp = res.pillars[0].children[0]
    check("research pair loses one member -> sub-pillar drops", sp.status == "dropped")
    check("dropped sub-pillar records a reason", sp.reason is not None)

    # One member of the 3-indicator group missing -> reweight inside the group
    # to 0.5/0.5; the sub-pillar survives with both groups at their nominal 1/2.
    data3 = _fake(["P1A1", "P1A2", "P1B", "P1C1", "P1C2"])
    _set_nan(data3, "D", "P1B")
    res = chips.aggregate_country(data3, "D", pillars=pillars)
    sp = res.pillars[0].children[0]
    check("1 of 3 group missing -> sub-pillar survives", sp.status == "present")
    check("group reweighted to 0.5/0.5 inside",
          np.allclose([g.effective_weight for g in sp.children[1].children], [0.0, 0.5, 0.5]))
    check("both groups keep their nominal 1/2",
          np.allclose([g.effective_weight for g in sp.children], [0.5, 0.5]))

    # Two members of the 3-indicator group missing -> the >50% rule drops the
    # group, and the sub-pillar drops with it (1 of 2 groups left).
    data4 = _fake(["P1A1", "P1A2", "P1B", "P1C1", "P1C2"])
    _set_nan(data4, "D", "P1B")
    _set_nan(data4, "D", "P1C1")
    res = chips.aggregate_country(data4, "D", pillars=pillars)
    sp = res.pillars[0].children[0]
    check("2 of 3 group missing -> sub-pillar drops", sp.status == "dropped")


def test_drop_propagation() -> None:
    print("\nDrop propagation up the hierarchy")
    # A 2-sub-pillar pillar: losing one sub-pillar drops the whole pillar.
    pillar = H.Pillar("PROTECT", 1.0, [
        H.SubPillar("Prep", 0.5, leaves=[H.Leaf("S1", "S1", 1.0)]),
        H.SubPillar("Risk", 0.5, leaves=[H.Leaf("S2", "S2", 1.0)]),
    ])
    data = _fake(["S1", "S2"])
    _set_nan(data, "D", "S2")
    res = chips.aggregate_country(data, "D", pillars=[pillar])
    check("2-of-2 pillar: 1 sub-pillar lost -> pillar drops", res.pillars[0].status == "dropped")

    # CHIPS: needs at least 3 of 5 pillars.
    def _five_pillar() -> list[H.Pillar]:
        return [
            H.Pillar(f"P{i}", 0.2, [H.SubPillar(f"SP{i}", 1.0, leaves=[H.Leaf(f"C{i}", f"C{i}", 1.0)])])
            for i in range(1, 6)
        ]

    data = _fake(["C1", "C2", "C3", "C4", "C5"])
    res = chips.aggregate_country(data, "D", pillars=_five_pillar())
    check("5 pillars present -> CHIPS present", res.chips.status == "present")

    data2 = _fake(["C1", "C2", "C3", "C4", "C5"])
    for col in ["C1", "C2"]:
        _set_nan(data2, "D", col)
    res = chips.aggregate_country(data2, "D", pillars=_five_pillar())
    check("3 of 5 pillars -> CHIPS present (reweighted)", res.chips.status == "present")
    eff = [pr.effective_weight for pr in res.pillars]
    check("3 pillars reweighted to 1/3", np.allclose(eff[:2], [0, 0]) and np.allclose(eff[2:], [1 / 3] * 3))

    data3 = _fake(["C1", "C2", "C3", "C4", "C5"])
    for col in ["C1", "C2", "C3"]:
        _set_nan(data3, "D", col)
    res = chips.aggregate_country(data3, "D", pillars=_five_pillar())
    check("2 of 5 pillars -> no CHIPS score",
          res.chips.status == "dropped" and res.chips.score is None)


def test_overrides_and_coverage() -> None:
    print("\nWhat-if overrides and coverage")
    pillars = [
        H.Pillar("P1", 0.2, [H.SubPillar("SP1", 1.0, leaves=[H.Leaf("C1", "C1", 1.0)])]),
        H.Pillar("P2", 0.2, [H.SubPillar("SP2", 1.0, leaves=[H.Leaf("C2", "C2", 1.0)])]),
        H.Pillar("P3", 0.2, [H.SubPillar("SP3", 1.0, leaves=[H.Leaf("C3", "C3", 1.0)])]),
        H.Pillar("P4", 0.2, [H.SubPillar("SP4", 1.0, leaves=[H.Leaf("C4", "C4", 1.0)])]),
        H.Pillar("P5", 0.2, [H.SubPillar("SP5", 1.0, leaves=[H.Leaf("C5", "C5", 1.0)])]),
    ]

    data2 = _fake(["C1", "C2", "C3", "C4", "C5"])
    _set_nan(data2, "D", "C1")
    res = chips.aggregate_country(data2, "D", pillars=pillars)
    check("missing C1 -> 4 of 5 pillars", res.coverage["pillars_present"] == 4)
    check("coverage = 80%", abs(res.coverage["coverage"] - 0.8) < 1e-9)
    check("4 indicators of 5 present", res.coverage["indicators_present"] == 4)

    res2 = chips.aggregate_country(data2, "D", pillars=pillars, override={"P1 · SP1": ("present", 0.5)})
    check("what-if present -> all 5 pillars", res2.coverage["pillars_present"] == 5)
    check("what-if present produces a score", res2.chips.status == "present")
    res3 = chips.aggregate_country(data2, "D", pillars=pillars, override={"P2 · SP2": ("absent", None)})
    check("what-if absent drops a pillar", res3.coverage["pillars_present"] == 3)

    res4 = chips.aggregate_country(data2, "D", pillars=pillars, fill_missing=0.5)
    check("fill_missing rescues everything",
          res4.chips.status == "present" and res4.coverage["pillars_present"] == 5)


# ---------------------------------------------------------------------------
# Hierarchy resolution
# ---------------------------------------------------------------------------

def test_hierarchy_resolution() -> None:
    print("\nHierarchy spec sanity")
    all_cols = set()
    for spec in H.HIERARCHY:
        for sp in spec["sub_pillars"]:
            groups = sp.get("internal_groups") or [{"indicators": sp["indicators"]}]
            for g in groups:
                for name, _w in g["indicators"]:
                    all_cols.add(H.COLUMN_ALIASES.get(name, name))
    pillars, unresolved = H.resolve_hierarchy(all_cols)
    check("all indicators resolve against their own aliases", not unresolved)
    check("5 pillars", len(pillars) == 5)
    check("pillar weights sum to 1", abs(sum(p.weight for p in pillars) - 1.0) < 1e-9)
    for p in pillars:
        check(f"{p.name} sub-pillar weights sum to 1",
              abs(sum(sp.weight for sp in p.sub_pillars) - 1.0) < 1e-9)
    leaves = H.all_leaves(pillars)
    check("58 leaf indicators", len(leaves) == 58)
    check("global leaf weights sum to 1",
          abs(sum(chips.leaf_global_weights(pillars).values()) - 1.0) < 1e-9)

    _bad, bad = H.resolve_hierarchy(["Nope", "Nope 2"])
    check("unresolvable names reported", len(bad) > 0)

    import copy
    dup = copy.deepcopy(H.HIERARCHY)
    dup[0]["sub_pillars"][0]["indicators"] = dup[0]["sub_pillars"][0]["indicators"] + [
        dup[0]["sub_pillars"][0]["indicators"][0]
    ]
    dup_cols = set()
    for spec in dup:
        for sp in spec["sub_pillars"]:
            groups = sp.get("internal_groups") or [{"indicators": sp["indicators"]}]
            for g in groups:
                for n, _w in g["indicators"]:
                    dup_cols.add(H.COLUMN_ALIASES.get(n, n))
    raised = False
    try:
        H.resolve_hierarchy(dup_cols, spec=dup)
    except ValueError:
        raised = True
    check("duplicate indicator names rejected", raised)


# ---------------------------------------------------------------------------
# Real-data integration
# ---------------------------------------------------------------------------

def test_real_data() -> None:
    print("\nReal dataset integration")
    try:
        from core.loader import load_app_data
        data = load_app_data()
    except FileNotFoundError:
        print("  skip (data file not found)")
        return

    pillars, unresolved = H.resolve_hierarchy(data.numeric_df.columns)
    check("every spec indicator maps to a real column", not unresolved)

    table = chips.chips_table(data, pillars=pillars)
    check("one row per country", len(table) == len(data.country_list))
    scored = table.dropna(subset=["chips"])
    check("chips scores in [0, 1]", bool(((scored["chips"] >= 0) & (scored["chips"] <= 1)).all()))
    check("ranks are 1..N", scored["rank"].min() == 1 and scored["rank"].max() == len(scored))
    check("coverage in [0, 1]", bool(((table["coverage"] >= 0) & (table["coverage"] <= 1)).all()))
    check("all scored countries keep 3-5 pillars",
          bool(scored["pillars_present"].between(3, 5).all()))
    for pillar_name in ["CONNECT", "HARNESS", "INNOVATE", "PROTECT", "SUSTAINABILITY"]:
        vals = table[pillar_name].dropna()
        check(f"{pillar_name} scores in [0, 1]", bool(((vals >= 0) & (vals <= 1)).all()))

    res = chips.aggregate_country(data, "India", pillars=pillars)
    check("India aggregates", res.chips.status == "present" and res.chips.score is not None)

    frames = chips.tree_to_frame(res.chips, chips.leaf_global_weights(pillars))
    check("treemap frame has 82 nodes", len(frames) == 82)
    check("treemap root weight is 1.0",
          abs(frames.loc[frames.kind == "chips", "weight"].iloc[0] - 1.0) < 1e-9)



# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all() -> int:
    test_group_rules()
    test_ai_subpillar()
    test_drop_propagation()
    test_overrides_and_coverage()
    test_hierarchy_resolution()
    test_real_data()
    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
        return 1
    print("ALL TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(run_all())



