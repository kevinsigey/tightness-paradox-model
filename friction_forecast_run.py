#!/usr/bin/env python3
"""
Friction as a forecasting signal: does labor friction lead unemployment and jobs?

PRE-COMMITTED INTERPRETATION (written before estimation, 2026-11-01):
Two stories compete. Story S (slack / failed conversion): openings that do not
convert into hires are demand that failed to become jobs; friction rising today
predicts unemployment RISING and hiring/employment growth FALLING at later
horizons. Story T (tightness proxy): friction is just labor-market heat;
friction rising predicts unemployment FALLING and job growth RISING.
All horizons (1, 3, 6 months) are reported for every spec, significant or not.
No horizon, variant, or sample is dropped after the fact.

Design: state panel (51 states, Apr 2015-Dec 2025), two-way fixed effects
(state + month) with standard errors clustered by state. Friction variants:
Friction_Proxy = (Openings - Hires)*1000/Labor_Force (the Phase 1 headline)
and Unfilled_Share = 1 - Hires/Openings. Unemployment spec controls for the
current unemployment rate (an unemployment-only autoregression is the
benchmark; friction's partial R-squared over that benchmark is reported).
Jobs specs control for the trailing 3-month growth of the target.
A pseudo-out-of-sample expanding-window check (pooled OLS with state dummies,
no month FE in the OOS variant) backs the unemployment spec.
National read: labor-force-weighted aggregates, Newey-West SEs, descriptive.

Seed: 20261101 (no sampling involved; recorded for reproducibility discipline).
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm

PANEL = "/home/hatch/workspace/tightness-phase1/master_labor_panel_v2.csv"
OUT = "/home/hatch/workspace/research_notes/tightness/friction_forecast_results.csv"
HORIZONS = [1, 3, 6]
FRICTIONS = {"friction_proxy": "Friction_Proxy", "unfilled_share": "Unfilled_Share"}


def demean_two_way(df, cols, g1="State", g2="Date"):
    """Within transform: x - state mean - month mean + grand mean."""
    out = {}
    for c in cols:
        x = df[c].astype(float)
        out[c] = (x - x.groupby(df[g1]).transform("mean")
                  - x.groupby(df[g2]).transform("mean") + x.mean())
    return pd.DataFrame(out, index=df.index)


def cluster_meat(X, resid, groups):
    """Cluster-robust meat for OLS: sum over clusters of (X_g' e_g)(X_g' e_g)'."""
    k = X.shape[1]
    meat = np.zeros((k, k))
    Xe = X * resid[:, None]
    df_g = pd.DataFrame(Xe).groupby(groups.values).sum().values
    meat = df_g.T @ df_g
    return meat


def ols_cluster(X, y, groups):
    """OLS with cluster-robust (CR1-style, G/(G-1) dof adj) covariance."""
    X = np.asarray(X, float); y = np.asarray(y, float)
    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    resid = y - X @ beta
    meat = cluster_meat(X, resid, groups)
    G = len(np.unique(groups)); n, k = X.shape
    vcov = XtX_inv @ meat @ XtX_inv * (G / (G - 1)) * ((n - 1) / (n - k))
    se = np.sqrt(np.diag(vcov))
    from scipy import stats
    t = beta / se
    p = 2 * stats.t.sf(np.abs(t), df=G - 1)
    return beta, se, t, p, resid


def twfe_spec(d, ycol, xcols, friction_col):
    """Two-way FE via demeaning; partial R2 of the friction variable vs the
    benchmark spec without it (same demeaned sample)."""
    cols = [ycol] + xcols
    dd = demean_two_way(d, cols)
    X = dd[xcols].values; y = dd[ycol].values
    beta, se, t, p, resid = ols_cluster(X, y, d["State"])
    ss_res = float(resid @ resid)
    # benchmark: drop friction column
    keep = [i for i, c in enumerate(xcols) if c != friction_col]
    Xb = dd[[xcols[i] for i in keep]].values
    _, _, _, _, resid_b = ols_cluster(Xb, y, d["State"])
    ss_b = float(resid_b @ resid_b)
    partial_r2 = (ss_b - ss_res) / ss_b if ss_b > 0 else np.nan
    i = xcols.index(friction_col)
    return dict(beta=beta[i], se=se[i], t=t[i], p=p[i], partial_r2=partial_r2,
                n=len(d), full_r2=1 - ss_res / float(((y - y.mean()) ** 2).sum()))


def main():
    df = pd.read_csv(PANEL, parse_dates=["Date"]).sort_values(["State", "Date"])
    g = df.groupby("State", group_keys=False)

    # --- targets and controls, built within state ---
    df["dlog_hires"] = g["Hires"].apply(lambda s: np.log(s))
    df["hires_3mma"] = g["Hires"].transform(lambda s: s.rolling(3).mean())
    df["log_hires_3mma"] = np.log(df["hires_3mma"])
    df["log_lhe"] = np.log(df["LH_Employment"])
    df["ctrl_hires_g3"] = g["log_hires_3mma"].diff(3)
    df["ctrl_lhe_g3"] = g["log_lhe"].diff(3)
    for h in HORIZONS:
        df[f"du_{h}"] = g["Unemployment_Rate"].shift(-h) - df["Unemployment_Rate"]
        df[f"dhires_{h}"] = g["log_hires_3mma"].shift(-h) - df["log_hires_3mma"]
        df[f"dlhe_{h}"] = g["log_lhe"].shift(-h) - df["log_lhe"]

    rows = []
    specs = [
        ("unemployment_change_pp", "du_{h}", ["Unemployment_Rate"]),
        ("hires_growth_log_3mma", "dhires_{h}", ["ctrl_hires_g3"]),
        ("lh_employment_growth_log", "dlhe_{h}", ["ctrl_lhe_g3"]),
    ]
    for outcome, ypat, ctrls in specs:
        for h in HORIZONS:
            ycol = ypat.format(h=h)
            for vname, vcol in FRICTIONS.items():
                d = df.dropna(subset=[ycol, vcol] + ctrls).copy()
                r = twfe_spec(d, ycol, [vcol] + ctrls, vcol)
                rows.append(dict(level="state_twfe", outcome=outcome, horizon=h,
                                 friction_variant=vname, **r))
                print(f"state {outcome:28s} h={h} {vname:15s} "
                      f"beta={r['beta']:+.4f} se={r['se']:.4f} p={r['p']:.4f} "
                      f"partialR2={r['partial_r2']:.5f} N={r['n']}")

    # --- pseudo-out-of-sample: unemployment, expanding window ---
    # Pooled OLS with state dummies, no month FE (the honest OOS variant).
    print("\n--- pseudo-OOS unemployment ---")
    for h in HORIZONS:
        for vname, vcol in FRICTIONS.items():
            d = df.dropna(subset=[f"du_{h}", vcol, "Unemployment_Rate"]).copy()
            d["const"] = 1.0
            dum = pd.get_dummies(d["State"], prefix="st", drop_first=True, dtype=float)
            base_cols = ["const", "Unemployment_Rate"] + list(dum.columns)
            full_cols = ["const", "Unemployment_Rate", vcol] + list(dum.columns)
            Xall = pd.concat([d[["const", "Unemployment_Rate", vcol]].reset_index(drop=True),
                              dum.reset_index(drop=True)], axis=1)
            y = d[f"du_{h}"].values
            dates = d["Date"].values
            months = np.sort(d["Date"].unique())
            start_idx = 32  # first forecast origin after >=32 training months
            errs_b, errs_f = [], []
            for mi in range(start_idx, len(months) - 0):
                origin = months[mi]
                tr = dates < origin
                te = dates == origin
                if te.sum() == 0 or tr.sum() < 500:
                    continue
                for cols, errs in ((base_cols, errs_b), (full_cols, errs_f)):
                    Xtr = Xall.loc[tr, cols].values; Xte = Xall.loc[te, cols].values
                    bb = np.linalg.lstsq(Xtr, y[tr], rcond=None)[0]
                    errs.append(y[te] - Xte @ bb)
            eb = np.concatenate(errs_b); ef = np.concatenate(errs_f)
            rmse_b = float(np.sqrt(np.mean(eb ** 2))); rmse_f = float(np.sqrt(np.mean(ef ** 2)))
            # Diebold-Mariano-lite: t on loss differential, Newey-West lag h
            ld = eb ** 2 - ef ** 2
            dm = sm.OLS(ld, np.ones((len(ld), 1))).fit(
                cov_type="HAC", cov_kwds={"maxlags": h})
            rows.append(dict(level="state_pseudo_oos", outcome="unemployment_change_pp",
                             horizon=h, friction_variant=vname,
                             beta=np.nan, se=np.nan, t=float(dm.tvalues[0]),
                             p=float(dm.pvalues[0]), partial_r2=np.nan,
                             n=len(ld), full_r2=np.nan,
                             rmse_benchmark=rmse_b, rmse_with_friction=rmse_f,
                             rmse_ratio=rmse_f / rmse_b))
            print(f"OOS h={h} {vname:15s} RMSE base={rmse_b:.4f} fric={rmse_f:.4f} "
                  f"ratio={rmse_f/rmse_b:.4f} DM p={float(dm.pvalues[0]):.4f} n={len(ld)}")

    # --- national read ---
    print("\n--- national ---")
    w = df.copy()
    nat = w.groupby("Date").apply(lambda d: pd.Series({
        "O": d["Openings"].sum(), "H": d["Hires"].sum(),
        "friction_proxy": np.average(d["Friction_Proxy"], weights=d["Labor_Force"]),
        "ur": np.average(d["Unemployment_Rate"], weights=d["Labor_Force"]),
        "log_hires": np.log(d["Hires"].sum()),
    }), include_groups=False).reset_index()
    nat["unfilled_share"] = 1 - nat["H"] / nat["O"]
    nat["ghost_gap_k"] = (nat["O"] - nat["H"])  # openings minus hires, thousands of jobs
    for h in HORIZONS:
        nat[f"du_{h}"] = nat["ur"].shift(-h) - nat["ur"]
        nat[f"dh_{h}"] = nat["log_hires"].shift(-h) - nat["log_hires"]
    for outcome, ypat in (("unemployment_change_pp", "du_{h}"), ("hires_growth_log", "dh_{h}")):
        for h in HORIZONS:
            ycol = ypat.format(h=h)
            for vname, vcol in [("friction_proxy", "friction_proxy"),
                                ("unfilled_share", "unfilled_share")]:
                ctrls = ["ur"] if outcome.startswith("unemployment") else []
                d = nat.dropna(subset=[ycol, vcol] + ctrls)
                X = sm.add_constant(d[[vcol] + ctrls].astype(float))
                fit = sm.OLS(d[ycol].astype(float), X).fit(
                    cov_type="HAC", cov_kwds={"maxlags": h + 1})
                rows.append(dict(level="national", outcome=outcome, horizon=h,
                                 friction_variant=vname, beta=float(fit.params[vcol]),
                                 se=float(fit.bse[vcol]), t=float(fit.tvalues[vcol]),
                                 p=float(fit.pvalues[vcol]),
                                 partial_r2=np.nan, n=int(fit.nobs),
                                 full_r2=float(fit.rsquared)))
                print(f"nat {outcome:24s} h={h} {vname:15s} beta={float(fit.params[vcol]):+.4f} "
                      f"p={float(fit.pvalues[vcol]):.4f} N={int(fit.nobs)}")

    # recent national friction values for the integration note
    print("\nNational friction, last 12 months of panel:")
    print(nat.tail(12)[["Date", "friction_proxy", "unfilled_share", "ur"]].to_string(index=False))
    corr = nat[["unfilled_share", "ghost_gap_k"]].corr().iloc[0, 1]
    print(f"corr(unfilled_share, national openings-hires gap) = {corr:.3f}")

    res = pd.DataFrame(rows)
    res.to_csv(OUT, index=False)
    print(f"\nwrote {OUT} ({len(res)} rows)")


if __name__ == "__main__":
    main()
