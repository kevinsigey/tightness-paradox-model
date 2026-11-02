# What predicts a state's labor-market friction?

*State characteristics assembled from the publishers' own distribution
channels (BEA, BLS, Census Bureau, U.S. DOL via FRED), modeled against
Kevin's Tightness Paradox targets. n = 51 (50 states + DC). Everything here
is associational. Script: `state_characteristics.py` (seed 20261101);
dataset: `state_characteristics.csv`; full model output:
`modeling_results.csv`. No paper edits.*

## Verdict

**Kevin's question 1 — what predicts how much friction a state HAS?**
A coherent profile, and it is the prosperous-white-collar one, not the
struggling one. States where a larger share of openings go unfilled are
states with **slower recent real GDP growth** (the single most robust
predictor: r = −0.63 for unfilled share, −0.58 for the friction proxy,
stable under rank correlation and with DC removed), **more college-educated
workforces** (bachelor's+ share, r ≈ +0.5), **larger professional &
business services sectors** (GDP share r ≈ +0.55), **larger
education & health employment shares** (r = +0.34 Pearson, +0.53 with DC
removed), **smaller leisure & hospitality employment shares** (r = −0.39),
**slower population growth** (r = −0.39), **higher work-from-home shares**
(r = +0.40), and **higher statutory minimum wages** (r = +0.38). Penalized
models predict friction levels well out of sample (leave-one-out CV
R² = 0.91 for the friction proxy, 0.93 for unfilled share) — but read the
next paragraph before quoting those numbers.

Two honesty discounts on the level results. (a) *Mechanics:* the JOLTS
openings and hires rates are close relatives of how the friction measures
are built, and they do much of the work in the headline CV R². Strip them
out and characteristics alone still predict, but modestly: CV R² = 0.20
(friction proxy) and 0.51 (unfilled share). (b) *DC leverage:* for the
friction-proxy target, several big Pearson correlations are inflated by
the District of Columbia (density 11,489/sq mi vs ~1,300 for the next
state; GDP per capita $278k on a commuter economy). Population density
(r = 0.69 → 0.20 without DC), GDP per capita (0.65 → 0.15), and the Gini
index (0.35 → 0.07) do not survive that check and should not be cited as
level predictors. The unfilled-share results, by contrast, are stable
across Pearson, Spearman, and no-DC cuts almost line by line. Slow GDP
growth, education, and professional-services share survive every cut for
both targets.

**Kevin's question 2 — what predicts WHERE friction is associated with
wage pressure (the betas)? Nothing in this characteristic set, for either
window.** For the full-sample (2015–2025) betas, five characteristics have
raw p < 0.05 — professional & business services GDP share (r = +0.36),
5-yr GDP growth (−0.31), QCEW average pay (+0.29), professional-services
employment share (+0.29), bachelor's+ share (+0.29) — and **all five die
under Benjamini-Hochberg correction** (best q = 0.20). The elastic net
keeps two of them yet scores CV R² = −0.19, worse than predicting the
mean: it does not generalize. The recent-window (2022–2025) betas are the
same story: three raw candidates (median household income +0.34, GDP
growth −0.33, QCEW pay +0.31), none survives FDR (best q = 0.21), the
penalized model selects nothing, CV R² = −0.11. Note the direction of the
dead candidates is at least coherent — richer, more professional-services
states show the less-negative/more-positive betas, rhyming with the
pre-registered friction-tercile result (which grouped on friction itself,
not on characteristics) — but at n = 51 with 25 candidates, that pattern
is a suggestion for a bigger design, not a finding. A structural reason
to expect weak results: the betas themselves are noisy (median SE 0.29
full-sample, 0.40 recent-window), which attenuates any cross-state
relationship toward zero.

**Bottom line.** State characteristics explain where friction *lives*
quite well — it lives in slow-growing, educated, professional-services,
care-sector labor markets — and explain essentially nothing about where
friction *bites into wages*. The beta heterogeneity documented earlier
(real dispersion, mostly negative full-sample, positive high-friction
tercile post-2022) is not accounted for by GDP, income distribution,
education, industry mix, housing costs, or any other characteristic
assembled here.

## Sources — where every variable is published

All values are for all 50 states + DC. "Route" is the publisher's own
distribution channel actually used.

| Variable | Publisher | Series / table | Reference period | Route | Flags |
|---|---|---|---|---|---|
| friction_level, unfilled_share (targets) | Kevin's panel (BLS state JOLTS inputs) | mean Friction_Proxy, mean Unfilled_Share, `master_labor_panel_v2.csv` | Apr 2015 – Dec 2025 | local file | target, not recomputed |
| beta_full, beta_recent (targets) | Kevin's estimates | per-state Friction_Lag3 betas, `state_groups_estimates.csv` | 2015–2025; 2022–2025 | local file | target |
| jolts_openings_rate, jolts_hires_rate | U.S. Bureau of Labor Statistics (JOLTS, state estimates) | mean Openings/Labor Force, mean Hires/Labor Force | Apr 2015 – Dec 2025 | derived from Kevin's panel | **Flag:** panel-derived, not re-pulled — www.bls.gov returns HTTP 403 from this network |
| laus_unemp_rate | U.S. Bureau of Labor Statistics (LAUS) | state unemployment rate, SA, series `{ST}UR` on FRED | 2024 annual average (latest year with 12 published months at pull time) | FRED fredgraph CSV | — |
| rgdp_per_capita | U.S. Bureau of Economic Analysis | real GDP by state, `{ST}NGSP` (millions of chained 2017 $) ÷ Census population `{ST}POP` | 2025 | FRED fredgraph CSV | DC value ($278k) reflects commuter production over resident population |
| rgdp_growth_5yr_pct | BEA | same series, 2025 vs 2020 | 2020 → 2025 | FRED fredgraph CSV | — |
| pop_growth_5yr_pct | U.S. Census Bureau (Population Estimates Program) | resident population, `{ST}POP` on FRED | 2020 → 2025 | FRED fredgraph CSV | — |
| bea_gdpshare_manuf / _profbus / _edhealth / _leishosp | BEA | SAGDP2, GDP by state by NAICS industry, current dollars; profbus = prof/sci/tech + management of companies + admin/waste; edhealth = educational services + health care & social assistance; leishosp = arts/entertainment/recreation + accommodation & food services | 2025 | BEA bulk download (SAGDP.zip) | shares of all-industry total |
| qcew_avg_annual_pay | BLS (QCEW) | average annual pay, total covered, all industries | 2025 annual | BLS QCEW open-data API, area files | — |
| qcew_empshare_manuf / _profbus / _edhealth / _leishosp | BLS (QCEW) | annual average employment, supersectors 1013 / 1024 / 1025 / 1026 (summed over ownerships), ÷ total covered employment | 2025 annual | BLS QCEW open-data API, industry files | — |
| median_hh_income | Census Bureau (ACS 1-year) | B19013, median household income | 2024 | ACS table-based summary files (www2.census.gov) | see API note below |
| gini_index | Census Bureau (ACS 1-year) | B19083, Gini index of income inequality | 2024 | ACS summary files | — |
| poverty_rate | Census Bureau (ACS 1-year) | B17001, below-poverty ÷ total | 2024 | ACS summary files | — |
| bachelors_plus_share | Census Bureau (ACS 1-year) | B15003, (bachelor's + master's + professional + doctorate) ÷ population 25+ | 2024 | ACS summary files | 2024 table (25 vars) used deliberately: the 2025 ACS redesigned B15003 to 23 variables |
| median_age | Census Bureau (ACS 1-year) | B01002, median age | 2024 | ACS summary files | — |
| median_gross_rent | Census Bureau (ACS 1-year) | B25064 | 2024 | ACS summary files | — |
| median_home_value | Census Bureau (ACS 1-year) | B25077 | 2024 | ACS summary files | — |
| wfh_share | Census Bureau (ACS 1-year) | B08301, worked from home ÷ total workers | 2024 | ACS summary files | — |
| acs_population (for density) | Census Bureau (ACS 1-year) | B01003, total population | 2024 | ACS summary files | — |
| pop_density | Census Bureau | ACS B01003 population ÷ 2024 Gazetteer state land area (ALAND_SQMI) | 2024 | Census Gazetteer file (www2.census.gov) | **Substitution flag:** stands in for urban population share; the Census API route to urban/rural tabulations requires an API key (see below), so density is the published urbanization proxy used |
| min_wage | U.S. Department of Labor, Wage and Hour Division | statutory state minimum wage, FRED series `STTMINWG{ST}` (source agency: DOL) | 2026 (latest published) | FRED fredgraph CSV | **Flag:** AL, LA, MS, SC, TN have no state minimum-wage statute and no FRED series; coded at the federal FLSA floor $7.25 with `min_wage_federal_floor = 1`. Split-rate states (e.g. NY) carry the series' headline value |

**Access notes (so the next pull is faster).** api.census.gov now returns
a "Missing Key" wall without an API key, so ACS was pulled from the
Census Bureau's own table-based summary files instead — same publisher,
same numbers. www.bls.gov and download.bls.gov return HTTP 403 from this
network, which is why (a) LAUS came via FRED's BLS-sourced series,
(b) QCEW came via the BLS open-data API host (data.bls.gov, which is
reachable), and (c) the two items below could not be obtained.
fredgraph quirks, all verified 2026-11-01: multi-series responses are
silently capped at 12 series (chunk to 10); requests carrying a browser
User-Agent stall (use curl's default UA); no-`cosd` batches are
pathologically slow.

**Not retrieved — flagged, not substituted.**
- *Union membership rate (BLS, CPS, "Union Members" news release,
  Table 5).* Publisher-direct access is blocked from this network
  (www.bls.gov, HTTP 403). The only copies found are third-party
  republications (e.g. a marketing agency's Zenodo deposit), which were
  deliberately not used: Kevin's rule is publisher or nothing. If a
  browser session with bls.gov access is available, Table 5 of the
  current USDL Union Members release fills this column in one step.
- *Urban population share.* Substituted by population density (above).
- *Right-to-work status.* Omitted: no publisher-direct machine-readable
  source was used, and the brief made it conditional on a citable
  publisher.

## Results

### Univariate — friction LEVEL (BH-FDR within target, 25 tests each)

Friction proxy (`friction_level`), FDR survivors (q < 0.05), with
robustness cuts. Pearson is the headline; Spearman and no-DC Pearson are
the audit.

| Feature | r | q | Spearman | r (no DC) |
|---|---|---|---|---|
| Population density | +0.69 | <0.001 | +0.24 | +0.20 |
| Real GDP per capita | +0.65 | <0.001 | +0.19 | +0.15 |
| Bachelor's+ share | +0.63 | <0.001 | +0.38 | +0.38 |
| Prof. & business services GDP share (BEA) | +0.60 | <0.001 | +0.37 | +0.39 |
| Real GDP growth, 5-yr | −0.58 | <0.001 | −0.58 | −0.56 |
| JOLTS openings rate (panel) | +0.57 | <0.001 | +0.22 | +0.12 |
| QCEW average annual pay | +0.55 | <0.001 | +0.26 | +0.26 |
| Prof. & business services emp. share (QCEW) | +0.49 | 0.001 | +0.22 | +0.26 |
| Work-from-home share | +0.45 | 0.003 | +0.27 | +0.23 |
| Gini index | +0.35 | 0.030 | +0.05 | +0.07 |
| Median household income | +0.34 | 0.036 | +0.16 | +0.18 |

Raw p < 0.05 but killed by FDR (3): BEA education & health GDP share,
QCEW leisure & hospitality employment share, median home value (see
`modeling_results.csv`).

Unfilled share (`unfilled_share`), FDR survivors (15; robustness cuts in
parentheses as Spearman / no-DC r): real GDP growth 5-yr −0.63 (−0.66 /
−0.60); bachelor's+ +0.56 (+0.48 / +0.50); prof. & business GDP share
+0.56 (+0.47 / +0.49); JOLTS hires rate −0.51 (−0.68 / −0.75,
near-mechanical); QCEW average pay +0.49 (+0.36 / +0.41); prof. & business
emp. share +0.45 (+0.30 / +0.37); work-from-home +0.40 (+0.33 / +0.31);
population growth 5-yr −0.39 (−0.40 / −0.42); leisure & hospitality emp.
share −0.39 (−0.52 / −0.41); minimum wage +0.38 (+0.40 / +0.33); median
household income +0.38 (+0.29 / +0.31); real GDP per capita +0.38 (+0.27 /
+0.25); education & health GDP share (BEA) +0.35 (+0.33 / +0.40);
population density +0.35 (+0.39 / +0.35); education & health emp. share
(QCEW) +0.34 (+0.46 / +0.53). No raw-significant feature was killed by FDR
for this target.

### Univariate — the BETAS (where friction bites wages)

| Target | FDR survivors | Raw p < 0.05, killed by FDR |
|---|---|---|
| beta_full (2015–2025) | **none** (best q = 0.20) | prof. & business GDP share +0.36 (p = .010); real GDP growth −0.31 (p = .025); QCEW pay +0.29 (p = .038); prof. & business emp. share +0.29 (p = .040); bachelor's+ +0.29 (p = .043) |
| beta_recent (2022–2025) | **none** (best q = 0.21) | median household income +0.34 (p = .016); real GDP growth −0.33 (p = .017); QCEW pay +0.31 (p = .025) |

### Penalized models (elastic net, LOOCV; mean-only baseline CV R² = −0.04)

| Target | CV R² (all features) | CV R² (no JOLTS rates) | Kept features (full-data fit) |
|---|---|---|---|
| friction_level | 0.91 | 0.20 | openings rate +, hires rate −, GDP growth −, prof. & business GDP share +, density +, bachelor's+ + |
| unfilled_share | 0.93 | 0.51 | openings +, hires −, GDP growth −, ed/health emp. share +, manufacturing GDP share −, prof. & business emp. share +, plus small terms |
| beta_full | **−0.19** | — | prof. & business GDP share +, GDP growth − (kept, but worse than the mean out of sample) |
| beta_recent | **−0.11** | — | none selected |

### Method and limits

Univariate Pearson correlations for all 25 characteristics × 4 targets,
Benjamini-Hochberg within each target family; Spearman and leave-DC-out
Pearson as robustness audits (full table in `modeling_results.csv`).
Penalized model: StandardScaler + ElasticNetCV (l1 ratio ∈ {0.2, 0.5,
0.8, 1.0}, 100-point alpha grid, inner 5-fold CV) inside an outer
leave-one-out CV; features median-imputed (the assembled dataset in fact
has **zero missing values** across all 25 characteristics × 51 states).
Limits: n = 51 with 25 candidate features is a screening design, not an
estimation design; characteristics are latest-vintage (2024–2026) while
the betas integrate 2015–2025 behavior, so the exercise reads
characteristics as persistent state "types," not as time-matched causes;
DC is a genuine observation but a leverage point, handled by audit
rather than deletion; and the two friction targets are built from the
same JOLTS inputs as two of the features, which is why the no-JOLTS
models are reported alongside the headline ones.
