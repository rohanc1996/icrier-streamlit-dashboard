"""SIDE Dashboard — interactive companion to the 2026 dataset.

Run from the repository root:

    streamlit run SIDE_dashboard/dashboard.py
"""
from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="SIDE Dashboard",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)


from components import ui  # noqa: E402
from core import scaling  # noqa: E402
from core.loader import DATA_SOURCES, load_app_data  # noqa: E402
from views import (  # noqa: E402
    chips_explorer,
    country_explorer,
    framework_editor,
    scaling_comparator,
)

PAGES = {
    "🏆 CHIPS Index Explorer": chips_explorer,
    "🌍 Country Explorer": country_explorer,
    "⚖️ Scaling Comparator": scaling_comparator,
    "🎛️ Create Your Own CHIPS Framework": framework_editor,
}

# Session/widget keys owned by the pages.  They are reset to their defaults when
# the base dataset changes, because country/indicator lists, scores and the
# editor's spec all depend on the active dataset.
_PAGE_STATE_PREFIXES = ("fw_", "ch_", "ce_", "sc_", "corr_", "oo_")
_PAGE_STATE_KEYS = {
    "chips_map", "chips_race", "world_map", "selected_country",
    "_chips_country_list", "_ce_country_list",
}


def _reset_page_state() -> None:
    """Clear page-level selections so they re-seed from the active dataset."""
    for k in list(st.session_state.keys()):
        if k == "data_source":
            continue
        if any(k.startswith(p) for p in _PAGE_STATE_PREFIXES) or k in _PAGE_STATE_KEYS:
            st.session_state.pop(k, None)


def main() -> None:
    # Compact topbar shown on every tab: title + dataset tagline on one row.
    title_col, tagline_col = st.columns([3, 1], vertical_alignment="center")
    with title_col:
        st.markdown("## 🌐 SIDE Dashboard")
    with tagline_col:
        st.markdown(
            "Interactive companion to the SIDE 2026 dataset. 71 countries, 60+ indicators."
        )
    st.divider()

    with st.sidebar:
        choice = st.radio("Navigate", list(PAGES.keys()), key="nav", label_visibility="collapsed")
        st.divider()

        # Base dataset selector (defaults to the first source: Relative).
        base_labels = list(DATA_SOURCES.keys())
        if "data_source" in st.session_state and st.session_state["data_source"] not in DATA_SOURCES:
            del st.session_state["data_source"]
        data_source = st.radio(
            "Base scores",
            base_labels,
            index=0,
            key="data_source",
            horizontal=True,
            help="Which dataset feeds the scores. Relative values are per-GNI, "
                 "per-capita or % measures — better for cross-country comparison; "
                 "Absolute values are the raw totals.",
        )
        if st.session_state.get("_prev_data_source", data_source) != data_source:
            _reset_page_state()
            st.caption("ℹ️ Switched base dataset — all selections reset to their defaults.")
        st.session_state["_prev_data_source"] = data_source
        st.divider()

        if "scaling_method" in st.session_state and st.session_state["scaling_method"] not in scaling.ALL_METHODS:
            del st.session_state["scaling_method"]
        st.caption(
            "**Scoring method** — how raw values become 0–1 scores. Used by the "
            "single-score pages; the Scaling Comparator always shows both "
            "methods."
        )
        st.radio(
            "Scoring method",
            list(scaling.ALL_METHODS),
            format_func=lambda m: scaling.METHOD_SHORT_LABELS[m],
            index=scaling.ALL_METHODS.index(scaling.METHOD_Z),
            key="scaling_method",
            horizontal=True,
            help="Scores are inverted where a low raw value is better, so 1.0 "
                 "always means 'best'.",
        )
        st.caption(
            "Full-range min-max · z-score (standardized, default)."
        )

    data = load_app_data(DATA_SOURCES[data_source])
    method = st.session_state.get("scaling_method", scaling.METHOD_Z)
    PAGES[choice].render(data, method=method,
                         data_file=DATA_SOURCES[data_source])


if __name__ == "__main__":
    main()
