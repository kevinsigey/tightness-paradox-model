# Tightness Paradox — Does the pooled null hide state-level effects?

*Exploration run 2026-11-01. Script: `state_groups_run.py` (seed 20261101).
All estimates: `state_groups_estimates.csv`; per-state detail:
`per_state_full.csv`, `per_state_recent.csv`; group assignments:
`state_group_assignments.csv`. Visuals: `state_forest.png`,
`grouped_coefficients.png`. Exploration only — the published paper is
unchanged.*

## Bottom line

**Verdict: suggestive in exactly one narrow place, noise almost everywhere
else — and nothing that revives the original positive story.**

1. **The direct test of the hypothesis fails on the full sample.** Splitting
   states six ways (friction level, unemployment, wage level, LH-share
   industry mix, labor-force size, Census region) inside the preferred TWFE
   design, **no grouping produces group coefficients that differ
   significantly from each other** (joint equality Wald p ≥ 0.11 for all
   six). The pooled null is not an artifact of averaging across these
   observable state types.
2. **Per-state regressions do show more dispersion than chance** (Q test
   below), and 8 states survive FDR correction — but **every survivor is
   negative**. Higher friction is associated with *lower* subsequent real
   wages in those states, the opposite of the original paper's claim. Zero
   states show a positive friction effect that survives FDR in the full
   sample. The two nominally positive states (DC +0.56, NM +0.59) do not
   survive any correction.
3. **The one live thread is the recent window, grouped by friction level.**
   In Jan 2022–Dec 2025, the high-friction tercile's TWFE coefficient is
   **+0.589 (p = 0.008)** against −0.283 for the low tercile, and the
   equality test rejects (p = 0.034). The same monotone tilt appears for
   unemployment, LH-share, and labor-force-size groupings. But it is one
   p = 0.034 among 12 equality tests run (Bonferroni-adjusted ≈ 0.41), and
   the per-state recent estimates are far too unstable to name individual
   states (below). File under *suggestive, pre-register and retest*, not
   *finding*.

## Design (mirrors the Phase 1 preferred spec)

- Outcome `ln_Real_Wage`; regressors `Friction_Lag3` (3-month lag, as
  constructed in the panel), the **unlagged** interaction
  `Friction_x_Education`, `Unemployment_Rate`, `ln_Min_Wage`, `LH_Share`.
- Pooled and grouped runs: state + month FE, two-way clustered SEs
  (state × month). The pooled full-sample run reproduces Phase 1 exactly:
  β = 0.0582, SE = 0.0944, p = 0.538.
- Per-state runs cannot carry state/month FE within one state, so each
  state is a time-series OLS with the same regressors plus an intercept
  and a linear trend, Newey–West HAC SEs (lag length
  floor(4·(T/100)^(2/9)): 4 lags at T = 128, 3 at T = 47). This design
  difference matters — see "Why the per-state mean is negative."
- Group membership is fixed from **full-period state means** in both
  windows (17/17/17 terciles), so the recent window uses the same groups.

## Grouped estimates (TWFE, friction interacted with group)

Full sample, Apr 2015–Dec 2025 (N = 6,528). Coefficients (two-way
clustered SEs); last columns are the joint equality Wald test.

| Grouping | Group coefficients | χ² | p |
|---|---|---|---|
| friction_level | low: +0.136 (0.217) \| mid: +0.080 (0.167) \| high: −0.000 (0.165) | 0.30 | 0.8621 |
| unemployment | low: +0.279 (0.165) \| mid: +0.155 (0.190) \| high: −0.176 (0.165) | 4.40 | 0.1105 |
| wage_level | low: +0.363 (0.177) \| mid: −0.001 (0.181) \| high: −0.111 (0.160) | 4.32 | 0.1152 |
| lh_share_industry_mix | low: +0.052 (0.201) \| mid: +0.249 (0.167) \| high: −0.105 (0.164) | 2.59 | 0.2738 |
| labor_force_size | low: +0.080 (0.167) \| mid: +0.166 (0.180) \| high: −0.086 (0.189) | 0.92 | 0.6318 |
| census_region | Midwest: +0.052 (0.161) \| Northeast: −0.264 (0.250) \| South: −0.007 (0.211) \| West: +0.408 (0.222) | 3.75 | 0.2900 |

Only two individual group coefficients are even nominally significant
(low-wage tercile +0.363, p = 0.041; West +0.408, p = 0.067), and neither
grouping's coefficients differ from each other. Of 21 pairwise difference
tests, 3 reach p < 0.10 unadjusted (smallest: unemployment low−high
+0.455, p = 0.037) — about what 21 tests produce by chance.

Recent window, Jan 2022–Dec 2025 (N = 2,397; pooled β = +0.102, SE 0.096,
p = 0.289):

| Grouping | Group coefficients | χ² | p |
|---|---|---|---|
| friction_level | low: −0.283 (0.270) \| mid: −0.070 (0.174) \| high: +0.589 (0.221) | 6.78 | 0.0338 |
| unemployment | low: −0.305 (0.239) \| mid: +0.170 (0.245) \| high: +0.431 (0.184) | 5.08 | 0.0788 |
| wage_level | low: −0.122 (0.263) \| mid: −0.100 (0.204) \| high: +0.394 (0.215) | 3.15 | 0.2074 |
| lh_share_industry_mix | low: −0.157 (0.297) \| mid: −0.003 (0.185) \| high: +0.408 (0.197) | 3.32 | 0.1900 |
| labor_force_size | low: −0.238 (0.280) \| mid: +0.166 (0.220) \| high: +0.384 (0.191) | 2.79 | 0.2477 |
| census_region | Midwest: +0.224 (0.231) \| Northeast: +0.518 (0.357) \| South: +0.203 (0.272) \| West: −0.328 (0.234) | 4.00 | 0.2612 |

The recent pattern is coherent — coefficients rise monotonically from the
low to the high tercile for friction, unemployment, LH share, and labor
force size — and it is not one cluster of states recycled: the high
terciles of the different groupings overlap by only ~7 of 17 states.
Against it: 12 equality tests were run across the two windows, so the
single rejection at p = 0.034 is not family-wise significant, and group
membership was defined on full-period means that include the recent
window itself.

## Per-state estimates and the multiple-testing discipline

Full sample (T = 128/state). Distribution of the 51 coefficients on
`Friction_Lag3`: median **−0.267**, interquartile range [−0.609, −0.038],
range [−1.537 (HI), +0.613 (AL)]; **41 of 51 are negative**. (Full table
below; forest plot in `state_forest.png`.)

- Nominal p < 0.05: **16 states** (14 negative, 2 positive). Chance alone
  at 5% across 51 tests predicts ~2.6 — so 16 is far more than the
  false-positive baseline. There *is* signal here; the question is what
  it means.
- **Benjamini–Hochberg FDR (q < 0.05): 8 states survive, all negative** —
  DE (−1.518), HI (−1.537), OK (−0.981), NC (−0.716), FL (−0.638),
  ID (−1.326), AZ (−0.600), MN (−0.589).
- **Bonferroni: 2 states** — DE (adjusted p = 0.0035) and OK (0.0268).
- Heterogeneity check (DerSimonian–Laird on the 51 estimates):
  **Q = 112.8 on 50 df, p ≈ 1×10⁻⁶; I² = 56%; τ² = 0.090 (τ ≈ 0.30).**
  The cross-state dispersion genuinely exceeds what the standard errors
  imply. This is not pure noise *as a distribution*.
- Empirical-Bayes shrinkage toward the random-effects mean (−0.312)
  compresses the range to [−0.773 (DE), +0.189]; 19 states' shrunken 95%
  posterior intervals exclude zero — again, **all 19 on the negative
  side**.

### Why the per-state mean is negative (read before citing any state)

The precision-weighted mean of the per-state coefficients is **−0.27**,
while the pooled TWFE estimate is **+0.058**. Same data, same regressors —
the difference is the design. The pooled spec's month fixed effects absorb
the national cycle; a single-state time series cannot. Friction is
strongly countercyclical and moves in common across states, so each
per-state coefficient also picks up that state's wage exposure to the
national cycle (above all 2020–21, when friction spiked and real wages
moved violently). The grouped TWFE — which keeps month FE and is
therefore the cleaner test — finds no full-sample group differences at
all. Treat the per-state negatives as *"states where the friction series
and the wage series co-moved negatively over a decade that included a
pandemic,"* not as estimates of a state-level friction effect. The
average marginal effects (b1 + b2·mean ln Education, delta-method) are
even less stable within states (22 nominal, 21 BH-significant, with
inconsistent signs from DE −3.02 to CA +1.38): the education interaction
is weakly identified in a single state's time series, so the AME is
reported in the CSV for completeness but is not decision-grade.

### Recent window, per state (T = 47/state)

9 states nominal p < 0.05; the two correction survivors point in
**opposite directions**: NJ **+1.489** (BH q = 0.0095, Bonferroni
p = 0.0095) and NV **−1.097** (BH q = 0.023, Bonferroni p = 0.047).
State rankings do not persist across windows: the correlation between
full-sample and recent betas is **0.14**. The full-sample FDR survivors
fade (DE −0.612, p = 0.102; OK flips to +0.241, p = 0.702), and NJ itself
was **−0.697 (p = 0.015)** on the full sample — a sign flip. Whatever the
recent window contains, it is not a stable list of "states where friction
works." Q in the recent window: 100.2 on 50 df (p ≈ 3×10⁻⁵), I² = 50%,
τ² = 0.121 — dispersion is again real, again unsigned.

## Caveats

- **Panel end / vintage:** the panel already runs through **Dec 2025**
  (monthly, Apr 2015–Dec 2025), so the "recent" window above *is* the
  latest data, not a stale cut. State JOLTS binds the panel end (Phase 1
  pull, downloaded 2026-09-28) and state JOLTS is subject to BLS revision;
  treat the last months as revisable. Oct 2025 is missing for all states
  (no CPI published during the federal shutdown), so the recent window
  has 47 months per state, not 48.
- **Grouping is descriptive:** terciles of full-period means; the recent
  window's groups are partly defined on themselves. A confirmatory
  version would fix groups on pre-2022 data only.
- WV's `ln_Min_Wage` is constant and drops from its per-state regression
  (recorded in the CSV); no other state lost a regressor.
- Nothing here addresses reverse causality; the TWFE caveat from Phase 1
  carries over unchanged.

## If Kevin wants to chase the one thread

Pre-register this exact test before touching newer data: TWFE on
Jan 2022 onward, friction-tercile interaction with groups fixed on
**2015–2019 means only**, equality Wald as the single test. If it
survives on post-2025 JOLTS vintages as they are published, it becomes a
finding; if it fades like the per-state heroes did, it was the window.

## Per-state table (full sample, sorted by beta; recent window alongside)

| State | Beta | SE (NW) | raw p | BH q | Bonf p | Recent beta | Recent p |
|---|---|---|---|---|---|---|---|
| HI | -1.537 | 0.480 | 0.0014 | 0.0174 | 0.0695 | -0.328 | 0.4098 |
| DE | -1.518 | 0.381 | 0.0001 | 0.0035 | 0.0035 | -0.612 | 0.1020 |
| ID | -1.326 | 0.489 | 0.0067 | 0.0428 | 0.3418 | -0.906 | 0.0161 |
| SC | -1.217 | 0.516 | 0.0183 | 0.0922 | 0.9314 | -0.684 | 0.0594 |
| OK | -0.981 | 0.283 | 0.0005 | 0.0134 | 0.0268 | 0.241 | 0.7019 |
| GA | -0.803 | 0.386 | 0.0373 | 0.1268 | 1.0000 | 0.297 | 0.6709 |
| NE | -0.794 | 0.419 | 0.0578 | 0.1474 | 1.0000 | -0.917 | 0.0814 |
| MS | -0.784 | 0.410 | 0.0557 | 0.1474 | 1.0000 | -1.086 | 0.1112 |
| WV | -0.717 | 0.373 | 0.0541 | 0.1474 | 1.0000 | -0.587 | 0.3389 |
| NC | -0.716 | 0.242 | 0.0031 | 0.0312 | 0.1560 | -0.601 | 0.1428 |
| NJ | -0.696 | 0.288 | 0.0154 | 0.0875 | 0.7874 | 1.489 | 0.0002 |
| FL | -0.638 | 0.227 | 0.0049 | 0.0419 | 0.2515 | -0.223 | 0.5027 |
| MT | -0.615 | 0.264 | 0.0199 | 0.0922 | 1.0000 | -0.178 | 0.6822 |
| SD | -0.602 | 0.303 | 0.0469 | 0.1474 | 1.0000 | -0.180 | 0.7459 |
| LA | -0.600 | 0.328 | 0.0674 | 0.1623 | 1.0000 | -0.448 | 0.1001 |
| AZ | -0.600 | 0.183 | 0.0011 | 0.0174 | 0.0550 | -0.379 | 0.3407 |
| MN | -0.589 | 0.217 | 0.0067 | 0.0428 | 0.3424 | -0.136 | 0.7049 |
| AR | -0.584 | 0.356 | 0.1011 | 0.2149 | 1.0000 | -1.164 | 0.0133 |
| NY | -0.566 | 0.340 | 0.0959 | 0.2127 | 1.0000 | -0.055 | 0.8942 |
| TX | -0.565 | 0.312 | 0.0700 | 0.1623 | 1.0000 | -0.842 | 0.0315 |
| CT | -0.557 | 0.292 | 0.0565 | 0.1474 | 1.0000 | 0.216 | 0.1387 |
| WY | -0.557 | 0.248 | 0.0246 | 0.1046 | 1.0000 | -0.264 | 0.3291 |
| AK | -0.412 | 0.324 | 0.2039 | 0.3624 | 1.0000 | -0.335 | 0.0780 |
| MO | -0.397 | 0.320 | 0.2150 | 0.3655 | 1.0000 | -0.875 | 0.0942 |
| WI | -0.297 | 0.297 | 0.3169 | 0.5050 | 1.0000 | 0.205 | 0.6370 |
| IA | -0.267 | 0.427 | 0.5321 | 0.6941 | 1.0000 | 0.392 | 0.1658 |
| VT | -0.257 | 0.243 | 0.2904 | 0.4777 | 1.0000 | -1.213 | 0.0174 |
| OH | -0.225 | 0.167 | 0.1772 | 0.3347 | 1.0000 | -0.242 | 0.5371 |
| PA | -0.212 | 0.168 | 0.2061 | 0.3624 | 1.0000 | -0.705 | 0.0049 |
| VA | -0.211 | 0.408 | 0.6049 | 0.7525 | 1.0000 | -0.916 | 0.1006 |
| ME | -0.211 | 0.310 | 0.4959 | 0.6655 | 1.0000 | -0.133 | 0.6898 |
| IL | -0.210 | 0.268 | 0.4339 | 0.6148 | 1.0000 | -0.565 | 0.0654 |
| CA | -0.205 | 0.237 | 0.3887 | 0.5893 | 1.0000 | 1.057 | 0.0373 |
| WA | -0.190 | 0.235 | 0.4185 | 0.6099 | 1.0000 | -0.468 | 0.2468 |
| KS | -0.156 | 0.506 | 0.7578 | 0.8620 | 1.0000 | -0.106 | 0.8700 |
| MI | -0.121 | 0.200 | 0.5444 | 0.6941 | 1.0000 | 0.113 | 0.7310 |
| KY | -0.092 | 0.303 | 0.7606 | 0.8620 | 1.0000 | -0.286 | 0.4275 |
| TN | -0.043 | 0.236 | 0.8556 | 0.9486 | 1.0000 | 0.183 | 0.6321 |
| OR | -0.032 | 0.208 | 0.8769 | 0.9516 | 1.0000 | -0.377 | 0.3944 |
| CO | -0.022 | 0.180 | 0.9037 | 0.9602 | 1.0000 | 0.048 | 0.8568 |
| UT | -0.017 | 0.438 | 0.9685 | 0.9685 | 1.0000 | -0.028 | 0.8834 |
| IN | 0.008 | 0.183 | 0.9638 | 0.9685 | 1.0000 | 0.613 | 0.1437 |
| ND | 0.015 | 0.299 | 0.9607 | 0.9685 | 1.0000 | -1.009 | 0.0980 |
| RI | 0.103 | 0.284 | 0.7175 | 0.8510 | 1.0000 | -0.053 | 0.9244 |
| NV | 0.136 | 0.160 | 0.3928 | 0.5893 | 1.0000 | -1.097 | 0.0009 |
| NH | 0.138 | 0.353 | 0.6960 | 0.8452 | 1.0000 | 0.022 | 0.9658 |
| MA | 0.174 | 0.254 | 0.4922 | 0.6655 | 1.0000 | -0.842 | 0.0048 |
| MD | 0.353 | 0.258 | 0.1721 | 0.3347 | 1.0000 | 0.067 | 0.8911 |
| DC | 0.562 | 0.258 | 0.0296 | 0.1162 | 1.0000 | 0.306 | 0.1451 |
| NM | 0.594 | 0.278 | 0.0329 | 0.1197 | 1.0000 | -0.196 | 0.6189 |
| AL | 0.613 | 0.437 | 0.1606 | 0.3276 | 1.0000 | -0.609 | 0.2245 |