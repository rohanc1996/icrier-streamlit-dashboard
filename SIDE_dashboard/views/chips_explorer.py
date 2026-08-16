"""View 1: CHIPS composite index explorer.

Five sections:
  1. 🏅 CHIPS leaderboard — every country, colour-coded by data coverage
  2. 🗺️ CHIPS map — world choropleth; click a country to open its drill-down
  3. 🔍 Country drill-down — treemap, what-if scenarios
  4. ⚠️ Missing-data impact — coverage scatter, status heatmap
  5. 📖 Methodology — plain-language rules and the full indicator map
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from components import charts, country_names, ui
from core import chips, chips_hierarchy as H, scaling

SECTIONS = [
    "🏅 CHIPS leaderboard",
    "🗺️ CHIPS map",
    "🔍 Country drill-down",
    "⚠️ Missing-data impact",
    "📖 Methodology",
]

DEFAULT_COUNTRY = "India"

# Short pillar prefixes so the heatmap columns stay readable.
PILLAR_SHORT = {
    "CONNECT": "CON",
    "HARNESS": "HAR",
    "INNOVATE": "INN",
    "PROTECT": "PRO",
    "SUSTAINABILITY": "SUS",
}


def _default_country(data) -> str:
    return DEFAULT_COUNTRY if DEFAULT_COUNTRY in data.country_list else data.country_list[0]


def _clicked_country(selection) -> str | None:
    """Pull the clicked country out of a plotly ``on_select`` payload."""
    try:
        points = getattr(getattr(selection, "selection", None), "points", None)
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


def _on_map_select() -> None:
    clicked = _clicked_country(st.session_state.get("chips_map"))
    if clicked and clicked in st.session_state.get("_chips_country_list", []):
        st.session_state["ch_country"] = clicked
        st.session_state["ch_section"] = "🔍 Country drill-down"


def _on_scatter_select() -> None:
    clicked = _clicked_country(st.session_state.get("chips_scatter"))
    if clicked and clicked in st.session_state.get("_chips_country_list", []):
        st.session_state["ch_country"] = clicked
        st.session_state["ch_section"] = "🔍 Country drill-down"


def _short_subpillar(key: str) -> str:
    pillar, _, sp = key.partition(" · ")
    return f"{PILLAR_SHORT.get(pillar, pillar[:4])}·{sp}"


def render(data, method=scaling.METHOD_CAPPED) -> None:
    ui.page_header(
        "🏆 CHIPS Index Explorer",
        "CONNECT · HARNESS · INNOVATE · PROTECT · SUSTAINABILITY — a transparent "
        "composite score with full missing-data diagnostics.",
    )
    pillars, unresolved = H.resolve_hierarchy(data.numeric_df.columns)
    st.session_state["_chips_country_list"] = data.country_list

    n_indicators = len(H.all_leaves(pillars))
    n_sub = sum(len(p.sub_pillars) for p in pillars)
    if unresolved:
        ui.explainer(
            "⚠️",
            f"**{len(unresolved)} indicator(s)** in the CHIPS spec could not be matched to a "
            f"dataset column and are treated as missing everywhere: {', '.join(unresolved)}. "
            "Add them to `COLUMN_ALIASES` in `core/chips_hierarchy.py`.",
        )
    else:
        ui.explainer(
            "🧮",
            f"**{n_indicators} indicators → {n_sub} sub-pillars → 5 pillars → CHIPS (0–1).** "
            "CONNECT, HARNESS and INNOVATE each carry **25%** of the index; PROTECT and "
            "SUSTAINABILITY **12.5%** each. Every indicator is scaled to 0–1 with the "
            "sidebar-selected method (capped min-max by default; inverted where lower "
            "is better). Missing data is never "
            "silently ignored: weights are "
            "redistributed and groups that lose too many components are dropped with the reason "
            "recorded — hover any block or cell to see it.",
        )

    # One baseline computation shared by the leaderboard, map and scatter.
    scores = chips.chips_table(data, pillars=pillars, method=method)

    section = st.radio(
        "Section", SECTIONS, horizontal=True, label_visibility="collapsed", key="ch_section"
    )
    if section == SECTIONS[0]:
        _leaderboard(scores)
    elif section == SECTIONS[1]:
        _map_panel(data, scores)
    elif section == SECTIONS[2]:
        _drilldown(data, scores, pillars, method)
    elif section == SECTIONS[3]:
        _missingness(data, scores, pillars, method)
    else:
        _methodology(pillars, unresolved)


def _leaderboard(scores) -> None:
    scored = scores.dropna(subset=["chips"])
    c1, c2, c3 = st.columns(3)
    c1.metric("Countries scored", int(scored["chips"].notna().sum()),
              help="Countries with at least 3 of 5 pillars present after the drop rules.")
    c2.metric("Median CHIPS score", f"{scored['chips'].median():.3f}")
    c3.metric("Median data coverage", f"{scores['coverage'].median() * 100:.0f}%",
              help="Share of the CHIPS weight backed by actual values; see Missing-data for country-level detail.")

    display = scores.copy()
    display["data_badge"] = display["coverage"].apply(
        lambda c: "🟢 full" if c >= 0.9 else ("🟡 partial" if c >= 0.7 else "🔴 sparse"))
    display["chips"] = display["chips"].round(3)
    cols = {
        "rank": st.column_config.NumberColumn("Rank", format="%d"),
        "Country": st.column_config.TextColumn("Country"),
        "chips": st.column_config.NumberColumn("CHIPS", format="%.3f"),
        "data_badge": st.column_config.TextColumn("Data"),
        "indicators_present": st.column_config.NumberColumn("Indicators", format="%d"),
        "pillars_present": st.column_config.NumberColumn("Pillars", format="%d"),
        "CONNECT": st.column_config.NumberColumn("Connect", format="%.2f"),
        "HARNESS": st.column_config.NumberColumn("Harness", format="%.2f"),
        "INNOVATE": st.column_config.NumberColumn("Innovate", format="%.2f"),
        "PROTECT": st.column_config.NumberColumn("Protect", format="%.2f"),
        "SUSTAINABILITY": st.column_config.NumberColumn("Sustainability", format="%.2f"),
    }
    ui.show_table(display[list(cols)], column_config=cols, height=540)
    st.caption(
        "Values are the raw dataset figures; **CHIPS and pillar scores use the "
        "sidebar-selected scaling method** (inverted where lower is better). The Data badge "
        "summarises coverage (🟢 full ≥90% of the CHIPS weight backed by values, 🟡 partial "
        "≥70%, 🔴 sparse) — see the Missing-data section for country-level detail. Sort by "
        "clicking a column header."
    )
    csv = scores.to_csv(index=False).encode()
    st.download_button("⬇️ Download CHIPS table (CSV)", data=csv,
                       file_name="chips_table.csv", mime="text/csv")


def _map_panel(data, scores) -> None:
    ui.explainer(
        "🗺️",
        "Countries without a CHIPS score (fewer than 3 pillars with enough data) are left "
        "uncoloured. Click any country to open its drill-down.",
    )
    selected = st.session_state.get("selected_country") or _default_country(data)
    fig = charts.chips_choropleth(scores, selected)
    st.plotly_chart(fig, key="chips_map", on_select=_on_map_select, selection_mode="points")
    n_scored = int(scores["chips"].notna().sum())
    st.caption(f"{n_scored} of {len(scores)} countries in our report have a CHIPS score.")


def _drilldown(data, scores, pillars, method) -> None:
    ui.explainer(
        "🔍",
        "Open a country to see every pillar and indicator, exactly which groups were dropped "
        "and why, and how far a missing sub-pillar could move the total.",
    )
    default = _default_country(data)
    country = st.selectbox("Country", data.country_list,
                           index=data.country_list.index(default), key="ch_country")
    res = chips.aggregate_country(data, country, pillars=pillars, method=method)

    scored = scores.dropna(subset=["chips"])
    rank_row = scored[scored["Country"] == country]
    rank = int(rank_row["rank"].iloc[0]) if not rank_row.empty else None

    m1, m2, m3, m4 = st.columns(4)
    if res.chips.score is not None:
        m1.metric("CHIPS score", f"{res.chips.score:.3f}")
    else:
        m1.metric("CHIPS score", "no score",
                  help="Fewer than 3 pillars survived the missing-data rules.")
    m2.metric("Global rank", f"#{rank}" if rank else "—")
    m3.metric("Data coverage", f"{res.coverage['coverage'] * 100:.0f}%",
              help="Share of the CHIPS weight backed by an actual value.")
    m4.metric("Indicators present",
              f"{res.coverage['indicators_present']} / {res.coverage['indicators_total']}")

    st.markdown("#### Pillar scores")
    pcols = st.columns(5)
    for col, pr in zip(pcols, res.pillars):
        col.metric(pr.name, f"{pr.score:.2f}" if pr.score is not None else "dropped")

    st.markdown("#### How the score is built")
    rows = chips.tree_to_frame(res.chips, chips.leaf_global_weights(pillars))
    st.plotly_chart(charts.chips_treemap(rows), width="stretch")
    st.caption("Area = share of the CHIPS weight; colour = the pillar hue (CONNECT blue, "
               "HARNESS teal, INNOVATE orange, PROTECT red, SUSTAINABILITY green) shaded by "
               "score — darker = higher. Grey = no data or dropped by a rule.")

    _whatif_panel(data, pillars, country, res, method)
    _movers_panel(data, pillars, country, res, method)


def _whatif_panel(data, pillars, country, res, method) -> None:
    st.markdown("#### What-if: how much does one sub-pillar matter?")
    keys = H.sub_pillar_keys(pillars)
    target = st.selectbox("Sub-pillar to simulate", ["— choose one —"] + keys, key="ch_sim_target")
    if target == "— choose one —":
        return

    drop_it = st.checkbox("Drop it altogether (treat the sub-pillar as having no data)",
                          key="ch_sim_drop")
    if drop_it:
        override = {target: ("absent", None)}
    else:
        actual_sp = next(
            (sp.score for pr in res.pillars for sp in pr.children
             if f"{pr.name} · {sp.name}" == target),
            None,
        )
        default = float(actual_sp) if actual_sp is not None else 0.5
        value = st.slider(
            "Assumed score for this sub-pillar", 0.0, 1.0, default, step=0.05,
            key="ch_sim_score",
            help="Set the sub-pillar's 0–1 score. It starts at the country's actual score, "
                 f"so leaving it in place reproduces the current result.",
        )
        if actual_sp is not None:
            st.caption(f"🎯 {country}'s current score for **{target}** is **{actual_sp:.2f}** — the "
                       "slider starts there, so leaving it alone reproduces today's score.")
        else:
            st.caption(f"ℹ️ **{target}** currently has no score for {country} (missing or dropped) — "
                       "the slider gives it a hypothetical value instead.")
        override = {target: ("present", value)}

    scen = chips.aggregate_country(data, country, pillars=pillars, override=override, method=method)
    scen_scores = chips.chips_table(data, pillars=pillars, override=override, method=method)
    scen_row = scen_scores[scen_scores["Country"] == country]
    scen_rank = None
    if not scen_row.empty and pd.notna(scen_row["rank"].iloc[0]):
        scen_rank = int(scen_row["rank"].iloc[0])

    actual = res.chips.score
    new = scen.chips.score
    delta = None if actual is None or new is None else new - actual
    a, b, c = st.columns(3)
    a.metric("Current CHIPS", f"{actual:.3f}" if actual is not None else "no score")
    b.metric("CHIPS under scenario", f"{new:.3f}" if new is not None else "no score",
             delta=(None if delta is None else f"{delta:+.3f}"))
    c.metric("Rank under scenario", f"#{scen_rank}" if scen_rank else "—")
    if drop_it:
        st.caption(f"Scenario applied to **{target}** — treated as having no data. Rank is "
                   "recomputed across all countries under the same scenario.")
    else:
        st.caption(f"Scenario applied to **{target}** — set to **{value:.2f}**. Rank is "
                   "recomputed across all countries under the same scenario.")


def _movers_panel(data, pillars, country, res, method) -> None:
    with st.expander("📊 Which sub-pillars move this country's score most?"):
        ui.explainer("💡", "Each row shows the CHIPS score if that one sub-pillar were removed "
                          "(treated as having no data). The most negative Δ marks the sub-pillars "
                          "the country currently leans on the hardest.")
        actual = res.chips.score
        movers = []
        for key in H.sub_pillar_keys(pillars):
            r = chips.aggregate_country(data, country, pillars=pillars,
                                        override={key: ("absent", None)}, method=method)
            new = r.chips.score
            movers.append({
                "Sub-pillar": key.replace(" · ", " / "),
                "Score now": actual,
                "Without it": new,
                "Δ": None if actual is None or new is None else new - actual,
            })
        movers_df = pd.DataFrame(movers).sort_values("Δ", ascending=True, na_position="last")
        ui.show_table(movers_df.round(3), height=520)


def _missingness(data, scores, pillars, method) -> None:
    ui.explainer(
        "⚠️",
        "How much of every country's score is backed by real data, where the gaps are, and "
        "which rules had to redistribute or drop components to produce the score.",
    )

    st.markdown("#### Score vs data coverage")
    st.plotly_chart(charts.coverage_scatter(scores), width="stretch",
                    on_select=_on_scatter_select, selection_mode="points")
    st.caption("Click any point to open its drill-down. Points left of the dashed line have "
               "the least data behind their score.")

    st.markdown("#### Missing-data heatmap")
    codes, reasons = chips.subpillar_status_matrix(data, pillars=pillars, method=method)
    order = scores.sort_values("coverage")["Country"].tolist()
    codes = codes.loc[order]
    reasons = reasons.loc[order]
    short_cols = {k: _short_subpillar(k) for k in codes.columns}
    codes = codes.rename(columns=short_cols)
    reasons = reasons.rename(columns=short_cols)
    st.plotly_chart(charts.missingness_heatmap(codes, reasons), width="stretch")
    st.caption("Grey = the sub-pillar has no data for that country; red = a rule dropped it "
               "(e.g. only 1 of 2 components present). Countries are ordered by coverage, "
               "lowest first.")

    with st.expander("🧊 Most data-fragile countries"):
        fragile = scores.dropna(subset=["chips"]).sort_values("coverage").head(20)
        ui.show_table(fragile[["Country", "coverage", "indicators_present", "chips", "rank"]].round(3))
        st.caption("The 20 scored countries with the lowest weighted data coverage.")


def _methodology(pillars, unresolved) -> None:
    ui.explainer(
        "📖",
        "The CHIPS composite is weighted at the pillar level: **CONNECT, HARNESS and INNOVATE each "
        "carry 25%** of the index and **PROTECT and SUSTAINABILITY 12.5% each**. Inside a group, "
        "weights are equal unless the spec sheet gives a specific weight. Everything else is the "
        "missing-data logic below — and every decision it makes is recorded per country.",
    )

    st.markdown("#### Missing-data rules")
    st.markdown(
        """1. **Weights come from the spec** — CONNECT, HARNESS and INNOVATE each carry 25% of
   the index and PROTECT and SUSTAINABILITY 12.5% each. Inside each group, weights are equal
   unless the spec gives one, down to the individual indicators.
2. **Missing values are redistributed** — if a component is missing, its weight is shared
   across the remaining present components of the same group.
3. **More than half missing → the group drops** — and is then treated as unavailable one
   level up.
4. **A 2-component group with only 1 component present drops** — the whole pair is
   unreliable and is removed as a unit.
5. **Same logic at every level** — indicators → sub-pillar → pillar → CHIPS. A dropped
   component is never silently zeroed; it is recorded with its reason.
6. **CHIPS needs at least 3 of 5 pillars** — fewer means no composite score.
7. **INNOVATE → AI is non-flat** — it splits into two internal groups: the **research pair**
   (AI Innovation - Research + AI R&D score, ½ each) and the **remaining three AI indicators**
   (AI commercial, private investment, newly funded AI companies, ⅓ each). A pair that loses
   one member drops (rule 4) — and because the sub-pillar has only 2 groups it drops if either
   group is lost. Inside the 3-indicator group, 1 missing is redistributed and 2 missing drop it.
8. **Scoring** — every indicator is min–max scaled to 0–1 over the full observed range
   (inverted for lower-is-better indicators such as prices and risk).""")

    st.markdown("#### The indicator map")
    table = H.hierarchy_table(pillars)
    ui.show_table(table, height=520)
    if unresolved:
        st.warning(f"Unresolved indicator names: {', '.join(unresolved)} — these are treated "
                   "as missing for every country until the mapping is added.")
    st.caption("Weights are normalised within each group (e.g. the four CONNECT · Affordability "
               "indicators each carry 25% of that sub-pillar). At the top, the CHI pillars carry "
               "25% of the index and the PS pillars 12.5% each. Hover any cell in the charts to "
               "see which rule applied.")



