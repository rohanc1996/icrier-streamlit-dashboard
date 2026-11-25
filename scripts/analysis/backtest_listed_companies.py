#!/usr/bin/env python3
"""Backtest gap-filling rules for WDI listed domestic companies (CM.MKT.LDOM.NO).

Question: when a country's series is stale, is it better to carry the last
observation forward, or to extrapolate the country's own trend?

Method
------
For every SIDE country and every year ``t`` with an observed value, predict
``t`` using only observations up to ``t - h`` (``h`` = 1..25). Two predictors:

* ``carry``  — the value at ``t - h``.
* ``trend``  — OLS on log(value) over the last ``k`` observations up to
  ``t - h``, projected to ``t``. Reported for ``k = 5`` and ``k = 8``.

Error is absolute percentage error against the actual value of ``t``. Series
that are zero or negative are skipped (log scale).

Output: ``deliverables/listed-companies-2025/backtest.md``.

Run:  python scripts/analysis/backtest_listed_companies.py
"""
from __future__ import annotations

import csv
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WDI = ROOT / "data" / "reference" / "WB listed company counts by year.csv"
ABSOLUTE = ROOT / "data" / "SIDE 2027 - Absolute.csv"
OUT = ROOT / "deliverables" / "listed-companies-2025" / "backtest.md"

# WDI spellings for SIDE country names (mirrors scripts/build_denominators.py).
ALIASES = {
    "Egypt": "Egypt, Arab Rep.",
    "Republic of Korea": "Korea, Rep.",
    "Slovakia": "Slovak Republic",
    "Türkiye": "Turkiye",
    "United States of America": "United States",
}

METADATA_ROWS = 4
HORIZONS = (1, 2, 3, 4, 7, 10, 15, 20, 23, 25)

# The six countries in the backtest's "group A": stale by 1-4 years in 2025.
GROUP_A = [
    ("Israel", 2024),
    ("Mexico", 2023),
    ("Russian Federation", 2023),
    ("United Kingdom", 2022),
    ("Costa Rica", 2022),
    ("Argentina", 2021),
]


def side_countries() -> list[str]:
    with ABSOLUTE.open(newline="", encoding="utf-8-sig") as handle:
        return [row["Country"].strip() for row in csv.DictReader(handle) if row["Country"].strip()]


def load_panel() -> dict[str, dict[int, float]]:
    with WDI.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    header = rows[METADATA_ROWS]
    years = [cell.strip() for cell in header[4:]]
    wanted = {ALIASES.get(c, c) for c in side_countries()}

    panel: dict[str, dict[int, float]] = {}
    for row in rows[METADATA_ROWS + 1 :]:
        if not row:
            continue
        name = row[0].strip()
        if name not in wanted:
            continue
        series: dict[int, float] = {}
        for year, cell in zip(years, row[4:]):
            text = cell.strip()
            if not year or not text:
                continue
            try:
                series[int(year)] = float(text)
            except ValueError:
                continue
        panel[name] = series
    return panel


def carry(series: dict[int, float], target: int, horizon: int) -> float | None:
    return series.get(target - horizon)


def trend(
    series: dict[int, float], target: int, horizon: int, window: int, min_points: int = 4
) -> float | None:
    points = [
        (year, series[year])
        for year in sorted(series)
        if year <= target - horizon and series[year] > 0
    ][-window:]
    if len(points) < min_points:
        return None
    xs = [year for year, _ in points]
    ys = [math.log(value) for _, value in points]
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    sxx = sum((x - mean_x) ** 2 for x in xs)
    if sxx == 0:
        return None
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / sxx
    intercept = mean_y - slope * mean_x
    return math.exp(intercept + slope * target)


def quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(q * len(ordered)))]


def main() -> int:
    panel = load_panel()
    assert len(panel) == 71, f"expected 71 SIDE countries, got {len(panel)}"

    errors: dict[tuple[str, int], list[float]] = {}
    bias: dict[int, list[float]] = {}
    failures: dict[str, list[tuple[int, int, float, float, float]]] = {}

    for name, series in panel.items():
        for horizon in HORIZONS:
            for target in sorted(series):
                actual = series[target]
                base = series.get(target - horizon)
                if actual <= 0 or not base or base <= 0:
                    continue
                predictions = {
                    "carry": base,
                    "trend5": trend(series, target, horizon, window=5),
                    "trend8": trend(series, target, horizon, window=8),
                }
                for label, predicted in predictions.items():
                    if not predicted or predicted <= 0:
                        continue
                    errors.setdefault((label, horizon), []).append(
                        abs(predicted - actual) / actual
                    )
                    if label == "carry":
                        bias.setdefault(horizon, []).append(math.log(base / actual))
                    if label.startswith("trend") and horizon >= 15:
                        failures.setdefault(name, []).append(
                            (target, horizon, base, predicted, actual)
                        )

    lines: list[str] = []
    lines.append("# Backtest: carry-forward vs trend for listed-company counts")
    lines.append("")
    lines.append(
        "Generated by `scripts/analysis/backtest_listed_companies.py`. Each row "
        "predicts year *t* from observations up to *t − h* only, over the 71 SIDE "
        "countries in `data/reference/WB listed company counts by year.csv`."
    )
    lines.append("")
    lines.append("## Median absolute percentage error by horizon")
    lines.append("")
    lines.append("| gap *h* | n | carry-forward | trend (5-pt) | trend (8-pt) | carry p90 |")
    lines.append("|---:|---:|---:|---:|---:|---:|")
    for horizon in HORIZONS:
        carry_errors = errors[("carry", horizon)]
        lines.append(
            f"| {horizon} | {len(carry_errors)} "
            f"| {statistics.median(carry_errors):.1%} "
            f"| {statistics.median(errors[('trend5', horizon)]):.1%} "
            f"| {statistics.median(errors[('trend8', horizon)]):.1%} "
            f"| {quantile(carry_errors, 0.90):.1%} |"
        )

    lines.append("")
    lines.append("## Carry-forward signed bias")
    lines.append("")
    lines.append("Median and mean of `log(predicted / actual)`; positive means over-prediction.")
    lines.append("")
    lines.append("| gap *h* | median | mean |")
    lines.append("|---:|---:|---:|")
    for horizon in HORIZONS:
        values = bias[horizon]
        lines.append(
            f"| {horizon} | {statistics.median(values):+.1%} | {sum(values) / len(values):+.1%} |"
        )

    lines.append("")
    lines.append("## Group A: error at each country's own horizon")
    lines.append("")
    lines.append("| country | last obs | gap | carry MdAPE | trend8 MdAPE | carry 2025 | trend8 2025 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for name, last in GROUP_A:
        horizon = 2025 - last
        series = panel[name]
        base = series[max(year for year in series if year <= last)]
        projected = trend(series, 2025, horizon, window=8)
        lines.append(
            f"| {name} | {last} | {horizon} "
            f"| {statistics.median(errors[('carry', horizon)]):.1%} "
            f"| {statistics.median(errors[('trend8', horizon)]):.1%} "
            f"| {base:.0f} | {projected:.0f} |"
        )

    lines.append("")
    lines.append("## Long-horizon trend failures")
    lines.append("")
    lines.append("Worst 20+ year trend projection per stale country, chosen by log error.")
    lines.append("")
    lines.append("| country | base | base year | trend prediction | actual | target year | error |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for name in (
        "Sweden",
        "Denmark",
        "Finland",
        "Ecuador",
        "Italy",
        "Belgium",
        "Netherlands",
        "France",
    ):
        if name not in failures:
            continue
        target, horizon, base, predicted, actual = max(
            failures[name], key=lambda item: abs(math.log(item[3] / item[4]))
        )
        lines.append(
            f"| {name} | {base:.0f} | {target - horizon} | {predicted:.0f} "
            f"| {actual:.0f} | {target} | {predicted / actual - 1:+.0%} |"
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
