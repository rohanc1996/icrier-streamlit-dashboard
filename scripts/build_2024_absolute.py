#!/usr/bin/env python3
"""Build ``data/SIDE 2024 - Absolute.csv`` from the 2024 pillar workbook.

Source:  ``data/Copy of absolute sheet side 2024 rohan.xlsx``
         One sheet per CHIPS pillar (Connect / Harness / Innovate / Protect /
         Sustain).  Each sheet is laid out as *indicator columns x country rows*,
         preceded by a metadata block (sub-pillar, weight, source, year,
         comment, missing-count, inverted-scale flags).

Output:  ``data/SIDE 2024 - Absolute.csv``
         The standard dashboard shape: first column ``Country``, then one
         column per indicator, one row per country.  Missing cells are ``-``.

Mapping policy
--------------
2024 predates the 2026 framework, so indicator names/units differ.  Every 2024
indicator that has a 2026 counterpart is renamed to the canonical 2026 dataset
header *and its value is rescaled into the 2026 unit* (traffic TB -> EB, revenue
billions -> millions, raw currency -> USD millions, per-100 subscriptions ->
absolute, etc.).  2024 indicators with no 2026 counterpart keep their own name.

The workbook carries no ``Coefficient of variation`` row, so none is written.

Run:  python scripts/build_2024_absolute.py
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "Copy of absolute sheet side 2024 rohan.xlsx"
# Cached copy of the workbook (sheet -> rows) so the build still reproduces if
# the source xlsx is moved away.
SRC_CACHE = Path("/var/folders/y2/yclm_15n3wn34cjz97fvk7vw0000gn/T/opencode/side2024.json")
OUT = ROOT / "data" / "SIDE 2024 - Absolute.csv"

# Metadata rows in column A that are not countries.
META_LABELS = {
    "sub-pillar", "sub - pillar", "countries", "country",
    "weight for index", "weight for index (halved)", "source", "year",
    "comment", "note", "any countries missing?", "old data?",
    "inverted scale?",
}

# 2024 indicator (per sheet) -> canonical 2026 dataset header.
# Only indicators whose unit matches the canonical header are remapped.
RENAME: dict[str, dict[str, str]] = {
    "Connect": {
        "Price of mobile data and voice basket (high consumption) (PPP$) (2022)":
            "Price of mobile data and voice basket (HC)  (PPP)",
        "Price of mobile data and voice basket (low consumption) (PPP$) (2022)":
            "Price of mobile data and voice basket (LC) (PPP)",
        "Median Mobile Download Speeds (Mbps) (Actual Values)":
            "Median Mobile Download Speeds (Mbps)",
        "Median Fixed Broadband Download Speeds (Mbps)":
            "Median Fixed Broadband Download Speed (Mbps)",
        "Number of internet users (calculated using multiple % but 2022 population) (million)":
            "Number of Internet Users (absolute numbers)",
        "Population covered by LTE":
            "Population covered by LTE (Absolute numbers)",
        "Mobile cellular subscriptions":
            "Mobile Cellular Subscriptions in millions (absolute numbers)",
        "Number of smart phone users":
            "Number of smartphone users (million)",
    },
    "Harness": {
        "Number (16-64 years) using social media for work related activities (Actual values)":
            "Number of internet users (16-64 years) using social media for work related activities",
        "Food Delivery users in million":
            "Number of users of digital food delivery platforms (millions)",
        "Number of users of digital health applications (Actual values)":
            "Number of users of digital health applications",
        "E-commerce users":
            "Number of e-commerce users",
        "VoD in millions of users":
            "Number of video on demand users",
        "Total monthly fixed broadband internet traffic (TB)":
            "Fixed-broadband Internet traffic (EB)",
        "Total monthly mobile broadband internet traffic (TB)":
            "Mobile broadband internet traffic (EB)",
        "Value of digital payment transactions (absolute values) (in billions of dollars)":
            "Value of digital payment transactions (millions of dollars)",
        "Number of people who made or recieved a digital payment (Actual values)":
            "Users of Digital Payments (in millions)",
        "ICT service exports (BOP current $)":
            "ICT Services Export  (million USD)",
        "Number of people who received public sector wages: into an account (age 15+)":
            "Number of people who received public sector wages into an account (age 15 +)",
        "Number of people who received private sector wages: into an account (age 15+)":
            "Number of people (age 15 +) who received private sector wages into an account",
        "Individuals who received government transfer or pension into an account":
            "Individuals who received government transfer or pension into an account (age 15 +)",
        "Neo banking Transaction value (absolute)":
            "Value of neo banking transactions (USD)",
        "No. Mobile of app downloads (in billions)":
            "Number of mobile app downloads",
    },
    "Innovate": {
        "Consumer IOT Revenue (in million USD)":
            "Consumer and Industrial IoT revenues (millions of USD)",
        "AR/VR revenues in million $":
            "AR/ VR revenues (millions of USD)",
        "Revenue for DeFi":
            "DeFi revenue (millions of USD)",
        "No. of Startups":
            "Number of Start-ups",
        "VC investments in AI in million dollars":
            "Venture Capital Investments in AI (millions of USD)",
        "Metaverse revenues in billion $USD":
            "Metaverse revenue (millions of USD)",
        "Total Unicorn Valuation in billions of USD":
            "Valuation of Unicorns (Millions of USD)",
    },
    "Protect": {
        "Cybersecurity spending in mn USD":
            "Cybersecurity revenue (Mn USD)",
        "Ransomware attacks 30 day average":
            "Ransomware attacks 30 day average",
        "Number of Secure servers (Actual values)":
            "Number of Secure servers",
        "Total email leaks (Quarterly average) (2020 Q3- 2023 Q3) (Actual values)":
            "Total number of email leaks (Quarterly average) (2022 Q3 - 2025 Q3)",
    },
    "Sustain": {
        # 1 kilotonne == 1 million kg: numerically equivalent.
        "E-waste generation in kiltonnes":
            "E-waste generated (million kg)",
        "Patents filed (2000-2021) in Smart Grids":
            "Patents filed (2000-2024) in Smart Grids",
        "Patents filed (2000-2021) in Information/Communication Technologies for Electromobility":
            "Patents filed (2000-2024) in Information/Communication Technologies for Electromobility",
        "Green data centres in million $":
            "Market Size of Green data centres in million $",
        "Environment, Health, and Safety (EHS) software including carbon footprint management":
            "Market Size of Environment, Health, and Safety (EHS) software including carbon footprint management",
        "Energy Management Software":
            "Market Size of Energy Management Software",
        "Sustainable Electronics (Smartphones and PCs)**":
            "Market Size of Sustainable Electronics (Smartphones and PCs)**",
    },
}

# Source indicator -> multiplier that converts its 2024 unit to the canonical
# 2026 unit.  Only unit-bearing indicators appear here; counts and already-
# canonical units need no entry.
FACTORS: dict[str, float] = {
    # mobile subscriptions are per-100-population x population -> absolute count
    "Mobile cellular subscriptions": 0.01,
    # 2026 stores LTE coverage in thousands
    "Population covered by LTE": 1e-3,
    # monthly traffic TB -> EB
    "Total monthly fixed broadband internet traffic (TB)": 1e-6,
    "Total monthly mobile broadband internet traffic (TB)": 1e-6,
    # billions of USD -> millions of USD
    "Value of digital payment transactions (absolute values) (in billions of dollars)": 1000.0,
    "Metaverse revenues in billion $USD": 1000.0,
    "Total Unicorn Valuation in billions of USD": 1000.0,
    # absolute counts -> millions
    "Number of people who made or recieved a digital payment (Actual values)": 1e-6,
    # raw current USD -> USD millions
    "ICT service exports (BOP current $)": 1e-6,
}

COUNTRY_RENAME = {
    "Russia": "Russian Federation",
    "South Korea": "Republic of Korea",
    "Turkey": "Türkiye",
    "UK": "United Kingdom",
    "United States": "United States of America",
    "USA": "United States of America",
    "US": "United States of America",
}

SHEET_ORDER = ["Connect", "Harness", "Innovate", "Protect", "Sustain"]


def _clean(text: object) -> str:
    return re.sub(r"\s+", " ", str(text)).strip() if text is not None else ""


def _to_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        s = value.strip().replace(",", "")
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _fmt(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, str):
        s = value.strip()
        if s in ("", "-", "—", "–", "NA", "N/A"):
            return "-"
        try:
            value = float(s.replace(",", ""))
        except ValueError:
            return s
    if isinstance(value, (int, float)):
        return f"{round(float(value), 6):,.6f}".rstrip("0").rstrip(".")
    return str(value)


def load_sheets() -> dict[str, list[list]]:
    """Return {sheet_name: matrix of cells} from the xlsx, or its cached JSON."""
    if SRC.exists():
        import openpyxl

        wb = openpyxl.load_workbook(SRC, data_only=True)
        return {
            ws.title: [
                [ws.cell(r, c).value for c in range(1, ws.max_column + 1)]
                for r in range(1, ws.max_row + 1)
            ]
            for ws in wb.worksheets
        }
    if SRC_CACHE.exists():
        return json.loads(SRC_CACHE.read_text())
    raise FileNotFoundError(f"Neither {SRC} nor its cache {SRC_CACHE} exists")


def read_sheet(matrix: list[list]) -> tuple[list[str], list[tuple[str, list]]]:
    """Return (indicator headers, [(country, values), ...]) for one sheet."""
    def cell(r: int, c: int):
        if 1 <= r <= len(matrix):
            row = matrix[r - 1]
            if 1 <= c <= len(row):
                return row[c - 1]
        return None

    ncol = max((len(row) for row in matrix), default=0)
    header_row = None
    for r in range(1, 12):
        if _clean(cell(r, 1)).lower() in ("countries", "country"):
            header_row = r
            break
    if header_row is None:
        # Some sheets (e.g. Sustain) leave column A blank on the header row and
        # only label the indicators in column B onward.
        for r in range(1, 12):
            first = _clean(cell(r, 1))
            second = cell(r, 2)
            if not first and isinstance(second, str) and second.strip():
                header_row = r
                break
    if header_row is None:
        raise ValueError("No header row found")

    headers = [_clean(cell(header_row, c)) for c in range(2, ncol + 1)]
    rows: list[tuple[str, list]] = []
    for r in range(header_row + 1, len(matrix) + 1):
        name = _clean(cell(r, 1))
        if not name or name.lower() in META_LABELS:
            continue
        values = [cell(r, c) for c in range(2, ncol + 1)]
        rows.append((name, values))
    return headers, rows


def main() -> int:
    sheets = load_sheets()

    countries: list[str] = []
    data: dict[str, dict[str, str]] = {}
    ordered_indicators: list[str] = []

    for sheet in SHEET_ORDER:
        headers, rows = read_sheet(sheets[sheet])
        rename = RENAME.get(sheet, {})
        for idx, raw_header in enumerate(headers):
            if not raw_header:
                continue
            target = rename.get(raw_header, raw_header).strip()
            if target in ordered_indicators:
                continue
            ordered_indicators.append(target)
            factor = FACTORS.get(raw_header)
            for country, values in rows:
                cname = COUNTRY_RENAME.get(country, country)
                value = values[idx]
                if factor is not None:
                    num = _to_float(value)
                    value = "-" if num is None else num * factor
                data.setdefault(cname, {})[target] = _fmt(value)
                if cname not in countries:
                    countries.append(cname)

    countries.sort()

    with OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Country", *ordered_indicators])
        for country in countries:
            writer.writerow([country, *[data[country].get(ind, "-") for ind in ordered_indicators]])

    print(f"Wrote {OUT} ({len(countries)} countries, {len(ordered_indicators)} indicators)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
