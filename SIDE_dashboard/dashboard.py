"""SIDE Dashboard — interactive companion to the SIDE digital-economy dataset.

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
from core.loader import (  # noqa: E402
    available_years,
    default_year,
    load_app_data,
    sources_for,
)
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
# the year or base dataset changes, because country/indicator lists, scores and
# the editor's spec all depend on the active dataset.
_PAGE_STATE_PREFIXES = ("fw_", "ch_", "ce_", "sc_", "corr_", "oo_")
_PAGE_STATE_KEYS = {
    "chips_map", "chips_race", "world_map", "selected_country",
    "_chips_country_list", "_ce_country_list",
}
# Which in-page section is open is dataset-independent, so keep it across a
# dataset switch.
_PAGE_STATE_KEEP = {"ch_section", "ce_section", "sc_section"}

# One global stylesheet: compact hover-"?" explainer boxes.
_CSS = """
<style>
/* Compact info boxes whose detail lives in a hover "?" tooltip. */
[class*="st-key-explainer_"] {
    background: rgba(28, 131, 225, 0.10);
    border: 1px solid rgba(28, 131, 225, 0.35);
    border-radius: 0.5rem;
    padding: 0.5rem 0.75rem;
    margin-bottom: 0.5rem;
}
</style>
"""


def _reset_page_state() -> None:
    """Clear page-level selections so they re-seed from the active dataset."""
    for k in list(st.session_state.keys()):
        if k == "data_source" or k in _PAGE_STATE_KEEP:
            continue
        if any(k.startswith(p) for p in _PAGE_STATE_PREFIXES) or k in _PAGE_STATE_KEYS:
            st.session_state.pop(k, None)


def _sidebar() -> tuple[str, str, str, str]:
    """Left sidebar: header, tab selector and settings.

    Returns ``(choice, year, base, method)``.
    """
    with st.sidebar:
        st.markdown("## 🌐 SIDE Dashboard")
        st.caption(
            "Interactive companion to ICRIER's SIDE digital-economy dataset — "
            "switch years and base scores below."
        )
        st.divider()

        choice = st.radio(
            "Navigate", list(PAGES), key="nav", label_visibility="collapsed"
        )

        st.divider()

        years = available_years()
        if not years:
            st.error("No SIDE datasets found in the `data/` folder.")
            st.stop()
        # A year can disappear if its files are removed; drop the stale widget
        # value so the selectbox re-seeds cleanly.
        if st.session_state.get("year") not in years:
            st.session_state.pop("year", None)
        year = st.selectbox(
            "Year", years, index=years.index(default_year()), key="year"
        )
        sources = sources_for(year)

        base_labels = list(sources)
        if "data_source" in st.session_state and st.session_state["data_source"] not in sources:
            del st.session_state["data_source"]
        base = st.radio(
            "Base scores",
            base_labels,
            index=0,
            key="data_source",
            horizontal=True,
            help="Which dataset feeds the scores. Relative values are per-GNI, "
                 "per-capita or % measures — better for cross-country comparison; "
                 "Absolute values are the raw totals.",
        )
        st.divider()

        if "scaling_method" in st.session_state and st.session_state["scaling_method"] not in scaling.ALL_METHODS:
            del st.session_state["scaling_method"]
        st.caption(
            "**Scoring method** — how raw values become 0–1 scores. Used by the "
            "single-score pages; the Scaling Comparator always shows both "
            "methods."
        )
        method = st.radio(
            "Scoring method",
            list(scaling.ALL_METHODS),
            format_func=lambda m: scaling.METHOD_SHORT_LABELS[m],
            index=scaling.ALL_METHODS.index(scaling.METHOD_Z),
            key="scaling_method",
            horizontal=True,
            help="Scores are inverted where a low raw value is better, so 1.0 "
                 "always means 'best'.",
        )
        st.caption("Full-range min-max · z-score (standardized, default).")

        selection = (year, base)
        if st.session_state.get("_prev_selection") != selection:
            _reset_page_state()
            st.caption("ℹ️ Switched dataset — all selections reset to their defaults.")
        st.session_state["_prev_selection"] = selection
    return choice, year, base, method


def main() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

    choice, year, base, method = _sidebar()

    sources = sources_for(year)
    data = load_app_data(sources[base])
    PAGES[choice].render(
        data, method=method, data_file=sources[base], sources=sources
    )


if __name__ == "__main__":
    main()
