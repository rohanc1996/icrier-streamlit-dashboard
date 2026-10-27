#!/usr/bin/env python3
"""Build the transposed smartphone-users CSV for the SIDE 2027 Connect pillar.

Method (as specified by Aarti):
    Findex %      = con5a + con9a
    Findex users  = Findex % / 100 × UNDESA population aged 15+
    Users         = average(Statista users, Findex users)
    Relative %    = Users / UNDESA population aged 15+ × 100

``con5a`` is missing for most high-income countries and is treated as zero.
Qatar, Rwanda and the UAE have no Findex data, so they use Statista only;
Uzbekistan has no Statista value, so it uses Findex only.

Inputs:
    data/2027 individual indicators/statista_2026 Smartphone Users by Country.csv
    scripts/data_sources/world_bank/cache/findex_smartphone_2024.json
    scripts/data_sources/undesa/cache/undes_population_15plus_2026.json

Output: data/2027 individual indicators/smartphone-users-transposed.csv

Run:  python scripts/data_sources/smartphone/build_smartphone_users_csv.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "itu"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "world_bank"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "undesa"))

from fetch_findex_smartphone import fetch as fetch_findex  # noqa: E402
from fetch_undes import ISO3  # noqa: E402
from fetch_undes_15plus import fetch as fetch_population_15plus  # noqa: E402

COUNTRY_REF = ROOT / "data" / "SIDE 2027 - Absolute.csv"
STATISTA = (
    ROOT
    / "data"
    / "2027 individual indicators"
    / "statista_2026 Smartphone Users by Country.csv"
)
OUT = (
    ROOT
    / "data"
    / "2027 individual indicators"
    / "smartphone-users-transposed.csv"
)

STATISTA_MILLIONS = "Statista smartphone users (millions, 2026)"
STATISTA_ABS = "Statista smartphone users (absolute numbers)"
FINDEX_SHARED = "Findex shared smartphone use (% age 15+, 2024)"
FINDEX_MAIN = "Findex main phone is smartphone (% age 15+, 2024)"
FINDEX_PCT = "Findex smartphone use (% age 15+, shared + main)"
FINDEX_ABS = "Findex smartphone users (absolute numbers)"
POP_15PLUS = "UNDESA population aged 15+ (2026)"
AVG_ABS = (
    "Number of smartphone users (average of Statista and Findex, absolute numbers)"
)
AVG_PCT = "Smartphone users (% of population aged 15+)"
STATISTA_YEAR = "Statista data year"
FINDEX_YEAR = "Findex data year"
POP_YEAR = "UNDESA population data year"

ROWS = [
    STATISTA_MILLIONS,
    STATISTA_ABS,
    FINDEX_SHARED,
    FINDEX_MAIN,
    FINDEX_PCT,
    FINDEX_ABS,
    POP_15PLUS,
    AVG_ABS,
    AVG_PCT,
    STATISTA_YEAR,
    FINDEX_YEAR,
    POP_YEAR,
]


def side_countries() -> list[str]:
    with COUNTRY_REF.open(newline="", encoding="utf-8") as fh:
        return [
            row[0]
            for row in list(csv.reader(fh))[1:]
            if row and row[0] and row[0] != "Coefficient of variation"
        ]


def statista_users() -> dict[str, float | None]:
    df = pd.read_csv(STATISTA).iloc[:71]
    df["Users (millions)"] = pd.to_numeric(
        df["Users (millions)"]
        .astype(str)
        .str.replace(",", "")
        .replace({" —": pd.NA, "—": pd.NA}),
        errors="coerce",
    )
    return dict(zip(df["Country"], df["Users (millions)"]))


def fmt_rate(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}"


def fmt_count(value: float | None) -> str:
    return "-" if value is None else f"{value:,.0f}"


def main() -> int:
    countries = side_countries()
    statista = statista_users()
    findex = fetch_findex(use_cache=True)
    population = fetch_population_15plus(use_cache=True)

    shared = findex["values"]["con5a"]
    main_phone = findex["values"]["con9a"]
    pop15 = population["values"]

    columns: dict[str, list[str]] = {row: [] for row in ROWS}

    for country in countries:
        iso = ISO3[country]
        statista_millions = statista.get(country)
        if statista_millions is None or pd.isna(statista_millions):
            statista_millions = None
        statista_abs = (
            statista_millions * 1_000_000
            if statista_millions is not None
            else None
        )

        shared_rate = shared.get(iso)
        main_rate = main_phone.get(iso)
        findex_rate = (
            (shared_rate or 0.0) + main_rate
            if main_rate is not None
            else None
        )
        pop = pop15.get(iso)
        findex_abs = (
            findex_rate / 100 * pop
            if findex_rate is not None and pop is not None
            else None
        )

        estimates = [v for v in (statista_abs, findex_abs) if v is not None]
        average = sum(estimates) / len(estimates) if estimates else None
        average_pct = (
            average / pop * 100
            if average is not None and pop is not None
            else None
        )

        columns[STATISTA_MILLIONS].append(fmt_rate(statista_millions))
        columns[STATISTA_ABS].append(fmt_count(statista_abs))
        columns[FINDEX_SHARED].append(fmt_rate(shared_rate))
        columns[FINDEX_MAIN].append(fmt_rate(main_rate))
        columns[FINDEX_PCT].append(fmt_rate(findex_rate))
        columns[FINDEX_ABS].append(fmt_count(findex_abs))
        columns[POP_15PLUS].append(fmt_count(pop))
        columns[AVG_ABS].append(fmt_count(average))
        columns[AVG_PCT].append(fmt_rate(average_pct))
        columns[STATISTA_YEAR].append("2026" if statista_millions is not None else "-")
        columns[FINDEX_YEAR].append("2024" if findex_rate is not None else "-")
        columns[POP_YEAR].append(population["year"] if pop is not None else "-")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Indicator"] + countries)
        for row in ROWS:
            writer.writerow([row] + columns[row])

    over_100 = [
        (country, value)
        for country, value in zip(countries, columns[AVG_PCT])
        if value != "-" and float(value) > 100
    ]
    missing_statista = [
        c for c, value in zip(countries, columns[STATISTA_ABS]) if value == "-"
    ]
    print(
        f"Wrote {OUT} ({len(countries)} countries; "
        f"Statista missing {', '.join(missing_statista) or 'none'}; "
        f"over 100%: {', '.join(c for c, _ in over_100) or 'none'})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
