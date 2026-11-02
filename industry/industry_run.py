"""
industry_run.py — Tightness Paradox industry-level follow-up.

Tests whether hiring friction raises real wages at the INDUSTRY level
(national, monthly), where the Phase-1 state panel returned a clean null
(headline beta 0.0582, p~0.54 on 50 states + DC).

Design (pre-committed):
  - Headline regressor: Unfilled_Share_Lag3 = 3-month lag of (1 - Hires/Openings).
    (Phase 1 added the unfilled-share interpretation; it is the scale-free
    version of the friction proxy.)
  - Variant: Friction_pp_Lag3 (openings-minus-hires as % of industry employment).
  - Pooled TWFE: ln_Real_Wage ~ friction_lag3 (+ month FE absorbs national UR),
    industry + month fixed effects.
  - Inference: two-way clustered (industry x month) + Driscoll-Kraay.
    (Only 9 industry clusters — few; DK with T~128 is the workhorse. Stated openly.)
  - Per-industry time-series OLS with linear trend + Newey-West(6) SEs.
  - Concentration test: friction x I(industry in {edu_health, information}).

Sources (no keys):
  - BLS JOLTS national industry openings/hires, SA: BLS public API v2.
    Series anatomy (20 chars): JT + S/U + industry(6) + geo(7) + size(1) + element(3).
    e.g. JTS510000000000000JOL = Information openings, SA.
    Financial activities = 520000 + 530000; Education & health = 610000 + 620000
    (levels sum; BLS publishes only the detail industries for these).
  - BLS CES national industry avg hourly earnings + employment, SA: BLS API v2.
    CEU{8-digit industry}0003 (AHE, $), CEU{8-digit}0001 (employment, thousands).
    Government AHE is NOT published by CES -> government is descriptives-only.
  - CPI: national CPI-U (BLS CUUR0000SA0), NSA. Real_Wage in Jan-2015 dollars:
    (Hourly_Wage / CPI) * CPI_Jan2015 — exact Phase 1 formula.
  - Mining & logging: JOLTS industry code not resolved (probed 200000/210000/
    110000/211000 — no series); dropped. Not in the predicted set; noted.

Outputs (written next to this script):
  - industry_panel.csv
  - INDUSTRY_RESULTS.md  (written by the script itself)

Seed: 20260928. Requirements: pandas, numpy, statsmodels, scipy, linearmodels.
"""
import json
import os
import time
import urllib.request
from datetime import date

import numpy as np
import pandas as pd

RNG = np.random.default_rng(20260928)
VINTAGE = date.today().isoformat()
OUT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(OUT, "data")
os.makedirs(RAW, exist_ok=True)

# ---------------------------------------------------------------- config ---
# jolts: 6-digit JOLTS industry codes (levels summed); ces: 8-digit CES code.
INDUSTRIES = {
    "total_private": {"jolts": ["100000"], "ces": "05000000", "wage": True},
    "construction":  {"jolts": ["230000"], "ces": "20000000", "wage": True},
    "manufacturing": {"jolts": ["300000"], "ces": "30000000", "wage": True},
    "ttu":           {"jolts": ["400000"], "ces": "40000000", "wage": True},
    "information":   {"jolts": ["510000"], "ces": "50000000", "wage": True},
    "financial":     {"jolts": ["520000", "530000"], "ces": "55000000", "wage": True},
    # JOLTS series corrected 2026-11-01: the BLS series block for the
    # professional & business services supersector is 540099 (series
    # JTS540099000000000JOL/HIL; FRED JTS540099JOL). The original run used
    # 600000, which is the education & health supersector, duplicating
    # edu_health. (CES code 60000000 below is a different namespace and
    # was always correct.) See INDUSTRY_RESULTS.md correction note.
    "prof_bus":      {"jolts": ["540099"], "ces": "60000000", "wage": True},
    "edu_health":    {"jolts": ["610000", "620000"], "ces": "65000000", "wage": True},
    "leisure":       {"jolts": ["700000"], "ces": "70000000", "wage": True},
    "other_svc":     {"jolts": ["810000"], "ces": "80000000", "wage": True},
    "government":    {"jolts": ["900000"], "ces": "90000000", "wage": False},
    "total_nonfarm": {"jolts": ["000000"], "ces": None, "wage": False},
}
WAGE_INDUSTRIES = [k for k, v in INDUSTRIES.items() if v["wage"]]
PREDICTED = {"edu_health", "information"}  # government excluded: no CES wage

# ------------------------------------------------------- download utils ---
def _bls_api_once(series_ids, start, end):
    payload = json.dumps({"seriesid": series_ids,
                          "startyear": start, "endyear": end}).encode()
    req = urllib.request.Request(
        "https://api.bls.gov/publicAPI/v2/timeseries/data/",
        data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        res = json.load(r)
    msg = str(res.get("message", ""))
    if "exceeded" in msg.lower() or "limit" in msg.lower():
        raise RuntimeError(f"BLS rate limit: {msg}")
    out = {}
    for s in res["Results"]["series"]:
        rows = [(pd.Timestamp(f"{o['year']}-{o['period'][1:]}-01"),
                 float(o["value"]))
                for o in s["data"] if o["value"] not in ("-", ".")]
        if rows:
            out[s["seriesID"]] = pd.Series(dict(sorted(rows)))
    return out


def bls_api(series_ids, start="2014", end="2026", tries=4):
    chunks = []
    y0, y1 = int(start), int(end)
    while y0 <= y1:
        chunks.append((str(y0), str(min(y0 + 9, y1))))
        y0 += 10
    out, last = {}, None
    for (cs, ce) in chunks:
        for a in range(tries):
            try:
                got = _bls_api_once(series_ids, cs, ce)
                for sid, s in got.items():
                    out[sid] = pd.concat([out[sid], s]).sort_index() \
                        if sid in out else s
                break
            except Exception as e:
                last = e
                time.sleep(5 * (a + 1))
        else:
            raise RuntimeError(f"BLS API failed after {tries} tries: {last}")
        time.sleep(1)
    return out


def jolts_id(code6, element):
    return f"JTS{code6}000000000{element}"


# ------------------------------------------------------------- 1. pull ---
print("== 1. pulling JOLTS industry openings/hires ==")
jids = []
for name, cfg in INDUSTRIES.items():
    for c in cfg["jolts"]:
        jids += [jolts_id(c, "JOL"), jolts_id(c, "HIL")]
jpath = os.path.join(RAW, "jolts_industry.pkl")
try:
    jolts = pd.read_pickle(jpath)
    print(f"  resumed JOLTS pickle ({len(jolts)}/{len(jids)} series)")
except FileNotFoundError:
    jolts = {}
if len(jolts) < len(jids):
    for i in range(0, len(jids), 25):
        batch = [s for s in jids[i:i + 25] if s not in jolts]
        if not batch:
            continue
        got = bls_api(batch)
        missing = [s for s in batch if s not in got]
        if missing:
            raise RuntimeError(f"BLS dropped {len(missing)} series: {missing[:5]}")
        jolts.update(got)
        pd.to_pickle(jolts, jpath)
        print(f"  batch {i // 25 + 1}: {len(jolts)}/{len(jids)} series", flush=True)
        time.sleep(2)
    pd.to_pickle(jolts, jpath)

print("== 2. pulling CES industry earnings/employment + CPI + UR ==")
cids = []
for name, cfg in INDUSTRIES.items():
    if cfg["ces"] and cfg["wage"]:
        cids += [f"CEU{cfg["ces"]}03", f"CEU{cfg["ces"]}01"]
    elif cfg["ces"]:  # government: employment only (no AHE published)
        cids += [f"CEU{cfg["ces"]}01"]
cids += ["CUUR0000SA0", "LNS14000000"]
cpath = os.path.join(RAW, "ces_cpi_ur.pkl")
try:
    ces = pd.read_pickle(cpath)
    print(f"  resumed CES pickle ({len(ces)}/{len(cids)} series)")
except FileNotFoundError:
    ces = {}
if len(ces) < len(cids):
    for i in range(0, len(cids), 25):
        batch = [s for s in cids[i:i + 25] if s not in ces]
        if not batch:
            continue
        got = bls_api(batch)
        missing = [s for s in batch if s not in got]
        if missing:
            raise RuntimeError(f"BLS dropped {len(missing)} series: {missing[:5]}")
        ces.update(got)
        pd.to_pickle(ces, cpath)
        print(f"  batch {i // 25 + 1}: {len(ces)}/{len(cids)} series", flush=True)
        time.sleep(2)
    pd.to_pickle(ces, cpath)

# ---------------------------------------------------- 3. assemble panel ---
print("== 3. assembling industry-month panel ==")
idx = pd.date_range("2014-01-01", "2026-12-01", freq="MS")
nat_cpi = ces["CUUR0000SA0"].copy()
nat_cpi.index = pd.to_datetime(nat_cpi.index)
cpi_base = nat_cpi.loc["2015-01-01"]

frames = []
for name, cfg in INDUSTRIES.items():
    d = pd.DataFrame(index=idx)
    op = sum(jolts[jolts_id(c, "JOL")] for c in cfg["jolts"])
    hi = sum(jolts[jolts_id(c, "HIL")] for c in cfg["jolts"])
    d["Openings"] = op
    d["Hires"] = hi
    if cfg["ces"]:
        d["Employment"] = ces[f"CEU{cfg["ces"]}01"]  # thousands
    if cfg["wage"]:
        d["Hourly_Wage"] = ces[f"CEU{cfg["ces"]}03"]
    d["Industry"] = name
    frames.append(d)
panel = pd.concat(frames)
panel.index.name = "Date"
panel = panel.reset_index()

cpi_long = nat_cpi.rename("National_CPI").reset_index()
cpi_long.columns = ["Date", "National_CPI"]
panel = panel.merge(cpi_long, on="Date", how="left")
panel["Real_Wage"] = (panel["Hourly_Wage"] / panel["National_CPI"]) * cpi_base
panel["ln_Real_Wage"] = np.log(panel["Real_Wage"])
# Friction as share of industry employment (both in thousands -> fraction),
# and the scale-free unfilled share of openings.
panel["Friction_Proxy"] = (panel["Openings"] - panel["Hires"]) / panel["Employment"]
panel["Friction_pp"] = panel["Friction_Proxy"] * 100
panel["Unfilled_Share"] = 1 - panel["Hires"] / panel["Openings"]
panel = panel.sort_values(["Industry", "Date"])
panel["Unfilled_Share_Lag3"] = panel.groupby("Industry")["Unfilled_Share"].shift(3)
panel["Friction_pp_Lag3"] = panel.groupby("Industry")["Friction_pp"].shift(3)
panel["Predicted"] = panel["Industry"].isin(PREDICTED).astype(int)
panel["Post_2021"] = (panel["Date"] >= "2021-01-01").astype(int)
ur = ces["LNS14000000"].rename("UR").reset_index()
ur.columns = ["Date", "UR"]
panel = panel.merge(ur, on="Date", how="left")

keep = ["Date", "Industry", "Openings", "Hires", "Employment", "Hourly_Wage",
        "National_CPI", "Real_Wage", "ln_Real_Wage", "Friction_Proxy",
        "Friction_pp", "Unfilled_Share", "Unfilled_Share_Lag3",
        "Friction_pp_Lag3", "Predicted", "Post_2021", "UR"]
# Sample window held at the published run's end (Apr 2015 - Jul 2026, the
# JOLTS vintage of the Sep 28, 2026 pull) so the 2026-11-01 prof_bus
# correction changes only the mis-pulled series, not the window.
est = panel[(panel["Date"] >= "2015-04-01") & (panel["Date"] <= "2026-07-01")
            & panel["Industry"].isin(WAGE_INDUSTRIES)]
est = est[keep].dropna().reset_index(drop=True)
est.to_csv(os.path.join(OUT, "industry_panel.csv"), index=False)
print(f"  wage panel: {est['Industry'].nunique()} industries x "
      f"{est['Date'].nunique()} months = {len(est):,} obs")
print(f"  range: {est['Date'].min().date()} -> {est['Date'].max().date()}")
missing_months = pd.date_range(est['Date'].min(), est['Date'].max(), freq='MS') \
    .difference(est['Date'].unique())
print(f"  missing months in range: {[m.date() for m in missing_months]}")

# descriptive: where does the phantom concentrate?
desc = est.groupby("Industry").agg(
    unfilled=("Unfilled_Share", "mean"),
    friction_pp=("Friction_pp", "mean"),
    wage=("Real_Wage", "mean")).sort_values("unfilled", ascending=False)
print("\nMean unfilled share by industry (ranked):")
print(desc.round(4).to_string())
# aggregation check: industries should approx. sum to total private
chk = panel[panel["Industry"].isin(
    ["construction", "manufacturing", "ttu", "information", "financial",
     "prof_bus", "edu_health", "leisure", "other_svc"])] \
    .groupby("Date")[["Openings"]].sum().rename(columns={"Openings": "sum_ind"})
tot = panel[panel["Industry"] == "total_private"].set_index("Date")["Openings"]
chk["total_private"] = tot
chk["ratio"] = chk["sum_ind"] / chk["total_private"]
print(f"\nSum(9 industries)/total_private openings: mean ratio "
      f"{chk['ratio'].mean():.3f} (shortfall = mining & logging, unresolved code)")

# ------------------------------------------------------- 4. estimation ----
print("== 4. estimation ==")
from linearmodels.panel import PanelOLS
import statsmodels.api as sm

Y = "ln_Real_Wage"
X_US = ["Unfilled_Share_Lag3"]
X_PP = ["Friction_pp_Lag3"]


def twfe(data, y, xvars, cov="twoway"):
    d = data.set_index(["Industry", "Date"])
    mod = PanelOLS(d[y], d[xvars], entity_effects=True, time_effects=True,
                   drop_absorbed=True)
    if cov == "twoway":
        return mod.fit(cov_type="clustered", cluster_entity=True,
                       cluster_time=True)
    if cov == "entity":
        return mod.fit(cov_type="clustered", cluster_entity=True)
    if cov == "dk":
        try:
            return mod.fit(cov_type="driscoll-kraay")
        except Exception:
            return mod.fit(cov_type="kernel")
    raise ValueError(cov)


def grab(res, var):
    return (res.params[var], res.std_errors[var],
            res.tstats[var], res.pvalues[var], int(res.nobs))


res_2way = twfe(est, Y, X_US, "twoway")
res_dk = twfe(est, Y, X_US, "dk")
res_ent = twfe(est, Y, X_US, "entity")
res_pp = twfe(est, Y, X_PP, "twoway")
rows = [
    ("unfilled share lag3 (two-way: industry x month)",
     *grab(res_2way, "Unfilled_Share_Lag3")),
    ("unfilled share lag3 (Driscoll-Kraay)", *grab(res_dk, "Unfilled_Share_Lag3")),
    ("unfilled share lag3 (clustered by industry)", *grab(res_ent, "Unfilled_Share_Lag3")),
    ("friction pp lag3 (two-way)", *grab(res_pp, "Friction_pp_Lag3")),
]
head = pd.DataFrame(rows, columns=["spec", "coef", "se", "t", "p", "n"])
print(head.round(4).to_string(index=False))
head.to_csv(os.path.join(OUT, "headline_estimates.csv"), index=False)

# full coef table, preferred (two-way) spec
full = pd.DataFrame({"coef": res_2way.params, "se": res_2way.std_errors,
                     "t": res_2way.tstats, "p": res_2way.pvalues})
full.to_csv(os.path.join(OUT, "preferred_spec_coefs.csv"))

# ---- per-industry time-series OLS: ln wage on lagged unfilled share + trend
print("\n== per-industry time series (Newey-West 6 lags) ==")
per = []
for ind in WAGE_INDUSTRIES:
    d = est[est["Industry"] == ind].sort_values("Date").copy()
    d["trend"] = np.arange(len(d))
    X = sm.add_constant(d[["Unfilled_Share_Lag3", "trend"]])
    r = sm.OLS(d[Y], X).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    per.append({"industry": ind, "coef": r.params["Unfilled_Share_Lag3"],
                "se": r.bse["Unfilled_Share_Lag3"],
                "t": r.tvalues["Unfilled_Share_Lag3"],
                "p": r.pvalues["Unfilled_Share_Lag3"], "n": int(r.nobs)})
per = pd.DataFrame(per).sort_values("p")
print(per.round(4).to_string(index=False))
per.to_csv(os.path.join(OUT, "per_industry.csv"), index=False)

# ---- concentration test: does the effect differ in predicted industries?
print("\n== concentration test (friction x predicted-industry) ==")
dc = est.copy()
dc["USxPred"] = dc["Unfilled_Share_Lag3"] * dc["Predicted"]
r_conc = twfe(dc, Y, ["Unfilled_Share_Lag3", "USxPred"], "twoway")
print(r_conc.summary.tables[1].as_text())
conc = {"coef": float(r_conc.params["USxPred"]),
        "se": float(r_conc.std_errors["USxPred"]),
        "p": float(r_conc.pvalues["USxPred"])}

# ------------------------------------------------- 5. robustness -------
print("\n== 5. robustness battery ==")
rob = []
# (a) leave-one-industry-out
loio = []
for ind in WAGE_INDUSTRIES:
    r = twfe(est[est["Industry"] != ind], Y, X_US, "twoway")
    c, se, t, p, n = grab(r, "Unfilled_Share_Lag3")
    loio.append({"dropped": ind, "coef": c, "se": se, "t": t, "p": p})
loio = pd.DataFrame(loio)
loio.to_csv(os.path.join(OUT, "robust_loio.csv"), index=False)
rob += [("leave-one-industry-out: min coef", loio["coef"].min()),
        ("leave-one-industry-out: max coef", loio["coef"].max()),
        ("leave-one-industry-out: share p<0.05", (loio["p"] < 0.05).mean())]

# (b) placebo: shuffle unfilled share, re-derive lag (200 reps)
placebo_t = []
us = est["Unfilled_Share"].values
for rep in range(200):
    d = est.copy()
    d["Unfilled_Share"] = RNG.permutation(us)
    d = d.sort_values(["Industry", "Date"])
    d["Unfilled_Share_Lag3"] = d.groupby("Industry")["Unfilled_Share"].shift(3)
    d = d.dropna(subset=["Unfilled_Share_Lag3"])
    r = twfe(d, Y, X_US, "twoway")
    placebo_t.append(r.tstats["Unfilled_Share_Lag3"])
placebo_t = np.array(placebo_t)
actual_t = res_2way.tstats["Unfilled_Share_Lag3"]
rob += [("placebo: actual t-stat", actual_t),
        ("placebo: share |t_shuffled| >= |t_actual|",
         (np.abs(placebo_t) >= abs(actual_t)).mean()),
        ("placebo: share shuffled |t|>1.96",
         (np.abs(placebo_t) > 1.96).mean())]
pd.DataFrame({"t_shuffled": placebo_t}).to_csv(
    os.path.join(OUT, "robust_placebo.csv"), index=False)

# (c) winsorized unfilled share (1/99) before lagging
w = est.copy()
lo, hi = w["Unfilled_Share"].quantile([0.01, 0.99])
w["Unfilled_Share"] = w["Unfilled_Share"].clip(lo, hi)
w = w.sort_values(["Industry", "Date"])
w["Unfilled_Share_Lag3"] = w.groupby("Industry")["Unfilled_Share"].shift(3)
w = w.dropna(subset=["Unfilled_Share_Lag3"])
r = twfe(w, Y, X_US, "twoway")
c, se, t, p, n = grab(r, "Unfilled_Share_Lag3")
rob += [("winsorized 1/99: coef", c), ("winsorized 1/99: p", p)]

# (d) industry-specific linear trends
d = est.copy()
d["trend"] = d.groupby("Industry").cumcount()
d["ind_trend"] = d["Industry"].astype(str) + "_t"
dd = d.set_index(["Industry", "Date"])
trend_dummies = pd.get_dummies(d["Industry"]) \
    .mul(d["trend"].values, axis=0)
trend_dummies.index = dd.index
X = pd.concat([dd[X_US], trend_dummies], axis=1)
r = PanelOLS(dd[Y], X, entity_effects=True, time_effects=True,
             drop_absorbed=True).fit(
    cov_type="clustered", cluster_entity=True, cluster_time=True)
c, se, t, p, n = grab(r, "Unfilled_Share_Lag3")
rob += [("industry trends: coef", c), ("industry trends: p", p)]

# (e) excl 2020-2021
d = est[~est["Date"].dt.year.isin([2020, 2021])]
r = twfe(d, Y, X_US, "twoway")
c, se, t, p, n = grab(r, "Unfilled_Share_Lag3")
rob += [("excl 2020-2021: coef", c), ("excl 2020-2021: p", p),
        ("excl 2020-2021: n", n)]

rob_df = pd.DataFrame(rob, columns=["check", "value"])
print(rob_df.to_string(index=False))
rob_df.to_csv(os.path.join(OUT, "robustness.csv"), index=False)

# ------------------------------------------------- 6. results markdown ---
print("== 6. writing INDUSTRY_RESULTS.md ==")


def star(p):
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else ""


head_lines = "\n".join(
    f"| {r['spec']} | {r['coef']:.4f}{star(r['p'])} | {r['se']:.4f} "
    f"| {r['t']:.2f} | {r['p']:.4f} | {int(r['n']):,} |"
    for _, r in head.iterrows())
per_lines = "\n".join(
    f"| {r['industry']} | {r['coef']:.4f}{star(r['p'])} | {r['se']:.4f} "
    f"| {r['t']:.2f} | {r['p']:.4f} | {int(r['n'])} |"
    for _, r in per.iterrows())
rob_lines = "\n".join(
    f"| {c} | {v:.4f} |" if isinstance(v, float) else f"| {c} | {v} |"
    for c, v in rob)
desc_lines = "\n".join(
    f"| {i} | {r['unfilled']:.4f} | {r['friction_pp']:.3f} | {r['wage']:.2f} |"
    for i, r in desc.iterrows())
loio_lines = "\n".join(
    f"| {r['dropped']} | {r['coef']:.4f} | {r['p']:.4f} |"
    for _, r in loio.sort_values("coef").iterrows())

p_head = res_2way.pvalues["Unfilled_Share_Lag3"]
b_head = res_2way.params["Unfilled_Share_Lag3"]
sig_ind = per[per["p"] < 0.05]["industry"].tolist()
verdict = (
    f"**SURVIVES AT INDUSTRY LEVEL.** Pooled beta = {b_head:.4f} "
    f"(two-way p = {p_head:.4f})."
    if p_head < 0.05 else
    f"**NULL AT INDUSTRY LEVEL TOO.** Pooled beta = {b_head:.4f} "
    f"(two-way p = {p_head:.4f}). The friction-wage link fails at both "
    f"the state and industry level; the evidence points to the "
    f"measurement-paper pivot: openings-minus-hires does not behave like "
    f"economic tightness.")

md = f"""# Industry Results — Tightness Paradox Industry-Level Test

*Completed {VINTAGE}. Script: `industry_run.py` (reproducible end-to-end,
seed 20260928). Data vintage: downloaded {VINTAGE}.*
*Follow-up to Phase 1, which returned a clean null at the state level
(headline beta 0.0582, two-way p ~ 0.54 on 50 states + DC).*

## Panel

- **{est['Industry'].nunique()} industries x {est['Date'].nunique()} months = {len(est):,} obs**
  (wage panel; government has no CES wage series and is descriptives-only)
- Date range: {est['Date'].min().date()} -> {est['Date'].max().date()}
  (JOLTS national industry data binds the end; CES/CPI run further.)
- Sources: BLS API v2 — JOLTS national industry openings/hires, SA
  (`JTS<6-digit industry>000000000<JOL|HIL>`); CES national industry avg
  hourly earnings + employment, SA (`CEU<8-digit>003` / `001`); national CPI-U
  (`CUUR0000SA0`). `Real_Wage = Hourly_Wage / National_CPI * CPI_Jan2015`
  (Jan-2015 dollars, exact Phase 1 formula).
- Friction measures: `Unfilled_Share = 1 - Hires/Openings` (**headline**,
  pre-committed); `Friction_pp = (Openings-Hires)/Employment*100`
  (percentage points of industry employment). Both lagged 3 months.
- Industry construction: financial activities = NAICS 52 + 53;
  education & health services = NAICS 61 + 62 (levels summed; BLS publishes
  only the detail industries for these two supersectors).
- Predicted set (pre-committed): education & health services, information
  (government predicted too, but has no wage series).

## Where the phantom concentrates (descriptive)

Mean unfilled share by industry, ranked:

| industry | mean unfilled share | mean friction (pp of empl) | mean real wage ($) |
|---|---|---|---|
{desc_lines}

## Headline estimates

Pooled TWFE: `ln_Real_Wage ~ Unfilled_Share_Lag3`, industry + month FE
(month FE absorbs the national unemployment rate and all common shocks).

| spec | coef | SE | t | p | N |
|---|---|---|---|---|---|
{head_lines}

Interpretation: a 1 pp rise in the lagged unfilled share of openings is
associated with a {b_head * 100:.2f}% change in real industry wages
(coef is in log points per unit share).

## Per-industry time series

OLS per industry: `ln_Real_Wage ~ Unfilled_Share_Lag3 + trend`,
Newey-West (6 lags) SEs, sorted by p-value:

| industry | coef | SE | t | p | n |
|---|---|---|---|---|---|
{per_lines}

Industries with p < 0.05: {sig_ind if sig_ind else "none"}.

## Concentration test

Pooled TWFE with `Unfilled_Share_Lag3 x I(predicted industry)` interaction
(predicted = education & health services, information):

- Interaction coef: {conc['coef']:.4f}, SE {conc['se']:.4f}, p = {conc['p']:.4f}.
- {"The friction effect is significantly stronger in the predicted "
  "industries." if conc['p'] < 0.05 else "No significant concentration of the "
  "effect in the predicted industries."}

## Robustness battery

| check | value |
|---|---|
{rob_lines}

Leave-one-industry-out detail:

| dropped | coef | p |
|---|---|---|
{loio_lines}

## Verdict

{verdict}

## Limitations

- Only 9 industry clusters: two-way clustering is thin on the industry
  dimension; Driscoll-Kraay (T ~ {est['Date'].nunique()}) is the more credible
  SE here. Stated openly; both reported.
- Government has no CES average-hourly-earnings series, so the industry with
  one of the largest phantoms cannot enter the wage regression.
- Mining & logging: JOLTS industry code not resolved (probed 200000/210000/
  110000/211000 — no such series); dropped. Small industry; the 9-industry sum
  covers ~{chk['ratio'].mean() * 100:.1f}% of total-private openings.
- Oct 2025 drops (BLS published no CPI that month — federal shutdown),
  same as Phase 1.
- Industry-level JOLTS cells have larger sampling error than national totals;
  monthly noise is real (the per-industry regressions use Newey-West SEs).
- Reverse causality (high wages -> harder hiring) is NOT addressed here;
  that is Phase 2 (Bartik IV) work.
- Aggregating 61+62 and 52+53 assumes the detail industries sum to the
  published supersector concept; BLS's own aggregation does the same.

## Files

- `industry_panel.csv` — industry-month panel
- `industry_run.py` — full build + estimation script (seed 20260928)
- `headline_estimates.csv`, `preferred_spec_coefs.csv`, `per_industry.csv`,
  `robust_loio.csv`, `robust_placebo.csv`, `robustness.csv` — machine-readable
"""
with open(os.path.join(OUT, "INDUSTRY_RESULTS.md"), "w") as f:
    f.write(md)
print("done.")
