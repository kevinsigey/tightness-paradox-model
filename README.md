# The Tightness Paradox — model, data, and code

Companion repository to **The Tightness Paradox**, a research paper by
Kevin Sigey: https://kevinsigey.github.io/portfolio/tightness-paradox.html

## The finding

For a decade, hiring friction — job openings that sit open and do not
convert into hires, measured as the unfilled share of openings
(one minus hires over openings) in state JOLTS — did not push wages
anywhere. After COVID, in the hardest-to-hire states, it started to.

The pre-registered confirmatory test froze state terciles on 2015–2019
friction means and ran one joint Wald test on January 2022–December
2025: equality of the three tercile coefficients is rejected
(p = 0.0099), with the high-friction tercile at +0.650 (p = 0.004) and
the low and mid terciles at −0.188 and −0.210.

**Status: tested, not settled.** The test was registered and run on the
same window whose exploratory split suggested the hypothesis.
Registration froze the groups, the window, the specification, and the
single test, so the result is not the product of trying cuts until one
worked — but it cannot make the window new. Confirmation needs data
that did not exist when the finding was made; the forward design for
that is registered in `vintage_test_registration.md` (the first true
run is the July 2027 annual State JOLTS vintage). The paper says all of
this on its face, and this repository is the raw evidence behind it.

## How the repo maps to the paper

| Paper | Files |
|---|---|
| §1–§3 The claim and the collapse (sixfold panel rebuild; the pooled coefficient falls from 6.17 to 0.058) | `modeling_results.csv` |
| §4–§5 The search through states (state heterogeneity) | `state_groups_run.py`, `state-groups.md`, `state_groups_estimates.csv`, `state_group_assignments.csv`, `state_groups_summary.json`, `per_state_full.csv`, `per_state_recent.csv`, `grouped_coefficients.png`, `state_forest.png` |
| §6 The pre-registered test | `prereg_followup.py` (design stated in its header, written before estimation), `prereg_results.md`, `prereg_estimates.csv`, `prereg_group_assignments.csv` |
| §7 The search: state types (what predicts a state's friction level; nothing predicts where it bites) | `state_characteristics.py`, `state_characteristics.md`, `state_characteristics.csv`, `pull_meta.json` |
| §9 Are the postings real? (genuine-or-phantom first pass) | `genuine_or_phantom_run.py`, `genuine_or_phantom_supp.py`, `genuine_or_phantom_draft.md`, `genuine_or_phantom_results.csv`, `genuine_or_phantom_states.csv`, `genuine_or_phantom_supp.csv`, `genuine_or_phantom_perstate_pipe.csv` |

Follow-up work kept with the study, not in the paper:

- `friction_forecast_run.py`, `friction_forecast.md`,
  `friction_forecast_results.csv` — does friction forecast unemployment
  or hiring? It does not, at any horizon tested; the one apparent hires
  signal was mechanical (the measure watching its own denominator
  recover).
- `whose_wages_run.py`, `whose_wages_draft.md`,
  `whose_wages_firstpass.md`, `whose_wages_*.csv` — an arbitration
  design against the Autor–Dube–McGrew job-ladder account. Parked as an
  inconclusive draft: its first pass kills only the narrow
  sector-composition story.
- `vintage_test_registration.md`, `vintage_test_forward_check.md` —
  the frozen forward-confirmation design, registered publicly on
  November 1, 2026 before any forward data exist, and the dated record
  of the first forward check (no discriminating data exists yet; first
  true run July 2027).

## Data

All inputs are public: Bureau of Labor Statistics JOLTS (state and
industry), LAUS, and CES via the BLS API; CPI-U (FRED CPIAUCSL); Census
ACS educational attainment; state minimum wages from the
U.S. DOL-cited table; BEA, Census Bureau, and QCEW series for the state
characteristics run. Rebuild panel: 50 states + DC, April 2015 to
December 2025, N = 6,528. Industry panel: 10 industries, April 2015 to
July 2026, N = 1,350. Data vintage September 28, 2026; estimation
seed 20260928.

The run scripts read the analysis panel
(`master_labor_panel_v2.csv`, built from the BLS pulls above) from a
local path; the panel itself is rebuilt from the public sources listed
here, and every published estimate is in the CSVs in this repository.

## Credit

Kevin Sigey · MS in Business Analytics, University of Illinois
Urbana-Champaign. The original result this rebuilds was his ACCY 512
final project (May 2026).
