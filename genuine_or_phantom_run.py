"""
Genuine or Phantom? -- first pass.
Follow-up exploration to the Tightness Paradox (Kevin Sigey), run November 1, 2026.

Question: in the cells (industries, states, frozen friction terciles) where JOLTS
openings fail to convert into hires, does the stock behave like genuine hard
search (long duration, but today's openings still become tomorrow's hires) or
like phantom/stale postings (stock accumulates, converts at no special rate,
hires do not respond)?

HARD IDENTIFICATION NOTE (also stated in the draft): within a single month,
unfilled share = 1 - H/O and implied duration = O/H are monotone transforms of
the same ratio. They cannot disagree, so "are high-unfilled cells long-duration"
is mechanical and proves nothing by itself. The independent information in
published JOLTS stocks and flows is in the DYNAMICS:
  * clearance3   -- hires over the next 3 months per opening today.
  * pipe_elast  -- elasticity of next-3-months hires to today's openings stock,
                   holding today's hires constant. Genuine postings convert
                   with a lag, so this should be positive. A stock that never
                   converts shows ~0.
  * match_elast -- contemporaneous elasticity of hires to openings.
  * persist     -- AR(1) persistence of log openings (staleness of the stock).
Duration LEVELS are still reported: they are the object any posting-level
duration dataset (Lightcast/Indeed) would have to match, and the gap between
JOLTS-implied duration and measured posting duration is where phantom hides.

Windows: states 2022-01..2025-12 (the paper's test window) and 2015-04..2019-12
(placebo); industries 2022-01..end of file (Jul 2026) and 2015-04..2019-12.
SEs: Newey-West(3) for single series; cluster-by-state for pooled terciles.
Seed not needed (no randomness). Outputs:
  genuine_or_phantom_results.csv  (industry + tercile cells)
  genuine_or_phantom_states.csv   (per-state detail, recent window)
"""
import numpy as np
import pandas as pd
from scipy import stats

BASE = "/home/hatch/workspace"
OUT = f"{BASE}/research_notes/tightness"

# ---------------------------------------------------------------- OLS helpers
def ols(y, X, vcov="nw", lags=3, clusters=None):
    y = np.asarray(y, float); X = np.asarray(X, float)
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    resid = y - X @ beta
    n, k = X.shape
    if vcov == "nw":
        S = (X * resid[:, None]).T @ (X * resid[:, None])
        for L in range(1, lags + 1):
            w = 1 - L / (lags + 1)
            G = (X[L:] * resid[L:, None]).T @ (X[:-L] * resid[:-L, None])
            S += w * (G + G.T)
        V = XtX_inv @ S @ XtX_inv
    elif vcov == "cluster":
        V = np.zeros((k, k))
        for g in np.unique(clusters):
            m = clusters == g
            s = X[m].T @ resid[m]
            V += np.outer(s, s)
        G = len(np.unique(clusters))
        V = XtX_inv @ V @ XtX_inv * (G / (G - 1)) * ((n - 1) / (n - k))
    se = np.sqrt(np.diag(V))
    p = 2 * stats.norm.sf(np.abs(beta / se))
    return beta, se, p

def series_measures(d, pooled_clusters=None):
    """d: one series (or pooled panel with a 'grp' column) sorted by date,
    with Openings, Hires, and forward sums precomputed as cumH3."""
    d = d[(d.Openings > 0) & (d.Hires > 0)].copy()
    out = {}
    out["n_months"] = len(d)
    out["mean_unfilled"] = (1 - d.Hires / d.Openings).mean()
    out["mean_yield"] = (d.Hires / d.Openings).mean()
    out["mean_duration"] = (d.Openings / d.Hires).mean()
    out["median_duration"] = (d.Openings / d.Hires).median()
    dd = d.dropna(subset=["cumH3"])
    out["clearance3"] = (dd.cumH3 / dd.Openings).mean()
    # pipeline elasticity: ln future hires on ln openings today, ln hires today
    y = np.log(dd.cumH3.values)
    X = np.column_stack([np.ones(len(dd)), np.log(dd.Openings.values), np.log(dd.Hires.values)])
    if pooled_clusters is not None:
        b, se, p = ols(y, X, vcov="cluster", clusters=dd.grp.values)
    else:
        b, se, p = ols(y, X, vcov="nw")
    out["pipe_elast"], out["pipe_se"], out["pipe_p"] = b[1], se[1], p[1]
    # contemporaneous matching elasticity
    y2 = np.log(d.Hires.values)
    X2 = np.column_stack([np.ones(len(d)), np.log(d.Openings.values)])
    if pooled_clusters is not None:
        b2, se2, p2 = ols(y2, X2, vcov="cluster", clusters=d.grp.values)
    else:
        b2, se2, p2 = ols(y2, X2, vcov="nw")
    out["match_elast"], out["match_se"], out["match_p"] = b2[0 + 1], se2[1], p2[1]
    return out

def add_forward(d, group=None):
    d = d.sort_values("Date").copy()
    if group:
        d["cumH3"] = d.groupby(group).Hires.transform(
            lambda s: s.shift(-1).rolling(3).sum().shift(-2))
        d["lnO_lag"] = d.groupby(group).Openings.transform(lambda s: np.log(s).shift(1))
    else:
        d["cumH3"] = d.Hires.shift(-1).rolling(3).sum().shift(-2)
        d["lnO_lag"] = np.log(d.Openings).shift(1)
    return d

def persistence(d, group=None):
    dd = d.dropna(subset=["lnO_lag"]).copy()
    y = np.log(dd.Openings.values)
    X = np.column_stack([np.ones(len(dd)), dd.lnO_lag.values])
    if group:
        b, se, p = ols(y, X, vcov="cluster", clusters=dd.grp.values)
    else:
        b, se, p = ols(y, X, vcov="nw")
    return b[1], se[1], p[1]

RECENT = ("2022-01-01", "2025-12-01")
PRE = ("2015-04-01", "2019-12-01")

def window(d, w):
    return d[(d.Date >= w[0]) & (d.Date <= w[1])]

rows = []

# ---------------------------------------------------------------- industries
ip = pd.read_csv(f"{BASE}/tightness-industry/industry_panel.csv", parse_dates=["Date"])
ind_end = ip.Date.max()
for ind, g in ip.groupby("Industry"):
    g = add_forward(g)
    for wname, w in [("recent", ("2022-01-01", ind_end)), ("pre", PRE)]:
        m = series_measures(window(g, (w[0], pd.Timestamp(w[1]))))
        m.update(level="industry", cell=ind, window=wname)
        pb, pse, pp = persistence(window(g, (w[0], pd.Timestamp(w[1]))))
        m.update(persist=pb, persist_se=pse, persist_p=pp)
        rows.append(m)

# ---------------------------------------------------------------- states: per-state detail (recent)
sp = pd.read_csv(f"{BASE}/tightness-phase1/master_labor_panel_v2.csv", parse_dates=["Date"])
ga = pd.read_csv(f"{OUT}/prereg_group_assignments.csv")
terc = dict(zip(ga.State, ga.frozen_tercile))
sp["tercile"] = sp.State.map(terc)

state_rows = []
for st, g in sp.groupby("State"):
    g = add_forward(g)
    r = window(g, RECENT)
    d = r[(r.Openings > 0) & (r.Hires > 0)]
    dd = d.dropna(subset=["cumH3"])
    state_rows.append(dict(
        state=st, tercile=terc.get(st),
        n_months=len(d),
        mean_unfilled=(1 - d.Hires / d.Openings).mean(),
        mean_yield=(d.Hires / d.Openings).mean(),
        mean_duration=(d.Openings / d.Hires).mean(),
        median_duration=(d.Openings / d.Hires).median(),
        clearance3=(dd.cumH3 / dd.Openings).mean(),
    ))
states = pd.DataFrame(state_rows)

# bridge: per-state recent wage beta vs conversion measures
recent_beta = pd.read_csv(f"{OUT}/per_state_recent.csv")
states = states.merge(recent_beta[["state", "beta", "p"]].rename(
    columns={"state": "state_ab", "beta": "wage_beta_recent", "p": "wage_beta_p"}),
    left_on="state", right_on="state_ab", how="left").drop(columns=["state_ab"])

# ---------------------------------------------------------------- terciles pooled
sp = add_forward(sp.assign(grp=sp.State), group="State")
for tname in ["low", "mid", "high"]:
    sub = sp[sp.tercile == tname]
    for wname, w in [("recent", RECENT), ("pre", PRE)]:
        d = window(sub, w)
        m = series_measures(d, pooled_clusters=True)
        m.update(level="tercile", cell=f"frozen_{tname}", window=wname)
        pb, pse, pp = persistence(d, group=True)
        m.update(persist=pb, persist_se=pse, persist_p=pp)
        rows.append(m)

res = pd.DataFrame(rows)
cols = ["level", "cell", "window", "n_months", "mean_unfilled", "mean_yield",
        "mean_duration", "median_duration", "clearance3",
        "pipe_elast", "pipe_se", "pipe_p", "match_elast", "match_se", "match_p",
        "persist", "persist_se", "persist_p"]
res[cols].to_csv(f"{OUT}/genuine_or_phantom_results.csv", index=False)
states.to_csv(f"{OUT}/genuine_or_phantom_states.csv", index=False)

pd.set_option("display.width", 250)
def show(df, title):
    print(f"\n===== {title} =====")
    print(df[["cell", "window", "mean_unfilled", "mean_duration", "clearance3",
              "pipe_elast", "pipe_p", "match_elast", "persist"]].round(3).to_string(index=False))

show(res[res.level == "industry"], "INDUSTRIES")
show(res[res.level == "tercile"], "FROZEN TERCILES (pooled, state-clustered SEs)")

print("\n===== STATES by tercile (recent window, medians of state means) =====")
print(states.groupby("tercile")[["mean_unfilled", "mean_duration", "clearance3"]].median().round(3))

print("\n===== BRIDGE: state wage beta (recent) vs conversion measures =====")
for scope, d in [("all states", states), ("high tercile only", states[states.tercile == "high"])]:
    d = d.dropna(subset=["wage_beta_recent"])
    for meas in ["mean_duration", "clearance3", "mean_unfilled"]:
        r = np.corrcoef(d[meas], d.wage_beta_recent)[0, 1]
        print(f"{scope}: corr({meas}, wage_beta) = {r:+.2f}  (n={len(d)})")

print("\nHigh-tercile states, recent window (sorted by duration):")
print(states[states.tercile == "high"].sort_values("mean_duration", ascending=False)[
    ["state", "mean_unfilled", "mean_duration", "clearance3", "wage_beta_recent"]].round(3).to_string(index=False))
