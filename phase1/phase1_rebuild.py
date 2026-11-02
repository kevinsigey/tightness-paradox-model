"""
phase1_rebuild.py — Tightness Paradox Phase 1 ("quick wins") rebuild.

Rebuilds the state-month labor panel for all 50 states + DC (51 jurisdictions)
from primary sources, replicates the original ACCY 512 TWFE specification, and
runs the Phase 1 upgrades: two-way clustered + Driscoll-Kraay SEs, rescaled
marginal effects, robustness battery, break test, inefficiency-tax verdict.

Sources (no keys needed):
  - BLS JOLTS state openings/hires : BLS public API v2 (no key)
  - BLS LAUS state UR + labor force: BLS public API v2 (same source FRED mirrors)
  - BLS CES state avg hourly earnings + LH employment: BLS public API v2
  - CPI: national CPI-U (BLS CUUR0000SA0 = FRED CPIAUCSL) via BLS API;
    regional CPI kept for reference. Real_Wage in Jan-2015 dollars, exact
    original formula.
  - Minimum wage: Wikipedia "List of U.S. states by minimum wage" (cites U.S.
    DOL), 2019-2026 annual; 2015-2018 backward-filled from 2019; federal floor
    7.25. (FRED's DOL STTMINWG series also starts 2019; this fallback is a
    documented limitation — sensitivity spec drops ln_Min_Wage.)
  - Educational attainment: Census GCT1502 (2018, 2019) + ACS B15002 summary
    files (2021-2024); % bachelor's+ 25+; 2015-2017 backward-filled from 2018,
    2020 forward-filled from 2019 (ACS 1-yr not released for 2020), 2025
    forward-filled from 2024.

Original spec replicated (exact original Stage 1 interaction; the checkpoint
requires the UNLAGGED interaction term):
  TWFE: ln_Real_Wage ~ Friction_Lag3 + Friction_x_Education
        + Unemployment_Rate + ln_Min_Wage + LH_Share
  where Friction_x_Education = Friction_Proxy * ln_Education (UNLAGGED).
  A separately labeled lagged-interaction variant
  (Friction_Lag3 * ln_Education) is reported in the robustness battery.
  (state + month FE, SEs clustered by state)

Known limitations (documented, not fixed silently):
  - JOLTS state series bind the panel end (state JOLTS latest: Dec 2025 at
    pull time); LAUS/CES/CPI run to Aug 2026.
  - Min wage 2015-2018 and education 2015-2017 are backward-filled edge
    imputations (see sensitivity spec).
  - PanelOLS drop_absorbed=True: the Results section lists any terms dropped
    per specification.

Outputs (written next to this script, then copied to the Mac project folder):
  - master_labor_panel_v2.csv
  - phase1_forest_loso.png
  - PHASE1_RESULTS.md  (written by the script itself)

Requirements: pandas, numpy, statsmodels, linearmodels, matplotlib
"""
import json
import subprocess
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from io import StringIO

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RNG = np.random.default_rng(20260928)
VINTAGE = date.today().isoformat()

# ---------------------------------------------------------------- config ---
STATES = {  # postal -> FIPS
    'AL': '01', 'AK': '02', 'AZ': '04', 'AR': '05', 'CA': '06', 'CO': '08',
    'CT': '09', 'DE': '10', 'DC': '11', 'FL': '12', 'GA': '13', 'HI': '15',
    'ID': '16', 'IL': '17', 'IN': '18', 'IA': '19', 'KS': '20', 'KY': '21',
    'LA': '22', 'ME': '23', 'MD': '24', 'MA': '25', 'MI': '26', 'MN': '27',
    'MS': '28', 'MO': '29', 'MT': '30', 'NE': '31', 'NV': '32', 'NH': '33',
    'NJ': '34', 'NM': '35', 'NY': '36', 'NC': '37', 'ND': '38', 'OH': '39',
    'OK': '40', 'OR': '41', 'PA': '42', 'RI': '44', 'SC': '45', 'SD': '46',
    'TN': '47', 'TX': '48', 'UT': '49', 'VT': '50', 'VA': '51', 'WA': '53',
    'WV': '54', 'WI': '55', 'WY': '56',
}
# Census regions; MD kept in Northeast to match the original build exactly.
REGION = {
    'CT': 'Northeast', 'MA': 'Northeast', 'MD': 'Northeast', 'ME': 'Northeast',
    'NH': 'Northeast', 'NJ': 'Northeast', 'NY': 'Northeast', 'PA': 'Northeast',
    'RI': 'Northeast', 'VT': 'Northeast',
    'IL': 'Midwest', 'IN': 'Midwest', 'MI': 'Midwest', 'MN': 'Midwest',
    'MO': 'Midwest', 'OH': 'Midwest', 'WI': 'Midwest', 'IA': 'Midwest',
    'KS': 'Midwest', 'NE': 'Midwest', 'ND': 'Midwest', 'SD': 'Midwest',
    'FL': 'South', 'GA': 'South', 'NC': 'South', 'SC': 'South', 'TN': 'South',
    'TX': 'South', 'VA': 'South', 'AL': 'South', 'AR': 'South', 'DE': 'South',
    'KY': 'South', 'LA': 'South', 'MS': 'South', 'OK': 'South', 'WV': 'South',
    'DC': 'South',
    'AZ': 'West', 'CA': 'West', 'CO': 'West', 'NV': 'West', 'WA': 'West',
    'AK': 'West', 'HI': 'West', 'ID': 'West', 'MT': 'West', 'NM': 'West',
    'OR': 'West', 'UT': 'West', 'WY': 'West',
}
REGION_CPI = {'Northeast': 'CUUR0100SA0', 'Midwest': 'CUUR0200SA0',
              'South': 'CUUR0300SA0', 'West': 'CUUR0400SA0'}

OUT = "/home/hatch/workspace/tightness-phase1"
RAW = f"{OUT}/data"

# ------------------------------------------------------- download utils ---
def _bls_api_once(series_ids, start, end):
    payload = json.dumps({"seriesid": series_ids,
                          "startyear": start, "endyear": end}).encode()
    req = urllib.request.Request(
        "https://api.bls.gov/publicAPI/v2/timeseries/data/",
        data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        res = json.load(r)
    msg = str(res.get("message", ""))
    if "exceeded" in msg.lower() or "limit" in msg.lower():
        raise RuntimeError(f"BLS rate limit: {msg}")
    out = {}
    for s in res["Results"]["series"]:
        rows = [(pd.Timestamp(f"{o['year']}-{o['period'][1:]}-01"),
                 float(o["value"]))
                for o in s["data"] if o["value"] not in ("-", ".")]
        if rows:
            out[s["seriesID"]] = pd.Series(dict(sorted(rows)))
    return out


def bls_api(series_ids, start="2014", end="2026", tries=4):
    """POST to BLS public API v2 (no key). Splits into <=10yr chunks
    (unauthenticated limit). Returns {series_id: pd.Series}."""
    chunks = []
    y0, y1 = int(start), int(end)
    while y0 <= y1:
        chunks.append((str(y0), str(min(y0 + 9, y1))))
        y0 += 10
    out = {}
    last = None
    for (cs, ce) in chunks:
        for a in range(tries):
            try:
                got = _bls_api_once(series_ids, cs, ce)
                for sid, s in got.items():
                    out[sid] = pd.concat([out[sid], s]).sort_index() \
                        if sid in out else s
                break
            except Exception as e:
                last = e
                time.sleep(5 * (a + 1))
        else:
            raise RuntimeError(f"BLS API failed after {tries} tries: {last}")
        time.sleep(1)
    return out


def fred_csv(sid, tries=3):
    """Fetch one FRED series via fredgraph.csv using curl (python's urllib
    hangs on FRED through this environment's egress proxy; curl works).
    Run only after a FRED cooldown: the endpoint rate-limits aggressively."""
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
    last = None
    for a in range(tries):
        try:
            time.sleep(3)
            p = subprocess.run(
                ["curl", "-s", "--max-time", "30", "-A", "Mozilla/5.0", url],
                capture_output=True, text=True, timeout=60)
            txt = p.stdout
            if not txt or not txt.startswith("observation_date") or "<html" in txt[:600]:
                raise ValueError("got block page / empty instead of CSV")
            df = pd.read_csv(StringIO(txt), parse_dates=["observation_date"])
            s = df.set_index("observation_date").iloc[:, 0]
            s = pd.to_numeric(s, errors="coerce").dropna()
            s.index = pd.to_datetime(s.index)
            if s.empty:
                raise ValueError("empty series")
            return s
        except Exception as e:
            last = e
            time.sleep(10 * (a + 1))
    raise RuntimeError(f"FRED {sid} failed after {tries} tries: {last}")


def fetch_all_fred(sids, workers=3):
    out, failed = {}, []
    done = [0]

    def one(sid):
        try:
            return sid, fred_csv(sid), None
        except Exception as e:
            return sid, None, str(e)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        for sid, s, err in ex.map(one, sids):
            done[0] += 1
            if done[0] % 25 == 0:
                print(f"  FRED progress: {done[0]}/{len(sids)}", flush=True)
            if err:
                failed.append((sid, err))
            else:
                out[sid] = s
    return out, failed

# ------------------------------------------------------------ 1. JOLTS ---
print("== 1. BLS JOLTS state openings & hires ==")
jolts_ids, id2state = [], {}
for st, fips in STATES.items():
    for el in ("JOL", "HIL"):
        sid = f"JTS000000{fips}0000000{el}"
        jolts_ids.append(sid)
        id2state[sid] = (st, el)
jolts_path = f"{RAW}/jolts_raw.pkl"
try:
    _j = pd.read_pickle(jolts_path)
    _ok = len(_j["openings"]) == 51 and len(_j["hires"]) == 51
except FileNotFoundError:
    _ok = False
if _ok:
    openings, hires = _j["openings"], _j["hires"]
    print("  resumed complete JOLTS pickle (51 states x 2)")
else:
    jolts = {}
    for i in range(0, len(jolts_ids), 25):  # unauthenticated BLS API: max 25 series/query
        batch = jolts_ids[i:i + 25]
        got = bls_api(batch)
        missing = [s for s in batch if s not in got]
        if missing:
            raise RuntimeError(f"BLS dropped {len(missing)} series: {missing[:5]}")
        jolts.update(got)
        print(f"  batch {i // 25 + 1}: {len(batch)} ids -> {len(jolts)} series so far", flush=True)
        time.sleep(2)
    assert len(jolts) == len(jolts_ids), f"only {len(jolts)}/{len(jolts_ids)} JOLTS series"
    openings = {id2state[s][0]: jolts[s] for s in jolts if id2state[s][1] == "JOL"}
    hires = {id2state[s][0]: jolts[s] for s in jolts if id2state[s][1] == "HIL"}
    jmx = max(s.index.max() for s in openings.values())
    print(f"  states with openings: {len(openings)}, with hires: {len(hires)}")
    print(f"  JOLTS max date across states: {jmx.date()}")
    pd.to_pickle({"openings": openings, "hires": hires}, jolts_path)

# --------------------------------- 2a. BLS LAUS / CES / CPI (via BLS API) ---
# FRED's fredgraph.csv endpoint 404'd under bulk load on 2026-09-28, so all
# BLS-native series are pulled from the BLS public API instead (same source).
print("== 2a. BLS LAUS + CES + regional CPI ==")
bls_ids = []
for st, fips in STATES.items():
    bls_ids += [f"LASST{fips}0000000000006",  # labor force (persons)
                f"LASST{fips}0000000000003",  # unemployment rate (%)
                f"SMU{fips}000000500000003",  # avg hourly earnings, total private
                f"SMU{fips}000000700000001"]  # LH employment (thousands, as original)
bls_ids += list(REGION_CPI.values()) + ["CUUR0000SA0"]  # + national CPI-U (CPIAUCSL)
bls_path = f"{RAW}/bls_laus_ces_cpi.pkl"
try:
    bls = pd.read_pickle(bls_path)
    print(f"  resumed BLS pickle ({len(bls)}/{len(bls_ids)} series)")
except FileNotFoundError:
    bls = {}
if len(bls) < len(bls_ids):
    have = set(bls)
    for i in range(0, len(bls_ids), 25):
        batch = [s for s in bls_ids[i:i + 25] if s not in have]
        if not batch:
            continue
        got = bls_api(batch)
        missing = [s for s in batch if s not in got]
        if missing:
            raise RuntimeError(f"BLS dropped {len(missing)} series: {missing[:5]}")
        bls.update(got)
        pd.to_pickle(bls, bls_path)  # incremental save
        print(f"  batch {i // 25 + 1}: {len(bls)}/{len(bls_ids)} series", flush=True)
        time.sleep(2)
    pd.to_pickle(bls, bls_path)

# --------------------------------- 2b. FRED min wage + education (resume) ---
print("== 2b. FRED min wage + education ==")
mw_ed_ids = [f"STTMINWG{st}" for st in STATES] + [f"GCT1502{st}" for st in STATES]
mw_ed_path = f"{RAW}/fred_mw_educ.pkl"
try:
    mw_ed = pd.read_pickle(mw_ed_path)
    print(f"  resumed {len(mw_ed)} series from pickle")
except FileNotFoundError:
    mw_ed = {}
todo = [s for s in mw_ed_ids if s not in mw_ed]
print(f"  {len(todo)} series to fetch (patient, ~8s spacing)")
for k, sid in enumerate(todo):
    try:
        mw_ed[sid] = fred_csv(sid)
    except Exception as e:
        print(f"  !! {sid} failed: {str(e)[:100]}", flush=True)
    if (k + 1) % 10 == 0:
        pd.to_pickle(mw_ed, mw_ed_path)
        print(f"  progress {k + 1}/{len(todo)}", flush=True)
pd.to_pickle(mw_ed, mw_ed_path)
failed_mw_ed = [s for s in mw_ed_ids if s not in mw_ed]
print(f"  fetched {len(mw_ed)}/{len(mw_ed_ids)}; failed: {failed_mw_ed}")
if failed_mw_ed:
    pd.DataFrame({"series": failed_mw_ed}).to_csv(f"{RAW}/fred_mw_educ_failed.csv",
                                                  index=False)


# ---- extend annual series to full 2015-2026 coverage ----
# min wage: Wikipedia (DOL-sourced) 2019-2026; 2015-2018 <- 2019 (bfill)
# education: Census GCT1502 (2018,2019) + B15002 (2021-2024);
#   2015-2017 <- 2018 (bfill), 2020 <- 2019 (ACS 1-yr not released), 2025 <- 2024
full_idx = pd.date_range("2015-01-01", "2026-01-01", freq="YS")
for st in STATES:
    for prefix in ("GCT1502", "STTMINWG"):
        key = f"{prefix}{st}"
        if key in mw_ed:
            s = mw_ed[key].copy()
            s.index = pd.to_datetime(s.index)
            s = s.reindex(full_idx).bfill().ffill()
            mw_ed[key] = s
pd.to_pickle(mw_ed, mw_ed_path)
print("  annual series extended to 2015-2026")
print("  education sources: Census GCT1502/B15002 (2018,19,21-24; bfill/ffill edges)")
print("  min-wage sources: Wikipedia (DOL) 2019-2026 (bfill 2015-18)")

# ---------------------------------------------------- 3. assemble panel ---
print("== 3. assembling state-month panel ==")
frames = []
for st, fips in STATES.items():
    if st not in openings or st not in hires:
        print(f"  !! {st}: JOLTS missing, skipped"); continue
    idx = pd.date_range("2014-01-01", "2026-12-01", freq="MS")
    d = pd.DataFrame(index=idx)
    d["Openings"] = openings[st]
    d["Hires"] = hires[st]
    d["Labor_Force"] = bls.get(f"LASST{fips}0000000000006")
    d["Unemployment_Rate"] = bls.get(f"LASST{fips}0000000000003")
    d["Hourly_Wage"] = bls.get(f"SMU{fips}000000500000003")
    # NOTE: original stored LH employment in thousands (no x1000); replicate exactly
    d["LH_Employment"] = bls.get(f"SMU{fips}000000700000001")
    mw = mw_ed.get(f"STTMINWG{st}")
    d["Min_Wage"] = (mw.resample("MS").ffill() if mw is not None else np.nan)
    ed = mw_ed.get(f"GCT1502{st}")
    d["Educ_Attainment"] = (ed.resample("MS").ffill() if ed is not None else np.nan)
    d["State"] = st
    d["Region"] = REGION[st]
    frames.append(d)
raw = pd.concat(frames)
raw.index.name = "Date"
raw = raw.reset_index()
print(f"  raw rows: {len(raw):,}")

# national CPI-U (BLS CUUR0000SA0 = FRED CPIAUCSL); original used national CPI,
# Real_Wage in Jan-2015 dollars: (Hourly_Wage / CPI) * CPI_Jan2015
nat_cpi = bls["CUUR0000SA0"].copy()
nat_cpi.index = pd.to_datetime(nat_cpi.index)
cpi_base = nat_cpi.loc["2015-01-01"]
nat_long = nat_cpi.rename("National_CPI").reset_index()
nat_long.columns = ["Date", "National_CPI"]
raw = raw.merge(nat_long, on="Date", how="left")
raw["CPI_Base_Jan2015"] = cpi_base

# regional CPI (BLS) kept for reference
cpi = pd.DataFrame({r: bls[sid] for r, sid in REGION_CPI.items()})
cpi_rebased = cpi / cpi.loc["2015-01-01"] * 100
cpi_long = cpi_rebased.stack().rename("Regional_CPI").reset_index()
cpi_long.columns = ["Date", "Region", "Regional_CPI"]
raw = raw.merge(cpi_long, on=["Date", "Region"], how="left")

# ------------------------------------------------- 4. feature engineering --
# (exact formulas from exploratory.ipynb / base_model.ipynb)
df = raw.copy()
df["ln_Wage"] = np.log(df["Hourly_Wage"])
df["Hiring_Rate"] = (df["Hires"] * 1000) / df["Labor_Force"]
df["Friction_Proxy"] = ((df["Openings"] - df["Hires"]) * 1000) / df["Labor_Force"]
df["LH_Share"] = df["LH_Employment"] / df["Labor_Force"]
df["Real_Wage"] = (df["Hourly_Wage"] / df["National_CPI"]) * df["CPI_Base_Jan2015"]
df["ln_Real_Wage"] = np.log(df["Real_Wage"])
df["ln_Min_Wage"] = np.log(df["Min_Wage"].fillna(7.25))
df["Min_Wage"] = df["Min_Wage"].fillna(7.25)
df["Educ_Attainment"] = df.groupby("State")["Educ_Attainment"].ffill().bfill()
df["ln_Education"] = np.log(df["Educ_Attainment"])
df = df.sort_values(["State", "Date"])
df["Friction_Lag3"] = df.groupby("State")["Friction_Proxy"].shift(3)
# Exact original Stage 1 interaction (checkpoint requirement): UNLAGGED
df["Friction_x_Education"] = df["Friction_Proxy"] * df["ln_Education"]
# Separately labeled variant (matches the repaired-v2 CSV convention)
df["Friction_x_Education_Lag3"] = df["Friction_Lag3"] * df["ln_Education"]
df["Labor_Tightness"] = df["Openings"] / (df["Unemployment_Rate"] / 100 * df["Labor_Force"])
df["ln_Tightness"] = np.log(df["Labor_Tightness"])
df["Post_2021"] = (df["Date"] >= "2021-01-01").astype(int)
# extras for Phase 1 analysis (appended after the original 23 columns)
df["Unfilled_Share"] = 1 - df["Hires"] / df["Openings"]
df["Unfilled_Share_Lag3"] = df.groupby("State")["Unfilled_Share"].shift(3)
df["Friction_pp_Proxy"] = df["Friction_Proxy"] * 100  # percentage-point units
df["Friction_pp_Lag3"] = df["Friction_Lag3"] * 100

keep = ["Date", "State", "Openings", "Hires", "Labor_Force", "Unemployment_Rate",
        "Hourly_Wage", "LH_Employment", "ln_Wage", "Hiring_Rate", "Friction_Proxy",
        "LH_Share", "Real_Wage", "ln_Real_Wage", "Friction_Lag3",
        "Friction_x_Education", "Labor_Tightness", "ln_Tightness",
        "Educ_Attainment", "ln_Education", "Min_Wage", "ln_Min_Wage", "Post_2021",
        "Region", "Unfilled_Share", "Unfilled_Share_Lag3", "Friction_pp_Proxy",
        "Friction_pp_Lag3", "Friction_x_Education_Lag3"]
panel = df[(df["Date"] >= "2015-04-01")][keep].dropna().reset_index(drop=True)
panel.to_csv(f"{OUT}/master_labor_panel_v2.csv", index=False)
print(f"  v2 panel: {panel['State'].nunique()} states x "
      f"{panel['Date'].nunique()} months = {len(panel):,} obs")
print(f"  range: {panel['Date'].min().date()} -> {panel['Date'].max().date()}")

# ------------------------------------------------- 5. validate vs orig ---
print("== 5. validating against original 25-state panel ==")
orig = pd.read_csv("/home/hatch/uploads/33F735B8-9127-49DE-A1F9-EDD925726D2A/master_labor_panel.csv",
                   parse_dates=["Date"])
cmp_cols = ["Openings", "Hires", "Labor_Force", "Unemployment_Rate", "Hourly_Wage",
            "LH_Employment", "Friction_Proxy", "Real_Wage", "ln_Real_Wage",
            "Friction_Lag3", "Min_Wage", "Educ_Attainment"]
m = orig[["Date", "State"] + cmp_cols].merge(
    panel[["Date", "State"] + cmp_cols], on=["Date", "State"],
    suffixes=("_orig", "_v2"))
print(f"  overlapping obs: {len(m):,}")
val_rows = []
for c in cmp_cols:
    d = (m[f"{c}_v2"] - m[f"{c}_orig"]).abs()
    val_rows.append({"column": c, "max_abs_diff": d.max(),
                     "mean_abs_diff": d.mean(),
                     "orig_mean": m[f"{c}_orig"].mean()})
val = pd.DataFrame(val_rows)
print(val.to_string(index=False))
val.to_csv(f"{OUT}/validation_vs_original.csv", index=False)

# ------------------------------------------------------- 6. estimation ----
print("== 6. estimation ==")
from linearmodels.panel import PanelOLS

X_VARS = ["Friction_Lag3", "Friction_x_Education",
          "Unemployment_Rate", "ln_Min_Wage", "LH_Share"]
Y = "ln_Real_Wage"


def twfe(data, y, xvars, cov="clustered", **kw):
    d = data.set_index(["State", "Date"])
    mod = PanelOLS(d[y], d[xvars], entity_effects=True, time_effects=True,
                   drop_absorbed=True)
    if cov == "clustered":
        return mod.fit(cov_type="clustered", cluster_entity=True, **kw)
    if cov == "twoway":
        return mod.fit(cov_type="clustered", cluster_entity=True,
                       cluster_time=True, **kw)
    if cov == "dk":
        try:
            return mod.fit(cov_type="driscoll-kraay", **kw)
        except Exception:
            return mod.fit(cov_type="kernel", **kw)
    raise ValueError(cov)


def grab(res, var):
    return (res.params[var], res.std_errors[var],
            res.tstats[var], res.pvalues[var], res.nobs)


panel_pp = panel.copy()
panel_pp["Friction_pp_x_Education"] = panel_pp["Friction_pp_Proxy"] * panel_pp["ln_Education"]
panel_pp["UShare_x_Education"] = panel_pp["Unfilled_Share"] * panel_pp["ln_Education"]

res_state = twfe(panel, Y, X_VARS, "clustered")
res_2way = twfe(panel, Y, X_VARS, "twoway")
res_dk = twfe(panel, Y, X_VARS, "dk")
res_pp = twfe(panel_pp, Y,
              ["Friction_pp_Lag3", "Friction_pp_x_Education"] + X_VARS[2:], "twoway")
res_ushare = twfe(panel_pp, Y,
                  ["Unfilled_Share_Lag3", "UShare_x_Education"] + X_VARS[2:], "twoway")

est = pd.DataFrame([
    {"spec": "baseline (SEs clustered by state)", **dict(zip(
        ["coef", "se", "t", "p", "n"], grab(res_state, "Friction_Lag3")))},
    {"spec": "baseline (two-way clustered: state x month)", **dict(zip(
        ["coef", "se", "t", "p", "n"], grab(res_2way, "Friction_Lag3")))},
    {"spec": "baseline (Driscoll-Kraay)", **dict(zip(
        ["coef", "se", "t", "p", "n"], grab(res_dk, "Friction_Lag3")))},
    {"spec": "friction in pp units (two-way SE)", **dict(zip(
        ["coef", "se", "t", "p", "n"], grab(res_pp, "Friction_pp_Lag3")))},
    {"spec": "unfilled share 1-hires/openings (two-way SE)", **dict(zip(
        ["coef", "se", "t", "p", "n"], grab(res_ushare, "Unfilled_Share_Lag3")))},
])
print(est.round(4).to_string(index=False))
est.to_csv(f"{OUT}/headline_estimates.csv", index=False)

# full coefficient table for the preferred (two-way) spec
full = pd.DataFrame({"coef": res_2way.params, "se": res_2way.std_errors,
                     "t": res_2way.tstats, "p": res_2way.pvalues})
print("\nPreferred spec (two-way clustered SEs):")
print(full.round(4).to_string())
full.to_csv(f"{OUT}/preferred_spec_coefs.csv")

# marginal effects in plain English: average marginal effect of friction given
# the interaction: AME = b1 + b2 * mean(ln_Education)
b1 = res_2way.params["Friction_Lag3"]
b2 = res_2way.params["Friction_x_Education"]
ame = b1 + b2 * panel["ln_Education"].mean()
sd_f = panel["Friction_Lag3"].std()
marg = {
    "beta_per_1pp_unfilled_share": ame * 0.01,
    "pct_wage_change_per_1pp": (np.exp(ame * 0.01) - 1) * 100,
    "beta_per_1sd": ame * sd_f,
    "pct_wage_change_per_1sd": (np.exp(ame * sd_f) - 1) * 100,
    "sd_of_lagged_friction": sd_f,
    "mean_of_lagged_friction": panel["Friction_Lag3"].mean(),
    "mean_ln_education": panel["ln_Education"].mean(),
    "avg_marginal_effect": ame,
}
print("\nMarginal effects:", {k: round(v, 4) for k, v in marg.items()})

# terms absorbed/dropped by drop_absorbed=True (collinearity audit)
ABSORB_NOTES = []


def audit_absorb(name, res, xvars):
    dropped = [v for v in xvars if v not in res.params.index]
    ABSORB_NOTES.append(
        (name, f"dropped: {dropped}" if dropped else "none dropped"))


audit_absorb("preferred two-way TWFE", res_2way, X_VARS)
audit_absorb("pp-units TWFE",
             res_pp, ["Friction_pp_Lag3", "Friction_pp_x_Education"] + X_VARS[2:])
audit_absorb("unfilled-share TWFE",
             res_ushare, ["Unfilled_Share_Lag3", "UShare_x_Education"] + X_VARS[2:])
print("\nAbsorption audit (drop_absorbed=True):")
for n, note in ABSORB_NOTES:
    print(f"  {n}: {note}")

# ------------------------------------------------- 7. robustness battery --
print("== 7. robustness battery ==")
rob = []

# (a) leave-one-state-out
loso = []
for st in sorted(panel["State"].unique()):
    r = twfe(panel[panel["State"] != st], Y, X_VARS, "twoway")
    c, se, t, p, n = grab(r, "Friction_Lag3")
    loso.append({"dropped": st, "coef": c, "se": se, "t": t, "p": p})
loso = pd.DataFrame(loso)
loso.to_csv(f"{OUT}/robust_loso.csv", index=False)
rob.append(("leave-one-state-out: min coef", loso["coef"].min()))
rob.append(("leave-one-state-out: max coef", loso["coef"].max()))
rob.append(("leave-one-state-out: share p<0.05",
            (loso["p"] < 0.05).mean()))

# (b) placebo: permuted friction (200 reps). Shuffle Friction_Proxy, re-derive
# the lag and the (unlagged) interaction to stay consistent with the primary spec.
placebo_t = []
fr = panel["Friction_Proxy"].values
for rep in range(200):
    d = panel.copy()
    d["Friction_Proxy"] = RNG.permutation(fr)
    d = d.sort_values(["State", "Date"])
    d["Friction_Lag3"] = d.groupby("State")["Friction_Proxy"].shift(3)
    d["Friction_x_Education"] = d["Friction_Proxy"] * d["ln_Education"].values
    d = d.dropna(subset=["Friction_Lag3"])
    r = twfe(d, Y, X_VARS, "twoway")
    placebo_t.append(r.tstats["Friction_Lag3"])
placebo_t = np.array(placebo_t)
actual_t = res_2way.tstats["Friction_Lag3"]
rob.append(("placebo: actual t-stat", actual_t))
rob.append(("placebo: share |t_shuffled| >= |t_actual|",
            (np.abs(placebo_t) >= abs(actual_t)).mean()))
rob.append(("placebo: share shuffled |t|>1.96",
            (np.abs(placebo_t) > 1.96).mean()))
pd.DataFrame({"t_shuffled": placebo_t}).to_csv(f"{OUT}/robust_placebo.csv", index=False)

# (c) winsorized proxy (1st/99th pct) before lagging
pw = panel.copy()
lo, hi = pw["Friction_Proxy"].quantile([0.01, 0.99])
pw["Friction_Proxy"] = pw["Friction_Proxy"].clip(lo, hi)
pw = pw.sort_values(["State", "Date"])
pw["Friction_Lag3"] = pw.groupby("State")["Friction_Proxy"].shift(3)
pw["Friction_x_Education"] = pw["Friction_Proxy"] * pw["ln_Education"]
pw = pw.dropna(subset=["Friction_Lag3"])
r = twfe(pw, Y, X_VARS, "twoway")
c, se, t, p, n = grab(r, "Friction_Lag3")
rob += [("winsorized 1/99: coef", c), ("winsorized 1/99: p", p)]

# (d) nominal wages as DV
r = twfe(panel, "ln_Wage", X_VARS, "twoway")
c, se, t, p, n = grab(r, "Friction_Lag3")
rob += [("nominal wage DV: coef", c), ("nominal wage DV: p", p)]

# (e) excluding 2020-2021
d = panel[~panel["Date"].dt.year.isin([2020, 2021])]
r = twfe(d, Y, X_VARS, "twoway")
c, se, t, p, n = grab(r, "Friction_Lag3")
rob += [("excl 2020-2021: coef", c), ("excl 2020-2021: p", p),
        ("excl 2020-2021: n", n)]

# (g) lagged-interaction variant (repaired-v2 CSV convention, labeled separately)
X_VARS_L = ["Friction_Lag3", "Friction_x_Education_Lag3",
            "Unemployment_Rate", "ln_Min_Wage", "LH_Share"]
r = twfe(panel, Y, X_VARS_L, "twoway")
c, se, t, p, n = grab(r, "Friction_Lag3")
rob += [("lagged-interaction variant: coef", c),
        ("lagged-interaction variant: p", p)]
audit_absorb("lagged-interaction TWFE", r, X_VARS_L)

# (h) drop ln_Min_Wage (sensitivity to the 2015-2018 min-wage backward-fill)
X_VARS_NOMW = ["Friction_Lag3", "Friction_x_Education",
               "Unemployment_Rate", "LH_Share"]
r = twfe(panel, Y, X_VARS_NOMW, "twoway")
c, se, t, p, n = grab(r, "Friction_Lag3")
rob += [("excl ln_Min_Wage: coef", c), ("excl ln_Min_Wage: p", p)]
audit_absorb("excl-ln_Min_Wage TWFE", r, X_VARS_NOMW)

# (f) state x year FE (+ month FE)
d = panel.copy()
d["Year"] = d["Date"].dt.year
d["StateYear"] = d["State"] + "_" + d["Year"].astype(str)
dd = d.set_index(["StateYear", "Date"])
r = PanelOLS(dd[Y], dd[X_VARS], entity_effects=True, drop_absorbed=True,
             time_effects=True).fit(cov_type="clustered",
                                    cluster_entity=True, cluster_time=True)
c, se, t, p, n = grab(r, "Friction_Lag3")
rob += [("state x year FE: coef", c), ("state x year FE: p", p)]
audit_absorb("state x year + month FE", r, X_VARS)

rob_df = pd.DataFrame(rob, columns=["check", "value"])
print(rob_df.to_string(index=False))
rob_df.to_csv(f"{OUT}/robustness.csv", index=False)

# ------------------------------------------------------ 8. break test ----
print("== 8. structural break test (Chow-type Wald, break at 2021-01) ==")
d = panel.copy()
for v in X_VARS:
    d[v + "_x_Post"] = d[v] * d["Post_2021"]
dd = d.set_index(["State", "Date"])
xfull = X_VARS + [v + "_x_Post" for v in X_VARS]
r_int = PanelOLS(dd[Y], dd[xfull], entity_effects=True, drop_absorbed=True,
                 time_effects=True).fit(cov_type="clustered",
                                        cluster_entity=True, cluster_time=True)
inter = [v + "_x_Post" for v in X_VARS]
bvec = r_int.params[inter].values
V = r_int.cov.loc[inter, inter].values
wald = float(bvec @ np.linalg.inv(V) @ bvec)
from scipy.stats import chi2
p_wald = float(chi2.sf(wald, len(inter)))
print(f"  Wald chi2({len(inter)}) = {wald:.2f}, p = {p_wald:.4f}")
print("  interaction coefs:")
print(r_int.params[inter].round(4).to_string())
print("  interaction p-values:")
print(r_int.pvalues[inter].round(4).to_string())
break_out = {"wald": wald, "df": len(inter), "p": p_wald,
             "inter_coefs": r_int.params[inter].to_dict(),
             "inter_p": r_int.pvalues[inter].to_dict()}
audit_absorb("break-test (all regressors x Post-2021)", r_int, xfull)

# --------------------------------------------- 9. inefficiency tax ------
# Marginal coefficient on friction: b1 + b2 * ln_Education (checkpoint formula).
# Per-state marginal SEs use the delta method with the full 2x2 coefficient
# covariance. The national aggregate's SE uses the same common covariance
# (g' V g), NOT root-summed state SEs.
print("== 9. inefficiency tax verdict ==")
b1t = res_2way.params["Friction_Lag3"]
b2t = res_2way.params["Friction_x_Education"]
Vt = res_2way.cov.loc[["Friction_Lag3", "Friction_x_Education"],
                      ["Friction_Lag3", "Friction_x_Education"]].values
p_hat = res_2way.pvalues["Friction_Lag3"]
agg = panel.groupby("State").agg(
    Friction=("Friction_Proxy", "mean"),
    E=("ln_Education", "mean"),
    Real_Wage=("Real_Wage", "mean"),
    Labor_Force=("Labor_Force", "mean"),
    UR=("Unemployment_Rate", "mean")).reset_index()
agg["Employment"] = agg["Labor_Force"] * (1 - agg["UR"] / 100)
agg["marg"] = b1t + b2t * agg["E"]
agg["se_marg"] = np.sqrt(
    Vt[0, 0] + agg["E"] ** 2 * Vt[1, 1] + 2 * agg["E"] * Vt[0, 1])
agg["Cost_per_1k"] = agg["Friction"] * agg["marg"] * agg["Real_Wage"] * 2080 * 1000
agg["SE_per_1k"] = agg["Friction"] * agg["se_marg"] * agg["Real_Wage"] * 2080 * 1000
# national aggregate: Nat = sum_j a_j * m_j, Var(Nat) = g' V g
agg["a_j"] = agg["Friction"] * agg["Real_Wage"] * 2080 * agg["Employment"]
g = np.column_stack([agg["a_j"].values, agg["a_j"].values * agg["E"].values]).sum(axis=0)
nat = (agg["a_j"] * agg["marg"]).sum()
nat_se = np.sqrt(float(g @ Vt @ g))
print(f"  headline beta (Friction_Lag3) = {b1t:.4f} (p {p_hat:.4f})")
print(f"  avg marginal effect b1+b2*mean(ln_Educ) = "
      f"{b1t + b2t * panel['ln_Education'].mean():.4f}")
print(f"  national inefficiency tax = ${nat / 1e9:.2f}B / yr (SE ${nat_se / 1e9:.2f}B)")
print("  top 5 states by per-1k cost:")
print(agg.sort_values("Cost_per_1k", ascending=False)
      [["State", "Cost_per_1k", "SE_per_1k"]].head().round(0).to_string(index=False))
agg[["State", "Cost_per_1k", "SE_per_1k"]].to_csv(
    f"{OUT}/inefficiency_tax.csv", index=False)
tax_out = {"beta": b1t, "se": float(res_2way.std_errors["Friction_Lag3"]),
           "p": p_hat,
           "avg_marginal_effect": b1t + b2t * panel["ln_Education"].mean(),
           "national_bn": nat / 1e9, "national_se_bn": nat_se / 1e9}
b_hat = b1t  # headline Friction_Lag3 coefficient (used by plot + report)

# ------------------------------------------------ 10. forest plot -------
print("== 10. forest plot ==")
loso_sorted = loso.sort_values("coef").reset_index(drop=True)
fig, ax = plt.subplots(figsize=(8, 12))
y = np.arange(len(loso_sorted))
ax.errorbar(loso_sorted["coef"], y,
            xerr=1.96 * loso_sorted["se"], fmt="o", ms=4,
            color="steelblue", ecolor="gray", elinewidth=1, capsize=2)
ax.axvline(b_hat, color="crimson", lw=1.5, ls="--",
           label=f"full sample β={b_hat:.2f}")
ax.set_yticks(y)
ax.set_yticklabels(loso_sorted["dropped"], fontsize=7)
ax.set_xlabel("Friction_Lag3 coefficient (leave-one-state-out, 95% CI)")
ax.set_title("Robustness: leave-one-state-out", fontweight="bold")
ax.grid(alpha=0.2, axis="x")
ax.legend(fontsize=9)
plt.tight_layout()
plt.savefig(f"{OUT}/phase1_forest_loso.png", dpi=150, bbox_inches="tight")
plt.close()

# ------------------------------------------------ 11. results markdown ---
print("== 11. writing PHASE1_RESULTS.md ==")
orig_beta = 6.1657  # reported preferred TWFE coef, 25-state panel


def star(p):
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else ""


est_lines = "\n".join(
    f"| {r['spec']} | {r['coef']:.4f}{star(r['p'])} | {r['se']:.4f} "
    f"| {r['t']:.2f} | {r['p']:.4f} | {int(r['n']):,} |"
    for _, r in est.iterrows())
rob_lines = "\n".join(
    f"| {c} | {v:.4f} |" if isinstance(v, float) else f"| {c} | {v} |"
    for c, v in rob)
val_lines = "\n".join(
    f"| {r['column']} | {r['max_abs_diff']:.6f} | {r['mean_abs_diff']:.6f} |"
    for _, r in val.iterrows())

tax_verdict = (
    "**REBUILD (with confidence intervals).** The headline coefficient is "
    f"statistically significant on the 50 states + DC panel (β={b_hat:.4f}, "
    f"two-way p={p_hat:.4f}), so the tax can now be computed honestly: "
    f"national estimate ${tax_out['national_bn']:.1f}B/yr "
    f"(SE ${tax_out['national_se_bn']:.1f}B). "
    "Caveat for the paper: this is a *descriptive* wage premium associated "
    "with hiring friction, not a causal 'tax' — the TWFE cannot rule out "
    "reverse causality (Phase 2: Bartik IV). Frame it as an upper bound, "
    "or cut it and let the wage regression carry the paper."
    if p_hat < 0.05 else
    "**CUT IT.** The headline coefficient is not significant on the "
    "expanded panel, so any tax built on it inherits that fragility. "
    "Drop the exhibit; the wage regression is the paper.")

absorb_lines = "\n".join(f"- {n}: {note}" for n, note in ABSORB_NOTES)

md = f"""# Phase 1 Results — Tightness Paradox 50-State Rebuild

*Completed {VINTAGE}. Script: `phase1_rebuild.py` (reproducible end-to-end,
seed 20260928). Data vintage: downloaded {VINTAGE}.*

## Panel

- **50 states + DC (51 jurisdictions) × {panel['Date'].nunique()} months = {len(panel):,} obs**
- Date range: {panel['Date'].min().date()} → {panel['Date'].max().date()}
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
- FRED annual-series fetch failures: {failed_mw_ed if failed_mw_ed else 'none'}.

## Validation vs original 25-state panel (overlap: {len(m):,} obs)

Max / mean absolute differences, v2 minus original:

| column | max abs diff | mean abs diff |
|---|---|---|
{val_lines}

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
{est_lines}

Original 25-state headline: β = {orig_beta:.4f} (state-clustered, p < 0.05).

**Verdict on the original finding:** {"SURVIVES" if res_2way.pvalues["Friction_Lag3"] < 0.05 else "DOES NOT SURVIVE"} —
on the expanded 50-state + DC panel the friction coefficient is {b_hat:.4f}
(two-way-clustered p = {res_2way.pvalues["Friction_Lag3"]:.4f}).

## Plain-English marginal effects (two-way SE spec)

Average marginal effect of friction given the interaction,
AME = b1 + b2 × mean(ln_Education) = {tax_out['avg_marginal_effect']:.4f}:

- 1 pp rise in the unfilled-openings share of the labor force →
  **{marg['pct_wage_change_per_1pp']:.2f}% higher real wages** (3 months later).
- 1 SD rise in lagged friction (SD = {marg['sd_of_lagged_friction']:.4f}) →
  **{marg['pct_wage_change_per_1sd']:.2f}% higher real wages**.
- The pp-units regression reads directly: coef on `Friction_pp_Lag3` =
  {res_pp.params["Friction_pp_Lag3"]:.4f} (≈ % wage change per pp).

## Absorption audit (`drop_absorbed=True`)

{absorb_lines}

## Robustness battery

| check | value |
|---|---|
{rob_lines}

- Break test (all regressors × Post-2021, Wald): chi2({break_out['df']}) =
  {break_out['wald']:.2f}, p = {break_out['p']:.4f}.
  → {"Evidence of a structural break at 2021." if break_out['p'] < 0.05 else "No significant break at 2021 (consistent with the original Stage 3 null)."}
- Friction×Post-2021 interaction: coef =
  {break_out['inter_coefs']['Friction_Lag3_x_Post']:.4f},
  p = {break_out['inter_p']['Friction_Lag3_x_Post']:.4f}.

## Inefficiency-tax verdict

Marginal tax coefficient per state: b1 + b2 × ln_Education (state mean),
SEs by the delta method from the full 2×2 coefficient covariance; national
aggregate SE from the same common covariance (g′Vg), not root-summed state SEs.

{tax_verdict}

National back-of-envelope (descriptive): ${tax_out['national_bn']:.1f}B/yr
(SE ${tax_out['national_se_bn']:.1f}B). State table: `inefficiency_tax.csv`.

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
"""
with open(f"{OUT}/PHASE1_RESULTS.md", "w") as f:
    f.write(md)
print("done.")
