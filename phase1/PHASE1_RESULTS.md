# Phase 1 Results — Tightness Paradox 50-State Rebuild

*Completed 2026-09-28. Script: `phase1_rebuild.py` (reproducible end-to-end,
seed 20260928). Data vintage: downloaded 2026-09-28.*

## Panel

- **50 states + DC (51 jurisdictions) × 128 months = 6,528 obs**
- Date range: 2015-04-01 → 2025-12-01
  (JOLTS state data binds the end of the panel; LAUS/CES/CPI run to Aug 2026.)
- Sources: BLS API v2 — JOLTS state openings/hires; LAUS `LASST…0000006/3`
  (labor force / UR); CES `SMU…500000003` (avg hourly earnings, total private),
  `SMU…700000001` (LH employment, thousands); national CPI-U
  (`CUUR0000SA0` = FRED `CPIAUCSL`). `Real_Wage =
  Hourly_Wage / National_CPI * National_CPI_Jan2015` (Jan-2015 dollars,
  exact original formula). Regional CPI kept for reference.
- Annual controls: minimum wage from Wikipedia's "List of U.S. states by
  minimum wage" (cites U.S. DOL), 2019-2026; 2015-2018 backward-filled from
  2019 (federal floor 7.25). Education (% bachelor's+, 25+) from Census
  GCT1502 (2018, 2019) + ACS B15002 summary files via Census FTP (2021-2024);
  2015-2017 backward-filled from 2018, 2020 forward-filled from 2019
  (ACS 1-year not released for 2020), 2025 forward-filled from 2024.
- Same 23-column schema as `master_labor_panel.csv`, plus `Region`,
  `Unfilled_Share`, `Unfilled_Share_Lag3`, `Friction_pp_Proxy`,
  `Friction_pp_Lag3`, `Friction_x_Education_Lag3`.
- FRED annual-series fetch failures: none.

## Validation vs original 25-state panel (overlap: 2,625 obs)

Max / mean absolute differences, v2 minus original:

| column | max abs diff | mean abs diff |
|---|---|---|
| Openings | 137.000000 | 1.774476 |
| Hires | 22.000000 | 1.099810 |
| Labor_Force | 0.000000 | 0.000000 |
| Unemployment_Rate | 0.000000 | 0.000000 |
| Hourly_Wage | 0.000000 | 0.000000 |
| LH_Employment | 0.000000 | 0.000000 |
| Friction_Proxy | 0.007198 | 0.000387 |
| Real_Wage | 0.277562 | 0.122309 |
| ln_Real_Wage | 0.009051 | 0.004790 |
| Friction_Lag3 | 0.007198 | 0.000359 |
| Min_Wage | 3.000000 | 0.351783 |
| Educ_Attainment | 5.093347 | 2.090993 |

*(Labor_Force, Unemployment_Rate, Hourly_Wage, LH_Employment match the original
pull exactly. Small diffs in Openings, Hires, Real_Wage / ln_Real_Wage /
Friction reflect BLS vintage revisions since the original download. Larger
diffs in Min_Wage / Educ_Attainment come from the
fallback construction of the 2015-2018 edges, not from source data — see
"Limitations" below. Full table: `validation_vs_original.csv`.)*

## Headline estimates

Spec (exact original Stage 1): TWFE `ln_Real_Wage ~ Friction_Lag3 +
Friction_x_Education + Unemployment_Rate + ln_Min_Wage + LH_Share`
(state + month FE), where `Friction_x_Education = Friction_Proxy *
ln_Education` is the **unlagged** interaction per the original notebook.
(The lagged-interaction variant is reported separately in the robustness
battery.)

| spec | coef | SE | t | p | N |
|---|---|---|---|---|---|
| baseline (SEs clustered by state) | 0.0582 | 0.0888 | 0.66 | 0.5123 | 6,528 |
| baseline (two-way clustered: state x month) | 0.0582 | 0.0944 | 0.62 | 0.5378 | 6,528 |
| baseline (Driscoll-Kraay) | 0.0582 | 0.0889 | 0.65 | 0.5128 | 6,528 |
| friction in pp units (two-way SE) | 0.0006 | 0.0009 | 0.62 | 0.5378 | 6,528 |
| unfilled share 1-hires/openings (two-way SE) | 0.0056 | 0.0046 | 1.23 | 0.2184 | 6,528 |

Original 25-state headline: β = 6.1657 (state-clustered, p < 0.05).

**Verdict on the original finding:** DOES NOT SURVIVE —
on the expanded 50-state + DC panel the friction coefficient is 0.0582
(two-way-clustered p = 0.5378).

## Plain-English marginal effects (two-way SE spec)

Average marginal effect of friction given the interaction,
AME = b1 + b2 × mean(ln_Education) = 0.1233:

- 1 pp rise in the unfilled-openings share of the labor force →
  **0.12% higher real wages** (3 months later).
- 1 SD rise in lagged friction (SD = 0.0116) →
  **0.14% higher real wages**.
- The pp-units regression reads directly: coef on `Friction_pp_Lag3` =
  0.0006 (≈ % wage change per pp).

## Absorption audit (`drop_absorbed=True`)

- preferred two-way TWFE: none dropped
- pp-units TWFE: none dropped
- unfilled-share TWFE: none dropped
- lagged-interaction TWFE: none dropped
- excl-ln_Min_Wage TWFE: none dropped
- state x year + month FE: dropped: ['ln_Min_Wage']
- break-test (all regressors x Post-2021): none dropped

## Robustness battery

| check | value |
|---|---|
| leave-one-state-out: min coef | 0.0342 |
| leave-one-state-out: max coef | 0.0956 |
| leave-one-state-out: share p<0.05 | 0.0000 |
| placebo: actual t-stat | 0.6162 |
| placebo: share |t_shuffled| >= |t_actual| | 0.5300 |
| placebo: share shuffled |t|>1.96 | 0.0500 |
| winsorized 1/99: coef | 0.0334 |
| winsorized 1/99: p | 0.7647 |
| nominal wage DV: coef | 0.0582 |
| nominal wage DV: p | 0.5378 |
| excl 2020-2021: coef | -0.0148 |
| excl 2020-2021: p | 0.9038 |
| excl 2020-2021: n | 5304 |
| lagged-interaction variant: coef | 1.7428 |
| lagged-interaction variant: p | 0.2104 |
| excl ln_Min_Wage: coef | 0.0952 |
| excl ln_Min_Wage: p | 0.3198 |
| state x year FE: coef | 0.0297 |
| state x year FE: p | 0.4014 |

- Break test (all regressors × Post-2021, Wald): chi2(5) =
  6.50, p = 0.2608.
  → No significant break at 2021 (consistent with the original Stage 3 null).
- Friction×Post-2021 interaction: coef =
  -0.2693,
  p = 0.2087.

## Inefficiency-tax verdict

Marginal tax coefficient per state: b1 + b2 × ln_Education (state mean),
SEs by the delta method from the full 2×2 coefficient covariance; national
aggregate SE from the same common covariance (g′Vg), not root-summed state SEs.

**CUT IT.** The headline coefficient is not significant on the expanded panel, so any tax built on it inherits that fragility. Drop the exhibit; the wage regression is the paper.

National back-of-envelope (descriptive): $11.9B/yr
(SE $15.3B). State table: `inefficiency_tax.csv`.

## Limitations

- **Panel end:** JOLTS state series bind the panel; at pull time state JOLTS
  ran through Dec 2025 (national JOLTS ran to Jul 2026). LAUS/CES/CPI ran to
  Aug 2026. Extending further requires only a re-pull of the JOLTS pickle.
- **Oct 2025 gap:** the panel has 128 months, not 129, because BLS did not
  publish a CPI for October 2025 (federal shutdown) — national and regional
  CPI are both missing that month, so Real_Wage cannot be constructed and the
  month drops for all 51 jurisdictions. It is the only missing CPI month in
  the 2014-2026 window.
- **Min wage 2015-2018:** backward-filled from 2019 values (Wikipedia's
  DOL-cited table starts 2019; FRED `STTMINWG` starts 2019 as well). This
  overstates early rates in states that raised minimums mid-decade; the
  "excl ln_Min_Wage" robustness spec tests sensitivity.
- **Education 2015-2017:** backward-filled from 2018; 2020 forward-filled from
  2019 (ACS 1-year not released for 2020); 2025 forward-filled from 2024.
- The national "ghost jobs" CSV (if used elsewhere) is constructed national
  data, not state-level posting-duration evidence; it does not independently
  validate ghost jobs.
- The TWFE cannot rule out reverse causality; the tax exhibit is descriptive
  (an upper bound) pending Phase 2's Bartik IV.

## Files

- `master_labor_panel_v2.csv` — rebuilt panel
- `phase1_rebuild.py` — full rebuild + estimation script (seed 20260928)
- `headline_estimates.csv`, `preferred_spec_coefs.csv`, `robust_loso.csv`,
  `robust_placebo.csv`, `robustness.csv`, `inefficiency_tax.csv`,
  `validation_vs_original.csv` — machine-readable outputs
- `phase1_forest_loso.png` — leave-one-state-out forest plot
