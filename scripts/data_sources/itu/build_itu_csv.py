#!/usr/bin/env python3
"""Build the transposed ITU CSV for the SIDE 2027 Connect pillar.

Combines ITU penetration rates with UN DESA WPP 2024 total population to derive
absolute numbers.

Output: data/2027 individual indicators/itu-transposed.csv

Layout matches speedtest-transposed.csv: indicators as rows, countries as
columns. The 71 SIDE countries are kept in SIDE order.

Run:  python scripts/data_sources/itu/build_itu_csv.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_itu import fetch as fetch_itu  # noqa: E402
from fetch_undes import ISO3, fetch as fetch_undes  # noqa: E402

COUNTRY_REF = ROOT / "data" / "SIDE 2027 - Absolute.csv"
SIDE_2026 = ROOT / "data" / "SIDE 2026 - Absolute.csv"
OUT = ROOT / "data" / "2027 individual indicators" / "itu-transposed.csv"

MOBILE_PER_100 = "Mobile Cellular Subscriptions per 100 population (ITU)"
MOBILE_ABS = "Mobile Cellular Subscriptions (absolute numbers)"
INTERNET_PCT = "% of population using the internet (ITU)"
INTERNET_ABS = "Number of Internet Users (absolute numbers)"
POP_MOBILE = "UN DESA total population (mobile year)"
POP_INTERNET = "UN DESA total population (internet year)"
MOBILE_YEAR = "Mobile data year"
INTERNET_YEAR = "Internet data year"
LTE_PCT = "Population covered by LTE and above (% of population)"
LTE_ABS = "Population covered by LTE and above (absolute numbers)"
POP_LTE = "UN DESA total population (LTE year)"
LTE_YEAR = "LTE data year"
MOBILE_HC = "Price of mobile data and voice basket (HC) (PPP$)"
MOBILE_LC = "Price of mobile data and voice basket (LC) (PPP$)"
FIXED_PPP = "Price of fixed broadband internet (5GB) (PPP$)"
SMARTPHONE = "Price of cheapest smartphone (PPP$) (SIDE 2026)"
PRICE_YEAR = "ITU price baskets data year"

ROWS = [
    MOBILE_PER_100,
    MOBILE_ABS,
    INTERNET_PCT,
    INTERNET_ABS,
    POP_MOBILE,
    POP_INTERNET,
    MOBILE_YEAR,
    INTERNET_YEAR,
    LTE_PCT,
    LTE_ABS,
    POP_LTE,
    LTE_YEAR,
    MOBILE_HC,
    MOBILE_LC,
    FIXED_PPP,
    SMARTPHONE,
    PRICE_YEAR,
]


def side_countries() -> list[str]:
    with COUNTRY_REF.open(newline="", encoding="utf-8") as fh:
        return [
            row[0]
            for row in list(csv.reader(fh))[1:]
            if row and row[0] and row[0] != "Coefficient of variation"
        ]


def side2026_smartphone() -> dict[str, float | None]:
    with SIDE_2026.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    header = rows[0]
    index = header.index("Price of cheapest smartphone (PPP$)")
    out: dict[str, float | None] = {}
    for row in rows[1:]:
        if not row or not row[0] or row[0] == "Coefficient of variation":
            continue
        value = row[index]
        try:
            out[row[0]] = float(value)
        except (TypeError, ValueError):
            out[row[0]] = None
    return out


def fmt_rate(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}"


def fmt_count(value: float | None) -> str:
    return "-" if value is None else f"{value:,.0f}"


def fmt_year(value: int | None) -> str:
    return "-" if value is None else str(value)


def main() -> int:
    itu = fetch_itu(use_cache=True)
    population = fetch_undes(use_cache=True)
    smartphone = side2026_smartphone()

    countries = side_countries()
    columns: dict[str, list[str]] = {row: [] for row in ROWS}

    for country in countries:
        iso = ISO3[country]
        mobile = itu["mobile_per_100"].get(iso)
        internet = itu["internet_pct"].get(iso)
        lte = itu["lte_pct"].get(iso)
        mobile_hc = itu["mobile_hc_ppp"].get(iso)
        mobile_lc = itu["mobile_lc_ppp"].get(iso)
        fixed = itu["fixed_ppp"].get(iso)

        mobile_rate = mobile["value"] if mobile else None
        mobile_year = mobile["year"] if mobile else None
        internet_rate = internet["value"] if internet else None
        internet_year = internet["year"] if internet else None
        lte_rate = lte["value"] if lte else None
        lte_year = lte["year"] if lte else None

        mobile_pop = population.get(iso, {}).get(str(mobile_year)) if mobile_year else None
        internet_pop = population.get(iso, {}).get(str(internet_year)) if internet_year else None
        lte_pop = population.get(iso, {}).get(str(lte_year)) if lte_year else None

        mobile_abs = (
            mobile_rate / 100 * mobile_pop
            if mobile_rate is not None and mobile_pop is not None
            else None
        )
        internet_abs = (
            internet_rate / 100 * internet_pop
            if internet_rate is not None and internet_pop is not None
            else None
        )
        lte_abs = (
            lte_rate / 100 * lte_pop
            if lte_rate is not None and lte_pop is not None
            else None
        )

        price_year = mobile_hc["year"] if mobile_hc else None

        columns[MOBILE_PER_100].append(fmt_rate(mobile_rate))
        columns[MOBILE_ABS].append(fmt_count(mobile_abs))
        columns[INTERNET_PCT].append(fmt_rate(internet_rate))
        columns[INTERNET_ABS].append(fmt_count(internet_abs))
        columns[POP_MOBILE].append(fmt_count(mobile_pop))
        columns[POP_INTERNET].append(fmt_count(internet_pop))
        columns[MOBILE_YEAR].append(fmt_year(mobile_year))
        columns[INTERNET_YEAR].append(fmt_year(internet_year))
        columns[LTE_PCT].append(fmt_rate(lte_rate))
        columns[LTE_ABS].append(fmt_count(lte_abs))
        columns[POP_LTE].append(fmt_count(lte_pop))
        columns[LTE_YEAR].append(fmt_year(lte_year))
        columns[MOBILE_HC].append(fmt_rate(mobile_hc["value"] if mobile_hc else None))
        columns[MOBILE_LC].append(fmt_rate(mobile_lc["value"] if mobile_lc else None))
        columns[FIXED_PPP].append(fmt_rate(fixed["value"] if fixed else None))
        columns[SMARTPHONE].append(fmt_rate(smartphone.get(country)))
        columns[PRICE_YEAR].append(fmt_year(price_year))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Indicator"] + countries)
        for row in ROWS:
            writer.writerow([row] + columns[row])

    mobile_years: dict[int, int] = {}
    internet_years: dict[int, int] = {}
    for country in countries:
        iso = ISO3[country]
        if iso in itu["mobile_per_100"]:
            year = itu["mobile_per_100"][iso]["year"]
            mobile_years[year] = mobile_years.get(year, 0) + 1
        if iso in itu["internet_pct"]:
            year = itu["internet_pct"][iso]["year"]
            internet_years[year] = internet_years.get(year, 0) + 1

    print(
        f"Wrote {OUT} ({len(countries)} countries; "
        f"mobile years {dict(sorted(mobile_years.items()))}; "
        f"internet years {dict(sorted(internet_years.items()))})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
