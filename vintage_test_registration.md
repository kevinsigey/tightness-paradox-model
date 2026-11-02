<!-- Publication record (not part of the registered text below).
Page: https://kevinsigey.github.io/portfolio/tightness-vintage-test.html
Repo: kevinsigey/portfolio, file tightness-vintage-test.html
Commit: e4f0ab27a594fb9bd9db7030a2027d5a8217ff3a
Pushed: November 1, 2026 (America/Chicago)
Builder: build_vintage_test.py (single content source renders the page and this text).
The text below the line is identical to the published page. -->

---

# The Vintage Test

The confirmation test for the Tightness Paradox's headline finding, registered in public on November 1, 2026, before any of the data it will run on exist.

Kevin Sigey · Registered November 1, 2026 · Companion registration to The Tightness Paradox

## 1 · What is being tested

The Tightness Paradox reports one located effect. Split into terciles of pre-COVID hiring friction, states behaved differently after COVID: on January 2022 to December 2025, the coefficient on lagged friction was -0.188 in the low-friction tercile, -0.210 in the mid tercile, and +0.650 in the high tercile, and a single pre-registered Wald test rejected the equality of the three at p = 0.0099.

That test was registered and run on the same window whose exploratory split suggested the hypothesis. Registration froze the groups, the window, the specification, and the test, so the result is not the product of trying cuts until one worked. What it cannot do is make the window new. The paper's status for the finding is therefore: tested, not settled.

This page is the settling test, registered before the fact. It freezes the identical design (sections 2 and 3), the data rules it will run under (section 4), and the downgrade rule that fires if it fails (section 5), and it timestamps all of it today, November 1, 2026, while the forward window, January 2026 onward, has produced no usable state data at all.

## 2 · The frozen groups

Each state's tercile is fixed by its mean Friction_Proxy over April 2015 to December 2019 only: the unfilled share of openings, one minus hires over openings, from monthly state JOLTS flows. Seventeen states per tercile. Membership was set on November 1, 2026 (prereg_group_assignments.csv) and never re-forms: if BLS revises the 2015 to 2019 history, no state moves.

Low friction: LA -0.0002 · TX -0.0002 · TN 0.0002 · MS 0.0005 · UT 0.0007 · WY 0.0010 · OK 0.0013 · AR 0.0013 · DE 0.0017 · MT 0.0017 · IN 0.0020 · AL 0.0023 · GA 0.0028 · SC 0.0029 · ID 0.0029 · KY 0.0030 · NV 0.0037
Mid friction: AK 0.0039 · AZ 0.0040 · NH 0.0042 · WV 0.0044 · CO 0.0047 · HI 0.0051 · NC 0.0051 · IL 0.0051 · OR 0.0052 · FL 0.0054 · CT 0.0055 · VT 0.0055 · RI 0.0057 · MO 0.0061 · CA 0.0064 · ME 0.0065 · ND 0.0066
High friction: SD 0.0067 · NY 0.0070 · IA 0.0072 · OH 0.0074 · WA 0.0075 · PA 0.0076 · NE 0.0076 · NJ 0.0077 · MI 0.0078 · KS 0.0078 · NM 0.0087 · MD 0.0090 · WI 0.0092 · VA 0.0112 · MA 0.0118 · MN 0.0133 · DC 0.0177

Frozen mean unfilled share, April 2015 to December 2019, beside each state, ascending within tercile. Full precision values are in prereg_group_assignments.csv, preserved with this registration.

## 3 · The frozen specification

The Phase 1 preferred specification, unchanged, as frozen in prereg_followup.py on November 1, 2026:

- Outcome: ln_Real_Wage, the log of real average weekly earnings, built as in the Phase 1 panel (state CES average weekly earnings deflated by CPI-U).
- Regressor: Friction_Lag3, the unfilled share lagged three months, interacted with the three frozen tercile dummies.
- Controls, unchanged: Friction_x_Education (unlagged), Unemployment_Rate, ln_Min_Wage, LH_Share.
- Estimator: two-way fixed effects (state and month), standard errors two-way clustered by state and month.
- The test: exactly one confirmatory test, the joint Wald test of beta_low = beta_mid = beta_high (chi-square, 2 degrees of freedom), two-sided, alpha = 0.05. Its p-value is the verdict. The three group coefficients are reported descriptively; every other computation is exploratory and labeled as such.

First run sample: January 2026 to December 2026, 51 states by 12 months, 612 observations before missing-month adjustments under the rules in section 4.

## 4 · The data rules

The test track. State JOLTS is an annual release now. Each July, BLS publishes the annual State Job Openings and Labor Turnover release, including monthly state estimates for the prior calendar year, with benchmark revisions folded in. The test runs on those vintages exactly as published; there is no choosing among vintages and no hand adjustment. The first annual edition (July 22, 2026) carried calendar 2025, which is inside the original window and changes nothing here. The first vintage containing forward data is the July 2027 annual release, carrying monthly state estimates for January to December 2026. That release is the first run.

The window. The first run covers January 2026 to December 2026. Each later annual vintage extends the forward window by a year, and the same single test is rerun on the cumulative forward window. Runs are logged in order, whichever way they land.

Construction. Forward months are built from the same sources and constructions as the Phase 1 panel: state JOLTS openings and hires from the annual release; CES earnings and LAUS unemployment through the BLS API; CPI-U from FRED; education, minimum wage, and the leisure and hospitality share as in the panel build.

Missing months. A month that cannot be constructed for the whole panel drops out for every state, and the drop is recorded. (October 2025 dropped out of the original panel this way, when no CPI published during the federal shutdown.) No state is patched individually, and no state is substituted or dropped on its own; if a state is ever missing from a vintage, that is reported as it stands.

The interim track, and its limits. BLS does not publish Census division JOLTS; the finest JOLTS geography that still publishes monthly is the four Census regions. Region unfilled shares will be logged as they arrive, read against each region's frozen composition (Northeast: 4 high, 5 mid, no low; Midwest: 8 high, 3 mid, 1 low; South: 3 high, 3 mid, 11 low; West: 2 high, 6 mid, 5 low). This track is directional context only. Regions mix terciles, the design has no region-level wage outcome, and a handful of region-months cannot carry a coefficient, so the interim track cannot re-run the test, cannot confirm the finding, and cannot falsify it. No interim reading will be described as evidence either way.

Reporting. Results are appended to The Tightness Paradox and to the run log preserved with this registration, whichever way they land. Section 5 says what each outcome does to the paper.

## 5 · The falsification line

> If the high-tercile coefficient on the forward window is zero or negative, or the equality test does not reject at conventional levels, the when-and-where finding is downgraded in the paper to a 2022-2025 episode, in those words.

The symmetric rule: if the high-tercile coefficient on the forward window is positive and the equality test rejects at alpha = 0.05, the finding is promoted, and the paper's status line changes from tested, not settled, to confirmed on data the hypothesis had never seen. Any other configuration, a positive high coefficient without rejection, or a rejection carried by the low and mid terciles, is inconclusive: the finding stays tested, not settled, and the log says so.

## 6 · Status at registration

No forward state data exist yet. The state panel ends with December 2025, where the monthly state release ended, and the first forward vintage is the July 2027 annual release (section 4).

What exists today is the level of the regressor, nationally, and it cannot speak to the finding. The national unfilled share (one minus hires over openings, seasonally adjusted JOLTS) averaged 0.337 a month across January 2022 to December 2025, 0.259 in 2025, and 0.274 across January to August 2026, the latest month published (August 2026: 7,079 thousand openings, 5,192 thousand hires). The finding is a claim about how a slope differs across state terciles, not about the national level of friction, so these numbers are recorded only as the state of the world on the day this registration was filed. They are not an interim result.

The calendar from here: national and region JOLTS continue monthly (September 2026 national JOLTS is scheduled for November 3, 2026); the first Vintage Test run follows the July 2027 annual State JOLTS release; this page and the paper are updated when it lands.

**Sources and method.** Design frozen in prereg_followup.py (registered November 1, 2026, before estimation) and reported in prereg_results.md; group assignments in prereg_group_assignments.csv; the companion paper is The Tightness Paradox. National JOLTS figures from the BLS API (series JTS000000000000000JOL and JTS000000000000000HIL), retrieved November 1, 2026. State JOLTS schedule per BLS notices on the move to an annual release (first annual edition July 22, 2026; monthly estimates for the prior calendar year published with each annual release).

Kevin Sigey · MS in Business Analytics, University of Illinois Urbana-Champaign · sigeykevin@gmail.com
