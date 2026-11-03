import copy
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "SIDE_dashboard")

from components import country_names
from core import chips, chips_hierarchy as H, scaling
from core.loader import load_app_data

GII_PATH = "data/WIPO Global Innovation Index/gii_indicators_side2026_countries.csv"
OUT = Path("deliverables/gii-eye-test/pretreatment")
OUT.mkdir(parents=True, exist_ok=True)

gii_raw = pd.read_csv(GII_PATH, dtype=str, keep_default_na=False)
DATASETS = {
    "Absolute": load_app_data("data/SIDE 2026 - Absolute.csv"),
    "Relative": load_app_data("data/SIDE 2026 - Relative.csv"),
}
iso_to_country = {country_names.COUNTRY_TO_ISO3[c]: c for c in DATASETS["Absolute"].country_list}
gii_raw["dashboard_country"] = gii_raw["iso3"].map(iso_to_country)

CANDIDATES = [
    ("market_cap_pct_gdp", "Market capitalisation, % GDP", "fetched", "market_cap_pct_gdp_year", "INNOVATE", "Investments and Startups", "% GDP", (0, 300)),
    ("mht_manufacturing_pct", "Medium/high-tech manufacturing, % MVA", "fetched", "mht_manufacturing_pct_year", "HARNESS", "Real Economy", "% manufacturing VA", (0, 100)),
    ("fdi_net_inflows_pct_gdp", "FDI net inflows, % GDP", "fetched", "fdi_net_inflows_pct_gdp_year", "INNOVATE", "Investments and Startups", "% GDP", (-40, 50)),
    ("gerd_pct_gdp", "Gross R&D expenditure, % GDP", "fetched", "gerd_pct_gdp_year", "INNOVATE", "Investments and Startups", "% GDP", (0, 10)),
    ("patent_apps_residents", "Resident patent applications (count)", "fetched", "patent_apps_residents_year", "INNOVATE", "Investments and Startups", "count", (0, None)),
    ("sci_tech_articles_wdi", "Scientific & technical articles (count)", "fetched", "sci_tech_articles_wdi_year", "INNOVATE", "AI", "count", (0, None)),
    ("low_carbon_share_primary_energy_pct", "Low-carbon share of primary energy, %", "fetched", "low_carbon_share_primary_energy_pct_year", "SUSTAINABILITY", "Sustainability", "%", (0, 100)),
    ("gdp_per_unit_energy_use", "GDP per unit of energy use", "fetched", "gdp_per_unit_energy_use_year", "SUSTAINABILITY", "Sustainability", "PPP$/kgoe", (0, None)),
    ("github_git_pushes_2025", "GitHub git pushes 2025 (count)", "fetched", "fixed:2025", "HARNESS", "Apps and platform", "count", (0, None)),
    ("openalex_articles_2024", "OpenAlex articles 2024 (count)", "fetched", "fixed:2024", "INNOVATE", "AI", "count", (0, None)),
    ("openalex_company_articles_2024", "OpenAlex company-authored articles 2024", "fetched", "fixed:2024", "INNOVATE", "AI", "count", (0, None)),
    ("ict_service_exports_usd", "ICT service exports, USD", "fetched", "ict_service_exports_usd_year", "HARNESS", "Real Economy", "USD", (0, None)),
    ("ip_receipts_usd", "IP receipts, USD", "fetched", "ip_receipts_usd_year", "INNOVATE", "Investments and Startups", "USD", (0, None)),
    ("patents_per_bn_ppp_gdp", "Resident patents per bn PPP$ GDP", "derived", "parent:patent_apps_residents", "INNOVATE", "Investments and Startups", "per bn PPP$ GDP", (0, None)),
    ("sci_articles_wdi_per_bn_ppp_gdp", "Articles per bn PPP$ GDP", "derived", "parent:sci_tech_articles_wdi", "INNOVATE", "AI", "per bn PPP$ GDP", (0, None)),
    ("github_git_pushes_per_mn_pop_2025", "GitHub pushes per mn population", "derived", "fixed:2025", "HARNESS", "Apps and platform", "per mn pop", (0, None)),
    ("openalex_articles_per_bn_ppp_gdp_2024", "OpenAlex articles per bn PPP$ GDP", "derived", "fixed:2024", "INNOVATE", "AI", "per bn PPP$ GDP", (0, None)),
    ("openalex_company_share_pct_2024", "Company-authored article share, %", "derived", "fixed:2024", "INNOVATE", "AI", "%", (0, 100)),
]
CAND_DICT = {c[0]: c for c in CANDIDATES}

EXACT = {
    "market_cap_pct_gdp": "winsor_top_2",
    "fdi_net_inflows_pct_gdp": "winsor_bottom_1",
    "patents_per_bn_ppp_gdp": "log",
    "sci_articles_wdi_per_bn_ppp_gdp": "none",
    "github_git_pushes_per_mn_pop_2025": "winsor_top_1",
    "mht_manufacturing_pct": "none",
    "gerd_pct_gdp": "none",
    "low_carbon_share_primary_energy_pct": "none",
    "gdp_per_unit_energy_use": "none",
}

GII_TREATMENT = {
    "market_cap_pct_gdp": "4.2.1: winsor top (2)",
    "fdi_net_inflows_pct_gdp": "5.3.4: winsor bottom (1)",
    "patents_per_bn_ppp_gdp": "6.1.1: log",
    "sci_articles_wdi_per_bn_ppp_gdp": "6.1.4: none",
    "github_git_pushes_per_mn_pop_2025": "7.3.2: winsor top (1)",
    "mht_manufacturing_pct": "6.2.4: none",
    "gerd_pct_gdp": "2.3.2: none",
    "low_carbon_share_primary_energy_pct": "3.3.2: none",
    "gdp_per_unit_energy_use": "3.3.1: none",
}


def num(col):
    return pd.to_numeric(gii_raw[col], errors="coerce")


def wipo_log(s):
    s = s.dropna().astype(float)
    lo, hi = s.min(), s.max()
    if hi == lo:
        return s
    scaled = 1 + (s - lo) * (hi - 1) / (hi - lo)
    return np.log(scaled)


def cap_top(s, n):
    s = s.dropna().copy()
    ordered = s.sort_values(ascending=False)
    if n >= len(ordered):
        return s
    cap = ordered.iloc[n]
    s[s > cap] = cap
    return s


def cap_bottom(s, n):
    s = s.dropna().copy()
    ordered = s.sort_values()
    if n >= len(ordered):
        return s
    cap = ordered.iloc[n]
    s[s < cap] = cap
    return s


def generic_treatment(s):
    s = s.dropna().astype(float)
    sk, ku = s.skew(), s.kurt()
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    n_out = int(((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).sum())
    flagged = (abs(sk) > 2.25 and ku > 3.5) or (abs(sk) <= 2.25 and ku > 10)
    if not flagged:
        return s, "none", n_out, sk, ku
    if n_out > 5 and s.min() > 0:
        return wipo_log(s), "log", n_out, sk, ku
    if sk < 0:
        return cap_bottom(s, n_out), f"winsor_bottom_{n_out}", n_out, sk, ku
    return cap_top(s, n_out), f"winsor_top_{n_out}", n_out, sk, ku


def treat(col):
    s = num(col)
    if col in EXACT:
        mode = EXACT[col]
        if mode == "log":
            return wipo_log(s), "log", GII_TREATMENT[col]
        if mode.startswith("winsor_top_"):
            n = int(mode.rsplit("_", 1)[1])
            return cap_top(s, n), mode, GII_TREATMENT[col]
        if mode.startswith("winsor_bottom_"):
            n = int(mode.rsplit("_", 1)[1])
            return cap_bottom(s, n), mode, GII_TREATMENT[col]
        return s.dropna(), "none", GII_TREATMENT[col]
    treated, mode, n_out, sk, ku = generic_treatment(s)
    return treated, mode, f"generic rule (skew={sk:.2f}, kurt={ku:.1f}, {n_out} Tukey out)"


def sp(a, b):
    idx = a.dropna().index.intersection(b.dropna().index)
    if len(idx) < 3:
        return np.nan
    return float(a.loc[idx].rank().corr(b.loc[idx].rank()))


def norm01(s):
    s = s.dropna()
    if s.max() == s.min():
        return pd.Series(0.0, index=s.index)
    return (s - s.min()) / (s.max() - s.min())


def concentration(s):
    s = s.dropna()
    if len(s) < 3:
        return {}
    ordered = s.sort_values(ascending=False)
    return {
        "top1_minus_top2": float(ordered.iloc[0] - ordered.iloc[1]),
        "median": float(s.median()),
        "share_below_025": float((s < 0.25).mean()),
    }


gdp = num("gdp_ppp_current_usd")
pop = num("population")
log_gdp, log_pop = np.log(gdp.replace(0, np.nan)), np.log(pop.replace(0, np.nan))

treated = {}
treatment_rows = []
for c in CANDIDATES:
    col = c[0]
    treated[col], mode, label = treat(col)
    raw = num(col)
    raw_norm = norm01(raw)
    post_norm = norm01(treated[col])
    raw_conc = concentration(raw_norm)
    post_conc = concentration(post_norm)
    treatment_rows.append({
        "Column": col,
        "Indicator": c[1],
        "GII mapping / rule": label,
        "Treatment": mode,
        "n": int(raw.notna().sum()),
        "raw median normalised": round(raw_conc.get("median", np.nan), 3),
        "post median normalised": round(post_conc.get("median", np.nan), 3),
        "raw share below 0.25": round(raw_conc.get("share_below_025", np.nan), 3),
        "post share below 0.25": round(post_conc.get("share_below_025", np.nan), 3),
        "raw top1-top2": round(raw_conc.get("top1_minus_top2", np.nan), 4),
        "post top1-top2": round(post_conc.get("top1_minus_top2", np.nan), 4),
    })
treatments = pd.DataFrame(treatment_rows)
treatments.to_csv(OUT / "wipo_pretreatment_map.csv", index=False)

dist_rows = []
for c in CANDIDATES:
    col = c[0]
    s = treated[col]
    n = norm01(s)
    lo, hi = c[7]
    viol = []
    if lo is not None and (s < lo).any():
        viol.append("below lower bound")
    if hi is not None and (s > hi).any():
        viol.append("above upper bound")
    dist_rows.append({
        "Column": col,
        "Indicator": c[1],
        "Treatment": treatments.loc[treatments.Column == col, "Treatment"].iloc[0],
        "n": int(s.notna().sum()),
        "Min": round(float(s.min()), 4),
        "Median": round(float(s.median()), 4),
        "Max": round(float(s.max()), 4),
        "Skew": round(float(s.skew()), 2),
        "Kurt": round(float(s.kurt()), 1),
        "Max/Median": round(float(s.max() / s.median()), 2) if s.median() > 0 else np.nan,
        "Median normalised": round(float(n.median()), 3),
        "Share < 0.25": round(float((n < 0.25).mean()), 3),
        "Bounds issues": " | ".join(viol),
        "Size r(GDP)": round(sp(s, log_gdp), 2),
        "Size r(Pop)": round(sp(s, log_pop), 2),
    })
dist = pd.DataFrame(dist_rows)
dist.to_csv(OUT / "wipo_pretreatment_distribution.csv", index=False)

construct_rows = []
for base in ["Absolute", "Relative"]:
    d = DATASETS[base]
    pillars, _ = H.resolve_hierarchy(d.numeric_df.columns)
    tab = chips.chips_table(d, pillars=pillars, method=scaling.METHOD_Z)
    for c in CANDIDATES:
        s = treated[c[0]]
        series = pd.Series(
            d.numeric_df["Country"].map(dict(zip(gii_raw.loc[s.index, "dashboard_country"], s))).values,
            index=d.numeric_df.index,
        )
        pillar_score = tab.set_index("Country")[c[4]]
        pair = pd.DataFrame({
            "x": series,
            "y": series.index.map(lambda i: pillar_score.get(d.numeric_df.loc[i, "Country"])),
        })
        r = sp(pair["x"], pair["y"])
        construct_rows.append({
            "Base": base,
            "Column": c[0],
            "Target pillar": c[4],
            "Construct r": round(float(r), 3) if pd.notna(r) else np.nan,
        })
construct = pd.DataFrame(construct_rows)
construct.to_csv(OUT / "wipo_pretreatment_construct_validity.csv", index=False)

PAIRS = [
    ("patent_apps_residents", "patents_per_bn_ppp_gdp"),
    ("sci_tech_articles_wdi", "sci_articles_wdi_per_bn_ppp_gdp"),
    ("github_git_pushes_2025", "github_git_pushes_per_mn_pop_2025"),
    ("openalex_articles_2024", "openalex_articles_per_bn_ppp_gdp_2024"),
    ("openalex_articles_2024", "openalex_company_share_pct_2024"),
]
pair_rows = []
for raw_col, der_col in PAIRS:
    a, b = treated[raw_col], treated[der_col]
    pair_rows.append({
        "Raw": raw_col,
        "Derived": der_col,
        "Spearman(raw, derived)": round(float(sp(a, b)), 3),
        "Size r(GDP) raw": round(float(sp(a, log_gdp)), 2),
        "Size r(GDP) derived": round(float(sp(b, log_gdp)), 2),
    })
pd.DataFrame(pair_rows).to_csv(OUT / "wipo_pretreatment_raw_vs_derived.csv", index=False)


def inject_series(d, col, values_by_country):
    nd = d.numeric_df.copy()
    nd[col] = nd["Country"].map(values_by_country)
    new = copy.copy(d)
    new.numeric_df = nd
    new.higher_is_better = dict(d.higher_is_better)
    new.higher_is_better[col] = True
    new.indicators = list(d.indicators) + [col]
    return new


def shadow_spec(pillar, col):
    spec = copy.deepcopy(H.HIERARCHY)
    for p in spec:
        if p["name"] == pillar:
            p["sub_pillars"].append({"name": f"Shadow: {col}", "indicators": [(col, 1.0)]})
            break
    return spec


infl_rows = []
BASELINE = {}
for base in DATASETS:
    for method in [scaling.METHOD_FULL, scaling.METHOD_Z]:
        d = DATASETS[base]
        pillars, _ = H.resolve_hierarchy(d.numeric_df.columns)
        BASELINE[(base, method)] = (d, pillars, chips.chips_table(d, pillars=pillars, method=method))

values_by_country = {
    c[0]: dict(zip(gii_raw.loc[treated[c[0]].index, "dashboard_country"], treated[c[0]]))
    for c in CANDIDATES
}

for c in CANDIDATES:
    col, label, kind, _ys, pillar, sub, units, _bounds = c
    for base in DATASETS:
        d0, pillars0, tab0 = BASELINE[(base, scaling.METHOD_FULL)]
        aug = inject_series(d0, col, values_by_country[col])
        spec = shadow_spec(pillar, col)
        pillars1, unres = H.resolve_hierarchy(aug.numeric_df.columns, spec=spec)
        assert not unres, unres
        gw = chips.leaf_global_weights(pillars1).get(col, np.nan)
        for method in [scaling.METHOD_FULL, scaling.METHOD_Z]:
            _, _, tab_base = BASELINE[(base, method)]
            tab_sh = chips.chips_table(aug, pillars=pillars1, method=method)
            j = tab_base[["Country", "chips", "rank", pillar]].merge(
                tab_sh[["Country", "chips", "rank", pillar]], on="Country", suffixes=("_b", "_s")
            )
            j["dpillar"] = j[f"{pillar}_s"] - j[f"{pillar}_b"]
            j["dchips"] = j["chips_s"] - j["chips_b"]
            j["drank"] = j["rank_s"] - j["rank_b"]
            top = j.reindex(j["dchips"].abs().sort_values(ascending=False).index).iloc[0]
            sc = chips.score_matrix(aug, pillars1, method=method)[col]
            conc = concentration(sc)
            infl_rows.append({
                "Base": base,
                "Method": method,
                "Column": col,
                "Pillar": pillar,
                "Shadow global weight": round(float(gw), 4),
                "max |dPillar|": round(float(j["dpillar"].abs().max()), 3),
                "max |dCHIPS|": round(float(j["dchips"].abs().max()), 3),
                "max |dRank|": int(j["drank"].abs().max()),
                "Top CHIPS mover": f"{top['Country']} ({top['dchips']:+.3f})",
                "Indicator median score": round(conc.get("median", np.nan), 3),
                "Share below 0.25": round(conc.get("share_below_025", np.nan), 3),
            })
infl = pd.DataFrame(infl_rows)
infl.to_csv(OUT / "wipo_pretreatment_chips_influence.csv", index=False)

worst = (
    infl.groupby(["Column", "Pillar"])
    .agg(
        max_dCHIPS=("max |dCHIPS|", "max"),
        max_dRank=("max |dRank|", "max"),
        shadow_w=("Shadow global weight", "max"),
        top_mover=("Top CHIPS mover", "first"),
    )
    .reset_index()
    .sort_values("max_dRank", ascending=False)
)

score = treatments.merge(
    dist[["Column", "Skew", "Kurt", "Max/Median", "Bounds issues", "Size r(GDP)", "Size r(Pop)"]],
    on="Column",
)
score = score.merge(worst[["Column", "max_dCHIPS", "max_dRank", "top_mover"]], on="Column", how="left")
con_abs = construct[construct.Base == "Absolute"].set_index("Column")["Construct r"]
score["Construct r (Abs)"] = score["Column"].map(con_abs)
score.to_csv(OUT / "wipo_pretreatment_scorecard.csv", index=False)

print("Wrote", OUT)
print(treatments[["Column", "Treatment", "raw median normalised", "post median normalised", "raw share below 0.25", "post share below 0.25"]].to_string(index=False))
print("\nWorst influence:")
print(worst[["Column", "max_dCHIPS", "max_dRank", "top_mover"]].to_string(index=False))
