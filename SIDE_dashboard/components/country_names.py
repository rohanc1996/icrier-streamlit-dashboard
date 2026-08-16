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

# ISO-3 -> ISO-2 (lowercase), used to derive regional-indicator flag emoji
# (e.g. `in` -> 🇮🇳). Plotly renders these as text markers with no image
# downloads and no extra dependencies.
ISO3_TO_ISO2 = {
    "DZA": "dz", "ARG": "ar", "AUS": "au", "AUT": "at", "BGD": "bd",
    "BEL": "be", "BRA": "br", "BGR": "bg", "CAN": "ca", "CHL": "cl",
    "CHN": "cn", "COL": "co", "CRI": "cr", "HRV": "hr", "CZE": "cz",
    "DNK": "dk", "DOM": "do", "ECU": "ec", "EGY": "eg", "ETH": "et",
    "FIN": "fi", "FRA": "fr", "DEU": "de", "GHA": "gh", "GRC": "gr",
    "GTM": "gt", "HUN": "hu", "IND": "in", "IDN": "id", "IRQ": "iq",
    "IRL": "ie", "ISR": "il", "ITA": "it", "JPN": "jp", "KAZ": "kz",
    "KEN": "ke", "KWT": "kw", "MYS": "my", "MEX": "mx", "MAR": "ma",
    "NLD": "nl", "NZL": "nz", "NGA": "ng", "NOR": "no", "PAK": "pk",
    "PER": "pe", "PHL": "ph", "POL": "pl", "PRT": "pt", "QAT": "qa",
    "KOR": "kr", "ROU": "ro", "RUS": "ru", "RWA": "rw", "SAU": "sa",
    "SRB": "rs", "SGP": "sg", "SVK": "sk", "ZAF": "za", "ESP": "es",
    "LKA": "lk", "SWE": "se", "CHE": "ch", "THA": "th", "TUR": "tr",
    "UKR": "ua", "ARE": "ae", "GBR": "gb", "USA": "us", "UZB": "uz",
    "VNM": "vn",
}

COUNTRY_TO_ISO2 = {country: ISO3_TO_ISO2[iso3] for country, iso3 in COUNTRY_TO_ISO3.items()}

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


def flag_emoji(country: str) -> str:
    """Country flag as regional-indicator emoji (e.g. ``🇮🇳`` for India).

    Derived from the ISO-2 code: each letter becomes a regional indicator
    symbol (U+1F1E6–U+1F1FF). Renders as a real flag on macOS, iOS, Android
    and most desktop browsers; Windows Chrome/Edge fall back to two letters.
    Returns an empty string for unknown countries.
    """
    iso2 = COUNTRY_TO_ISO2.get(country)
    if not iso2:
        return ""
    return "".join(chr(0x1F1E6 + ord(ch) - ord("a")) for ch in iso2)
