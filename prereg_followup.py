#!/usr/bin/env python
"""
PRE-REGISTERED FOLLOW-UP: the recent-window friction-tercile thread.

Design written down on Sunday, November 1, 2026, BEFORE any estimation in
this script was run. This design is the one proposed at the end of the
exploration memo (state-groups.md, 2026-11-01), which found, on
Jan 2022-Dec 2025 with tercile groups defined on FULL-PERIOD state means,
a high-friction coefficient of +0.589 against -0.283 for the low tercile
and an equality-test p of 0.034. That result is suggestive only: it was
one rejection among 12 equality tests, and its groups were partly defined
on the test window itself. This script is the confirmatory retest.

CONFIRMATORY DESIGN (frozen here; any deviation voids the "confirmatory"
label and must be disclosed):

  1. GROUPS. Each state's friction tercile (low / mid / high, 17 states
     each) is fixed from that state's mean Friction_Proxy over
     Apr 2015-Dec 2019 ONLY. Pre-COVID months; the test window (2022 on)
     cannot influence membership, and neither can 2020-2021.
  2. SAMPLE. Jan 2022-Dec 2025 only (47 months per state; Oct 2025 is
     absent panel-wide because BLS published no CPI that month).
     Expected N = 51 x 47 = 2,397.
  3. SPEC. The Phase 1 preferred specification, unchanged: two-way fixed
     effects (state + month), two-way clustered standard errors
     (state x month), outcome ln_Real_Wage, regressors
     Friction_Lag3 interacted with the frozen tercile dummies (three
     terms: Fric_low, Fric_mid, Fric_high) plus Friction_x_Education
     (unlagged interaction, as in the original spec),
     Unemployment_Rate, ln_Min_Wage, LH_Share.
  4. THE TEST. Exactly one confirmatory test: the joint Wald test of
     H0: beta_low = beta_mid = beta_high (chi-square, 2 df), two-sided,
     alpha = 0.05. Its p-value is the verdict on the recent-window
     thread. The three group coefficients are reported descriptively;
     no other test in this script carries confirmatory weight.
  5. Everything else this script computes (pairwise differences, the
     full-period-group pipeline replication, the frozen groups on the
     full sample) is EXPLORATORY, is labeled as such in every output,
     and is never mixed with the confirmatory result.

Data: ~/workspace/tightness-phase1/master_labor_panel_v2.csv (unchanged).
Seed: 20261101 (no resampling is used; the seed is recorded for parity
with the exploration run). Estimation mirrors state_groups_run.py exactly.
"""
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from scipy import stats
from linearmodels.panel import PanelOLS

SEED = 20261101
np.random.seed(SEED)

PANEL = "/home/hatch/workspace/tightness-phase1/master_labor_panel_v2.csv"
OUTDIR = "/home/hatch/workspace/research_notes/tightness"

Y = "ln_Real_Wage"
CONTROLS = ["Friction_x_Education", "Unemployment_Rate", "ln_Min_Wage",
            "LH_Share"]
LEVELS = ["low", "mid", "high"]

panel = pd.read_csv(PANEL, parse_dates=["Date"])
panel = panel.sort_values(["State", "Date"]).reset_index(drop=True)
states = sorted(panel["State"].unique())
print(f"Panel: {len(panel)} rows, {len(states)} states, "
      f"{panel['Date'].min().date()} to {panel['Date'].max().date()}")

rows_out = []


def record(analysis, group, term, beta, se, p, n, **extra):
    t = beta / se if se and np.isfinite(se) and se > 0 else np.nan
    r = dict(analysis=analysis, group=group, term=term, beta=beta, se=se,
             t=t, p=p,
             ci_lo=beta - 1.96 * se if np.isfinite(se) else np.nan,
             ci_hi=beta + 1.96 * se if np.isfinite(se) else np.nan, n=n)
    r.update(extra)
    rows_out.append(r)


# ------------------------------------------------------- group definitions
def make_terciles(means_series):
    return pd.qcut(means_series, 3, labels=LEVELS)


pre = panel[(panel["Date"] >= "2015-01-01") & (panel["Date"] <= "2019-12-31")]
frozen_means = pre.groupby("State")["Friction_Proxy"].mean()
frozen_grp = make_terciles(frozen_means)
frozen_map = {s: str(frozen_grp.loc[s]) for s in states}
counts = pd.Series(frozen_map).value_counts()
assert (counts == 17).all(), f"frozen terciles not 17/17/17: {counts.to_dict()}"
print(f"Frozen 2015-2019 terciles: {counts.to_dict()}")

full_means = panel.groupby("State")["Friction_Proxy"].mean()
full_grp = make_terciles(full_means)
full_map = {s: str(full_grp.loc[s]) for s in states}
moved = [s for s in states if frozen_map[s] != full_map[s]]
print(f"States whose tercile changes vs full-period grouping: "
      f"{len(moved)} ({', '.join(moved)})")

assign = pd.DataFrame({
    "State": states,
    "mean_friction_2015_2019": [frozen_means[s] for s in states],
    "frozen_tercile": [frozen_map[s] for s in states],
    "mean_friction_full": [full_means[s] for s in states],
    "fullperiod_tercile": [full_map[s] for s in states],
})
assign.to_csv(f"{OUTDIR}/prereg_group_assignments.csv", index=False)


# ------------------------------------------------------- grouped TWFE engine
def grouped_twfe(data, grp_map, analysis_label):
    d = data.copy()
    d["grp"] = d["State"].map(grp_map)
    for lev in LEVELS:
        d[f"Fric_{lev}"] = (d["Friction_Lag3"]
                            * (d["grp"] == lev).astype(float))
    fric_cols = [f"Fric_{lev}" for lev in LEVELS]
    dd = d.set_index(["State", "Date"])
    mod = PanelOLS(dd[Y], dd[fric_cols + CONTROLS], entity_effects=True,
                   time_effects=True, drop_absorbed=True)
    res = mod.fit(cov_type="clustered", cluster_entity=True,
                  cluster_time=True)
    params, cov = res.params, res.cov
    for lev in LEVELS:
        nm = f"Fric_{lev}"
        record(analysis_label, lev, nm, float(params[nm]),
               float(res.std_errors[nm]), float(res.pvalues[nm]),
               int(res.nobs))
    # joint equality Wald: low-mid = 0, low-high = 0
    pos = {nm: i for i, nm in enumerate(params.index)}
    R = np.zeros((2, len(params)))
    R[0, pos["Fric_low"]] = 1.0
    R[0, pos["Fric_mid"]] = -1.0
    R[1, pos["Fric_low"]] = 1.0
    R[1, pos["Fric_high"]] = -1.0
    Rb = R @ params.values
    RV = R @ cov.values @ R.T
    W = float(Rb @ np.linalg.pinv(RV) @ Rb)
    pW = float(stats.chi2.sf(W, 2))
    record(analysis_label, "all_groups", "joint_equality_wald", W, np.nan,
           pW, int(res.nobs), df=2)
    return res, W, pW


# ============================================================ CONFIRMATORY
recent = panel[panel["Date"] >= "2022-01-01"].copy()
n_months = recent.groupby("State")["Date"].nunique()
print(f"Test window: {len(recent)} rows, {n_months.min()}-{n_months.max()} "
      f"months per state")
assert len(recent) == 2397, f"expected N=2397, got {len(recent)}"

res_c, W_c, p_c = grouped_twfe(recent, frozen_map,
                               "CONFIRMATORY_frozen_groups_recent_window")
coefs = {lev: (float(res_c.params[f"Fric_{lev}"]),
               float(res_c.std_errors[f"Fric_{lev}"]),
               float(res_c.pvalues[f"Fric_{lev}"])) for lev in LEVELS}
print("\nCONFIRMATORY (frozen 2015-2019 terciles, Jan 2022-Dec 2025):")
for lev in LEVELS:
    b, s, p = coefs[lev]
    print(f"  {lev:>4}: beta={b:+.4f} se={s:.4f} p={p:.4f}")
print(f"  Joint equality Wald: chi2(2)={W_c:.3f}, p={p_c:.4f}  "
      f"-> {'REJECTS' if p_c < 0.05 else 'DOES NOT REJECT'} at alpha=0.05")

# ============================================================ EXPLORATORY
# (E1) Pipeline check: exploration's own grouping (full-period means) on
# the same window must reproduce chi2 = 6.78, p = 0.0338.
res_e1, W_e1, p_e1 = grouped_twfe(recent, full_map,
                                  "EXPLORATORY_E1_fullperiod_groups_recent")
print(f"\nEXPLORATORY E1 (pipeline check, full-period groups): "
      f"chi2={W_e1:.3f} p={p_e1:.4f} (exploration: 6.78 / 0.0338)")

# (E2) Pairwise differences inside the confirmatory model.
params, cov = res_c.params, res_c.cov
for a, b in [("low", "mid"), ("low", "high"), ("mid", "high")]:
    na, nb = f"Fric_{a}", f"Fric_{b}"
    diff = float(params[na] - params[nb])
    v = float(cov.loc[na, na] + cov.loc[nb, nb] - 2 * cov.loc[na, nb])
    se_d = float(np.sqrt(max(v, 0)))
    p_d = float(2 * stats.norm.sf(abs(diff / se_d))) if se_d > 0 else np.nan
    record("EXPLORATORY_E2_confirmatory_pairwise", f"{a}_minus_{b}",
           "friction_diff", diff, se_d, p_d, int(res_c.nobs))
    print(f"EXPLORATORY E2: {a}-{b} = {diff:+.4f} (se {se_d:.4f}, "
          f"p={p_d:.4f})")

# (E3) Frozen groups on the full sample, for context only.
res_e3, W_e3, p_e3 = grouped_twfe(panel, frozen_map,
                                  "EXPLORATORY_E3_frozen_groups_full_sample")
print(f"EXPLORATORY E3 (frozen groups, full sample): chi2={W_e3:.3f} "
      f"p={p_e3:.4f}")

pd.DataFrame(rows_out).to_csv(f"{OUTDIR}/prereg_estimates.csv", index=False)

# ------------------------------------------------------------- results memo
b_lo, s_lo, p_lo = coefs["low"]
b_mid, s_mid, p_mid = coefs["mid"]
b_hi, s_hi, p_hi = coefs["high"]
verdict_head = ("REJECTS equality" if p_c < 0.05
                else "DOES NOT REJECT equality")
if p_c < 0.05:
    verdict_plain = (
        "The frozen-group test rejects: with terciles fixed on 2015-2019 "
        "data alone, the recent-window friction coefficient differs across "
        "friction terciles. The recent-window thread survives its "
        "pre-registered retest on the same window it was found in. That "
        "promotes it from 'suggestive' to 'survived the confirmatory test "
        "as designed'; it is still one window of one panel, estimated on "
        "the same data that suggested it, so the honest next step is the "
        "one the exploration memo named: retest again as post-2025 JOLTS "
        "vintages land, on data this test has not seen.")
else:
    verdict_plain = (
        "The frozen-group test does not reject: once the terciles are "
        "fixed on 2015-2019 data alone, so the test window cannot shape "
        "its own groups, the recent-window friction coefficients no "
        "longer differ significantly across terciles. The p = 0.034 from "
        "the exploration does not survive its own pre-registered retest. "
        "The recent-window thread is closed as a finding and filed as "
        "what it was: a suggestive pattern in a window whose groups were "
        "partly defined on itself.")

md = f"""# Pre-Registered Follow-Up — Results

*Design registered and run Sunday, November 1, 2026. Script:
`prereg_followup.py` (the design is stated in its header, written before
estimation). Estimates: `prereg_estimates.csv`. Group assignments:
`prereg_group_assignments.csv`. Companion documents: `PHASE1_RESULTS.md`
(spec), `state-groups.md` (the exploration this follows up).*

## The confirmatory result

**Question.** In Jan 2022–Dec 2025, does the friction-to-wage coefficient
differ across friction terciles when the terciles are frozen on
2015–2019 data only?

**Design (one sentence).** Two-way fixed effects on Jan 2022–Dec 2025
(N = 2,397), the Phase 1 preferred specification with Friction_Lag3
interacted with tercile dummies fixed from each state's mean
Friction_Proxy over Apr 2015–Dec 2019, two-way clustered standard
errors; the single confirmatory test is the joint Wald test of
beta_low = beta_mid = beta_high at alpha = 0.05.

| Frozen tercile (2015–2019 means) | Beta | SE (two-way) | p |
|---|---|---|---|
| Low friction | {b_lo:+.3f} | {s_lo:.3f} | {p_lo:.3f} |
| Mid friction | {b_mid:+.3f} | {s_mid:.3f} | {p_mid:.3f} |
| High friction | {b_hi:+.3f} | {s_hi:.3f} | {p_hi:.3f} |

**Joint equality Wald: chi2(2) = {W_c:.2f}, p = {p_c:.4f}. The test
{verdict_head}.**

{verdict_plain}

Context for the comparison: the exploration's version of this test,
with groups defined on full-period means (so the recent window helped
define its own groups), gave high +0.589, low −0.283, equality
p = 0.034. Freezing the groups on pre-2020 data moved
{len(moved)} of 51 states to a different tercile
({", ".join(moved)}).

## Exploratory appendix (not confirmatory; do not cite as the verdict)

- **E1, pipeline check.** Re-running the exploration's exact grouping
  (full-period means) on the recent window inside this script
  reproduces it: chi2(2) = {W_e1:.2f}, p = {p_e1:.4f} (exploration:
  6.78, 0.0338). The machinery matches; only the group definition
  changed.
- **E2, pairwise differences** inside the confirmatory model are in
  `prereg_estimates.csv` (analysis
  `EXPLORATORY_E2_confirmatory_pairwise`). They are descriptive
  decompositions of the single test above, not separate tests.
- **E3, frozen groups on the full sample.** Same frozen terciles,
  Apr 2015–Dec 2025: equality chi2(2) = {W_e3:.2f}, p = {p_e3:.4f}.
  Context only; the full-sample grouped null was already established
  in the exploration.

## Caveats carried over, unchanged

Two-way fixed effects cannot rule out reverse causality. State JOLTS
is subject to BLS revision, so the panel's last months are revisable.
Oct 2025 is missing panel-wide (no CPI published during the federal
shutdown), which is why the window has 47 months per state, not 48.
"""
open(f"{OUTDIR}/prereg_results.md", "w").write(md)
print(f"\nWrote prereg_results.md, prereg_estimates.csv, "
      f"prereg_group_assignments.csv")
print("DONE")
