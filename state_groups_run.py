#!/usr/bin/env python
"""
State-heterogeneity exploration for the Tightness Paradox rebuild.

Question (Kevin, 2026-11-01): does the pooled null (Friction_Lag3 beta = 0.058,
two-way clustered p = 0.54) hide state-level effects that average out?

Mirrors the Phase 1 preferred spec exactly:
  ln_Real_Wage ~ Friction_Lag3 + Friction_x_Education + Unemployment_Rate
                 + ln_Min_Wage + LH_Share      (state + month FE)
  Friction_x_Education = Friction_Proxy * ln_Education (UNLAGGED interaction)
  Preferred SEs: two-way clustered (state x month).

Per-state runs cannot carry state/month FE within one state, so each state is
estimated as a time-series OLS with the same regressors + intercept + linear
time trend, Newey-West HAC SEs (lag length floor(4*(T/100)^(2/9)), the
Newey-West 1994 plug-in rule). The headline per-state number is the coefficient
on Friction_Lag3 (comparable to the pooled 0.058); the state average marginal
effect b1 + b2*mean(ln_Education) with delta-method SE is reported alongside.

Multiple-testing discipline: Benjamini-Hochberg FDR + Bonferroni on the 51
per-state p-values; DerSimonian-Laird heterogeneity (Q, I^2, tau^2) and
empirical-Bayes (precision-weighted) shrinkage of the per-state betas.

Seed: 20261101. Exploration only; does not touch the published paper.
"""
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests
from scipy import stats
from linearmodels.panel import PanelOLS

SEED = 20261101
np.random.seed(SEED)

PANEL = "/home/hatch/workspace/tightness-phase1/master_labor_panel_v2.csv"
OUTDIR = "/home/hatch/workspace/research_notes/tightness"

Y = "ln_Real_Wage"
X_VARS = ["Friction_Lag3", "Friction_x_Education", "Unemployment_Rate",
          "ln_Min_Wage", "LH_Share"]

panel = pd.read_csv(PANEL, parse_dates=["Date"])
panel = panel.sort_values(["State", "Date"]).reset_index(drop=True)
states = sorted(panel["State"].unique())
print(f"Panel: {len(panel)} rows, {len(states)} states, "
      f"{panel['Date'].min().date()} to {panel['Date'].max().date()}")

rows_out = []  # master tidy output


def record(sample, analysis, group_var, group, term, beta, se, p, n, **extra):
    t = beta / se if se and np.isfinite(se) and se > 0 else np.nan
    r = dict(sample=sample, analysis=analysis, group_var=group_var, group=group,
             term=term, beta=beta, se=se, t=t, p=p,
             ci_lo=beta - 1.96 * se if np.isfinite(se) else np.nan,
             ci_hi=beta + 1.96 * se if np.isfinite(se) else np.nan, n=n)
    r.update(extra)
    rows_out.append(r)


# ---------------------------------------------------------------- pooled TWFE
def pooled_twfe(data, sample_label):
    d = data.set_index(["State", "Date"])
    mod = PanelOLS(d[Y], d[X_VARS], entity_effects=True, time_effects=True,
                   drop_absorbed=True)
    res = mod.fit(cov_type="clustered", cluster_entity=True, cluster_time=True)
    b = res.params["Friction_Lag3"]; s = res.std_errors["Friction_Lag3"]
    record(sample_label, "pooled_twfe", "", "all", "Friction_Lag3", b, s,
           res.pvalues["Friction_Lag3"], int(res.nobs))
    return b, s, res


b_full, s_full, _ = pooled_twfe(panel, "full_2015_2025")
print(f"Pooled TWFE full sample: beta={b_full:.4f} se={s_full:.4f} "
      f"(Phase 1 headline: 0.0582 / 0.0944)")


# ---------------------------------------------------------------- per-state
def nw_lags(T):
    return max(1, int(np.floor(4 * (T / 100.0) ** (2.0 / 9.0))))


def per_state(data, sample_label):
    out = []
    for st, g in data.groupby("State"):
        g = g.sort_values("Date").copy()
        g["trend"] = np.arange(len(g))
        xvars = [v for v in X_VARS if g[v].std(skipna=True) > 1e-8]
        dropped = [v for v in X_VARS if v not in xvars]
        X = sm.add_constant(g[xvars + ["trend"]], has_constant="add")
        res = sm.OLS(g[Y].values, X.values).fit(
            cov_type="HAC", cov_kwds={"maxlags": nw_lags(len(g)),
                                      "use_correction": True})
        idx = {name: i for i, name in enumerate(X.columns)}
        i1 = idx["Friction_Lag3"]
        beta, se, p = res.params[i1], res.bse[i1], res.pvalues[i1]
        # AME: b1 + b2 * mean(ln_Education), delta method on HAC cov
        ame, ame_se, ame_p = np.nan, np.nan, np.nan
        if "Friction_x_Education" in idx:
            i2 = idx["Friction_x_Education"]
            m = g["ln_Education"].mean()
            grad = np.zeros(len(X.columns)); grad[i1] = 1.0; grad[i2] = m
            ame = float(grad @ res.params)
            ame_se = float(np.sqrt(grad @ res.cov_params() @ grad))
            ame_p = float(2 * stats.norm.sf(abs(ame / ame_se)))
        out.append(dict(state=st, beta=beta, se=se, p=p, ame=ame,
                        ame_se=ame_se, ame_p=ame_p, n=len(g),
                        lags=nw_lags(len(g)), dropped=";".join(dropped)))
        record(sample_label, "per_state", "", st, "Friction_Lag3", beta, se, p,
               len(g), ame=ame, ame_se=ame_se, ame_p=ame_p,
               nw_lags=nw_lags(len(g)), dropped_vars=";".join(dropped))
    df = pd.DataFrame(out)
    # multiple-testing corrections
    df["q_bh"] = multipletests(df["p"], method="fdr_bh")[1]
    df["p_bonf"] = multipletests(df["p"], method="bonferroni")[1]
    df["q_bh_ame"] = multipletests(df["ame_p"].fillna(1.0), method="fdr_bh")[1]
    for _, r in df.iterrows():
        record(sample_label, "per_state_corrected", "", r["state"],
               "Friction_Lag3", r["beta"], r["se"], r["p"], int(r["n"]),
               q_bh=r["q_bh"], p_bonf=r["p_bonf"])
    return df


ps_full = per_state(panel, "full_2015_2025")


# ------------------------------------------------- heterogeneity + shrinkage
def heterogeneity(df, sample_label):
    b = df["beta"].values; s = df["se"].values
    w = 1.0 / s ** 2
    mu_fe = float((w * b).sum() / w.sum())
    Q = float((w * (b - mu_fe) ** 2).sum())
    k = len(b); dfree = k - 1
    p_Q = float(stats.chi2.sf(Q, dfree))
    I2 = max(0.0, (Q - dfree) / Q) if Q > 0 else 0.0
    C = w.sum() - (w ** 2).sum() / w.sum()
    tau2 = max(0.0, (Q - dfree) / C)
    if tau2 > 0:
        wr = 1.0 / (s ** 2 + tau2)
        mu_re = float((wr * b).sum() / wr.sum())
    else:
        mu_re = mu_fe
    post_var = 1.0 / (1.0 / s ** 2 + (1.0 / tau2 if tau2 > 0 else np.inf))
    shrunk = np.where(tau2 > 0,
                      post_var * (b / s ** 2 + mu_re / tau2), mu_re)
    post_sd = np.sqrt(post_var) if tau2 > 0 else np.full(k, np.nan)
    out = df.copy()
    out["beta_shrunk"] = shrunk
    out["shrunk_sd"] = post_sd
    record(sample_label, "heterogeneity", "", "all_states", "Q_statistic",
           Q, np.nan, p_Q, int(k), df=dfree, I2=I2, tau2=tau2, mu_fe=mu_fe,
           mu_re=mu_re)
    return out, dict(Q=Q, df=dfree, p_Q=p_Q, I2=I2, tau2=tau2,
                     mu_fe=mu_fe, mu_re=mu_re)


ps_full, het_full = heterogeneity(ps_full, "full_2015_2025")
print(f"Heterogeneity full: Q={het_full['Q']:.1f} df={het_full['df']} "
      f"p={het_full['p_Q']:.3f} I2={het_full['I2']:.2f} tau2={het_full['tau2']:.4f}")


# ---------------------------------------------------------------- grouped
means = panel.groupby("State").agg(
    mean_friction=("Friction_Proxy", "mean"),
    mean_ur=("Unemployment_Rate", "mean"),
    mean_wage=("Hourly_Wage", "mean"),
    mean_lh=("LH_Share", "mean"),
    mean_lf=("Labor_Force", "mean"),
    region=("Region", "first")).reset_index()


def terciles(series):
    return pd.qcut(series, 3, labels=["low", "mid", "high"])


for col, name in [("mean_friction", "friction_level"), ("mean_ur", "unemployment"),
                  ("mean_wage", "wage_level"), ("mean_lh", "lh_share"),
                  ("mean_lf", "labor_force_size")]:
    means[name] = terciles(means[col])
means["region_grp"] = means["region"]

GROUPINGS = {
    "friction_level": ("friction_level", ["low", "mid", "high"]),
    "unemployment": ("unemployment", ["low", "mid", "high"]),
    "wage_level": ("wage_level", ["low", "mid", "high"]),
    "lh_share_industry_mix": ("lh_share", ["low", "mid", "high"]),
    "labor_force_size": ("labor_force_size", ["low", "mid", "high"]),
    "census_region": ("region_grp", sorted(means["region"].unique())),
}
grp_map = {r.State: {gname: getattr(r, col) for gname, (col, _) in
                     GROUPINGS.items()} for r in means.itertuples()}


def grouped_twfe(data, sample_label):
    d = data.copy()
    results = {}
    for gname, (col, levels) in GROUPINGS.items():
        d["grp"] = d["State"].map({s: grp_map[s][gname] for s in grp_map})
        for lev in levels:
            d[f"Fric_{lev}"] = d["Friction_Lag3"] * (d["grp"] == lev).astype(float)
        fric_cols = [f"Fric_{lev}" for lev in levels]
        dd = d.set_index(["State", "Date"])
        X = fric_cols + [v for v in X_VARS if v != "Friction_Lag3"]
        mod = PanelOLS(dd[Y], dd[X], entity_effects=True, time_effects=True,
                       drop_absorbed=True)
        res = mod.fit(cov_type="clustered", cluster_entity=True,
                      cluster_time=True)
        params = res.params; cov = res.cov
        for lev in levels:
            nm = f"Fric_{lev}"
            record(sample_label, "grouped_twfe", gname, str(lev), nm,
                   params[nm], res.std_errors[nm], res.pvalues[nm],
                   int(res.nobs))
        # joint equality Wald: all pairwise diffs = 0
        G = len(levels)
        R = np.zeros((G - 1, len(params)))
        pos = {nm: i for i, nm in enumerate(params.index)}
        for i in range(G - 1):
            R[i, pos[f"Fric_{levels[0]}"]] = 1.0
            R[i, pos[f"Fric_{levels[i + 1]}"]] = -1.0
        Rb = R @ params.values
        RV = R @ cov.values @ R.T
        W = float(Rb @ np.linalg.pinv(RV) @ Rb)
        pW = float(stats.chi2.sf(W, G - 1))
        record(sample_label, "group_equality_wald", gname, "all_groups",
               "joint_equality", W, np.nan, pW, int(res.nobs), df=G - 1)
        # pairwise differences
        for i in range(G):
            for j in range(i + 1, G):
                a, bb = f"Fric_{levels[i]}", f"Fric_{levels[j]}"
                diff = params[a] - params[bb]
                v = (cov.loc[a, a] + cov.loc[bb, bb] - 2 * cov.loc[a, bb])
                se_d = float(np.sqrt(max(v, 0)))
                p_d = float(2 * stats.norm.sf(abs(diff / se_d))) if se_d > 0 else np.nan
                record(sample_label, "group_pairwise_diff", gname,
                       f"{levels[i]}_minus_{levels[j]}", "friction_diff",
                       float(diff), se_d, p_d, int(res.nobs))
        results[gname] = (levels, params, res.std_errors)
        d = d.drop(columns=fric_cols + ["grp"])
    return results


grp_full = grouped_twfe(panel, "full_2015_2025")

# ---------------------------------------------------------------- recent window
recent = panel[panel["Date"] >= "2022-01-01"].copy()
print(f"Recent window: {len(recent)} rows, "
      f"{recent['Date'].min().date()} to {recent['Date'].max().date()}, "
      f"{recent.groupby('State').size().iloc[0]} months/state")
b_rec, s_rec, _ = pooled_twfe(recent, "recent_2022_2025")
print(f"Pooled TWFE recent: beta={b_rec:.4f} se={s_rec:.4f}")
ps_recent = per_state(recent, "recent_2022_2025")
ps_recent, het_recent = heterogeneity(ps_recent, "recent_2022_2025")
print(f"Heterogeneity recent: Q={het_recent['Q']:.1f} p={het_recent['p_Q']:.3f} "
      f"I2={het_recent['I2']:.2f} tau2={het_recent['tau2']:.4f}")
grp_recent = grouped_twfe(recent, "recent_2022_2025")

# ---------------------------------------------------------------- outputs
master = pd.DataFrame(rows_out)
master.to_csv(f"{OUTDIR}/state_groups_estimates.csv", index=False)
ps_full_out = ps_full.merge(means[["State"] + [c for c, _ in
                              [(v[0], None) for v in GROUPINGS.values()]]],
                            left_on="state", right_on="State", how="left")
ps_full_out.to_csv(f"{OUTDIR}/per_state_full.csv", index=False)
ps_recent.to_csv(f"{OUTDIR}/per_state_recent.csv", index=False)
means.to_csv(f"{OUTDIR}/state_group_assignments.csv", index=False)

import json
summary = dict(
    pooled_full=dict(beta=float(b_full), se=float(s_full)),
    pooled_recent=dict(beta=float(b_rec), se=float(s_rec)),
    het_full=het_full, het_recent=het_recent,
    per_state_full_nom_sig=int((ps_full["p"] < 0.05).sum()),
    per_state_full_bh=int((ps_full["q_bh"] < 0.05).sum()),
    per_state_full_bonf=int((ps_full["p_bonf"] < 0.05).sum()),
    per_state_recent_nom_sig=int((ps_recent["p"] < 0.05).sum()),
    per_state_recent_bh=int((ps_recent["q_bh"] < 0.05).sum()),
    per_state_recent_bonf=int((ps_recent["p_bonf"] < 0.05).sum()),
)
json.dump(summary, open(f"{OUTDIR}/state_groups_summary.json", "w"), indent=1,
          default=float)
print(json.dumps(summary, indent=1, default=float))

# ---------------------------------------------------------------- visuals
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# (1) per-state forest plot: full sample sorted by beta, recent window beside
order = ps_full.sort_values("beta")["state"].tolist()
pf = ps_full.set_index("state").loc[order]
pr = ps_recent.set_index("state").loc[order]
fig, axes = plt.subplots(1, 2, figsize=(11, 13), sharey=True)
for ax, d, title in [
        (axes[0], pf, "Full sample, Apr 2015 - Dec 2025 (T=128)"),
        (axes[1], pr, "Recent window, Jan 2022 - Dec 2025 (T=47)")]:
    y = np.arange(len(d))
    colors = ["#b2182b" if q < 0.05 else "#4393c3" if p < 0.05 else "#999999"
              for q, p in zip(d["q_bh"], d["p"])]
    for yi, (b_, s_, c_) in enumerate(zip(d["beta"], d["se"], colors)):
        ax.plot([b_ - 1.96 * s_, b_ + 1.96 * s_], [yi, yi], color=c_,
                lw=1.0, zorder=2)
    ax.scatter(d["beta"], y, c=colors, s=14, zorder=3)
    ax.axvline(0, color="black", lw=0.9)
    ax.set_yticks(y); ax.set_yticklabels(d.index, fontsize=8)
    ax.set_xlabel("Friction_Lag3 coefficient (Newey-West HAC 95% CI)")
    ax.set_title(title, fontsize=10)
    ax.grid(axis="x", alpha=0.25)
axes[0].axvline(0.0582, color="#b2182b", ls="--", lw=1.0)
axes[0].text(0.075, len(d) - 0.4, "pooled TWFE = 0.058", color="#b2182b",
             fontsize=8)
fig.suptitle("Per-state friction-to-wage coefficients: red = survives BH-FDR, "
             "blue = nominal p<.05 only", fontsize=11)
fig.tight_layout(rect=[0, 0, 1, 0.97])
fig.savefig(f"{OUTDIR}/state_forest.png", dpi=160)
plt.close(fig)

# (2) grouped-coefficient chart: full vs recent, by grouping
gfull = master[(master.analysis == "grouped_twfe") &
               (master["sample"] == "full_2015_2025")]
grec = master[(master.analysis == "grouped_twfe") &
              (master["sample"] == "recent_2022_2025")]
titles = {"friction_level": "By mean friction level (terciles)",
          "unemployment": "By mean unemployment (terciles)",
          "wage_level": "By mean wage level (terciles)",
          "lh_share_industry_mix": "By LH share / industry mix (terciles)",
          "labor_force_size": "By labor-force size (terciles)",
          "census_region": "By Census region"}
fig, axes = plt.subplots(2, 3, figsize=(13, 7.5), sharex=False)
for ax, (gname, title) in zip(axes.flat, titles.items()):
    a = gfull[gfull.group_var == gname].reset_index(drop=True)
    b = grec[grec.group_var == gname].set_index("group")
    x = np.arange(len(a))
    ax.errorbar(x - 0.11, a["beta"], yerr=1.96 * a["se"], fmt="o", ms=5,
                color="#2166ac", capsize=3, label="Full 2015-2025")
    bb = b.loc[a["group"]]
    ax.errorbar(x + 0.11, bb["beta"], yerr=1.96 * bb["se"], fmt="s", ms=5,
                color="#b2182b", capsize=3, label="Recent 2022-2025")
    ax.axhline(0, color="black", lw=0.9)
    ax.axhline(0.0582, color="gray", ls=":", lw=1.0)
    ax.set_xticks(x); ax.set_xticklabels(a["group"], fontsize=9)
    ax.set_title(title, fontsize=10)
    ax.grid(axis="y", alpha=0.25)
axes[0, 0].legend(fontsize=8, loc="lower left")
fig.suptitle("Grouped TWFE friction coefficients (two-way clustered 95% CI; "
             "dotted = pooled full-sample 0.058)", fontsize=11)
fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(f"{OUTDIR}/grouped_coefficients.png", dpi=160)
plt.close(fig)
print("Visuals written: state_forest.png, grouped_coefficients.png")
print("DONE")
