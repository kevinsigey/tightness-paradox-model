#!/usr/bin/env python3
"""
State characteristics as predictors of labor-market friction (Kevin Sigey).

Assembles, for all 50 states + DC, published state characteristics from the
publisher's own distribution channel, and models two kinds of targets taken
from Kevin's Tightness Paradox files (targets are NOT recomputed from raw
microdata; the panel means and per-state betas are read from his files):

  Targets (Kevin's files):
    - friction_level   : state mean of Friction_Proxy, master_labor_panel_v2.csv
    - unfilled_share   : state mean of Unfilled_Share, same panel
    - beta_full        : per-state Friction_Lag3 beta, full 2015-2025 sample,
                         state_groups_estimates.csv (analysis == 'per_state')
    - beta_recent      : same, recent 2022-2025 sample

  Characteristics (publisher routes actually used):
    - FRED fredgraph CSV (keyless): BEA real GDP by state, Census population
      estimates, BLS LAUS unemployment, DOL state minimum wage (FRED series
      STTMINWG*, source agency = U.S. Department of Labor, WHD).
    - BEA bulk download SAGDP.zip (SAGDP2, current-dollar GDP by industry).
    - BLS QCEW open-data API (data.bls.gov/cew), annual area + industry files.
    - Census Bureau ACS table-based summary files (www2.census.gov), 1-year.
      (api.census.gov now returns a "Missing Key" wall without an API key,
      so the Bureau's own summary-file distribution is used instead.)
    - Census Gazetteer state file (land area) for population density.
    - State JOLTS openings/hires rates: derived from Kevin's panel, which is
      built from BLS state JOLTS; flagged as panel-derived, not re-pulled,
      because www.bls.gov returns HTTP 403 from this network.

  NOT retrieved (flagged, not substituted from aggregators):
    - BLS CPS union membership rate by state: www.bls.gov (news release
      USDL "Union Members", Table 5) returns HTTP 403 from this network and
      no publisher-direct mirror exists; third-party republications were
      deliberately not used.
    - ACS/Census urban population share: the Census API route requires a
      key; population density (Census Gazetteer land area + ACS population)
      is used as the published urbanization proxy and flagged as such.

Modeling (n = 51, associational only):
    - Univariate Pearson correlations of every characteristic with every
      target, Benjamini-Hochberg FDR within each target family.
    - Elastic net (alpha + l1 chosen by inner 5-fold CV) inside a
      StandardScaler pipeline, evaluated by leave-one-out CV; CV R^2 is
      reported against a mean-only baseline evaluated the same way.

Seed: 20261101. Outputs:
    state_characteristics.csv  (assembled dataset, one row per state)
    modeling_results.csv       (univariate table + penalized-model summary)
"""

import io
import json
import re
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from scipy import stats
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import ElasticNetCV
from sklearn.model_selection import LeaveOneOut, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

SEED = 20261101
np.random.seed(SEED)

OUT_DIR = Path(__file__).resolve().parent
PANEL_CSV = Path.home() / "workspace/tightness-phase1/master_labor_panel_v2.csv"
EST_CSV = OUT_DIR / "state_groups_estimates.csv"
TMP = Path("/tmp/state_char")
TMP.mkdir(exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124 Safari/537.36"}

# postal, FIPS, name
STATES = [
    ("AL", "01", "Alabama"), ("AK", "02", "Alaska"), ("AZ", "04", "Arizona"),
    ("AR", "05", "Arkansas"), ("CA", "06", "California"), ("CO", "08", "Colorado"),
    ("CT", "09", "Connecticut"), ("DE", "10", "Delaware"), ("DC", "11", "District of Columbia"),
    ("FL", "12", "Florida"), ("GA", "13", "Georgia"), ("HI", "15", "Hawaii"),
    ("ID", "16", "Idaho"), ("IL", "17", "Illinois"), ("IN", "18", "Indiana"),
    ("IA", "19", "Iowa"), ("KS", "20", "Kansas"), ("KY", "21", "Kentucky"),
    ("LA", "22", "Louisiana"), ("ME", "23", "Maine"), ("MD", "24", "Maryland"),
    ("MA", "25", "Massachusetts"), ("MI", "26", "Michigan"), ("MN", "27", "Minnesota"),
    ("MS", "28", "Mississippi"), ("MO", "29", "Missouri"), ("MT", "30", "Montana"),
    ("NE", "31", "Nebraska"), ("NV", "32", "Nevada"), ("NH", "33", "New Hampshire"),
    ("NJ", "34", "New Jersey"), ("NM", "35", "New Mexico"), ("NY", "36", "New York"),
    ("NC", "37", "North Carolina"), ("ND", "38", "North Dakota"), ("OH", "39", "Ohio"),
    ("OK", "40", "Oklahoma"), ("OR", "41", "Oregon"), ("PA", "42", "Pennsylvania"),
    ("RI", "44", "Rhode Island"), ("SC", "45", "South Carolina"), ("SD", "46", "South Dakota"),
    ("TN", "47", "Tennessee"), ("TX", "48", "Texas"), ("UT", "49", "Utah"),
    ("VT", "50", "Vermont"), ("VA", "51", "Virginia"), ("WA", "53", "Washington"),
    ("WV", "54", "West Virginia"), ("WI", "55", "Wisconsin"), ("WY", "56", "Wyoming"),
]
POSTALS = [s[0] for s in STATES]


def get(url, tries=3, timeout=120):
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=timeout)
            if r.status_code == 200 and len(r.content) > 0:
                return r
            last = f"HTTP {r.status_code}"
        except Exception as e:  # noqa: BLE001
            last = str(e)
        time.sleep(2 * (i + 1))
    raise RuntimeError(f"GET failed {url}: {last}")


# ---------------------------------------------------------------- targets
def load_targets():
    panel = pd.read_csv(PANEL_CSV, parse_dates=["Date"])
    g = panel.groupby("State")
    t = pd.DataFrame({
        "friction_level": g["Friction_Proxy"].mean(),
        "unfilled_share": g["Unfilled_Share"].mean(),
        # BLS state JOLTS rates as compiled in Kevin's panel (flagged derived)
        "jolts_openings_rate": g.apply(
            lambda d: (d["Openings"] / d["Labor_Force"]).mean() * 100,
            include_groups=False),
        "jolts_hires_rate": g.apply(
            lambda d: (d["Hires"] / d["Labor_Force"]).mean() * 100,
            include_groups=False),
    })
    est = pd.read_csv(EST_CSV)
    ps = est[(est["analysis"] == "per_state") & (est["term"] == "Friction_Lag3")]
    for sample, col in [("full_2015_2025", "beta_full"),
                        ("recent_2022_2025", "beta_recent")]:
        s = ps[ps["sample"] == sample].set_index("group")["beta"]
        t[col] = s
        t[col + "_se"] = ps[ps["sample"] == sample].set_index("group")["se"]
    return t.reset_index().rename(columns={"State": "state"})


# ---------------------------------------------------------------- FRED
def fred_batch(series_ids, cosd="2018-01-01"):
    """One fredgraph call for many series -> wide DataFrame indexed by date.
    NOTE 1: fredgraph without a start date is pathologically slow for
    51-series batches (server-side generation); always pass cosd.
    NOTE 2: this sandbox's egress path stalls multi-series fredgraph
    responses when the request carries a browser User-Agent (and stalls
    Python `requests` generally); curl with its DEFAULT user-agent
    completes in ~2 s. So the pull shells out to curl with no -A flag.
    Verified 2026-11-01: identical URL, browser UA -> timeout at 30 s;
    default curl UA -> 200 in 1.9 s.
    NOTE 3: fredgraph silently caps a multi-series response at 12 series,
    so batches are chunked into groups of 10 and merged on the date index.
    """
    import subprocess

    def one_chunk(ids):
        url = ("https://fred.stlouisfed.org/graph/fredgraph.csv?id=" +
               ",".join(ids) + f"&cosd={cosd}")
        last = None
        for i in range(3):
            p = subprocess.run(["curl", "-s", "--max-time", "90", url],
                               capture_output=True, text=True)
            if p.returncode == 0 and p.stdout.startswith("observation_date"):
                df = pd.read_csv(io.StringIO(p.stdout),
                                 parse_dates=["observation_date"])
                return df.set_index("observation_date")
            last = f"curl rc={p.returncode} out={p.stdout[:80]!r}"
            time.sleep(2 * (i + 1))
        raise RuntimeError(f"fredgraph chunk failed: {last}")

    frames = [one_chunk(series_ids[i:i + 10])
              for i in range(0, len(series_ids), 10)]
    return pd.concat(frames, axis=1)


def pull_fred():
    out = pd.DataFrame({"state": POSTALS})
    # --- BLS LAUS unemployment rate (monthly, SA): mean over latest full year
    ur = fred_batch([f"{s}UR" for s in POSTALS], cosd="2024-01-01")
    years = {}
    for s in POSTALS:
        ser = ur[f"{s}UR"].dropna()
        full = [y for y in range(2015, 2027)
                if ((ser.index.year == y).sum() == 12)]
        y = max(full)
        years[s] = y
        out.loc[out.state == s, "laus_unemp_rate"] = ser[ser.index.year == y].mean()
    laus_year = int(pd.Series(years).mode()[0])
    # --- BEA real GDP (quarterly, SAAR, millions of chained 2017 $)
    ng = fred_batch([f"{s}NGSP" for s in POSTALS])
    # --- Census population estimates (annual, thousands)
    pop = fred_batch([f"{s}POP" for s in POSTALS])
    gdp_years = {}
    for s in POSTALS:
        # FRED's {ST}NGSP is the ANNUAL BEA series (1 obs/yr); groupby-year
        # mean is used so the code is frequency-agnostic.
        ser = ng[f"{s}NGSP"].dropna()
        by_year = ser.groupby(ser.index.year).mean()
        y = max(yy for yy in by_year.index if (yy - 5) in by_year.index)
        gdp_years[s] = y
        gdp_y = by_year[y]                                # millions of 2017 $
        gdp_y5 = by_year[y - 5]
        p_y = pop[f"{s}POP"].dropna().groupby(
            pop[f"{s}POP"].dropna().index.year).mean()
        pop_y = p_y[y]                                    # thousands
        pop_y5 = p_y[y - 5]
        row = out.state == s
        out.loc[row, "rgdp_per_capita"] = gdp_y * 1e6 / (pop_y * 1e3)
        out.loc[row, "rgdp_growth_5yr_pct"] = (gdp_y / gdp_y5 - 1) * 100
        out.loc[row, "pop_growth_5yr_pct"] = (pop_y / pop_y5 - 1) * 100
    gdp_year = int(pd.Series(gdp_years).mode()[0])
    # --- U.S. DOL statutory minimum wage (FRED STTMINWG*, source: DOL WHD)
    # AL, LA, MS, SC, TN have NO statutory state minimum wage (DOL WHD state
    # table), so FRED carries no STTMINWG series for them; the applicable
    # floor is the federal FLSA rate, coded 7.25 and flagged.
    NO_STATE_MW = ["AL", "LA", "MS", "SC", "TN"]
    mw = fred_batch([f"STTMINWG{s}" for s in POSTALS if s not in NO_STATE_MW],
                    cosd="2023-01-01")
    mw_years = {}
    for s in POSTALS:
        if s in NO_STATE_MW:
            out.loc[out.state == s, "min_wage"] = 7.25
            out.loc[out.state == s, "min_wage_federal_floor"] = 1
            continue
        ser = mw[f"STTMINWG{s}"].dropna()
        out.loc[out.state == s, "min_wage"] = ser.iloc[-1]
        out.loc[out.state == s, "min_wage_federal_floor"] = 0
        mw_years[s] = int(ser.index[-1].year)
    meta = {"laus_year": laus_year, "gdp_year": gdp_year,
            "pop_year": gdp_year, "minwage_year_mode": int(pd.Series(mw_years).mode()[0])}
    return out, meta


# ---------------------------------------------------------------- BEA SAGDP2
BEA_SUMS = {
    "bea_gdpshare_manuf": ["Manufacturing"],
    "bea_gdpshare_profbus": [
        "Professional, scientific, and technical services",
        "Management of companies and enterprises",
        "Administrative and support and waste management and remediation services"],
    "bea_gdpshare_edhealth": ["Educational services",
                              "Health care and social assistance"],
    "bea_gdpshare_leishosp": ["Arts, entertainment, and recreation",
                              "Accommodation and food services"],
}


def pull_bea():
    zpath = TMP / "SAGDP.zip"
    if not zpath.exists():
        zpath.write_bytes(get("https://apps.bea.gov/regional/zip/SAGDP.zip").content)
    out = pd.DataFrame({"state": POSTALS})
    year_used = None
    with zipfile.ZipFile(zpath) as z:
        for postal, fips, _name in STATES:
            name = f"SAGDP2_{postal}_1997_2025.csv"
            df = pd.read_csv(z.open(name), dtype={"GeoFIPS": str})
            df["Description"] = df["Description"].str.strip()
            years_avail = [c for c in df.columns if c.isdigit()]
            for c in years_avail:
                df[c] = pd.to_numeric(df[c], errors="coerce")
            tot_row = df[df.Description == "All industry total"].iloc[0]
            yr = max(c for c in years_avail if pd.notna(tot_row[c]))
            year_used = yr
            tot = float(tot_row[yr])
            for col, descs in BEA_SUMS.items():
                val = sum(float(df.loc[df.Description == d, yr].iloc[0])
                          for d in descs)
                out.loc[out.state == postal, col] = val / tot * 100
    return out, int(year_used)


# ---------------------------------------------------------------- BLS QCEW
QCEW_IND = {  # QCEW supersector industry codes
    "qcew_empshare_manuf": "1013",     # Manufacturing
    "qcew_empshare_profbus": "1024",   # Professional and business services
    "qcew_empshare_edhealth": "1025",  # Education and health services
    "qcew_empshare_leishosp": "1026",  # Leisure and hospitality
}


def qcew_year_available(year):
    try:
        r = requests.get(f"https://data.bls.gov/cew/data/api/{year}/a/area/01000.csv",
                         headers=UA, timeout=60)
        return r.status_code == 200 and "annual_avg_emplvl" in r.text
    except Exception:  # noqa: BLE001
        return False


def pull_qcew():
    year = 2025 if qcew_year_available(2025) else 2024
    out = pd.DataFrame({"state": POSTALS})
    tot_emp, pay = {}, {}
    for postal, fips, _n in STATES:
        area = fips + "000"
        r = get(f"https://data.bls.gov/cew/data/api/{year}/a/area/{area}.csv")
        df = pd.read_csv(io.StringIO(r.text), dtype=str)
        row = df[(df.own_code == "0") & (df.industry_code == "10")].iloc[0]
        tot_emp[postal] = float(row["annual_avg_emplvl"])
        pay[postal] = float(row["avg_annual_pay"])
    out["qcew_avg_annual_pay"] = out.state.map(pay)
    for col, ind in QCEW_IND.items():
        r = get(f"https://data.bls.gov/cew/data/api/{year}/a/industry/{ind}.csv")
        df = pd.read_csv(io.StringIO(r.text), dtype=str)
        df = df[(df.agglvl_code == "53") & (df.own_code.isin(["1", "2", "3", "5"]))]
        df["annual_avg_emplvl"] = df["annual_avg_emplvl"].astype(float)
        emp = df.groupby("area_fips")["annual_avg_emplvl"].sum()
        out[col] = [emp.get(f + "000", np.nan) / tot_emp[p] * 100
                    for p, f, _n in STATES]
    return out, year


# ---------------------------------------------------------------- Census ACS
ACS_TABLES = ["B01002", "B01003", "B08301", "B15003", "B17001",
              "B19013", "B19083", "B25064", "B25077"]


def acs_base(year):
    return (f"https://www2.census.gov/programs-surveys/acs/summary_file/"
            f"{year}/table-based-SF/data/1YRData/acsdt1y{year}-")


def pull_acs():
    year = None
    # 2024 preferred: the 2025 ACS redesigned some tables (e.g. B15003 went
    # from 25 to 23 variables), which would silently change variable
    # mappings; the 2024 1-year mappings used below are verified.
    for cand in (2024, 2025):
        try:
            r = requests.get(acs_base(cand) + "b19013.dat", headers=UA, timeout=60)
            if r.status_code == 200 and r.text.startswith("GEO_ID"):
                year = cand
                break
        except Exception:  # noqa: BLE001
            pass
    if year is None:
        raise RuntimeError("ACS summary files unreachable for 2025 and 2024")
    tabs = {}
    for tname in ACS_TABLES:
        r = get(acs_base(year) + f"{tname.lower()}.dat")
        df = pd.read_csv(io.StringIO(r.text), sep="|", dtype=str)
        df = df[df.GEO_ID.str.startswith("0400000US")].copy()
        df["fips"] = df.GEO_ID.str[-2:]
        tabs[tname] = df.set_index("fips")
    out = pd.DataFrame({"state": POSTALS,
                        "fips": [f for _p, f, _n in STATES]})

    def col(tab, var):
        return pd.to_numeric(tabs[tab][f"{tab}_E{var}"], errors="coerce")

    out["acs_population"] = [col("B01003", "001")[f] for f in out.fips]
    out["median_age"] = [col("B01002", "001")[f] for f in out.fips]
    out["median_hh_income"] = [col("B19013", "001")[f] for f in out.fips]
    out["gini_index"] = [col("B19083", "001")[f] for f in out.fips]
    out["median_gross_rent"] = [col("B25064", "001")[f] for f in out.fips]
    out["median_home_value"] = [col("B25077", "001")[f] for f in out.fips]
    pov = col("B17001", "002") / col("B17001", "001") * 100
    out["poverty_rate"] = [pov[f] for f in out.fips]
    bach = (col("B15003", "022") + col("B15003", "023") +
            col("B15003", "024") + col("B15003", "025")) / col("B15003", "001") * 100
    out["bachelors_plus_share"] = [bach[f] for f in out.fips]
    wfh = col("B08301", "021") / col("B08301", "001") * 100
    out["wfh_share"] = [wfh[f] for f in out.fips]
    return out, year


def pull_density(acs_pop):
    r = get("https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
            "2024_Gazetteer/2024_Gaz_state_national.zip")
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        name = z.namelist()[0]
        gz = pd.read_csv(z.open(name), sep="\t", dtype=str)
    gz["ALAND_SQMI"] = gz["ALAND_SQMI"].astype(float)
    land = dict(zip(gz["USPS"], gz["ALAND_SQMI"]))
    return [p / land[s] for p, s in zip(acs_pop, POSTALS)]


# ---------------------------------------------------------------- modeling
def bh_q(pvals):
    p = np.asarray(pvals, dtype=float)
    n = len(p)
    order = np.argsort(p)
    q = np.empty(n)
    prev = 1.0
    for i, idx in enumerate(order[::-1]):
        rank = n - i
        prev = min(prev, p[idx] * n / rank)
        q[idx] = prev
    return q


FEATURES = [
    "rgdp_per_capita", "rgdp_growth_5yr_pct",
    "bea_gdpshare_edhealth", "bea_gdpshare_profbus",
    "bea_gdpshare_leishosp", "bea_gdpshare_manuf",
    "laus_unemp_rate", "qcew_avg_annual_pay",
    "qcew_empshare_edhealth", "qcew_empshare_profbus",
    "qcew_empshare_leishosp", "qcew_empshare_manuf",
    "jolts_openings_rate", "jolts_hires_rate",
    "median_hh_income", "gini_index", "poverty_rate", "bachelors_plus_share",
    "median_age", "pop_density", "median_gross_rent", "median_home_value",
    "wfh_share", "pop_growth_5yr_pct", "min_wage",
]
TARGETS = ["friction_level", "unfilled_share", "beta_full", "beta_recent"]


def run_models(df):
    rows = []
    X = df[FEATURES].copy()
    med = X.median()
    X = X.fillna(med)
    for tgt in TARGETS:
        y = df[tgt].astype(float)
        # univariate
        ps, rs = [], []
        for f in FEATURES:
            r_, p_ = stats.pearsonr(X[f], y)
            rs.append(r_)
            ps.append(p_)
        qs = bh_q(ps)
        for f, r_, p_, q_ in zip(FEATURES, rs, ps, qs):
            rho, _ = stats.spearmanr(X[f], y)
            rows.append({"target": tgt, "feature": f, "pearson_r": r_,
                         "p": p_, "q_bh": q_, "spearman_rho": rho,
                         "kind": "univariate"})
        # penalized: outer LOOCV around scaler + ElasticNetCV
        pipe = Pipeline([
            ("sc", StandardScaler()),
            ("en", ElasticNetCV(l1_ratio=[0.2, 0.5, 0.8, 1.0],
                                alphas=np.logspace(-3, 1.5, 100),
                                cv=5, max_iter=20000,
                                random_state=SEED)),
        ])
        loo = LeaveOneOut()
        pred = cross_val_predict(pipe, X, y, cv=loo)
        ss_res = float(((y - pred) ** 2).sum())
        base_pred = cross_val_predict(DummyRegressor(strategy="mean"), X, y, cv=loo)
        ss_base = float(((y - base_pred) ** 2).sum())
        ss_tot = float(((y - y.mean()) ** 2).sum())
        cv_r2 = 1 - ss_res / ss_tot
        base_r2 = 1 - ss_base / ss_tot
        pipe.fit(X, y)
        en = pipe.named_steps["en"]
        coefs = {f: float(c) for f, c in zip(FEATURES, en.coef_) if abs(c) > 1e-10}
        rows.append({"target": tgt, "feature": "__elasticnet__",
                     "pearson_r": np.nan, "p": np.nan, "q_bh": np.nan,
                     "spearman_rho": np.nan, "kind": "penalized",
                     "cv_r2": cv_r2, "baseline_cv_r2": base_r2,
                     "alpha": float(en.alpha_), "l1_ratio": float(en.l1_ratio_),
                     "nonzero_coefs": json.dumps(coefs)})
        print(f"[{tgt}] CV R2={cv_r2:.3f} (baseline {base_r2:.3f}), "
              f"alpha={en.alpha_:.4g}, l1={en.l1_ratio_}, "
              f"nonzero={len(coefs)}")
        # Supplementary honesty check for the two LEVEL targets: the JOLTS
        # openings/hires rates are near-mechanical relatives of the friction
        # measures, so re-run the same LOOCV pipeline without them to see
        # how much the genuine characteristics carry on their own.
        if tgt in ("friction_level", "unfilled_share"):
            keep = [f for f in FEATURES
                    if f not in ("jolts_openings_rate", "jolts_hires_rate")]
            pipe2 = Pipeline([
                ("sc", StandardScaler()),
                ("en", ElasticNetCV(l1_ratio=[0.2, 0.5, 0.8, 1.0],
                                    alphas=np.logspace(-3, 1.5, 100),
                                    cv=5, max_iter=20000,
                                    random_state=SEED)),
            ])
            pred2 = cross_val_predict(pipe2, X[keep], y, cv=loo)
            cv_r2_nj = 1 - float(((y - pred2) ** 2).sum()) / ss_tot
            pipe2.fit(X[keep], y)
            en2 = pipe2.named_steps["en"]
            coefs2 = {f: float(c) for f, c in zip(keep, en2.coef_)
                      if abs(c) > 1e-10}
            rows.append({"target": tgt, "feature": "__elasticnet_no_jolts__",
                         "pearson_r": np.nan, "p": np.nan, "q_bh": np.nan,
                         "spearman_rho": np.nan, "kind": "penalized_no_jolts",
                         "cv_r2": cv_r2_nj, "baseline_cv_r2": base_r2,
                         "alpha": float(en2.alpha_),
                         "l1_ratio": float(en2.l1_ratio_),
                         "nonzero_coefs": json.dumps(coefs2)})
            print(f"[{tgt}] no-JOLTS CV R2={cv_r2_nj:.3f}, "
                  f"nonzero={len(coefs2)}")
    return pd.DataFrame(rows)


def main():
    targets = load_targets()
    fred, fred_meta = pull_fred()
    bea, bea_year = pull_bea()
    qcew, qcew_year = pull_qcew()
    acs, acs_year = pull_acs()
    acs["pop_density"] = pull_density(acs["acs_population"].tolist())
    df = targets.merge(fred, on="state").merge(bea, on="state") \
                .merge(qcew, on="state").merge(
                    acs.drop(columns=["acs_population"]), on="state")
    df = df[["state", "fips"] + TARGETS +
            [c for c in df.columns if c not in
             ["state", "fips"] + TARGETS + ["beta_full_se", "beta_recent_se"]]]
    df.to_csv(OUT_DIR / "state_characteristics.csv", index=False)
    print("dataset:", df.shape, "| meta:", fred_meta,
          "| BEA year:", bea_year, "| QCEW year:", qcew_year, "| ACS year:", acs_year)
    print(df[FEATURES].isna().sum()[lambda s: s > 0])
    res = run_models(df)
    res.to_csv(OUT_DIR / "modeling_results.csv", index=False)
    meta = {**fred_meta, "bea_industry_year": bea_year,
            "qcew_year": qcew_year, "acs_year": acs_year}
    (OUT_DIR / "pull_meta.json").write_text(json.dumps(meta, indent=2))
    print("meta:", meta)


if __name__ == "__main__":
    main()
