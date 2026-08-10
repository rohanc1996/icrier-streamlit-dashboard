"""Country name <-> ISO-3 code mapping for the world map.

Plotly's choropleth can match countries reliably by ISO-3 code, which avoids
name-matching problems such as ``Türkiye`` vs ``Turkey``, ``Viet Nam`` vs
``Vietnam``, ``United States of America`` vs ``United States``, and
``Russian Federation`` vs ``Russia``.
"""
from __future__ import annotations

COUNTRY_TO_ISO3 = {
    "Algeria": "DZA",
    "Argentina": "ARG",
    "Australia": "AUS",
    "Austria": "AUT",
    "Bangladesh": "BGD",
    "Belgium": "BEL",
    "Brazil": "BRA",
    "Bulgaria": "BGR",
    "Canada": "CAN",
    "Chile": "CHL",
    "China": "CHN",
    "Colombia": "COL",
    "Costa Rica": "CRI",
    "Croatia": "HRV",
    "Czechia": "CZE",
    "Denmark": "DNK",
    "Dominican Republic": "DOM",
    "Ecuador": "ECU",
    "Egypt": "EGY",
    "Ethiopia": "ETH",
    "Finland": "FIN",
    "France": "FRA",
    "Germany": "DEU",
    "Ghana": "GHA",
    "Greece": "GRC",
    "Guatemala": "GTM",
    "Hungary": "HUN",
    "India": "IND",
    "Indonesia": "IDN",
    "Iraq": "IRQ",
    "Ireland": "IRL",
    "Israel": "ISR",
    "Italy": "ITA",
    "Japan": "JPN",
    "Kazakhstan": "KAZ",
    "Kenya": "KEN",
    "Kuwait": "KWT",
    "Malaysia": "MYS",
    "Mexico": "MEX",
    "Morocco": "MAR",
    "Netherlands": "NLD",
    "New Zealand": "NZL",
    "Nigeria": "NGA",
    "Norway": "NOR",
    "Pakistan": "PAK",
    "Peru": "PER",
    "Philippines": "PHL",
    "Poland": "POL",
    "Portugal": "PRT",
    "Qatar": "QAT",
    "Republic of Korea": "KOR",
    "Romania": "ROU",
    "Russian Federation": "RUS",
    "Rwanda": "RWA",
    "Saudi Arabia": "SAU",
    "Serbia": "SRB",
    "Singapore": "SGP",
    "Slovakia": "SVK",
    "South Africa": "ZAF",
    "Spain": "ESP",
    "Sri Lanka": "LKA",
    "Sweden": "SWE",
    "Switzerland": "CHE",
    "Thailand": "THA",
    "Türkiye": "TUR",
    "Ukraine": "UKR",
    "United Arab Emirates": "ARE",
    "United Kingdom": "GBR",
    "United States of America": "USA",
    "Uzbekistan": "UZB",
    "Viet Nam": "VNM",
}

ISO3_TO_COUNTRY = {v: k for k, v in COUNTRY_TO_ISO3.items()}

# Short display labels used as scatter annotations for highlighted countries.
SHORT_NAMES = {
    "United States of America": "USA",
    "United Kingdom": "UK",
    "Republic of Korea": "South Korea",
    "Russian Federation": "Russia",
    "United Arab Emirates": "UAE",
    "Viet Nam": "Vietnam",
    "Saudi Arabia": "Saudi Arabia",
    "Czechia": "Czechia",
    "Dominican Republic": "Dominican Rep.",
    "Costa Rica": "Costa Rica",
}


def short_name(country: str) -> str:
    return SHORT_NAMES.get(country, country)
