"""Independently derive sub-pillar ranks from the exported JSON and compare.

This replays what the frontend has had to do in JavaScript: read only the
``scores[].subPillars`` values in ``chips.json``, round each score to 2 dp on
the 0-100 scale, then apply a competition ("min") rank with 1 = best, skipping
sub-pillars that are not scored. It then compares that derivation cell by cell
with the ``rank`` the exporter now publishes.

Three rounding conventions are replayed, because they only diverge at exact
two-decimal ties (a third decimal of 5):

* ``js_half_up``  — ``Math.round(score * 10000) / 100``, i.e. ``floor(x + .5)``
  on the binary product: what the site's JavaScript does today.
* ``decimal_half_even`` — the same value rounded as an exact decimal, ties to
  even (Python ``round`` / ``toFixed`` at the intended decimal).
* ``numpy_half_even`` — ``pandas.Series.round(2)`` on the 0-100 value, which is
  what ``core/rankings.py`` and the exporter use.

The first two agree with each other here; the third is the published rule. A
difference between them is a *tie convention* difference, not a ranking bug,
and is exactly the drift the frontend should stop re-deriving.

Usage::

    ./.venv/bin/python scripts/analysis/verify_subpillar_ranks.py
"""

from __future__ import annotations

import json
import math
import sys
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
EXPORT = REPO_ROOT / "data" / "derived" / "web" / "2026" / "chips.json"
OUT = REPO_ROOT / "deliverables" / "website-prototype" / "subpillar-rank-check.json"
METHODS = ("full_minmax", "z")
MODES = ("js_half_up", "decimal_half_even", "numpy_half_even")


def round_2dp(value: float, mode: str) -> float:
    """The score as its 2-dp value on the 0-100 scale (e.g. 0.525 -> 0.53).

    Ranking is scale-invariant, so these 0-100 values rank exactly like the
    0-1 values the exporter ranks; keeping one scale makes ties comparable.
    """
    if mode == "js_half_up":
        # JS Math.round is floor(x + 0.5) for positive x.
        return math.floor(value * 10000 + 0.5) / 100
    if mode == "decimal_half_even":
        return float(
            Decimal(value * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
        )
    if mode == "numpy_half_even":
        # Exactly what the exporter/rankings.py do: round on 0-100.
        return float(pd.Series([value * 100]).round(2).iloc[0])
    raise ValueError(mode)


def derive(scores: list[dict], mode: str) -> dict[tuple[str, str], float | None]:
    """Frontend-style derivation: { (iso3, key): rank or None }."""
    keys = list(scores[0]["subPillars"])
    out: dict[tuple[str, str], float | None] = {}
    for key in keys:
        column = {
            row["iso3"]: None if row["subPillars"][key]["score"] is None
            else round_2dp(row["subPillars"][key]["score"], mode)
            for row in scores
        }
        series = pd.Series(column, dtype="float64")
        ranks = series.rank(ascending=False, method="min")
        for iso3, rank in ranks.items():
            out[(iso3, key)] = None if pd.isna(rank) else float(rank)
    return out


def main() -> int:
    payload = json.loads(EXPORT.read_text(encoding="utf-8"))
    report: dict = {
        "export": str(EXPORT.relative_to(REPO_ROOT)),
        "conventions": {
            "js_half_up": "Math.round(score*10000)/100 (the site's JavaScript today)",
            "decimal_half_even": "exact-decimal round to 2 dp, ties to even",
            "numpy_half_even": "pandas Series.round(2) on the 0-100 value (the engine)",
        },
        "methods": {},
    }
    total_ranked = 0
    total_unranked = 0
    total_diffs_js = 0

    for method in METHODS:
        scores = payload["methods"][method]["scores"]
        cells = [(row["iso3"], key) for row in scores for key in row["subPillars"]]
        exported = {
            (row["iso3"], key): sub["rank"]
            for row in scores
            for key, sub in row["subPillars"].items()
        }
        present = {
            (row["iso3"], key): sub["status"] == "present"
            for row in scores
            for key, sub in row["subPillars"].items()
        }
        result: dict = {
            "cells": len(cells),
            "ranked": sum(1 for c in cells if present[c]),
            "unranked": sum(1 for c in cells if not present[c]),
            "nullness_disagreements": 0,
        }
        derived_by_mode = {mode: derive(scores, mode) for mode in MODES}
        score_by_cell = {
            (row["iso3"], key): sub["score"]
            for row in scores
            for key, sub in row["subPillars"].items()
        }

        def tie_cause(key: str, iso3: str) -> list[dict]:
            """The tie group the cell sits in, and who breaks it by rounding."""
            cell_engine = round_2dp(score_by_cell[(iso3, key)], "numpy_half_even")
            out = []
            for row in scores:
                sub = row["subPillars"][key]
                if sub["score"] is None:
                    continue
                engine = round_2dp(sub["score"], "numpy_half_even")
                if engine != cell_engine:
                    continue
                js = round_2dp(sub["score"], "js_half_up")
                if js != engine:
                    out.append({
                        "iso3": row["iso3"],
                        "score": sub["score"],
                        "score0to100": sub["score"] * 100,
                        "jsRounded": js,
                        "engineRounded": engine,
                    })
            return out

        for mode in MODES:
            derived = derived_by_mode[mode]
            diffs = []
            for cell in cells:
                if not present[cell]:
                    if exported[cell] is not None:
                        diffs.append({"cell": cell, "issue": "non-present but ranked"})
                    continue
                if derived[cell] != exported[cell]:
                    item = {
                        "iso3": cell[0],
                        "subPillar": cell[1],
                        "score": score_by_cell[cell],
                        "derivedRank": derived[cell],
                        "exportedRank": exported[cell],
                        "rankShift": exported[cell] - derived[cell],
                    }
                    if mode != "numpy_half_even":
                        item["tieCause"] = tie_cause(cell[1], cell[0])
                    diffs.append(item)
            result[mode] = {"disagreements": len(diffs), "examples": diffs}

        result["nullness_disagreements"] = sum(
            1 for cell in cells
            if (derived_by_mode["js_half_up"][cell] is None) != (exported[cell] is None)
        )
        report["methods"][method] = result
        total_ranked += result["ranked"]
        total_unranked += result["unranked"]
        total_diffs_js += result["js_half_up"]["disagreements"]
        print(f"{method}: {result['ranked']} ranked + {result['unranked']} unranked; "
              f"disagreements vs JS={result['js_half_up']['disagreements']}, "
              f"decimal={result['decimal_half_even']['disagreements']}, "
              f"numpy(engine)={result['numpy_half_even']['disagreements']}")

    report["totals"] = {
        "cells": total_ranked + total_unranked,
        "ranked": total_ranked,
        "unranked": total_unranked,
        "js_disagreements": total_diffs_js,
        "js_agreements": total_ranked - total_diffs_js,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO_ROOT)}")
    print(f"{total_ranked + total_unranked} cells "
          f"({total_ranked} ranked, {total_unranked} unranked): "
          f"JS derivation agrees on {total_ranked - total_diffs_js} of "
          f"{total_ranked} ranked cells, differs on {total_diffs_js}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
