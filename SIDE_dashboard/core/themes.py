"""The five themes from the notebook, reused as defaults across the dashboard.

These mirror the pair lists in ``skewed_column_scaling_analysis.ipynb``
(cells 9-13).
"""
from __future__ import annotations

HIGHLIGHT_COUNTRIES = ["India", "United States of America", "China", "Brazil", "Germany"]

THEMES = [
    {
        "name": "Infrastructure vs adoption",
        "description": (
            "Does better infrastructure go hand-in-hand with wider digital "
            "adoption? Uses mobile download speed against adoption measures."
        ),
        "pairs": [
            ("Median Mobile Download Speeds (Mbps)", "Number of Internet Users (absolute numbers)"),
            ("Median Mobile Download Speeds (Mbps)", "Number of smartphone users (million)"),
            ("Median Mobile Download Speeds (Mbps)", "Mobile Cellular Subscriptions in millions (absolute numbers)"),
            ("Median Mobile Download Speeds (Mbps)", "Population covered by LTE (Absolute numbers)"),
            ("Median Mobile Download Speeds (Mbps)", "Fixed-broadband Internet traffic (EB)"),
        ],
    },
    {
        "name": "Affordability vs adoption",
        "description": (
            "Are lower device and access costs linked to higher adoption and "
            "better infrastructure performance?"
        ),
        "pairs": [
            ("Price of cheapest smartphone (PPP$)", "Number of smartphone users (million)"),
            ("Price of cheapest smartphone (PPP$)", "Number of Internet Users (absolute numbers)"),
            ("Price of cheapest smartphone (PPP$)", "Median Mobile Download Speeds (Mbps)"),
            ("Price of mobile data and voice basket (HC) (PPP)", "Number of smartphone users (million)"),
            ("Price of mobile data and voice basket (HC) (PPP)", "Median Mobile Download Speeds (Mbps)"),
        ],
    },
    {
        "name": "Digital economy activity",
        "description": (
            "Does digital-payment adoption track other consumer-facing digital "
            "activity such as e-commerce and app spend?"
        ),
        "pairs": [
            ("Users of Digital Payments (in millions)", "Value of digital payment transactions (millions of dollars)"),
            ("Users of Digital Payments (in millions)", "Number of e-commerce users"),
            ("Users of Digital Payments (in millions)", "Number of users of digital food delivery platforms (millions)"),
            ("Users of Digital Payments (in millions)", "Consumer Spend on Mobile Apps (millions USD)"),
        ],
    },
    {
        "name": "AI ecosystem",
        "description": (
            "Is AI adoption more closely linked to investment, talent, compute "
            "capacity, or research output?"
        ),
        "pairs": [
            ("Number of AI users", "Total AI Private Investment in Millions"),
            ("Number of AI users", "AI Talent Pillar Score"),
            ("Number of AI users", "Compute Capacity (Rmax) in Millions"),
            ("Number of AI users", "Open Data Score"),
            ("Number of AI users", "Patents filed (2000-2024) in Information/Communication Technologies for Electromobility"),
        ],
    },
    {
        "name": "Startups & innovation",
        "description": (
            "Are start-up proliferation and unicorn valuations linked to "
            "broader digital-sector capital and market depth?"
        ),
        "pairs": [
            ("Number of Start-ups", "VC investments in AI and environmental sustainability by country (USD million)"),
            ("Number of Start-ups", "ICT Services Export (million USD)"),
            ("Number of Start-ups", "IT market Capitalisation in USD"),
            ("Valuation of Unicorns (Millions of USD)", "VC investments in AI and environmental sustainability by country (USD million)"),
            ("Valuation of Unicorns (Millions of USD)", "ICT Services Export (million USD)"),
            ("Valuation of Unicorns (Millions of USD)", "IT market Capitalisation in USD"),
        ],
    },
]


def get_theme(name: str) -> dict:
    for theme in THEMES:
        if theme["name"] == name:
            return theme
    raise KeyError(name)
