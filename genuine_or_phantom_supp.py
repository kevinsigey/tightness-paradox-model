"""
Genuine or Phantom? -- supplementary computations (November 1, 2026).

Two corrections to the first pass in genuine_or_phantom_run.py:
1. The pooled tercile regressions on log levels mix cross-state size variation
   (big states have big openings and big hires). Here the elasticities are
   re-estimated within state (state fixed effects, i.e. demeaned by state),
   with standard errors clustered by state. Persistence is also within-state.
2. The industry panel's 'prof_bus' series was pulled with JOLTS industry code
   600000, which is the education and health services supersector; 'edu_health'
   is its components 610000 + 620000. The two series are the same industry
   (correlation 1.0000, max gap 1k). This script reports the merged cell once,
   as education & health services, and flags professional & business services
   (JOLTS code 540000) as absent from the panel.
Outputs: genuine_or_phantom_supp.csv + printed tables.
"""
import numpy as np
import pandas as pd
from scipy import stats

BASE = "/home/hatch/workspace"
OUT = f"{BASE}/research_notes/tightness"

def ols_cluster(y, X, clusters):
    y = np.asarray(y, float); X = np.asarray(X, float)
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    resid = y - X @ beta
    n, k = X.shape
    V = np.zeros((k, k))
    for g in np.unique(clusters):
        m = clusters == g
        s = X[m].T @ resid[m]
        V += np.outer(s, s)
    G = len(np.unique(clusters))
    V = XtX_inv @ V @ XtX_inv * (G / (G - 1)) * ((n - 1) / (n - k))
    se = np.sqrt(np.diag(V))
    return beta, se, 2 * stats.norm.sf(np.abs(beta / se))

RECENT = ("2022-01-01", "2025-12-01")
PRE = ("2015-04-01", "2019-12-01")

sp = pd.read_csv(f"{BASE}/tightness-phase1/master_labor_panel_v2.csv", parse_dates=["Date"])
ga = pd.read_csv(f"{OUT}/prereg_group_assignments.csv")
sp["tercile"] = sp.State.map(dict(zip(ga.State, ga.frozen_tercile)))
sp = sp.sort_values(["State", "Date"]).copy()
sp["cumH3"] = sp.groupby("State").Hires.transform(lambda s: s.shift(-1).rolling(3).sum().shift(-2))
sp["lnO"] = np.log(sp.Openings)
sp["lnH"] = np.log(sp.Hires)
sp["lnC3"] = np.log(sp.cumH3)

rows = []
for tname in ["low", "mid", "high"]:
    for wname, w in [("recent", RECENT), ("pre", PRE)]:
        d = sp[(sp.tercile == tname) & (sp.Date >= w[0]) & (sp.Date <= w[1])].copy()
        # within-state demeaning
        for c in ["lnO", "lnH", "lnC3"]:
            d[c + "_w"] = d[c] - d.groupby("State")[c].transform("mean")
        dd = d.dropna(subset=["lnC3_w"])
        # pipeline: lnC3 ~ lnO + lnH (within), cluster by state
        X = np.column_stack([dd.lnO_w.values, dd.lnH_w.values])
        b, se, p = ols_cluster(dd.lnC3_w.values, X, dd.State.values)
        pipe, pipe_se, pipe_p = b[0], se[0], p[0]
        # matching: lnH ~ lnO (within)
        X2 = np.column_stack([d.lnO_w.values])
        b2, se2, p2 = ols_cluster(d.lnH_w.values, X2, d.State.values)
        # persistence: lnO_t ~ lnO_{t-1} (within)
        d["lnO_lag_w"] = d.groupby("State").lnO.shift(1)
        d["lnO_lag_w"] = d.lnO_lag_w - d.groupby("State").lnO_lag_w.transform("mean")
        dp = d.dropna(subset=["lnO_lag_w"])
        X3 = np.column_stack([dp.lnO_lag_w.values])
        b3, se3, p3 = ols_cluster(dp.lnO_w.values, X3, dp.State.values)
        rows.append(dict(level="tercile_within", cell=f"frozen_{tname}", window=wname,
                         n_months=len(dd), pipe_elast=pipe, pipe_se=pipe_se, pipe_p=pipe_p,
                         match_elast=b2[0], match_se=se2[0], match_p=p2[0],
                         persist=b3[0], persist_se=se3[0], persist_p=p3[0]))
        print(f"{tname:5s} {wname:6s} pipe={pipe:+.3f} (p={pipe_p:.3f})  match={b2[0]:+.3f} (p={p2[0]:.3f})  persist={b3[0]:.3f}")

# per-state pipe elasticity (recent), summarized by tercile -- descriptive only
def ols_nw(y, X, lags=3):
    y = np.asarray(y, float); X = np.asarray(X, float)
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    resid = y - X @ beta
    S = (X * resid[:, None]).T @ (X * resid[:, None])
    for L in range(1, lags + 1):
        wgt = 1 - L / (lags + 1)
        G = (X[L:] * resid[L:, None]).T @ (X[:-L] * resid[:-L, None])
        S += wgt * (G + G.T)
    V = XtX_inv @ S @ XtX_inv
    se = np.sqrt(np.diag(V))
    return beta, se, 2 * stats.norm.sf(np.abs(beta / se))

per_state = []
for st, g in sp.groupby("State"):
    d = g[(g.Date >= RECENT[0]) & (g.Date <= RECENT[1])].dropna(subset=["cumH3"])
    X = np.column_stack([np.ones(len(d)), np.log(d.Openings.values), np.log(d.Hires.values)])
    b, se, p = ols_nw(np.log(d.cumH3.values), X)
    per_state.append(dict(state=st, tercile=g.tercile.iloc[0], pipe_elast=b[1], pipe_p=p[1]))
ps = pd.DataFrame(per_state)
print("\nPer-state pipeline elasticity, recent window, by tercile (descriptive, n=17 each):")
print(ps.groupby("tercile").pipe_elast.describe()[["count", "25%", "50%", "75%"]].round(3))
print("share of states with pipe_elast > 0 by tercile:")
print((ps.assign(pos=ps.pipe_elast > 0).groupby("tercile").pos.mean()).round(2).to_dict())

pd.DataFrame(rows).to_csv(f"{OUT}/genuine_or_phantom_supp.csv", index=False)
ps.to_csv(f"{OUT}/genuine_or_phantom_perstate_pipe.csv", index=False)
