---
name: SIDE data conventions
description: Load, inspect and write SIDE CSV data correctly — canonical reader, country normalisation, frozen editions, and the 2027 additive rule. Use before any pandas work on data/ or when adding an indicator.
---

# SIDE data conventions

Apply these whenever you read or write a dataset in this repo.

## Read through the canonical pipeline

Do not `pd.read_csv()` raw and start using columns. The loader normalises
whitespace, column names, duplicate headers, numeric parsing and country names:

```python
import sys
sys.path.insert(0, "SIDE_dashboard")
from core.loader import (
    load_app_data, shrink_whitespace, normalize_column_name,
    _dedupe_columns, parse_numeric,
)
```

For a quick look at an edition:

```python
data = load_app_data("data/SIDE 2027 - Absolute.csv")
print(len(data.country_list), "countries")
print(data.numeric_df.shape)
```

Notes:

- `load_app_data` is the same path the dashboard uses. If it fails, the dashboard
  fails; fix the loader, not a private copy.
- `data.numeric_df` has `Country` first, then one column per indicator with
  numeric values (NaN where missing).
- `data.higher_is_better[column]` tells you whether the raw value is inverted.
- `data.friendly_names` and `data.categories` are the display labels.

## Known traps

- **Header drift between editions.** Use `core/columns.py` and the edition maps
  in `core/loader.py`; never hard-code a year range into a header.
- **Country name variants.** Resolve through `components/country_names.py` and
  the per-edition `EDITION_COUNTRY_NAMES` map. Do not `.str.replace()` by hand.
- **Summary rows** like `Coefficient of variation` and pandas `Unnamed: N`
  columns are not data.
- **Units change between editions** (e.g. billions vs millions of USD). Check
  `EDITION_ADJUSTMENTS` before comparing raw values across years.
- **Rounding:** indicator scores round to 1 decimal on a 0–100 scale, aggregates
  stay full precision, the final CHIPS score rounds to 2 decimals. Preserve it.

## Frozen years

`data/SIDE 2024/2025/2026 - *.csv` are the published record. Any 2027 change must
be additive. `scripts/tests/frozen_years.py` checks this; run it after data or
scoring edits.

## Writing a new indicator

1. Source file goes in `data/2027 individual indicators/`.
2. Cleaned column goes in the matching `data/2027 pillar-wise/SIDE 2027 Absolute - <Pillar>.csv`
   **and** `data/SIDE 2027 - Absolute.csv` — both, in sync.
3. Framework entry goes in `core/chips_hierarchy.py` under the 2027-only
   extension, with a weight that keeps each level at 100%.
4. Verify with `data.higher_is_better`, coverage counts, and the regression test.

Prefer `/indicator <name>` for the full workflow.
