"""Small UI helpers to keep the views readable and beginner-friendly."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from core import scaling


def page_header(title: str, subtitle: str) -> None:
    st.title(title)
    st.caption(subtitle)
    st.divider()


def explainer(emoji: str, body: str) -> None:
    """A plain-language info box shown at the top of each page."""
    st.info(f"{emoji} {body}")


def fmt(v) -> str:
    """Format a number for a general audience (commas, sensible decimals)."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    if isinstance(v, (int, np.integer)):
        return f"{int(v):,}"
    v = float(v)
    if abs(v) >= 1000:
        return f"{v:,.0f}"
    if abs(v) >= 100:
        return f"{v:,.1f}"
    return f"{v:.2f}"


def indicator_selectbox(data, label: str, key: str, default=None, categories=None, group_categories: bool = False):
    """Selectbox over indicators showing friendly names (returns the column name).

    With ``group_categories=True`` the options are sorted by category and the
    labels are prefixed with the category, so all indicators of a category form
    a contiguous, clearly labelled block in one dropdown.
    """
    options = list(data.indicators)
    if categories:
        allowed = set(categories)
        options = [c for c in options if data.categories.get(c, "Other") in allowed]
    if not options:
        st.warning("No indicators match that category filter. Pick at least one category.")
        return None

    if group_categories:
        options = sorted(options, key=lambda c: (data.categories.get(c, "Other"), c))

        def fmt_label(col: str) -> str:
            return f"{data.categories.get(col, 'Other')} — {data.friendly_names.get(col, col)}"
    else:
        def fmt_label(col: str) -> str:
            return f"{data.friendly_names.get(col, col)}  ·  {data.categories.get(col, 'Other')}"

    if default is None or default not in options:
        default = options[0]
    return st.selectbox(
        label,
        options=options,
        format_func=fmt_label,
        index=options.index(default),
        key=key,
    )


def show_table(df: pd.DataFrame, column_config=None, height: int | None = None) -> None:
    """Consistent, index-free dataframe widget."""
    kwargs: dict = {"width": "stretch", "hide_index": True, "column_config": column_config}
    if height is not None:
        kwargs["height"] = height
    st.dataframe(df, **kwargs)


# Reusable column configuration for the "ranked table" style views.
def rank_column_config(data) -> dict:
    cfg = {
        "rank": st.column_config.NumberColumn("Rank", format="%d"),
        "value": st.column_config.NumberColumn("Value", format="%.3g"),
        "percentile": st.column_config.NumberColumn("Percentile", format="%.0f"),
        "max_swing": st.column_config.NumberColumn("Max swing", format="%d"),
        "n": st.column_config.NumberColumn("Countries", format="%d"),
        "pearson": st.column_config.NumberColumn("Pearson", format="%.2f"),
        "spearman": st.column_config.NumberColumn("Spearman", format="%.2f"),
    }
    # Score and rank columns are generated from the scaling methods so that a
    # new method automatically gets labelled columns here.
    for method in scaling.ALL_METHODS:
        label = scaling.METHOD_SHORT_LABELS[method]
        cfg[method] = st.column_config.NumberColumn(f"{label} score", format="%.2f")
        cfg[f"rank_{method}"] = st.column_config.NumberColumn(f"Rank · {label}", format="%d")
    return cfg
