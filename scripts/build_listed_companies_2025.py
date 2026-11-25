#!/usr/bin/env python3
"""Build ``data/derived/listed_companies_2025_estimates.csv``.

Fills the 2025 gap in WDI ``CM.MKT.LDOM.NO`` (listed domestic companies,
total) for the 19 SIDE countries whose series is stale, without touching the
verbatim WDI extract.

Rules (see ``docs/decisions/0001-listed-companies-2025.md``):

* **Reported** — WDI already has 2025. Used as-is.
* **Exchange lookup** — a verified 2025/2026 count exists in
  ``data/derived/listed_companies_2025_exchange_lookups.csv``. Preferred over
  carry-forward at any gap, because an observation beats a carried value.
* **Carry forward** — no exchange figure, and the last observation is 1-4 years
  old. Carrying the last value is the most accurate rule at these horizons; the
  backtest in ``scripts/analysis/backtest_listed_companies.py`` puts median
  absolute error at 3.6% (1 year) to 13.1% (4 years), against 7.0-17.8% for a
  trend extrapolation.
* **Missing** — no 2025 observation, no lookup, and a gap too long to carry.
  Left blank on purpose.

The source year and the method travel with every value so downstream code can
choose to trust only ``reported``.

Run:  python scripts/build_listed_companies_2025.py
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WDI = ROOT / "data" / "reference" / "WB listed company counts by year.csv"
LOOKUPS = ROOT / "data" / "derived" / "listed_companies_2025_exchange_lookups.csv"
ABSOLUTE = ROOT / "data" / "SIDE 2027 - Absolute.csv"
OUT = ROOT / "data" / "derived" / "listed_companies_2025_estimates.csv"

TARGET_YEAR = 2025
MAX_CARRY_GAP = 4  # 1-4 years stale: carry forward; 5+: exchange lookup.

METADATA_ROWS = 4
ALIASES = {
    "Egypt": "Egypt, Arab Rep.",
    "Republic of Korea": "Korea, Rep.",
    "Slovakia": "Slovak Republic",
    "Türkiye": "Turkiye",
    "United States of America": "United States",
}

FIELDS = [
    "Country",
    "Listed_companies_2025",
    "Method",
    "Source_year",
    "WDI_last_year",
    "WDI_last_value",
    "Confidence",
    "Source",
]


def side_countries() -> list[str]:
    with ABSOLUTE.open(newline="", encoding="utf-8-sig") as handle:
        return [row["Country"].strip() for row in csv.DictReader(handle) if row["Country"].strip()]


def load_wdi() -> dict[str, dict[int, float]]:
    with WDI.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    header = rows[METADATA_ROWS]
    years = [cell.strip() for cell in header[4:]]
    wanted = {ALIASES.get(country, country) for country in side_countries()}

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


def load_lookups() -> dict[str, dict[str, str]]:
    with LOOKUPS.open(newline="", encoding="utf-8-sig") as handle:
        return {row["Country"].strip(): row for row in csv.DictReader(handle)}


def as_number(text: float) -> str:
    rounded = round(text)
    if abs(text - rounded) < 1e-6:
        return str(int(rounded))
    return f"{text:.6g}"


def main() -> int:
    countries = side_countries()
    panel = load_wdi()
    lookups = load_lookups()

    records: list[dict[str, str]] = []
    carried: list[str] = []
    looked_up: list[str] = []
    missing: list[str] = []

    for country in countries:
        wdi_name = ALIASES.get(country, country)
        series = panel[wdi_name]
        reported = series.get(TARGET_YEAR)
        last_year = max(series) if series else None
        last_value = series[last_year] if last_year is not None else None

        if reported is not None:
            method, value, source_year = "reported", reported, str(TARGET_YEAR)
            confidence, source = "official", "WDI CM.MKT.LDOM.NO"
        elif country in lookups and lookups[country]["value_2025"].strip():
            entry = lookups[country]
            method, value = "exchange", float(entry["value_2025"])
            source_year = entry["source_year"].strip() or str(TARGET_YEAR)
            confidence = entry["confidence"].strip()
            source = entry["source"].strip()
            looked_up.append(country)
        elif last_year is not None and TARGET_YEAR - last_year <= MAX_CARRY_GAP:
            method, value, source_year = "carry_forward", last_value, str(last_year)
            confidence = "medium"
            source = f"carry forward WDI {last_year}"
            carried.append(country)
        else:
            method, value, source_year = "missing", None, ""
            confidence, source = "", ""
            missing.append(country)

        records.append(
            {
                "Country": country,
                "Listed_companies_2025": "" if value is None else as_number(value),
                "Method": method,
                "Source_year": source_year,
                "WDI_last_year": "" if last_year is None else str(last_year),
                "WDI_last_value": "" if last_value is None else as_number(last_value),
                "Confidence": confidence,
                "Source": source,
            }
        )

    _validate(countries, records, carried, looked_up)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)

    reported = sum(1 for record in records if record["Method"] == "reported")
    never = [record["Country"] for record in records if not record["WDI_last_year"]]
    print(f"Wrote {OUT.relative_to(ROOT)}  ({len(records)} rows)")
    print(f"  reported        : {reported}/71")
    print(f"  carry forward   : {len(carried)} — {', '.join(carried)}")
    print(f"  exchange lookup : {len(looked_up)} — {', '.join(looked_up)}")
    print(f"  missing         : {len(missing)} — {', '.join(missing) or 'none'}")
    print(f"  never reported  : {len(never)} — {', '.join(never)}")
    return 0


def _validate(
    countries: list[str],
    records: list[dict[str, str]],
    carried: list[str],
    looked_up: list[str],
) -> None:
    assert [record["Country"] for record in records] == countries, "country order drifted"
    assert len(carried) == 0, f"expected no carry-forwards once lookups exist, got {len(carried)}"
    assert len(looked_up) == 14, f"expected 14 exchange lookups, got {len(looked_up)}"
    stale = [
        record
        for record in records
        if record["Method"] != "reported" and record["WDI_last_year"]
    ]
    assert len(stale) == 19, f"expected 19 stale countries, got {len(stale)}"
    for record in stale:
        assert record["Method"] in {"carry_forward", "exchange", "missing"}
    for record in records:
        if record["Method"] == "missing":
            assert not record["Listed_companies_2025"], "missing row carries a value"
        else:
            assert record["Listed_companies_2025"], f"no value for {record['Country']}"
            assert int(record["Source_year"]) <= TARGET_YEAR + 1, record["Country"]
        if record["Method"] == "carry_forward":
            gap = TARGET_YEAR - int(record["WDI_last_year"])
            assert 1 <= gap <= MAX_CARRY_GAP, f"{record['Country']} carry gap {gap}"


if __name__ == "__main__":
    raise SystemExit(main())
