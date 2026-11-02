# Pre-Registered Follow-Up — Results

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
| Low friction | -0.188 | 0.235 | 0.424 |
| Mid friction | -0.210 | 0.173 | 0.226 |
| High friction | +0.650 | 0.224 | 0.004 |

**Joint equality Wald: chi2(2) = 9.22, p = 0.0099. The test
REJECTS equality.**

The frozen-group test rejects: with terciles fixed on 2015-2019 data alone, the recent-window friction coefficient differs across friction terciles. The recent-window thread survives its pre-registered retest on the same window it was found in. That promotes it from 'suggestive' to 'survived the confirmatory test as designed'; it is still one window of one panel, estimated on the same data that suggested it, so the honest next step is the one the exploration memo named: retest again as post-2025 JOLTS vintages land, on data this test has not seen.

Context for the comparison: the exploration's version of this test,
with groups defined on full-period means (so the recent window helped
define its own groups), gave high +0.589, low −0.283, equality
p = 0.034. Freezing the groups on pre-2020 data moved
12 of 51 states to a different tercile
(FL, GA, HI, IA, KY, ME, MO, NJ, SC, SD, WA, WV).

## Exploratory appendix (not confirmatory; do not cite as the verdict)

- **E1, pipeline check.** Re-running the exploration's exact grouping
  (full-period means) on the recent window inside this script
  reproduces it: chi2(2) = 6.78, p = 0.0338 (exploration:
  6.78, 0.0338). The machinery matches; only the group definition
  changed.
- **E2, pairwise differences** inside the confirmatory model are in
  `prereg_estimates.csv` (analysis
  `EXPLORATORY_E2_confirmatory_pairwise`). They are descriptive
  decompositions of the single test above, not separate tests.
- **E3, frozen groups on the full sample.** Same frozen terciles,
  Apr 2015–Dec 2025: equality chi2(2) = 1.97, p = 0.3733.
  Context only; the full-sample grouped null was already established
  in the exploration.

## Caveats carried over, unchanged

Two-way fixed effects cannot rule out reverse causality. State JOLTS
is subject to BLS revision, so the panel's last months are revisable.
Oct 2025 is missing panel-wide (no CPI published during the federal
shutdown), which is why the window has 47 months per state, not 48.
