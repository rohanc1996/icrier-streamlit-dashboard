"""CHIPS composite index — hierarchy, weights and column mappings.

This module is the single source of truth for the CHIPS indicator framework:

    Pillar → Sub-pillar → Indicator (with weight within its group)

- Weights are given as decimals within a group (they are normalised to sum to
  1).  A ``None`` weight means "equal weight" (the default everywhere).
- The INNOVATE → AI sub-pillar is **not flat**: it is made of three internal
  groups (investment pair, AI commercial, research pair) that follow their own
  missingness rules (see ``core/chips.py``).
- Indicator *names* here are the friendly names from the CHIPS spec sheet.
  ``COLUMN_ALIASES`` maps them to the exact normalised dataset column headers;
  ``resolve_hierarchy`` turns the declarative spec into ready-to-use dataclasses
  and reports any name that could not be matched to a column.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Friendly CHIPS spec names → exact (normalised) dataset column headers.
# Only the names that differ from the headers need an entry; everything else is
# resolved by exact match.
# ---------------------------------------------------------------------------
COLUMN_ALIASES = {
    # CONNECT · Affordability
    "Price of mobile data and voice basket (HC) PPP": "Price of mobile data and voice basket (HC) (PPP)",
    "Price of mobile data and voice basket (LC) PPP": "Price of mobile data and voice basket (LC) (PPP)",
    "Price of cheapest smartphone in USD PPP": "Price of cheapest smartphone (PPP$)",
    "Fixed (broadband) internet price, USD PPP": "Price of fixed broadband internet (PPP)",
    # CONNECT · Quality
    "Median Fixed Broadband Download Speeds (Mbps)": "Median Fixed Broadband Download Speed (Mbps)",
    # CONNECT · Access
    "Number of internet users": "Number of Internet Users (absolute numbers)",
    "Mobile cellular subscriptions": "Mobile Cellular Subscriptions in millions (absolute numbers)",
    "Population covered by LTE": "Population covered by LTE (Absolute numbers)",
    "Number of smart phone users": "Number of smartphone users (million)",
    # CONNECT · AI
    "% of population that are using AI": "Number of AI users",
    "Compute capacity (Govt readiness)": "Compute capacity",
    "AI Infrastructure (Tortoise)": "AI Infrastructure",
    # HARNESS · Apps and platform
    "Number (16-64 years) using social media for work related activities": "Number of internet users (16-64 years) using social media for work related activities",
    "Number of users of digital food delivery platforms": "Number of users of digital food delivery platforms (millions)",
    "E-commerce users": "Number of e-commerce users",
    "Video On Demand Users": "Number of video on demand users",
    # HARNESS · Data Intensity
    "Total monthly fixed broadband internet traffic (TB)": "Fixed-broadband Internet traffic (EB)",
    "Total monthly mobile broadband internet traffic (TB)": "Mobile broadband internet traffic (EB)",
    # HARNESS · Fintech
    "Value of digital transactions in billion dollars": "Value of digital payment transactions (millions of dollars)",
    # HARNESS · Real Economy
    "Digitally delivered services (exports)": "Total digitally delivered services (million USD)",
    "ICT sector employment": "Employment: ICT sector (thousands)",
    # HARNESS · AI
    "Open Data score": "Open Data Score",
    "Development: Open Source models score (tortoise)": "Development: Open Source models score",
    "AI Skilled population (vibrancy)": "Relative AI Skill Penetration",
    "AI Talent Pillar (tortoise)": "AI Talent Pillar Score",
    # INNOVATE · Investments and Startups
    "No. of start-ups": "Number of Start-ups",
    "Total Unicorn Valuation in Bn $": "Valuation of Unicorns (Millions of USD)",
    "Total funding till date of Startups": "Total funding till date of Startups having their Head Quarters or atleast one office location in India (Millions of USD)",
    # INNOVATE · Other Emerging Technology
    "Consumer IOT Revenues in MN USD": "Consumer and Industrial IoT revenues (millions of USD)",
    "AR/VR Revenues in mn $": "AR/ VR revenues (millions of USD)",
    "Metaverse Revenues in bn $": "Metaverse revenue (millions of USD)",
    "DeFi Revenue in mn $": "DeFi revenue (millions of USD)",
    # INNOVATE · AI
    "Total AI Private Investment as a share of GDP": "Total AI Private Investment in Millions",
    "Newly Funded AI Companies per LLC company": "Newly Funded AI Companies",
    # PROTECT · Preparedness
    "Cybersecurity Revenue in billion USD": "Cybersecurity revenue (Mn USD)",
    # PROTECT · Risk of Attack
    "Total number of email leaks": "Total number of email leaks (Quarterly average) (2022 Q3 - 2025 Q3)",
    # SUSTAINABILITY
    "E-waste generated (kg per capita)": "E-waste generated (million kg)",
    "Share of energy startups that are digital": "Number of energy and digital startups",
    "Patents filed (2000-2023) in Smart Grids as a % of enabling tech patents": "Patents filed (2000-2024) in Smart Grids",
    "Renewable energy share of electricity production (%)": "Net electricity production from Renewables (Hydro, Geo, Solar, Wind, Other) (GWh)",
    "Average Annual Loss by Climate (USD million)": "AAL by Climate (Million USD) for the Telecom Sector- Existing Climate",
}


# ---------------------------------------------------------------------------
# The declarative hierarchy.  Each indicator is a ``(name, weight)`` pair;
# ``weight`` may be None to mean "equal within the group".
# ---------------------------------------------------------------------------
HIERARCHY = [
    {
        "name": "CONNECT",
        "sub_pillars": [
            {
                "name": "Affordability",
                "indicators": [
                    ("Price of mobile data and voice basket (HC) PPP", 0.25),
                    ("Price of mobile data and voice basket (LC) PPP", 0.25),
                    ("Price of cheapest smartphone in USD PPP", 0.25),
                    ("Fixed (broadband) internet price, USD PPP", 0.25),
                ],
            },
            {
                "name": "Quality",
                "indicators": [
                    ("Median Mobile Download Speeds (Mbps)", 0.5),
                    ("Median Fixed Broadband Download Speeds (Mbps)", 0.5),
                ],
            },
            {
                "name": "Access",
                "indicators": [
                    ("Number of internet users", 0.25),
                    ("Mobile cellular subscriptions", 0.25),
                    ("Population covered by LTE", 0.25),
                    ("Number of smart phone users", 0.25),
                ],
            },
            {
                "name": "AI",
                "indicators": [
                    ("% of population that are using AI", 0.33),
                    ("Compute capacity (Govt readiness)", 0.33),
                    ("AI Infrastructure (Tortoise)", 0.33),
                ],
            },
        ],
    },
    {
        "name": "HARNESS",
        "sub_pillars": [
            {
                "name": "Apps and platform",
                "indicators": [
                    ("Number (16-64 years) using social media for work related activities", 0.17),
                    ("Number of users of digital food delivery platforms", 0.17),
                    ("Number of users of digital health applications", 0.17),
                    ("E-commerce users", 0.17),
                    ("Consumer Spend on Mobile Apps (millions USD)", 0.17),
                    ("Video On Demand Users", 0.17),
                ],
            },
            {
                "name": "Data Intensity",
                "indicators": [
                    ("Total monthly fixed broadband internet traffic (TB)", 0.5),
                    ("Total monthly mobile broadband internet traffic (TB)", 0.5),
                ],
            },
            {
                "name": "Fintech",
                "indicators": [
                    ("Value of digital transactions in billion dollars", 0.5),
                    ("Users of Digital Payments (in millions)", 0.5),
                ],
            },
            {
                "name": "Real Economy",
                "indicators": [
                    ("Digitally delivered services (exports)", 0.5),
                    ("ICT sector employment", 0.5),
                ],
            },
            {
                "name": "AI",
                "indicators": [
                    ("Open Data score", 0.25),
                    ("Development: Open Source models score (tortoise)", 0.25),
                    ("AI Skilled population (vibrancy)", 0.25),
                    ("AI Talent Pillar (tortoise)", 0.25),
                ],
            },
        ],
    },
    {
        "name": "INNOVATE",
        "sub_pillars": [
            {
                "name": "Investments and Startups",
                "indicators": [
                    ("No. of start-ups", 0.33),
                    ("Total Unicorn Valuation in Bn $", 0.33),
                    ("Total funding till date of Startups", 0.33),
                ],
            },
            {
                "name": "Other Emerging Technology",
                "indicators": [
                    ("Consumer IOT Revenues in MN USD", 0.14),
                    ("AR/VR Revenues in mn $", 0.14),
                    ("Metaverse Revenues in bn $", 0.14),
                    ("DeFi Revenue in mn $", 0.14),
                    ("Robotics revenue (millions of USD)", 0.14),
                    ("Drones revenue (millions of USD)", 0.14),
                    ("Crypto Index Score", 0.14),
                ],
            },
            {
                # AI 1 + AI 2 of the spec sheet combined into one sub-pillar
                # with three internal groups (see rules 7-8 in the spec):
                #   1. investment pair — private investment + newly funded AI companies
                #   2. AI commercial   — single indicator
                #   3. research pair   — AI innovation/research + AI R&D score
                "name": "AI",
                "is_ai": True,
                "internal_groups": [
                    {
                        "name": "Investment",
                        "weight": 1 / 3,
                        "indicators": [
                            ("Total AI Private Investment as a share of GDP", 0.5),
                            ("Newly Funded AI Companies per LLC company", 0.5),
                        ],
                    },
                    {
                        "name": "AI commercial",
                        "weight": 1 / 3,
                        "indicators": [
                            ("AI commercial", 1.0),
                        ],
                    },
                    {
                        "name": "Research",
                        "weight": 1 / 3,
                        "indicators": [
                            ("AI Innovation - Research", 0.5),
                            ("AI Research and Development- score", 0.5),
                        ],
                    },
                ],
            },
        ],
    },
    {
        "name": "PROTECT",
        "sub_pillars": [
            {
                "name": "Preparedness",
                "indicators": [
                    ("Cybersecurity Revenue in billion USD", 0.5),
                    ("Number of Secure servers", 0.5),
                ],
            },
            {
                "name": "Risk of Attack",
                "indicators": [
                    ("Ransomware attacks 30 day average", 0.33),
                    ("Ransomware victims", 0.33),
                    ("Total number of email leaks", 0.33),
                ],
            },
            {
                "name": "AI",
                "indicators": [
                    ("Safety and security", 0.33),
                    ("Responsible AI - Conference Submissions on RAI Topics (Total)", 0.33),
                    ("Public trust score", 0.33),
                ],
            },
        ],
    },
    {
        # Sustainability has no sub-pillars; the pillar is a single flat group.
        "name": "SUSTAINABILITY",
        "sub_pillars": [
            {
                "name": "Sustainability",
                "indicators": [
                    ("E-waste generated (kg per capita)", 0.17),
                    ("Share of energy startups that are digital", 0.17),
                    ("VC investments in AI and environmental sustainability by country (USD million)", 0.17),
                    ("Patents filed (2000-2023) in Smart Grids as a % of enabling tech patents", 0.17),
                    ("Renewable energy share of electricity production (%)", 0.17),
                    ("Average Annual Loss by Climate (USD million)", 0.17),
                ],
            },
        ],
    },
]



# ---------------------------------------------------------------------------
# Resolved structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Leaf:
    """One indicator.  ``column`` is None when the spec name could not be
    matched to a dataset column (such an indicator counts as missing for every
    country and is reported by ``resolve_hierarchy``)."""

    name: str
    column: str | None
    weight: float


@dataclass(frozen=True)
class Group:
    """One internal group inside the non-flat INNOVATE → AI sub-pillar."""

    name: str
    weight: float
    leaves: list[Leaf]


@dataclass(frozen=True)
class SubPillar:
    """A sub-pillar.  Flat sub-pillars use ``leaves``; the AI sub-pillar uses
    ``groups`` (and has ``is_ai=True``)."""

    name: str
    weight: float
    leaves: list[Leaf] = field(default_factory=list)
    groups: list[Group] = field(default_factory=list)
    is_ai: bool = False


@dataclass(frozen=True)
class Pillar:
    name: str
    weight: float
    sub_pillars: list[SubPillar]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _equal_weights(n: int) -> list[float]:
    return [1.0 / n] * n if n else []


def _normalise(given: list[float | None]) -> list[float]:
    """Equal weights when none are given; otherwise normalise to sum to 1."""
    if not given:
        return []
    if all(w is None for w in given):
        return _equal_weights(len(given))
    weights = [1.0 if w is None else float(w) for w in given]
    total = sum(weights)
    return [w / total for w in weights]


def _resolve_column(name: str, columns: set[str]) -> str | None:
    """Exact match first, then the alias table, then a case-insensitive scan."""
    if name in columns:
        return name
    alias = COLUMN_ALIASES.get(name)
    if alias is not None and alias in columns:
        return alias
    lowered = {c.lower(): c for c in columns}
    if name.lower() in lowered:
        return lowered[name.lower()]
    alias_lower = (COLUMN_ALIASES.get(name) or "").lower()
    if alias_lower in lowered:
        return lowered[alias_lower]
    return None



def resolve_hierarchy(columns, spec: list | None = None) -> tuple[list[Pillar], list[str]]:
    """Build the resolved hierarchy against a set of dataset column headers.

    Returns ``(pillars, unresolved)`` where ``unresolved`` lists any spec
    indicator names that could not be matched to a column.  Weights are
    normalised so every group sums to 1 and equal-weight is applied wherever no
    weight was specified.  ``spec`` defaults to the module-level ``HIERARCHY``
    and only exists so tests can exercise the resolver with malformed specs.
    """
    spec = HIERARCHY if spec is None else spec
    columns = {str(c) for c in columns}
    pillars: list[Pillar] = []
    unresolved: list[str] = []
    seen_names: set[str] = set()

    for pillar_spec in spec:
        sp_specs = pillar_spec["sub_pillars"]
        sps: list[SubPillar] = []
        for sp in sp_specs:
            if sp.get("internal_groups"):
                groups = []
                for g in sp["internal_groups"]:
                    leaves = []
                    for name, w in g["indicators"]:
                        _register_leaf(name, seen_names)
                        column = _resolve_column(name, columns)
                        if column is None:
                            unresolved.append(name)
                        leaves.append(Leaf(name, column, 1.0 if w is None else float(w)))
                    groups.append(Group(g["name"], float(g["weight"]), leaves))
                sps.append(SubPillar(sp["name"], sp.get("weight"), groups=groups,
                                     is_ai=sp.get("is_ai", False)))
            else:
                leaves = []
                for name, w in sp["indicators"]:
                    _register_leaf(name, seen_names)
                    column = _resolve_column(name, columns)
                    if column is None:
                        unresolved.append(name)
                    leaves.append(Leaf(name, column, 1.0 if w is None else float(w)))
                sps.append(SubPillar(sp["name"], sp.get("weight"), leaves=leaves))
        pillars.append(Pillar(pillar_spec["name"], pillar_spec.get("weight"), sps))

    _normalise_pillars(pillars)
    return pillars, unresolved


def _register_leaf(name: str, seen: set[str]) -> None:
    """Leaf names are used as DataFrame/treemap keys, so they must be unique."""
    if name in seen:
        raise ValueError(f"Duplicate indicator name in CHIPS hierarchy: {name!r}")
    seen.add(name)


def _normalise_pillars(pillars: list[Pillar]) -> None:
    """Fill in equal weights wherever None and renormalise every group."""
    pillar_weights = _normalise([p.weight for p in pillars])
    for p, w in zip(pillars, pillar_weights):
        object.__setattr__(p, "weight", w)  # frozen dataclass
        sp_weights = _normalise([sp.weight for sp in p.sub_pillars])
        for sp, sw in zip(p.sub_pillars, sp_weights):
            object.__setattr__(sp, "weight", sw)
            if sp.groups:
                for g in sp.groups:
                    leaves_weights = _normalise([leaf.weight for leaf in g.leaves])
                    for leaf, lw in zip(g.leaves, leaves_weights):
                        object.__setattr__(leaf, "weight", lw)
            else:
                leaves_weights = _normalise([leaf.weight for leaf in sp.leaves])
                for leaf, lw in zip(sp.leaves, leaves_weights):
                    object.__setattr__(leaf, "weight", lw)


def all_leaves(pillars: list[Pillar]) -> list[Leaf]:
    """Every leaf indicator in the hierarchy, in spec order."""
    out: list[Leaf] = []
    for p in pillars:
        for sp in p.sub_pillars:
            if sp.groups:
                for g in sp.groups:
                    out.extend(g.leaves)
            else:
                out.extend(sp.leaves)
    return out


def sub_pillar_keys(pillars: list[Pillar]) -> list[str]:
    """'PILLAR · SUB-PILLAR' keys used by the what-if overrides and heatmaps."""
    return [f"{p.name} · {sp.name}" for p in pillars for sp in p.sub_pillars]


def hierarchy_table(pillars: list[Pillar]):
    """One row per indicator: pillar, sub-pillar, group, weights, column."""
    import pandas as pd

    rows = []
    for p in pillars:
        for sp in p.sub_pillars:
            if sp.groups:
                for g in sp.groups:
                    for leaf in g.leaves:
                        rows.append({
                            "Pillar": p.name,
                            "Sub-pillar": sp.name,
                            "Internal group": g.name,
                            "Indicator": leaf.name,
                            "Dataset column": leaf.column or "—",
                            "Weight in group": round(leaf.weight, 4),
                            "Group weight": round(g.weight, 4),
                        })
            else:
                for leaf in sp.leaves:
                    rows.append({
                        "Pillar": p.name,
                        "Sub-pillar": sp.name,
                        "Internal group": "",
                        "Indicator": leaf.name,
                        "Dataset column": leaf.column or "—",
                        "Weight in group": round(leaf.weight, 4),
                        "Group weight": None,
                    })
    return pd.DataFrame(rows)
