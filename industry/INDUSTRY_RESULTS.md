# Industry Results — Tightness Paradox Industry-Level Test

*Completed 2026-09-28; corrected and re-run 2026-11-01. Script:
`industry_run.py` (reproducible end-to-end, seed 20260928).*
*Correction (2026-11-01): the professional & business services JOLTS
series was originally pulled with series block 600000, which is the
education & health services supersector, so the panel's prof_bus rows
duplicated edu_health. Corrected to the professional & business services
series block 540099 (JTS540099000000000JOL/HIL) and re-run on the same
Apr 2015 - Jul 2026 window. Only the prof_bus rows changed; every other
industry's figures are identical to the September run.*
*Follow-up to Phase 1, which returned a clean null at the state level
(headline beta 0.0582, two-way p ~ 0.54 on 50 states + DC).*

## Panel

- **10 industries x 135 months = 1,350 obs**
  (wage panel; government has no CES wage series and is descriptives-only)
- Date range: 2015-04-01 -> 2026-07-01
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
| edu_health | 0.4707 | 2.960 | 25.41 |
| financial | 0.4611 | 2.192 | 33.13 |
| information | 0.2951 | 1.554 | 37.43 |
| manufacturing | 0.2550 | 1.195 | 25.31 |
| total_private | 0.1905 | 1.153 | 25.74 |
| other_svc | 0.1718 | 1.074 | 23.25 |
| prof_bus | 0.1679 | 1.265 | 30.97 |
| ttu | 0.0861 | 0.523 | 22.15 |
| leisure | -0.0803 | -0.207 | 15.53 |
| construction | -0.4236 | -1.192 | 28.04 |

## Headline estimates

Pooled TWFE: `ln_Real_Wage ~ Unfilled_Share_Lag3`, industry + month FE
(month FE absorbs the national unemployment rate and all common shocks).

| spec | coef | SE | t | p | N |
|---|---|---|---|---|---|
| unfilled share lag3 (two-way: industry x month) | 0.0101 | 0.0146 | 0.69 | 0.4882 | 1,350 |
| unfilled share lag3 (Driscoll-Kraay) | 0.0101*** | 0.0038 | 2.63 | 0.0087 | 1,350 |
| unfilled share lag3 (clustered by industry) | 0.0101 | 0.0147 | 0.69 | 0.4905 | 1,350 |
| friction pp lag3 (two-way) | 0.0046 | 0.0033 | 1.36 | 0.1725 | 1,350 |

Interpretation: a 1 pp rise in the lagged unfilled share of openings is
associated with a 1.01% change in real industry wages
(coef is in log points per unit share).

## Per-industry time series

OLS per industry: `ln_Real_Wage ~ Unfilled_Share_Lag3 + trend`,
Newey-West (6 lags) SEs, sorted by p-value:

| industry | coef | SE | t | p | n |
|---|---|---|---|---|---|
| financial | -0.1160*** | 0.0362 | -3.21 | 0.0013 | 135 |
| other_svc | -0.0185*** | 0.0058 | -3.17 | 0.0015 | 135 |
| manufacturing | -0.0482*** | 0.0153 | -3.16 | 0.0016 | 135 |
| total_private | -0.0489*** | 0.0184 | -2.65 | 0.0080 | 135 |
| leisure | 0.0211** | 0.0084 | 2.51 | 0.0122 | 135 |
| prof_bus | -0.0402** | 0.0180 | -2.24 | 0.0251 | 135 |
| construction | -0.0061 | 0.0050 | -1.22 | 0.2211 | 135 |
| edu_health | -0.0224 | 0.0194 | -1.15 | 0.2485 | 135 |
| information | -0.0197 | 0.0230 | -0.86 | 0.3918 | 135 |
| ttu | -0.0172 | 0.0210 | -0.82 | 0.4136 | 135 |

Industries with p < 0.05: financial, other_svc, manufacturing,
total_private, prof_bus (all **negative**), and leisure (**positive**).

Note the sign pattern: five of the six significant per-industry estimates go
the **wrong way** for the hypothesis — higher unfilled shares predict
*lower* wages three months later. The two predicted industries
(edu_health p = 0.25, information p = 0.39) are both null. The negative
estimates are consistent with reverse causality (low-wage industries struggle
to fill openings) rather than with tightness pushing wages up; either way
they contradict the friction-raises-wages story.

## Concentration test

Pooled TWFE with `Unfilled_Share_Lag3 x I(predicted industry)` interaction
(predicted = education & health services, information):

- Interaction coef: -0.0183, SE 0.0202, p = 0.3662.
- No significant concentration of the effect in the predicted industries.

## Robustness battery

| check | value |
|---|---|
| leave-one-industry-out: min coef | -0.0010 |
| leave-one-industry-out: max coef | 0.0301 |
| leave-one-industry-out: share p<0.05 | 0.0000 |
| placebo: actual t-stat | 0.6934 |
| placebo: share |t_shuffled| >= |t_actual| | 0.4950 |
| placebo: share shuffled |t|>1.96 | 0.0800 |
| winsorized 1/99: coef | 0.0130 |
| winsorized 1/99: p | 0.4524 |
| industry trends: coef | 0.0046 |
| industry trends: p | 0.4799 |
| excl 2020-2021: coef | 0.0096 |
| excl 2020-2021: p | 0.5500 |
| excl 2020-2021: n | 1110 |

Leave-one-industry-out detail:

| dropped | coef | p |
|---|---|---|
| leisure | -0.0010 | 0.8535 |
| manufacturing | 0.0074 | 0.6233 |
| edu_health | 0.0082 | 0.5754 |
| ttu | 0.0091 | 0.5362 |
| information | 0.0098 | 0.5248 |
| total_private | 0.0101 | 0.4911 |
| prof_bus | 0.0101 | 0.5144 |
| other_svc | 0.0118 | 0.5099 |
| financial | 0.0147 | 0.3249 |
| construction | 0.0301 | 0.2051 |

## Verdict

**NULL AT INDUSTRY LEVEL TOO.** Pooled beta = 0.0101 (two-way p = 0.4882).
The friction-wage link fails at both the state and industry level; the
evidence points to the measurement-paper pivot: openings-minus-hires does
not behave like economic tightness.

On the Driscoll-Kraay discrepancy (DK p = 0.0087 vs two-way p = 0.49):
the DK significance does not survive scrutiny. It vanishes when
industry-specific trends are added (p = 0.48), no leave-one-industry-out run
is significant, and — most damning — the significant per-industry estimates
are predominantly *negative*, the opposite sign of the pooled DK effect.
A positive pooled coefficient built on negative industry-level coefficients
is a weighting artifact, not a real effect. The pre-committed headline
inference (two-way clustering) and the full robustness battery agree: null.

The phantom itself is real and concentrates where predicted — education &
health services has the highest mean unfilled share (0.47) and government
(descriptives-only, no CES wage series) is comparably extreme. It just does
not predict wages. That is the measurement paper: the ghost-job phantom is a
first-order feature of the labor market that openings-based tightness
measures misread as demand pressure.

## Limitations

- Only 10 industry clusters (9 proper industries + the total-private
  aggregate, which LOIO shows does not drive the result): two-way clustering
  is thin on the industry dimension; Driscoll-Kraay (T ~ 135) is the more
  credible SE here in principle, but see the Verdict section — the two
  disagree and the DK significance collapses under scrutiny. Stated openly;
  both reported.
- Government has no CES average-hourly-earnings series, so the industry with
  one of the largest phantoms cannot enter the wage regression.
- Mining & logging: JOLTS industry code not resolved (probed 200000/210000/
  110000/211000 — no such series); dropped. Small industry; the 9-industry sum
  covers ~99.6% of total-private openings (slightly under 100% because BLS
  seasonally adjusts each industry series independently — components need
  not sum exactly to the adjusted total).
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
