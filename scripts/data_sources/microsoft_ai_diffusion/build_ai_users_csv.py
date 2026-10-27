#!/usr/bin/env python3
"""Build the transposed Q2 2026 AI-users CSV for the SIDE 2027 Connect pillar.

Absolute AI users are computed two ways: the Q2 2026 AI user share multiplied
by UN DESA total population for 2026 (matching the SIDE 2026 column), and the
share multiplied by the World Bank working-age population (15-64, 2025), which
matches the denominator used by Microsoft's AI diffusion share.

Output: data/2027 individual indicators/ai-users-transposed.csv

Run:  python scripts/data_sources/microsoft_ai_diffusion/build_ai_users_csv.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "itu"))

from fetch_ai_diffusion import fetch as fetch_ai  # noqa: E402
from fetch_undes import ISO3, fetch as fetch_population  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "world_bank"))
from fetch_working_age import fetch as fetch_working_age  # noqa: E402

COUNTRY_REF = ROOT / "data" / "SIDE 2027 - Absolute.csv"
OUT = ROOT / "data" / "2027 individual indicators" / "ai-users-transposed.csv"
YEAR = "2026"

SHARE = "AI user share (% of working-age population, Q2 2026)"
AI_USERS = "Number of AI users (absolute numbers, share × total population)"
POPULATION = "UN DESA total population (2026)"
WORKING_AGE = "World Bank working-age population (15-64, 2025)"
AI_USERS_WORKING_AGE = (
    "Number of AI users (absolute numbers, share × World Bank working-age population)"
)
WORKING_AGE_YEAR = "World Bank working-age population year"
PERIOD = "Data period"
ROWS = [
    SHARE,
    AI_USERS,
    POPULATION,
    WORKING_AGE,
    AI_USERS_WORKING_AGE,
    PERIOD,
    WORKING_AGE_YEAR,
]

ALIASES = {
    "Czechia": "Czech Republic",
    "Republic of Korea": "South Korea",
    "Russian Federation": "Russia",
    "United States of America": "United States",
    "Viet Nam": "Vietnam",
}


def side_countries() -> list[str]:
    with COUNTRY_REF.open(newline="", encoding="utf-8") as fh:
        return [
            row[0]
            for row in list(csv.reader(fh))[1:]
            if row and row[0] and row[0] != "Coefficient of variation"
        ]


def resolve_name(country: str, shares: dict[str, float]) -> str:
    if country == "Türkiye":
        match = next(
            (name for name in shares if name.startswith("T") and name.endswith("rkiye")),
            None,
        )
        if match:
            return match
    return ALIASES.get(country, country)


def fmt_share(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}"


def fmt_count(value: float | None) -> str:
    return "-" if value is None else f"{value:,.0f}"


def main() -> int:
    ai = fetch_ai(use_cache=True)
    population = fetch_population(use_cache=True)
    working_age = fetch_working_age(use_cache=True)
    shares = ai["shares"]
    countries = side_countries()

    columns: dict[str, list[str]] = {row: [] for row in ROWS}

    for country in countries:
        report_name = resolve_name(country, shares)
        share = shares.get(report_name)
        iso = ISO3[country]
        pop = population.get(iso, {}).get(YEAR)
        working_age_pop = working_age["values"].get(iso)

        ai_users = (
            share / 100 * pop
            if share is not None and pop is not None
            else None
        )
        ai_users_working_age = (
            share / 100 * working_age_pop
            if share is not None and working_age_pop is not None
            else None
        )

        columns[SHARE].append(fmt_share(share))
        columns[AI_USERS].append(fmt_count(ai_users))
        columns[POPULATION].append(fmt_count(pop))
        columns[WORKING_AGE].append(fmt_count(working_age_pop))
        columns[AI_USERS_WORKING_AGE].append(fmt_count(ai_users_working_age))
        columns[PERIOD].append(ai["period"] if share is not None else "-")
        columns[WORKING_AGE_YEAR].append(
            working_age["year"] if working_age_pop is not None else "-"
        )

    missing = [c for c, v in zip(countries, columns[SHARE]) if v == "-"]
    if missing:
        raise RuntimeError(f"Missing AI diffusion shares for: {', '.join(missing)}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Indicator"] + countries)
        for row in ROWS:
            writer.writerow([row] + columns[row])

    print(f"Wrote {OUT} ({len(countries)} countries, {ai['period']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
