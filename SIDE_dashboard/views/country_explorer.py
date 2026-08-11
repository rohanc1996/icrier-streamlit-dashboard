"""View 1: Interactive country explorer (map + profile + comparison)."""
from __future__ import annotations

import streamlit as st

from components import charts, country_names, ui
from core import rankings
from core.themes import HIGHLIGHT_COUNTRIES

DEFAULT_INDICATOR = "Median Mobile Download Speeds (Mbps)"

# Indicators used for headline metrics in the profile panel.
HEADLINE_INDICATORS = [
    "Median Mobile Download Speeds (Mbps)",
    "Number of Internet Users (absolute numbers)",
    "Number of smartphone users (million)",
    "Users of Digital Payments (in millions)",
    "Number of e-commerce users",
    "Total AI Private Investment in Millions",
    "Number of Start-ups",
    "Price of cheapest smartphone (PPP$)",
]

COMPARISON_INDICATORS = [
    "Median Mobile Download Speeds (Mbps)",
    "Price of cheapest smartphone (PPP$)",
    "Number of Internet Users (absolute numbers)",
    "Number of smartphone users (million)",
    "Users of Digital Payments (in millions)",
    "Number of e-commerce users",
    "Number of Start-ups",
    "Total AI Private Investment in Millions",
]


def _clicked_country(selection):
    """Extract the clicked country name from the plotly map selection event."""
    try:
        sel = getattr(selection, "selection", None)
        points = getattr(sel, "points", None)
        if not points:
            return None
        point = points[0]
        custom = getattr(point, "customdata", None)
        if custom is not None and len(custom) and custom[0]:
            return custom[0]
        location = getattr(point, "location", None)
        if location:
            return country_names.ISO3_TO_COUNTRY.get(location)
    except Exception:
        return None
    return None


def _on_country_change() -> None:
    """Keep the map-highlighted country in sync with the rankings selectbox."""
    st.session_state["selected_country"] = st.session_state["ce_country"]


def _on_map_select() -> None:
    """Handle a country click on the world map.

    Streamlit runs callable ``on_select`` handlers *before* the script body, so
    this can set the section radio and the rankings selectbox without tripping
    the "widget already instantiated this run" restriction. The click selection
    of the keyed chart is stored under its key in session state.
    """
    clicked = _clicked_country(st.session_state.get("world_map"))
    if clicked and clicked in st.session_state.get("_ce_country_list", []):
        st.session_state["selected_country"] = clicked
        st.session_state["ce_country"] = clicked
        st.session_state["ce_section"] = "📋 Country rankings"


def render(data) -> None:
    ui.page_header(
        "🌍 Country Explorer",
        "Three views in one place: colour the world map by any indicator, "
        "inspect a single country's rankings, or compare up to five countries "
        "side by side in a spider chart.",
    )
    ui.explainer(
        "🧭",
        "**🗺️ World map** — colour one indicator at a time; click a country to "
        "jump straight to its rankings. **📋 Country rankings** — pick a country "
        "(India by default) for headline metrics and its position on every "
        "indicator. **🕸️ Compare countries** — put 2–5 countries on a spider "
        "chart of capped scores.",
    )

    # India is the default country on first load.
    if "selected_country" not in st.session_state:
        st.session_state["selected_country"] = (
            "India" if "India" in data.country_list else data.country_list[0]
        )
    default_country = "India" if "India" in data.country_list else data.country_list[0]

    # The map-click callback (_on_map_select) runs before the script body and
    # needs the country list to validate the click, so keep it in session state.
    st.session_state["_ce_country_list"] = data.country_list

    # Only one section is visible at a time. A horizontal radio replaces
    # st.tabs because the pinned Streamlit (1.50) has no key/on_change support
    # on tabs, while the radio's key lets _on_map_select switch straight to the
    # rankings section programmatically.
    section = st.radio(
        "Section",
        ["🗺️ World map", "📋 Country rankings", "🕸️ Compare countries"],
        horizontal=True,
        label_visibility="collapsed",
        key="ce_section",
    )

    if section == "🗺️ World map":
        indicator = ui.indicator_selectbox(
            data, "Colour the map by", key="ce_indicator", default=DEFAULT_INDICATOR
        )
        if indicator is None:
            return
        map_fig = charts.choropleth(
            data, indicator, st.session_state.get("selected_country")
        )
        # A callable on_select runs before the script body, so the click can
        # update the section radio and the rankings selectbox (see above).
        st.plotly_chart(
            map_fig, key="world_map", on_select=_on_map_select, selection_mode="points"
        )

    elif section == "📋 Country rankings":
        c1, c2 = st.columns([4, 1], vertical_alignment="center")
        with c1:
            st.selectbox(
                "Search countries",
                data.country_list,
                index=data.country_list.index(default_country),
                key="ce_country",
                on_change=_on_country_change,
            )
        with c2:
            if st.button(
                "↺ Reset to India",
                key="ce_clear",
                width="stretch",
                help="Go back to the default country.",
            ):
                st.session_state["selected_country"] = default_country
                # Deleting the widget key makes the selectbox fall back to its
                # `index` (India) on the next run. A plain assignment is blocked
                # because the selectbox was already instantiated this run.
                del st.session_state["ce_country"]
                st.rerun()
        _profile_panel(data, st.session_state.get("ce_country", default_country))

    else:
        _comparison_panel(data)
def _profile_panel(data, country: str) -> None:
    st.markdown(f"## 📋 Country profile — {country}")
    pr = rankings.profile_ranks(data, country)
    if pr.empty:
        st.warning("No usable data found for this country.")
        return

    metrics = []
    for ind in HEADLINE_INDICATORS:
        row = pr[pr["indicator"] == ind]
        if not row.empty:
            r = row.iloc[0]
            metrics.append((ind, r["value"], r["rank"], r["of"]))
    if metrics:
        # Headline metrics in a 4-column grid so labels wrap instead of squish.
        for row_start in range(0, len(metrics), 4):
            cols = st.columns(4)
            for c, (ind, val, rank, n) in zip(cols, metrics[row_start:row_start + 4]):
                with c:
                    st.metric(
                        label=data.friendly_names.get(ind, ind),
                        value=ui.fmt(val),
                        delta=f"rank #{int(rank)} / {int(n)}",
                    )

    st.subheader("Ranking on every indicator")
    view = pr.copy()
    view["Indicator"] = view["indicator"].map(lambda i: data.friendly_names.get(i, i))
    view["Value"] = view["value"].map(ui.fmt)
    view["Percentile"] = view["percentile"].map(lambda p: f"{p:.0f}")
    ui.show_table(view[["rank", "Indicator", "Value", "Percentile"]], height=430)

    left, right = st.columns(2)
    with left:
        st.subheader("💪 Strengths")
        for _, r in pr.head(5).iterrows():
            st.markdown(f"- **{data.friendly_names.get(r['indicator'], r['indicator'])}**: #{int(r['rank'])}/{int(r['of'])}")
    with right:
        st.subheader("🎯 Areas to improve")
        for _, r in pr.tail(5).iloc[::-1].iterrows():
            st.markdown(f"- **{data.friendly_names.get(r['indicator'], r['indicator'])}**: #{int(r['rank'])}/{int(r['of'])}")

    with st.expander(f"📊 {country} vs the world median (capped score)"):
        fig = charts.profile_bars(data, country, HEADLINE_INDICATORS)
        if fig is not None:
            st.plotly_chart(fig, width="stretch")
        else:
            st.caption("Not enough data to draw this chart.")


def _comparison_panel(data) -> None:
    ui.explainer(
        "🕸️",
        "Pick 2–5 countries and a few indicators. The spider chart (or parallel "
        "coordinates) shows the capped score — 0 to 1, higher is always better — "
        "so you can spot patterns at a glance.",
    )

    c1, c2 = st.columns(2)
    with c1:
        countries = st.multiselect(
            "Countries to compare",
            data.country_list,
            default=[c for c in HIGHLIGHT_COUNTRIES if c in data.country_list][:5],
            max_selections=5,
            key="ce_compare_countries",
        )
    with c2:
        indicators = st.multiselect(
            "Indicators",
            list(data.indicators),
            default=[i for i in COMPARISON_INDICATORS if i in data.indicators],
            key="ce_compare_indicators",
            format_func=lambda i: data.friendly_names.get(i, i),
            help="Scores use the capped 5–95 scaling, inverted where a low "
                 "value is better, so 1.0 always means 'best'.",
        )

    if len(countries) < 2:
        st.caption("Select at least 2 countries to see the comparison.")
        return
    if len(indicators) < 3:
        st.caption("Select at least 3 indicators for a meaningful chart.")
        return

    chart_type = st.radio(
        "Chart type",
        ["Spider (radar) chart", "Parallel coordinates"],
        horizontal=True,
        key="ce_compare_type",
    )
    if chart_type == "Spider (radar) chart":
        st.plotly_chart(charts.radar_chart(data, countries, indicators), width="stretch")
    else:
        st.plotly_chart(charts.parallel_coords(data, countries, indicators), width="stretch")

