"""View: Create Your Own CHIPS Framework.

A thought-experiment page: anyone can rebuild the CHIPS composite index —
change pillar / sub-pillar / indicator weights, reassign indicators between
sub-pillars, add dataset indicators the report left out, or override a
country's individual indicator scores — and see instantly how the whole
leaderboard and each country's score would change.  The published framework
is never altered; the custom one lives in session state only.

Two guard-rails keep the experiment sensible:

- **Weights must total 100%** at every level (pillars, each pillar's
  sub-pillars, the INNOVATE · AI internal groups, and each indicator group).
  The engine normalises, so the editor instead gates the results: while any
  level is off, the results area lists the offending totals and the last
  valid state is shown only after a fix (or the "scale to 100" helper).
- **Indicator membership is a dropdown**, not free-form: every dataset
  indicator is assigned to one of the existing sub-pillars (or "not in the
  framework"), and INNOVATE · AI rows also pick an internal group.

Per-country **score overrides** patch the 0-1 score matrix before
aggregation, so weights, missing-data rules and rank recomputation all flow
through unchanged.  Overriding a missing indicator fills the gap with the
subjective value (coverage reflects it).
"""
from __future__ import annotations

import copy
import hashlib
import json
from collections import defaultdict

import numpy as np
import pandas as pd
import streamlit as st

from components import charts, ui
from core import chips, chips_hierarchy as H, rankings, scaling
from core.loader import load_app_data

DEFAULT_COUNTRY = "India"

# Dataset columns that are not real candidate indicators for a custom framework
# (a stray "Count" column and a duplicate of an already-used AI column).
JUNK_ADDABLE = {"Count", "AI Infrastructure"}

NOT_IN_FRAMEWORK = "— not in framework —"
GROUP_NONE = "—"
AI_GROUPS = ["Research", "Investment & commercial"]
AI_DEFAULT_GROUP = "Investment & commercial"


# ---------------------------------------------------------------------------
# Cached engine outputs.  The custom ones are keyed by the serialised spec AND
# the score overrides (plus the method), so any edit to either produces a
# fresh computation while identical states reuse the cache.  The baseline
# (published) framework has a fixed spec, so it is cached by method alone.
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _baseline_chips_table(method: str) -> pd.DataFrame:
    data = load_app_data()
    return chips.chips_table(data, method=method)


@st.cache_data(show_spinner=False)
def _baseline_score_matrix(method: str) -> pd.DataFrame:
    data = load_app_data()
    pillars, _ = H.resolve_hierarchy(data.numeric_df.columns)
    return chips.score_matrix(data, pillars=pillars, method=method)


@st.cache_data(show_spinner=False)
def _custom_chips_table(method: str, spec_json: str, overrides_json: str) -> pd.DataFrame:
    data = load_app_data()
    spec = json.loads(spec_json)
    pillars, _ = H.resolve_hierarchy(data.numeric_df.columns, spec=spec)
    return chips.chips_table(data, pillars=pillars, method=method,
                             indicator_overrides=json.loads(overrides_json))


@st.cache_data(show_spinner=False)
def _custom_score_matrix(method: str, spec_json: str, overrides_json: str) -> pd.DataFrame:
    data = load_app_data()
    spec = json.loads(spec_json)
    pillars, _ = H.resolve_hierarchy(data.numeric_df.columns, spec=spec)
    return chips.score_matrix(data, pillars=pillars, method=method,
                              indicator_overrides=json.loads(overrides_json))


# ---------------------------------------------------------------------------
# Spec / override editing helpers
# ---------------------------------------------------------------------------

def _fw_widget_key(*parts: str) -> str:
    return "fw_" + hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()[:10]


def _clear_framework_widgets() -> None:
    """Drop editor widget state so the widgets re-seed from the spec.

    Called after a reset, a JSON load, or a "scale to 100" — whenever the
    structure or weights change underneath the widget keys.
    """
    for k in list(st.session_state.keys()):
        if k.startswith("fw_"):
            st.session_state.pop(k, None)


def _normalize_weights(weights: list[float | None]) -> list[float | None]:
    """Scale a group's weights to sum to 1.0 (all-None groups stay equal)."""
    if not weights or all(w is None for w in weights):
        return weights
    s = sum(1.0 if w is None else float(w) for w in weights)
    if s <= 0:
        return weights
    return [float(w) / s for w in weights]


def _default_spec() -> list[dict]:
    """The published framework, with every group scaled to sum to 100%.

    The committed spec stores rounded weights (0.17, 0.33, …), so normalising
    here makes the editor open in a valid state while preserving the effective
    (normalised) weights exactly.
    """
    return _scale_spec_to_100(copy.deepcopy(H.HIERARCHY))


def _scale_spec_to_100(spec: list[dict]) -> list[dict]:
    """Return a copy of the spec with every level scaled to total 100%."""
    out = copy.deepcopy(spec)
    for p, w in zip(out, _normalize_weights([p.get("weight") for p in out])):
        p["weight"] = w
        sps = p["sub_pillars"]
        for sp, sw in zip(sps, _normalize_weights([s.get("weight") for s in sps])):
            sp["weight"] = sw
            if sp.get("internal_groups"):
                for g in sp["internal_groups"]:
                    scaled = _normalize_weights([w for _n, w in g["indicators"]])
                    g["indicators"] = [(n, nw) for (n, _w), nw in zip(g["indicators"], scaled)]
            else:
                inds = sp.get("indicators", [])
                scaled = _normalize_weights([w for _n, w in inds])
                sp["indicators"] = [(n, nw) for (n, _w), nw in zip(inds, scaled)]
    return out


def _get_spec() -> list[dict]:
    if "ch_fw_spec" not in st.session_state:
        st.session_state["ch_fw_spec"] = _default_spec()
    return st.session_state["ch_fw_spec"]


def _get_overrides() -> dict:
    if "ch_fw_overrides" not in st.session_state:
        st.session_state["ch_fw_overrides"] = {}
    return st.session_state["ch_fw_overrides"]


def _spec_to_json(spec: list[dict]) -> str:
    return json.dumps(spec, sort_keys=True, allow_nan=False)


def _overrides_to_json(overrides: dict) -> str:
    return json.dumps(overrides, sort_keys=True)


def _validate_spec(spec) -> tuple[bool, str]:
    if not isinstance(spec, list) or not spec:
        return False, "Spec must be a JSON list of at least one pillar."
    for p in spec:
        if not isinstance(p, dict) or not isinstance(p.get("name"), str) or "sub_pillars" not in p:
            return False, "Each pillar needs a 'name' (string) and a 'sub_pillars' list."
        if not isinstance(p["sub_pillars"], list) or not p["sub_pillars"]:
            return False, f"Pillar '{p.get('name')}' has no sub-pillars."
        for sp in p["sub_pillars"]:
            if not isinstance(sp, dict) or not isinstance(sp.get("name"), str):
                return False, "Each sub-pillar needs a 'name' (string)."
            if sp.get("internal_groups") is not None:
                if not isinstance(sp["internal_groups"], list) or not sp["internal_groups"]:
                    return False, f"Sub-pillar '{sp.get('name')}' needs non-empty 'internal_groups'."
                for g in sp["internal_groups"]:
                    if not isinstance(g.get("indicators"), list):
                        return False, f"Internal group in '{sp.get('name')}' needs an 'indicators' list."
            else:
                if not isinstance(sp.get("indicators"), list):
                    return False, f"Sub-pillar '{sp.get('name')}' needs an 'indicators' list."
    return True, ""


def _locate_map(spec: list[dict]) -> dict[str, tuple[str, str, str]]:
    """Spec indicator name -> (pillar, sub-pillar, internal group) display labels."""
    out: dict[str, tuple[str, str, str]] = {}
    for p in spec:
        for sp in p["sub_pillars"]:
            if sp.get("internal_groups"):
                for g in sp["internal_groups"]:
                    for name, _w in g["indicators"]:
                        out[name] = (p["name"], sp["name"], g["name"])
            else:
                for name, _w in sp["indicators"]:
                    out[name] = (p["name"], sp["name"], "")
    return out


def _raw_weight_map(spec: list[dict]) -> dict[str, float | None]:
    """Spec indicator name -> its entered (raw) weight."""
    out: dict[str, float | None] = {}
    for p in spec:
        for sp in p["sub_pillars"]:
            if sp.get("internal_groups"):
                for g in sp["internal_groups"]:
                    for name, w in g["indicators"]:
                        out[name] = w
            else:
                for name, w in sp["indicators"]:
                    out[name] = w
    return out


def _sub_pillar_options(spec: list[dict]) -> list[str]:
    return [f"{p['name']} · {sp['name']}"
            for p in spec for sp in p["sub_pillars"]] + [NOT_IN_FRAMEWORK]


# ---------------------------------------------------------------------------
# Indicator membership table
# ---------------------------------------------------------------------------

def _framework_table(data, spec: list[dict]) -> pd.DataFrame:
    """One row per dataset indicator: where it sits (editable sub-pillar /
    group dropdowns), its raw weight, and its pillar for orientation."""
    pillars, _ = H.resolve_hierarchy(data.numeric_df.columns, spec=spec)
    col_to_name = {leaf.column: leaf.name for leaf in H.all_leaves(pillars) if leaf.column}
    raw = _raw_weight_map(spec)
    loc = _locate_map(spec)
    rows = []
    for col in data.indicators:
        if col in JUNK_ADDABLE:
            continue
        name = col_to_name.get(col)
        if name is None or name not in loc:
            rows.append({
                "Indicator": col,
                "Sub-pillar": NOT_IN_FRAMEWORK,
                "Group": GROUP_NONE,
                "Pillar": "—",
                "Weight in group (%)": None,
            })
        else:
            pillar, sub, group = loc[name]
            w = raw.get(name)
            rows.append({
                "Indicator": col,
                "Sub-pillar": f"{pillar} · {sub}",
                "Group": group if group else GROUP_NONE,
                "Pillar": pillar,
                "Weight in group (%)": None if w is None else float(w) * 100,
            })
    return pd.DataFrame(rows)


def _spec_from_table(data, spec: list[dict], df: pd.DataFrame) -> list[dict]:
    """Rebuild the spec from the (possibly edited) indicator table.

    The table's Sub-pillar (and Group, for INNOVATE · AI) dropdowns decide
    where every indicator counts; "— not in framework —" removes it.  Pillar /
    sub-pillar / group weights are carried over untouched.  Weight cells hold
    raw percentages; blank keeps the indicator's previous weight (or equal
    weight for a fresh addition).
    """
    pillars, _ = H.resolve_hierarchy(data.numeric_df.columns, spec=spec)
    leaves = H.all_leaves(pillars)
    col_to_name = {leaf.column: leaf.name for leaf in leaves if leaf.column}
    name_to_col = {leaf.name: leaf.column for leaf in leaves}
    raw = _raw_weight_map(spec)
    col_to_prev = {name_to_col[n]: w for n, w in raw.items() if name_to_col.get(n)}

    assigned: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    for _, r in df.iterrows():
        col = r["Indicator"]
        sub_key = r["Sub-pillar"]
        if not isinstance(sub_key, str) or sub_key == NOT_IN_FRAMEWORK:
            continue
        pillar_name, _, sub_name = sub_key.partition(" · ")
        group = r["Group"] if isinstance(r["Group"], str) else GROUP_NONE
        assigned[(pillar_name, sub_name)].append((col, group))

    def _weight(col: str, default) -> float | None:
        rows = df[df["Indicator"] == col]
        if rows.empty:
            return default
        w = rows["Weight in group (%)"].iloc[0]
        if w is None or (isinstance(w, float) and np.isnan(w)) or w == "":
            return default
        return float(w) / 100

    def _name(col: str) -> str:
        return col_to_name.get(col) or col

    def _default_weight(cols: list[str]) -> float | None:
        """Weight for a fresh addition: the group's existing member weight if
        there is one, else the equal share.  (A plain ``None`` would be treated
        by the engine as weight 1.0 next to explicit weights.)"""
        existing = [col_to_prev[c] for c in cols
                    if c in col_to_prev and col_to_prev[c] is not None]
        if existing:
            return existing[0]
        return 1.0 / len(cols) if cols else None

    new_spec: list[dict] = []
    for p in spec:
        new_sp_list = []
        for sp in p["sub_pillars"]:
            entries = assigned.get((p["name"], sp["name"]), [])
            if sp.get("internal_groups"):
                groups = []
                for g in sp["internal_groups"]:
                    gcols = [col for col, grp in entries
                             if grp == g["name"] or (g["name"] == AI_DEFAULT_GROUP and grp == GROUP_NONE)]
                    inds = [(_name(col),
                             _weight(col, col_to_prev.get(col) if col in col_to_prev else _default_weight(gcols)))
                            for col in gcols]
                    groups.append({"name": g["name"], "weight": g.get("weight"), "indicators": inds})
                new_sp_list.append({
                    "name": sp["name"], "weight": sp.get("weight"),
                    "internal_groups": groups, "is_ai": sp.get("is_ai", False),
                })
            else:
                cols = [col for col, _grp in entries]
                inds = [(_name(col),
                         _weight(col, col_to_prev.get(col) if col in col_to_prev else _default_weight(cols)))
                        for col in cols]
                new_sp_list.append({"name": sp["name"], "weight": sp.get("weight"), "indicators": inds})
        new_spec.append({"name": p["name"], "weight": p.get("weight"), "sub_pillars": new_sp_list})
    return new_spec


def _empty_group_warnings(spec: list[dict]) -> None:
    msgs = []
    for p in spec:
        for sp in p["sub_pillars"]:
            n = (sum(len(g["indicators"]) for g in sp["internal_groups"])
                 if sp.get("internal_groups") else len(sp.get("indicators", [])))
            if n == 0:
                msgs.append(f"**{p['name']} · {sp['name']}** has no indicators and will be dropped.")
    if msgs:
        st.warning("Empty groups: " + " ".join(msgs))


# ---------------------------------------------------------------------------
# Weight controls
# ---------------------------------------------------------------------------

def _total_caption(label: str, total: float) -> None:
    pct = total * 100
    if abs(total - 1.0) <= 0.005:
        st.markdown(f":green[**{label} total {pct:.1f}%** ✓]")
    else:
        st.markdown(f":red[**{label} total {pct:.1f}%** ✗ — must equal 100%]")


def _edit_weight_controls(data, spec: list[dict]) -> list[dict]:
    """Pillar, sub-pillar and (for INNOVATE · AI) internal-group weights.

    Shown as percentages of the index / pillar / sub-pillar.  Sub-pillars
    with no explicit weight are seeded from their resolved (equal) weight.
    Every level shows a live running total so the user can see at a glance
    whether the "must total 100%" rule holds.
    """
    resolved, _ = H.resolve_hierarchy(data.numeric_df.columns, spec=spec)
    norm = {p.name: p for p in resolved}
    pillar_cols = st.columns(len(spec))
    for i, p in enumerate(spec):
        rp = norm.get(p["name"])
        with pillar_cols[i]:
            st.markdown(f"**{p['name']}**")
            seed_p = float(p["weight"]) * 100 if p.get("weight") is not None else (rp.weight * 100 if rp else 0.0)
            pct = st.number_input(
                "Pillar weight (%)", min_value=0.0, value=seed_p,
                step=1.0, format="%.1f", key=_fw_widget_key("pw", p["name"]),
                help="Weight of this pillar in the CHIPS index (%).  The five pillars "
                     "must total 100%.")
            p["weight"] = pct / 100
            for j, sp in enumerate(p["sub_pillars"]):
                rsp = rp.sub_pillars[j] if rp and j < len(rp.sub_pillars) else None
                seed_sp = float(sp.get("weight", 0.0)) * 100 if sp.get("weight") is not None else (rsp.weight * 100 if rsp else 0.0)
                sp_label = sp["name"]
                sp_pct = st.number_input(
                    f"{sp_label} — weight (%)", min_value=0.0,
                    value=seed_sp, step=1.0, format="%.1f",
                    key=_fw_widget_key("spw", p["name"], sp["name"]),
                    help=f"Weight of '{sp_label}' within the {p['name']} pillar (%). "
                         "This pillar's sub-pillars must total 100%.")
                sp["weight"] = sp_pct / 100
                if sp.get("internal_groups"):
                    for g in sp["internal_groups"]:
                        g_pct = st.number_input(
                            f"↳ {g['name']} group — weight (%)", min_value=0.0,
                            value=float(g["weight"]) * 100, step=1.0, format="%.1f",
                            key=_fw_widget_key("gw", p["name"], sp["name"], g["name"]),
                            help=f"Weight of the '{g['name']}' group within {sp_label} (%). "
                                 "The two groups must total 100%.")
                        g["weight"] = g_pct / 100
                    _total_caption("Groups", sum(g["weight"] for g in sp["internal_groups"]))
            _total_caption(f"{p['name']} sub-pillars", sum(sp["weight"] for sp in p["sub_pillars"]))
    st.divider()
    _total_caption("All pillars", sum(p["weight"] for p in spec))
    st.caption("Every level must total 100% before the results are shown. Use "
               "**↔ Scale to 100** below to snap everything back to valid.")
    return spec


# ---------------------------------------------------------------------------
# Score overrides
# ---------------------------------------------------------------------------

def _score_override_editor(data, country: str, pillars, method: str, spec_json: str) -> None:
    """Editable table of one country's indicator scores.

    "Your score" replaces the computed 0-1 score for this country (blank keeps
    the computed score).  Overriding a missing indicator fills the gap with
    the subjective value, which is why missing rows show "no data" rather than
    being hidden.
    """
    st.markdown(f"#### ✏️ Adjust {country}'s indicator scores")
    ui.explainer(
        "✏️",
        "Replace any indicator's computed 0–1 score with **your** judgement. Overrides "
        "apply only to this country, feed straight into its CHIPS score and rank, and a "
        "missing indicator can be filled with a subjective value (coverage then reflects it).",
    )
    base = _custom_score_matrix(method, spec_json, "{}")
    row = base[base["Country"] == country].iloc[0]
    existing = _get_overrides().get(country, {})
    rows = []
    for leaf in H.all_leaves(pillars):
        cur = row.get(leaf.name)
        rows.append({
            "Indicator": leaf.name,
            "Current score": None if pd.isna(cur) else float(cur),
            "Your score": existing.get(leaf.name),
            "Weight": None if leaf.weight is None else float(leaf.weight) * 100,
        })
    df = pd.DataFrame(rows)
    edited = st.data_editor(
        df,
        key=_fw_widget_key("ov", country),
        hide_index=True,
        width="stretch",
        num_rows="fixed",
        disabled={"Indicator": True, "Current score": True, "Weight": True},
        column_config={
            "Indicator": st.column_config.TextColumn("Indicator"),
            "Current score": st.column_config.NumberColumn("Current score", format="%.2f"),
            "Your score": st.column_config.NumberColumn(
                "Your score", min_value=0.0, max_value=1.0, step=0.01, format="%.2f",
                help="Override this indicator's 0–1 score for this country. "
                     "Blank keeps the computed score."),
            "Weight": st.column_config.NumberColumn("Weight in index (%)", format="%.2f"),
        },
    )
    new = {}
    for _, r in edited.iterrows():
        v = r["Your score"]
        if v is not None and not (isinstance(v, float) and np.isnan(v)):
            new[r["Indicator"]] = float(v)
    overrides = _get_overrides()
    overrides[country] = new
    st.session_state["ch_fw_overrides"] = overrides
    if new:
        st.caption(f"✏️ {len(new)} override(s) set for **{country}** — shown in the treemap and "
                   "reflected in the score and rank below.")


# ---------------------------------------------------------------------------
# Diff summary
# ---------------------------------------------------------------------------

def _spec_diff_summary(data, spec: list[dict]) -> tuple[list[str], list[str], list[str]]:
    """(added columns, removed columns, indicators whose global weight changed)
    compared with the default framework."""
    default_pillars, _ = H.resolve_hierarchy(data.numeric_df.columns)
    custom_pillars, _ = H.resolve_hierarchy(data.numeric_df.columns, spec=spec)
    d_cols = {leaf.column for leaf in H.all_leaves(default_pillars) if leaf.column}
    c_cols = {leaf.column for leaf in H.all_leaves(custom_pillars) if leaf.column}
    added = sorted(c_cols - d_cols)
    removed = sorted(d_cols - c_cols)
    dw = chips.leaf_global_weights(default_pillars)
    cw = chips.leaf_global_weights(custom_pillars)
    changed = sorted(n for n in set(dw) | set(cw)
                     if abs(dw.get(n, 0.0) - cw.get(n, 0.0)) > 1e-9)
    return added, removed, changed


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def _default_country(data) -> str:
    return DEFAULT_COUNTRY if DEFAULT_COUNTRY in data.country_list else data.country_list[0]


def render(data, method=scaling.METHOD_CAPPED) -> None:
    ui.page_header(
        "🎛️ Create Your Own CHIPS Framework",
        "The CHIPS index embeds a weighting judgement. Build an alternative — reweight "
        "pillars, sub-pillars and indicators, reassign indicators, add dataset indicators "
        "the report left out, or override a country's indicator scores — and see how the "
        "whole leaderboard and each country's score would change.",
    )
    ui.explainer(
        "🎛️",
        "The published CHIPS framework is never altered: your custom framework is only a "
        "thought experiment that lives in this session. Two guard-rails keep it sensible — "
        "**every level of weights must total 100%** before results are shown, and membership "
        "is assigned from the existing sub-pillars. It is recomputed with the same "
        "missing-data rules as the default, so scores stay comparable.",
    )

    spec = _get_spec()

    with st.expander("⚖️ Weight controls", expanded=True):
        spec = _edit_weight_controls(data, spec)

        st.markdown("**Indicator membership & within-group weights**")
        table = _framework_table(data, spec)
        edited = st.data_editor(
            table,
            key="fw_table",
            hide_index=True,
            width="stretch",
            num_rows="fixed",
            disabled={"Indicator": True, "Pillar": True},
            column_config={
                "Indicator": st.column_config.TextColumn("Indicator"),
                "Sub-pillar": st.column_config.SelectboxColumn(
                    "Sub-pillar",
                    options=_sub_pillar_options(spec),
                    width="medium",
                    help="Which sub-pillar this indicator counts in. "
                         "'— not in framework —' removes it."),
                "Group": st.column_config.SelectboxColumn(
                    "Group",
                    options=[GROUP_NONE] + AI_GROUPS,
                    width="small",
                    help="Internal group within INNOVATE · AI only; ignored elsewhere."),
                "Pillar": st.column_config.TextColumn("Pillar", width="small"),
                "Weight in group (%)": st.column_config.NumberColumn(
                    "Weight in group (%)", min_value=0.0, format="%.1f",
                    help="Weight of the indicator within its group (%). The group's "
                         "members must total 100%."),
            },
        )
        spec = _spec_from_table(data, spec, edited)
        st.session_state["ch_fw_spec"] = spec
        st.caption("Assign an indicator by picking its **Sub-pillar** (INNOVATE · AI rows also "
                   "pick a **Group**); set it to '— not in framework —' to drop it. Edit the "
                   "weight column to change how much an indicator counts within its group. "
                   "Moving or adding an indicator usually means re-balancing the affected "
                   "groups to 100%.")

    _empty_group_warnings(spec)

    weight_issues = H.validate_spec_totals(spec)
    if weight_issues:
        with st.container(border=True):
            st.error("Weights must total 100% at every level before results can be shown:")
            for it in weight_issues:
                st.markdown(f"- **{it['level']}** · {it['path']}: currently **{it['total'] * 100:.1f}%**")
            if st.button("↔ Scale all weights to 100%", key="fw_scale"):
                st.session_state["ch_fw_spec"] = _scale_spec_to_100(spec)
                _clear_framework_widgets()
                st.rerun()

    json_col, reset_col, _ = st.columns([1, 1, 3])
    with json_col:
        spec_download = _spec_to_json(spec).encode("utf-8")
        st.download_button("⬇️ Download framework (JSON)", data=spec_download,
                           file_name="chips_framework.json", mime="application/json")
    with reset_col:
        if st.button("↺ Reset to default framework", type="secondary"):
            st.session_state["ch_fw_spec"] = _default_spec()
            _clear_framework_widgets()
            st.rerun()

    with st.expander("📤 Load a framework from JSON"):
        pasted = st.text_area("Framework JSON", height=220,
                              key="fw_import", help="Paste a framework saved earlier. "
                                                    "It must match the CHIPS spec format.")
        if st.button("Load this framework"):
            try:
                parsed = json.loads(pasted)
            except json.JSONDecodeError as e:
                st.error(f"Not valid JSON: {e}")
                parsed = None
            if parsed is not None:
                ok, msg = _validate_spec(parsed)
                if not ok:
                    st.error(f"Invalid framework: {msg}")
                else:
                    pillars, unresolved = H.resolve_hierarchy(data.numeric_df.columns, spec=parsed)
                    st.session_state["ch_fw_spec"] = parsed
                    _clear_framework_widgets()
                    if unresolved:
                        st.warning("Loaded — but these indicator names don't match any dataset "
                                   f"column and will count as missing everywhere: {', '.join(unresolved)}")
                    else:
                        st.success(f"Loaded framework ({len(pillars)} pillars).")
                    st.rerun()

    with st.expander("👁️ View / copy the current framework as JSON"):
        st.code(_spec_to_json(spec), language="json")

    # ------------------------------------------------------------------
    # Results (gated on valid weights)
    # ------------------------------------------------------------------
    if weight_issues:
        st.info("Fix the weights above (or use **↔ Scale to 100**), then the leaderboard "
                "comparison and country drill-down will appear here.")
        return

    custom_pillars, unresolved = H.resolve_hierarchy(data.numeric_df.columns, spec=spec)
    spec_json = _spec_to_json(spec)
    overrides_json = _overrides_to_json(_get_overrides())
    custom_scores = _custom_chips_table(method, spec_json, overrides_json)
    baseline_scores = _baseline_chips_table(method)

    if unresolved:
        st.warning("Some indicator names in this framework don't match a dataset column and count "
                   f"as missing everywhere: {', '.join(unresolved)}")

    n_inds = len(H.all_leaves(custom_pillars))
    eff = {p.name: p.weight for p in custom_pillars}
    eff_txt = " · ".join(f"**{k}** {v * 100:.1f}%" for k, v in eff.items())
    st.markdown(f"#### Your framework: **{n_inds} indicators** · effective pillar weights: {eff_txt}")

    added, removed, changed = _spec_diff_summary(data, spec)
    bits = []
    if added:
        bits.append(f"➕ **{len(added)}** indicator(s) added: {', '.join(added)}")
    if removed:
        bits.append(f"➖ **{len(removed)}** indicator(s) removed: {', '.join(removed)}")
    if changed:
        bits.append(f"⚖️ **{len(changed)}** indicator(s) reweighted")
    n_ov = sum(len(v) for v in _get_overrides().values())
    if n_ov:
        bits.append(f"✏️ **{n_ov}** score override(s)")
    if bits:
        st.caption(" vs the published framework — " + " · ".join(bits))
    else:
        st.caption("Identical to the published framework — tweak a weight above to see the leaderboard move.")

    view = st.radio("Results", ["📊 Leaderboard comparison", "🔍 Country drill-down"],
                    horizontal=True, key="ch_fw_view")
    if view == "📊 Leaderboard comparison":
        _custom_leaderboard(custom_pillars, custom_scores, baseline_scores)
    else:
        _custom_country_drilldown(data, method, spec, custom_pillars, baseline_scores)


def _custom_leaderboard(custom_pillars, custom_scores, baseline_scores) -> None:
    st.markdown("#### How the leaderboard changes")
    scored_base = int(baseline_scores["chips"].notna().sum())
    scored_cust = int(custom_scores["chips"].notna().sum())
    med_base = baseline_scores["chips"].dropna().median()
    med_cust = custom_scores["chips"].dropna().median()

    c1, c2, c3 = st.columns(3)
    c1.metric("Countries scored", f"{scored_cust} (baseline {scored_base})",
              help="Countries with at least 3 of 5 pillars surviving the drop rules.")
    if scored_cust:
        c2.metric("Median CHIPS score", f"{med_cust:.3f}",
                  delta=f"{med_cust - med_base:+.3f}" if med_base == med_base else None,
                  delta_color="off",
                  help="Median of the custom CHIPS scores vs the baseline median.")
    else:
        c2.metric("Median CHIPS score", "—",
                  help="No country scored under this framework — too many groups dropped.")
    c3.metric("Median coverage", f"{custom_scores['coverage'].median() * 100:.0f}%",
              help="Share of the custom CHIPS weight backed by actual values.")

    pillar_names = [p.name for p in custom_pillars]
    delta = rankings.rank_delta_table(baseline_scores, custom_scores, pillar_names=pillar_names)
    delta = delta.reset_index().rename(columns={"index": "Country"})

    display = delta.sort_values("Δrank", ascending=True)
    cfg = {
        "Country": st.column_config.TextColumn("Country"),
        "baseline_rank": st.column_config.NumberColumn("Baseline rank", format="%d"),
        "custom_rank": st.column_config.NumberColumn("Custom rank", format="%d"),
        "Δrank": st.column_config.NumberColumn("Δ rank", format="%+d"),
        "baseline_chips": st.column_config.NumberColumn("Baseline CHIPS", format="%.3f"),
        "custom_chips": st.column_config.NumberColumn("Custom CHIPS", format="%.3f"),
        "Δchips": st.column_config.NumberColumn("Δ CHIPS", format="%+.3f"),
    }
    for name in pillar_names:
        cfg[f"custom_{name}"] = st.column_config.NumberColumn(name.title(), format="%.2f")
    ui.show_table(display, column_config=cfg, height=540)
    st.caption("Sorted by Δ rank (most improved first). A positive Δ rank means the country slips "
               "down under your framework; negative means it climbs. Sorted? Click a column header.")

    g1, g2 = st.columns(2)
    scored = display.dropna(subset=["custom_rank", "baseline_rank"])
    with g1:
        st.markdown("#### 🚀 Biggest climbers")
        ui.show_table(scored.nsmallest(5, "Δrank")[["Country", "baseline_rank", "custom_rank", "Δrank"]].reset_index(drop=True), height=220)
    with g2:
        st.markdown("#### 🎢 Biggest fallers")
        ui.show_table(scored.nlargest(5, "Δrank")[["Country", "baseline_rank", "custom_rank", "Δrank"]].reset_index(drop=True), height=220)

    st.markdown("#### Leaderboard under your framework")
    race_fig, axis_fig = charts.chips_race(custom_scores)
    box_h = min(charts.RACE_BOX_HEIGHT, int(race_fig.layout.height or 500))
    st.markdown(
        f"<style>.st-key-ch_fw_race {{height: {box_h}px !important;"
        f" overflow-y: auto !important; overflow-x: hidden !important;}}</style>",
        unsafe_allow_html=True,
    )
    st.plotly_chart(race_fig, key="ch_fw_race", use_container_width=True)
    st.plotly_chart(axis_fig, use_container_width=True,
                    config={"displayModeBar": False, "staticPlot": True})

    st.markdown("#### World map under your framework")
    st.plotly_chart(charts.chips_choropleth(custom_scores, None), width="stretch")

    csv = custom_scores.to_csv(index=False).encode()
    st.download_button("⬇️ Download custom CHIPS table (CSV)", data=csv,
                       file_name="chips_table_custom.csv", mime="text/csv")


def _custom_country_drilldown(data, method, spec, custom_pillars, baseline_scores) -> None:
    default = _default_country(data)
    country = st.selectbox("Country", data.country_list,
                           index=data.country_list.index(default), key="ch_fw_country")

    spec_json = _spec_to_json(spec)
    _score_override_editor(data, country, custom_pillars, method, spec_json)

    # Recompute with the freshest overrides (the editor above may have changed them).
    overrides_json = _overrides_to_json(_get_overrides())
    custom_scores = _custom_chips_table(method, spec_json, overrides_json)

    base_pillars, _ = H.resolve_hierarchy(data.numeric_df.columns)
    base_res = chips.aggregate_country(data, country, pillars=base_pillars,
                                       score_df=_baseline_score_matrix(method))
    cust_res = chips.aggregate_country(data, country, pillars=custom_pillars,
                                       score_df=_custom_score_matrix(method, spec_json, overrides_json))

    def _rank(df, c):
        scored = df.dropna(subset=["chips"])
        row = scored[scored["Country"] == c]
        return int(row["rank"].iloc[0]) if not row.empty else None

    base_rank, cust_rank = _rank(baseline_scores, country), _rank(custom_scores, country)
    base_chips = base_res.chips.score
    cust_chips = cust_res.chips.score

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Baseline CHIPS", f"{base_chips:.3f}" if base_chips is not None else "no score")
    m2.metric("Custom CHIPS", f"{cust_chips:.3f}" if cust_chips is not None else "no score",
              delta=(None if cust_chips is None or base_chips is None else f"{cust_chips - base_chips:+.3f}"))
    m3.metric("Rank", f"#{cust_rank}" if cust_rank else "—",
              delta=(None if cust_rank is None or base_rank is None else f"{cust_rank - base_rank:+d}"),
              help="Rank under your framework, with the change from the baseline rank.")
    m4.metric("Data coverage", f"{cust_res.coverage['coverage'] * 100:.0f}%",
              help="Share of the custom CHIPS weight backed by an actual value.")

    st.markdown("#### Pillar breakdown — baseline vs your framework")
    rows = []
    all_pillar_names = list(dict.fromkeys([p.name for p in base_pillars] + [p.name for p in custom_pillars]))
    base_by_name = {p.name: p for p in base_pillars}
    cust_by_name = {p.name: p for p in custom_pillars}
    for name in all_pillar_names:
        bp = base_by_name.get(name)
        cp = cust_by_name.get(name)
        b_score = bp and next((pr.score for pr in base_res.pillars if pr.name == name), None)
        c_score = cp and next((pr.score for pr in cust_res.pillars if pr.name == name), None)
        rows.append({
            "Pillar": name,
            "Baseline weight": (bp.weight if bp else np.nan) * 100,
            "Your weight": (cp.weight if cp else np.nan) * 100,
            "Baseline score": b_score,
            "Your score": c_score,
            "Δ score": (None if b_score is None or c_score is None else c_score - b_score),
        })
    p_df = pd.DataFrame(rows)
    pcfg = {
        "Pillar": st.column_config.TextColumn("Pillar"),
        "Baseline weight": st.column_config.NumberColumn("Baseline weight (%)", format="%.1f"),
        "Your weight": st.column_config.NumberColumn("Your weight (%)", format="%.1f"),
        "Baseline score": st.column_config.NumberColumn("Baseline score", format="%.2f"),
        "Your score": st.column_config.NumberColumn("Your score", format="%.2f"),
        "Δ score": st.column_config.NumberColumn("Δ score", format="%+.2f"),
    }
    ui.show_table(p_df.round(3), column_config=pcfg, height=280)

    st.markdown("#### Score breakdown under your framework")
    rows = chips.tree_to_frame(cust_res.chips, chips.leaf_global_weights(custom_pillars))
    st.plotly_chart(charts.chips_treemap(rows), width="stretch")
    st.caption("Area = share of the CHIPS weight **under your framework**; colour = pillar hue "
               "shaded by score. Hover any block to see its weight, score and missing-data "
               "status — overridden indicators are marked 'your override'.")
