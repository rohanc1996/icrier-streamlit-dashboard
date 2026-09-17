"""Year-agnostic column-name normalisation.

Indicator headers in the SIDE sheets embed edition-specific tokens — patent
year ranges (``(2000-2024)``), quarter ranges (``(2022 Q3 - 2025 Q3)``) and
stray punctuation.  A later year's file therefore carries the *same* indicator
under a slightly different string, which would defeat the exact-match lookup
tables the loader and CHIPS hierarchy rely on.

``canonical_key`` reduces a header to a stable key by lower-casing, replacing
every run of non-alphanumeric characters with a space and dropping the
embedded year / quarter tokens.  It is deliberately conservative: 2-digit
numbers (``16-64``), amounts (``1000``) and descriptive text are preserved, so
distinct indicators never collapse into one key.
"""
from __future__ import annotations

import re

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
_QUARTER_RE = re.compile(r"\bq[1-4]\b")


def canonical_key(name: object) -> str:
    """Return a year-agnostic matching key for a column header.

    >>> canonical_key("Patents filed (2000-2024) in Smart Grids")
    'patents filed in smart grids'
    >>> canonical_key("Total number of email leaks (Quarterly average) (2022 Q3 - 2025 Q3)")
    'total number of email leaks quarterly average'
    """
    text = _NON_ALNUM_RE.sub(" ", str(name).lower())
    text = _YEAR_RE.sub(" ", text)
    text = _QUARTER_RE.sub(" ", text)
    return " ".join(text.split())
