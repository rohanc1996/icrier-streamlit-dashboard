#!/usr/bin/env python3
"""Build a side-by-side source panel for internet and smartphone users.

One row per SIDE country (71), users in millions. The point of the file is to
let a reader eyeball each source against the others before trusting an average.

Columns
-------
``Population_2024_m`` / ``Population_2025_m``
    UN DESA WPP 2024 total population, from the ITU population cache.
``Internet_Statista_2026_m``
    ``data/reference/statista 2026 Internet User Counts.csv``.
``Internet_SIDE2026_report_m``
    ``Number of Internet Users (absolute numbers)`` from
    ``data/SIDE 2026 - Absolute.csv``. This is NOT a Statista series: it
    reproduces ``(ITU 2024 + Findex 2024) / 2`` to within a median 0.0%.
``Internet_ITU_2024_m`` / ``Internet_ITU_2025_m``
    ITU DataHub indicator 11624 (Individuals using the Internet, % of total
    population) multiplied by the matching UN DESA population. 2025 is blank
    for the 38 countries where ITU still reports 2024.
``Internet_Findex_2024_totalpop_m``
    Global Findex 2024 rate (age 15+) applied to **total** population. This is
    deliberately not the demographically consistent count: it matches the
    convention used by SIDE 2026/2027, where the Findex rate is applied to the
    whole population before being averaged with ITU. Averaging the ITU and
    Findex count columns here therefore reproduces ``SIDE 2026``.
``Smartphone_Statista_2026_m``
    ``data/2027 individual indicators/statista_2026 Smartphone Users by
    Country.csv``. Caveat: of the 70 source links on that page, 46 are
    Statista *mobile internet* pages and 23 are smartphone pages.
``Smartphone_SIDE2026_report_m``
    ``Number of smartphone users (million)`` from ``SIDE 2026 - Absolute.csv``
    (the column holds raw counts despite its name).
``Smartphone_Findex_2024_m``
    Findex 2024 shared + main smartphone use (age 15+), as built by
    ``scripts/data_sources/smartphone/build_smartphone_users_csv.py``.

There is no Statista 2025 export in the repo. ``SIDE 2025 - Absolute.csv`` is
not a substitute: it has 59 countries under different names and its smartphone
column is zero for 25 of them.

Run:  python scripts/analysis/build_source_panel.py

Output: deliverables/source-checks/internet-smartphone-source-panel.csv
"""
from __future__ import annotations

import csv
import gzip
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ITU_DIR = ROOT / "scripts" / "data_sources" / "itu"
sys.path.insert(0, str(ITU_DIR))
from fetch_undes import ISO3  # noqa: E402

OUT = (
    ROOT
    / "deliverables"
    / "source-checks"
    / "internet-smartphone-source-panel.csv"
)

STATISTA_INTERNET = ROOT / "data" / "reference" / "statista 2026 Internet User Counts.csv"
STATISTA_SMARTPHONE = (
    ROOT
    / "data"
    / "2027 individual indicators"
    / "statista_2026 Smartphone Users by Country.csv"
)
SIDE_2026 = ROOT / "data" / "SIDE 2026 - Absolute.csv"
SIDE_2027 = ROOT / "data" / "SIDE 2027 - Absolute.csv"
POP_CACHE = ITU_DIR / "cache" / "undes_population.json"
ITU_SERIES_CACHE = ITU_DIR / "cache" / "itu_internet_by_year.json"

ITU_BASE = "https://api.datahub.itu.int/v3"
ITU_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Origin": "https://beta.datahub.itu.int",
    "Referer": "https://beta.datahub.itu.int/",
}

COLUMNS = [
    "Country",
    "Population_2024_m",
    "Population_2025_m",
    "Internet_Statista_2026_m",
    "Internet_SIDE2026_report_m",
    "Internet_ITU_2024_m",
    "Internet_ITU_2025_m",
    "Internet_Findex_2024_totalpop_m",
    "Smartphone_Statista_2026_m",
    "Smartphone_SIDE2026_report_m",
    "Smartphone_Findex_2024_m",
]


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False), errors="coerce"
    )


def load_absolute(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df.columns = [c.strip().replace("\n", " ") for c in df.columns]
    df = df[(df["Country"] != "") & (df["Country"] != "Coefficient of variation")]
    return df.set_index("Country")


def statista_internet() -> pd.Series:
    values: dict[str, float] = {}
    with STATISTA_INTERNET.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.reader(fh):
            if not row or not row[0].strip() or row[0].strip() == "Sources:":
                break
            if row[0].strip() == "Country":
                continue
            country = re.sub("\u2020", "", row[0]).strip()
            values[country] = float(row[1].replace(",", ""))
    return pd.Series(values, dtype=float)


def statista_smartphone() -> pd.Series:
    df = pd.read_csv(STATISTA_SMARTPHONE).iloc[:71]
    return pd.Series(dict(zip(df["Country"], numeric(df["Users (millions)"]))))


def itu_internet_by_year() -> dict[str, dict[int, float]]:
    if ITU_SERIES_CACHE.exists():
        raw = json.loads(ITU_SERIES_CACHE.read_text(encoding="utf-8"))
        return {iso: {int(y): v for y, v in years.items()} for iso, years in raw.items()}

    url = f"{ITU_BASE}/data/bycode/11624"
    last: Exception | None = None
    payload: list[dict] = []
    for attempt in range(1, 7):
        try:
            req = urllib.request.Request(url, headers=ITU_HEADERS)
            with urllib.request.urlopen(req, timeout=90) as resp:
                body = resp.read()
                if body[:2] == b"\x1f\x8b":
                    body = gzip.decompress(body)
            payload = json.loads(body.decode("utf-8"))
            break
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            last = exc
            time.sleep(3 * attempt)
    else:
        raise RuntimeError(f"ITU series request failed: {url}") from last

    series: dict[str, dict[int, float]] = {}
    for row in payload:
        answers = row.get("answer") or []
        iso = row.get("isoCode")
        if not iso or not answers or answers[0].get("value") in (None, ""):
            continue
        try:
            year = int(row["dataYear"])
            value = float(answers[0]["value"])
        except (KeyError, TypeError, ValueError):
            continue
        series.setdefault(iso, {})[year] = value

    ITU_SERIES_CACHE.parent.mkdir(parents=True, exist_ok=True)
    ITU_SERIES_CACHE.write_text(
        json.dumps(series, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return series


def millions(value: object) -> float | None:
    """Convert a raw user count to millions, rounded to 3 dp."""
    if value is None or pd.isna(value):
        return None
    return round(float(value) / 1_000_000, 3)


def already_millions(value: object) -> float | None:
    """Round a value that is already expressed in millions."""
    if value is None or pd.isna(value):
        return None
    return round(float(value), 3)


def main() -> int:
    side = list(load_absolute(SIDE_2027).index)
    side_2026 = load_absolute(SIDE_2026)

    st_internet = statista_internet()
    st_smartphone = statista_smartphone()

    it = pd.read_csv(ROOT / "data" / "2027 individual indicators" / "itu-transposed.csv", index_col=0)
    sp = pd.read_csv(
        ROOT / "data" / "2027 individual indicators" / "smartphone-users-transposed.csv",
        index_col=0,
    )
    popula = json.loads(POP_CACHE.read_text(encoding="utf-8"))
    itu = itu_internet_by_year()

    fx_internet = numeric(it.loc["% of population using the internet (Findex, age 15+)"])
    fx_smartphone = numeric(sp.loc["Findex smartphone users (absolute numbers)"])

    old_internet = numeric(side_2026["Number of Internet Users (absolute numbers)"])
    old_smartphone = numeric(side_2026["Number of smartphone users (million)"])

    records = []
    for country in side:
        iso = ISO3.get(country, "")
        pop = popula.get(iso, {})
        pop_2024 = pop.get("2024")
        pop_2025 = pop.get("2025")
        rates = itu.get(iso, {})

        itu_2024 = (
            rates[2024] / 100 * pop_2024 if 2024 in rates and pop_2024 else None
        )
        itu_2025 = (
            rates[2025] / 100 * pop_2025 if 2025 in rates and pop_2025 else None
        )
        fxi = fx_internet.get(country)
        fxs = fx_smartphone.get(country)

        records.append(
            {
                "Country": country,
                "Population_2024_m": millions(pop_2024),
                "Population_2025_m": millions(pop_2025),
                "Internet_Statista_2026_m": already_millions(st_internet.get(country)),
                "Internet_SIDE2026_report_m": millions(
                    old_internet.get(country) if country in old_internet.index else None
                ),
                "Internet_ITU_2024_m": millions(itu_2024),
                "Internet_ITU_2025_m": millions(itu_2025),
                "Internet_Findex_2024_totalpop_m": millions(
                    fxi / 100 * pop_2024 if pd.notna(fxi) else None
                ),
                "Smartphone_Statista_2026_m": already_millions(st_smartphone.get(country)),
                "Smartphone_SIDE2026_report_m": millions(
                    old_smartphone.get(country) if country in old_smartphone.index else None
                ),
                "Smartphone_Findex_2024_m": millions(fxs if pd.notna(fxs) else None),
            }
        )

    panel = pd.DataFrame(records, columns=COLUMNS)
    assert len(panel) == 71, f"expected 71 rows, got {len(panel)}"
    assert panel["Country"].is_unique

    OUT.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(OUT, index=False, float_format="%.3f")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(panel)} rows, {len(panel.columns)} columns)")
    print(
        "  internet Statista 2026: "
        f"{panel['Internet_Statista_2026_m'].notna().sum()}/71; "
        "smartphone Statista 2026: "
        f"{panel['Smartphone_Statista_2026_m'].notna().sum()}/71; "
        "ITU 2025: "
        f"{panel['Internet_ITU_2025_m'].notna().sum()}/71"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
