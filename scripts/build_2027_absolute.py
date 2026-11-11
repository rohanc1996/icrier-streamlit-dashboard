#!/usr/bin/env python3
"""Consolidate the 2027 pillar-wise raw data into ``SIDE 2027 - Absolute.csv``.

Source:  ``data/2027 pillar-wise/SIDE 2027 Absolute - <Pillar>.csv``
         One file per CHIPS pillar, laid out as *indicator rows x country
         columns* (plus a metadata block).  Values use plain international or
         Indian digit grouping (``8,11,818``), and a few empty tokens.

Output:  ``data/SIDE 2027 - Absolute.csv``
         The dashboard shape: first column ``Country``, then one column per
         indicator, one row per country.  The existing canonical 2026 header
         and column order are preserved; only cells are filled.  New 2027
         indicators are appended at the end.

Mapping policy
--------------
The pillar files use the CHIPS spec names, while the consolidated file uses
the canonical 2026 headers the loader / CHIPS hierarchy are keyed on.  Every
source indicator is mapped explicitly to its canonical column below.  The two
duplicate ``AI Infrastructure`` columns stay as they are: the framework uses
``AI Infrastructure.1`` (the Tortoise series), so only that column is filled.

Run:  python scripts/build_2027_absolute.py
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "data" / "2027 pillar-wise"
OUT = ROOT / "data" / "SIDE 2027 - Absolute.csv"

MISSING_TOKENS = {"", "-", "--", "N/A", "Not in 2026 table"}

# Short labels used in the pillar files -> canonical country names in the
# consolidated file.  The other 63 countries are identical in both.
COUNTRY_MAP = {
    "Dom Rep": "Dominican Republic",
    "S. Korea": "Republic of Korea",
    "Russia": "Russian Federation",
    "S Arabia": "Saudi Arabia",
    "S Africa": "South Africa",
    "UAE": "United Arab Emirates",
    "UK": "United Kingdom",
    "USA": "United States of America",
}

# source indicator -> target column (None means "skip this source row")
MAPPING: dict[str, dict[str, str | None]] = {
    "SIDE 2027 Absolute - Connect.csv": {
        "Price of mobile data and voice basket (HC) PPP":
            "Price of mobile data and voice basket (HC)  (PPP)",
        "Price of mobile data and voice basket (LC) PPP":
            "Price of mobile data and voice basket (LC) (PPP)",
        "Price of cheapest smartphone in USD PPP":
            "Price of cheapest smartphone (PPP$)",
        "Fixed (broadband) internet price, USD PPP":
            "Price of fixed broadband internet (PPP)",
        "Median Mobile Download Speeds (Mbps)":
            "Median Mobile Download Speeds (Mbps)",
        "Median Fixed Broadband Download Speeds (Mbps)":
            "Median Fixed Broadband Download Speed (Mbps)",
        "Number of internet users":
            "Number of Internet Users (absolute numbers)",
        "Mobile cellular subscriptions":
            "Mobile Cellular Subscriptions in millions (absolute numbers)",
        "Population covered by LTE":
            "Population covered by LTE (Absolute numbers)",
        "Number of smart phone users":
            "Number of smartphone users (million)",
        "Number of AI users":
            "Number of AI users",
        "Compute capacity (Govt readiness)":
            "Compute capacity",
        "AI Infrastructure (Tortoise)":
            "AI Infrastructure.1",
    },
    "SIDE 2027 Absolute - Harness.csv": {
        "Social media for work-related activities (% of social media users aged 16+)":
            "Number of internet users (16-64 years) using social media for work related activities",
        "Number of users of digital food delivery platforms":
            "Number of users of digital food delivery platforms (millions)",
        "Number of users of digital health applications (millions)":
            "Number of users of digital health applications",
        "E-commerce users ( million)":
            "Number of e-commerce users",
        "Consumer Spend on Mobile Apps (millions USD)":
            "Consumer Spend on Mobile Apps (millions USD)",
        "Video On Demand Users ( millions)":
            "Number of video on demand users",
        "Total monthly fixed broadband internet traffic (EB)":
            "Fixed-broadband Internet traffic (EB)",
        "Total monthly mobile broadband internet traffic (EB)":
            "Mobile broadband internet traffic (EB)",
        "Value of digital transactions in billion dollars":
            "Value of digital payment transactions (millions of dollars)",
        "Users of Digital Payments (in millions)":
            "Users of Digital Payments (in millions)",
        "Digitally delivered services (imports, Million USD)":
            "Digitally delivered services (imports)",
        "Digitally delivered services (exports, Million USD) Imports":
            "Digitally delivered services (exports)",
        "Digitally delivered services (Net exports, Million USD)": None,
        "Digitally Manufacturing goods ? Net exports ? Computers, phones , chips,": None,
        "ICT sector employment (thousands)":
            "Employment: ICT sector (thousands)",
        "Open Data score":
            "Open Data Score",
        "Development":
            "Development: Open Source models score",
        "AI Human Capital":
            "AI Human Capital",
        "AI Talent Pillar":
            "AI Talent Pillar Score",
        "Availability zones hosting high AI capability (Tier 1) GPUs":
            "Availability zones hosting high AI capability (Tier 1) GPUs",
        "AI tech cycle trade exposure ( % of GDP)":
            "AI tech cycle trade exposure (% of GDP)",
    },
    "SIDE 2027 Absolute - Innovate.csv": {
        "No. of start -ups":
            "Number of Start-ups",
        "Total Unicorn Valuation in":
            "Valuation of Unicorns (Millions of USD)",
        "Total funding till date of Startups":
            "Total funding till date of Startups having their Head Quarters or atleast one office location in India (Millions of USD)",
        "Consumer IOT Revenues in mn $":
            "Consumer and Industrial IoT revenues (millions of USD)",
        "AR/VR Revenues in mn $":
            "AR/ VR revenues (millions of USD)",
        "Metaverse Revenues in bn $":
            "Metaverse revenue (millions of USD)",
        "DeFi Revenue in mn $":
            "DeFi revenue (millions of USD)",
        "Robotics revenue in mn $":
            "Robotics revenue (millions of USD)",
        "Drones revenue  in mn $":
            "Drones revenue (millions of USD)",
        "Crypto Index Score":
            "Crypto Index Score",
        "Estimated funding raised by privately held AI companies (millions)":
            "Total AI Private Investment in Millions",
        "Newly Funded AI Companies (vibrancy)":
            "Newly Funded AI Companies",
        "AI commercial (tortoise)":
            "AI commercial",
        "AI Innovation - Research (tortoise)":
            "AI Innovation - Research",
        "AI Research and Development- score (vibrancy)":
            "AI Research and Development- score",
    },
    "SIDE 2027 Absolute - Protect.csv": {
        "Cybersecurity Revenue in billion USD":
            "Cybersecurity revenue (Mn USD)",
        "Number of Secure servers":
            "Number of Secure servers",
        "Ransomware attacks 30 day average":
            "Ransomware attacks 30 day average",
        "Ransomware victims":
            "Ransomware victims",
        "Total number of email leaks":
            "Total number of email leaks (Quarterly average) (2022 Q3 - 2025 Q3)",
        "Safety and security":
            "Safety and security",
        "Responsible AI - Conference Submissions on RAI Topics (Total)":
            "Responsible AI - Conference Submissions on RAI Topics (Total)",
        "Public trust score":
            "Public trust score",
    },
    "SIDE 2027 Absolute - Sustain.csv": {
        "E-waste generated (million kg)":
            "E-waste generated (million kg)",
        "Number of energy and digital startups":
            "Number of energy and digital startups",
        "VC investments in AI and environmental sustainability by country (USD million)":
            "VC investments in AI and environmental sustainability by country (USD million)",
        "Patents filed (2000-2024) in Smart Grids":
            "Patents filed (2000-2024) in Smart Grids",
        "Total renewable energy production (GWh)\n":
            "Total renewable energy production (GWh)",
        "Relative Average Annual Loss by Climate (USD million)":
            "AAL by Climate (Million USD) for the Telecom Sector- Existing Climate",
    },
}


def parse_number(text: str) -> str:
    """Normalise a raw cell to a plain numeric string ('' when missing)."""
    value = text.strip()
    if value in MISSING_TOKENS:
        return ""
    cleaned = value.replace(",", "").strip()
    try:
        number = float(cleaned)
    except ValueError:
        return ""
    if number.is_integer():
        return str(int(number))
    return repr(number)


def read_output() -> tuple[list[str], list[str], dict[str, list[str]]]:
    with OUT.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    header = rows[0]
    countries = [row[0] for row in rows[1:]]
    data = {name: ["" for _ in countries] for name in header}
    for row_idx, row in enumerate(rows[1:]):
        for col_idx, name in enumerate(header):
            data[name][row_idx] = row[col_idx] if col_idx < len(row) else ""
    return header, countries, data


def add_column(header: list[str], data: dict[str, list[str]], name: str, n: int) -> None:
    if name in data:
        return
    header.append(name)
    data[name] = ["" for _ in range(n)]


def main() -> None:
    header, countries, data = read_output()
    country_index = {country: idx for idx, country in enumerate(countries)}
    n = len(countries)

    for filename, mapping in MAPPING.items():
        path = SRC_DIR / filename
        with path.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.reader(handle))
        src_header = rows[0]
        indicator_col = src_header.index("Indicator")
        country_start = src_header.index("Country") + 1
        src_countries = src_header[country_start:]

        for row in rows[2:]:
            name = row[indicator_col].strip()
            if name not in mapping:
                continue
            target = mapping[name]
            if target is None:
                continue
            add_column(header, data, target, n)
            for offset, src_country in enumerate(src_countries):
                country = COUNTRY_MAP.get(src_country, src_country)
                if country not in country_index:
                    raise KeyError(f"{filename}: unknown country {src_country!r}")
                raw = row[country_start + offset] if country_start + offset < len(row) else ""
                parsed = parse_number(raw)
                if parsed:
                    data[target][country_index[country]] = parsed

    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for idx, country in enumerate(countries):
            writer.writerow([country] + [data[name][idx] for name in header[1:]])

    print(f"Wrote {OUT} ({len(countries)} countries, {len(header) - 1} indicators)")


if __name__ == "__main__":
    main()
