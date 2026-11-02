# The Vintage Test — Forward Check 1

*Run November 1, 2026, alongside the registration (vintage_test_registration.md).
This is the interim track doing its first pass. It is not a test run, and
nothing in it moves the finding's status, which remains: tested, not settled.*

## What was pulled

- National JOLTS, seasonally adjusted, via the BLS API (series
  JTS000000000000000JOL and JTS000000000000000HIL), retrieved November 1,
  2026. Latest month published: **August 2026** (openings 7,079 thousand,
  preliminary; hires 5,192 thousand). September 2026 national JOLTS is
  scheduled for release November 3, 2026.
- FRED's JOLTS listings (retrieved November 1, 2026) confirm the four Census
  region job-openings and hires series are current through August 2026.
- BLS notices on the state JOLTS schedule (bls.gov, retrieved November 1,
  2026).

## The geography correction (material to the design)

**BLS does not publish Census division JOLTS, and never has in this program.**
The JOLTS geography ladder is: nation, four Census regions, states. FRED's
JOLTS category tree carries exactly two geography types (Nation, Census
Region), and the BLS JOLTS selection tool offers states or regions only.
Consequences:

- The "division-level version of the same test" named in section 10 of The
  Tightness Paradox and in landscape.md (follow-up paper 1) cannot be run as
  written. The registration corrects the interim track to Census **regions**.
- Even at region level, no version of the test is possible: regions mix
  frozen terciles (Northeast 4 high / 5 mid / 0 low; Midwest 8 / 3 / 1;
  South 3 / 3 / 11; West 2 / 6 / 5), and the design has no region-level wage
  outcome. The interim track is a friction-level log, nothing more.
- The paper's section 10 still says "division." The only edit made to the
  paper in this pass is the one registration link line Kevin authorized;
  the wording correction is flagged to Kevin separately.

## The one computable interim number (national, not the test)

Unfilled share, national, 1 minus hires over openings, SA:

| Window | Mean monthly unfilled share |
|---|---|
| Jan 2022 to Dec 2025 (the test window) | 0.337 |
| Calendar 2025 | 0.259 |
| Jan 2026 to Aug 2026 (forward window so far) | 0.274 |

Monthly 2026 values: Jan 0.262, Feb 0.292, Mar 0.196, Apr 0.313, May 0.303,
Jun 0.258, Jul 0.298, Aug 0.267.

**What this can say:** the regressor's national level in the forward window
is running close to its 2025 level, below its 2022 to 2025 average. That is
the state of the world the forward test will inherit.

**What it cannot say:** anything about the finding. The finding is a claim
that the friction-to-wage slope differs across state terciles (high +0.650
against low -0.188 and mid -0.210, equality rejected at p = 0.0099 on
2022 to 2025). A national mean of the regressor contains no slope, no
terciles, and no wages. It is consistent with the finding being true, false,
or irrelevant, and this log records it only so the registration day has a
dated snapshot attached.

State-level forward inputs are also still absent on the outcome side: QCEW
2026 wages exist in part (Q1 2026 published), but with no state friction
series to pair them with, they cannot enter any version of the design.

## The calendar

- Nov 3, 2026: September 2026 national JOLTS (region series update with it).
- Monthly: national and region JOLTS continue; logged on the interim track.
- **July 2027: the first true test.** BLS's annual State JOLTS release
  publishes monthly state estimates for the prior calendar year; the July
  2027 edition carries January to December 2026, which is the registered
  forward window. (The first annual edition was released July 22, 2026,
  covering calendar 2025.) BLS had not published the exact July 2027 date
  in its release schedules as of November 1, 2026; the registration reads
  the date off the BLS calendar when it posts.
- Each July after: the window extends by a year; the same single test
  reruns on the cumulative forward window; results append to the paper
  either way, per the falsification line.

## Proposed (not created)

A single dated check in the first week of August 2027: pull the July 2027
annual State JOLTS vintage, rebuild the forward panel, run the frozen test
once, and append the result to the paper. Proposed here per instructions;
no recurring job was created by this pass.
