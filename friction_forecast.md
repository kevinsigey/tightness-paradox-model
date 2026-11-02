# Can Friction Forecast Unemployment and Jobs?

*Run 2026-11-01. Script: `friction_forecast_run.py` (this folder); all estimates:
`friction_forecast_results.csv` (36 rows, every horizon and variant reported).
Panel: `master_labor_panel_v2.csv`, 51 states, Apr 2015–Dec 2025.*

## Verdict first

**Friction does not forecast unemployment, and its apparent ability to
forecast hiring is an arithmetic artifact. As an NFP nowcast feature its
prior is low, and the hub already fields a close cousin of it.**

- **Unemployment: no.** State level, two-way fixed effects, clustered SEs,
  controlling for the current unemployment rate: the friction coefficient is
  insignificant at every horizon (1, 3, 6 months), for both friction variants
  (all p between 0.29 and 0.99), with partial R-squared of 0.0000 to 0.0003.
  Friction adds nothing over an unemployment-only autoregression in sample.
  Out of sample it trims RMSE by about 1 percent (ratios 0.986 to 0.994),
  consistently but trivially; the Diebold-Mariano p-values look strong only
  because 4,600+ pooled state-months overstate independence under common
  shocks. A 1 percent RMSE trim on state unemployment changes is not a
  signal anyone should trade or publish on.
- **Hires: the lead is mechanical, not information.** Friction positively
  "predicts" hires growth at 3 and 6 months (partial R-squared 1.3 to 2.8
  percent, p < 0.001) and negatively at 1 month. But friction is built from
  hires: Friction_Proxy = (Openings − Hires) × 1000 / Labor_Force. A month
  with a transitorily low hires print has a wide gap by construction, and
  hires then rebound off the low base. The decomposition proves it: entered
  separately, the hires rate carries the entire effect (coefficient −3.97
  at 3 months, p < 0.001, i.e. low hires today predict hires growth
  tomorrow), while the openings rate is null at 1 and 6 months and weakly
  positive at 3 (+0.65, p = 0.017, the one non-mechanical crumb: postings
  do convert with a lag). Smoothing hires inside the gap does not remove
  the artifact, because the target's base is the same smoothed hires.
- **One genuine, small jobs signal survives:** friction negatively predicts
  leisure-and-hospitality employment growth at 1 and 3 months (both
  variants, p ≤ 0.017; gone by 6 months). That target comes from CES, a
  different survey than the JOLTS flows inside friction, so there is no
  arithmetic overlap. Size: roughly −0.07 percent of employment growth per
  one-standard-deviation rise in friction. Real, sector-specific, tiny.
- **The story the data supports:** neither of the pre-committed stories at
  any usable horizon. Not Story S (friction today does not become slack
  tomorrow: unemployment coefficients are null, not positive) and not
  Story T at state level (the negative unemployment coefficients never
  clear noise). Friction is a coincident description of a market that is
  failing to convert, not a leading indicator of where unemployment or
  payrolls go next. That is fully consistent with the paper's own arc:
  friction's information content showed up in *wages*, conditionally and
  late, not in quantities.

## The tests

Pre-committed interpretation, written into the script header before
estimation: Story S (slack) says friction up predicts unemployment up and
job growth down at later horizons; Story T (tightness) says the reverse.
All horizons (1, 3, 6) and both variants (Friction_Proxy; Unfilled_Share =
1 − Hires/Openings) are reported for every outcome. Nothing was dropped.

State unemployment change (percentage points), TWFE, clustered by state,
controlling for current unemployment:

| horizon | Friction_Proxy beta (p) | Unfilled share beta (p) | partial R2 |
|---|---|---|---|
| 1 mo | −1.21 (0.29) | −0.072 (0.41) | 0.0002–0.0003 |
| 3 mo | −0.57 (0.77) | +0.007 (0.95) | ≈ 0.0000 |
| 6 mo | −0.04 (0.99) | +0.065 (0.71) | 0.0000–0.0001 |

A one-standard-deviation friction move implies about a 0.01-point change
in unemployment at one month. Nothing.

Hires growth (log, 3-month moving-average base) tells the artifact story:
friction coefficients −0.43 (p = 0.002) at 1 month, +1.68 and +2.27
(p < 0.001) at 3 and 6 months for Friction_Proxy, mirrored by the
unfilled share. Sign flips of exactly this shape (negative immediate,
positive later) are what a low-base rebound looks like, and the
openings/hires decomposition in the analysis above settles it.

LH employment growth (log, CES leisure & hospitality, the only employment
series in the state panel; a narrow, cyclically sensitive sector, not
total state employment): Friction_Proxy −0.058 (p = 0.005) at 1 month,
−0.078 (p = 0.017) at 3, −0.068 (p = 0.22) at 6. Small, short-lived,
Story S in sign, one sector only.

Pseudo-out-of-sample (expanding window, pooled OLS with state dummies,
no month FE in the OOS variant): friction trims unemployment RMSE by
0.6 to 1.4 percent at all horizons for both variants. Directionally
consistent, practically negligible, and not independent evidence given
the in-sample nulls.

## National read (descriptive, N ≈ 122–127, low power)

Labor-force-weighted national friction against national unemployment
changes, controlling for the current rate: coefficients are negative and
grow with horizon (unfilled share: −0.86 at 1 month, p = 0.14; −2.28 at
3, p = 0.08; −3.67 at 6, p = 0.04; Friction_Proxy mirrors). Read
cautiously: with one national cycle in the sample, a marginal p = 0.04
in one of twelve national cells, and the 2022–2025 pattern (friction
falling from its peak while unemployment drifted up) doing the work,
this is the business cycle describing itself, not a forecasting
relationship. National hires growth: nothing at any horizon.

Data reality, stated once: monthly state JOLTS ends with December 2025
and goes annual, so state-level friction features die as a live feed.
National JOLTS continues monthly, so a *national* friction feature stays
fed indefinitely. (The panel aggregate also shows the October 2025
federal-shutdown gap in state reporting.) National friction through
2025 sat at an unfilled share of roughly 0.26 to 0.27, with December
2025 dipping to 0.195.

## Feeding the jobs predictor: the concrete assessment

The hub's `labor_nowcast` engine (`tradehub/engines/labor.py`, labor-v1)
is a ridge nowcast of the first-print payroll change for Kalshi
KXPAYROLLS strikes, trained on ALFRED first-release vintages with
publication lags enforced. Two facts frame everything:

1. **The hub already has this idea in the building.** Its candidate
   feature set (`ALL_FEATURES`) includes `jolts_hires_3m` and
   `ghost_gap_3m`, where ghost_gap is the national openings-minus-hires
   gap (with openings heuristically discounted by half after 2021, the
   `GHOST_DISCOUNT`), read from JOLTS vintages with a 40-day lag rule.
   The shipped model (`CORE_FEATURES`) uses only payroll momentum and
   claims; the JOLTS features exist but are not in the core. Kevin's
   unfilled share correlates 0.956 with the national openings-minus-hires
   gap, so most of what it carries, the ghost gap already carries.
2. **What friction would add is the functional form, not new data.** The
   unfilled share is a conversion *rate*: scale-free, bounded, and it
   replaces the hub's ad-hoc 0.5 ghost discount with "the share of
   openings that failed to convert," which is the quantity the Tightness
   work actually measured. The candidate features would be the national
   unfilled share level and its 3-month change, built from the JTSJOL /
   JTSHIL vintages the hub already fetches.

**Cadence and staleness, honestly priced:** JOLTS lags hard. Under the
hub's own 40-day rule, when nowcasting reference month M's payroll print
(the print that lands in early M+1), the freshest usable JOLTS month is
M−2. Payrolls for M are largely determined by M's own hiring, which the
friction read cannot see; friction enters as a two-month-old regime
variable, not a nowcast of the month itself. Regime variables can still
help a ridge (they condition the mapping from claims and payroll momentum
to the print), but expectations should be set accordingly, and these
tests say friction's regime information showed up in wages, not in
quantities: the prior for an NFP gain is low.

**The backtest to run before trusting it (one paragraph):** use the
hub's own harness (`scripts/backtest_labor.py`) and its ALFRED vintage
discipline, no revised data anywhere; fit the shipped core, the core
plus `ghost_gap_3m`, and the core plus unfilled-share level and 3-month
change, on identical training windows with the COVID exclusion the
engine already applies (Mar 2020–Jun 2021), and score first-print strike
probabilities out of sample over the post-2022 window (where ADP
vintages exist from Sep 2022 and the ghost discount regime applies) on
Brier and log score against both the market and the core-only model.
**Falsification line:** if the friction-augmented model does not beat
the core-only model out of sample on that pre-set window, the feature
stays out, and the window is not renegotiated after the fact. Given the
labor scoreboard's standing (ours 0.182 vs market 0.169 on the Sep 2026
rerun, i.e. the market is currently ahead), a feature that cannot beat
the in-house core has no path to beating the market.

## Bottom line for the paper and the hub

Friction is a measurement of a market failing to convert, and a
conditional wage signal in the hardest-to-hire states after COVID. It is
not a forecasting input for unemployment or payrolls: the unemployment
tests are clean nulls, and the one strong lead (hiring) dissolves under
decomposition into the mean reversion of its own denominator. If the
feature is ever tested in the hub, it should be as the ratio-form
replacement for the ghost gap's ad-hoc discount, through the backtest
above, with the falsification line agreed before the run.
