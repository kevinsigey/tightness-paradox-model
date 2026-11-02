#!/usr/bin/env python3
"""
Whose Wages? -- first pass (preliminary, descriptive).

Question: in Kevin Sigey's frozen high-friction tercile of states, was the
2022-2025 wage strength concentrated in low-wage industries (consistent with
Autor-Dube-McGrew's low-wage job-ladder channel showing up in the state mean)
or spread across industry wage tiers?

Method (this pass): BLS QCEW annual single-file data. Statewide NAICS-sector
rows (agglvl_code 54, own_code 5 = total all ownerships; NAICS 92 government
and 99 unclassified excluded). Industries are assigned to wage tiers by their
2021 national employment-weighted average annual pay (terciles across the 19
included sectors). For each frozen state group (prereg_group_assignments.csv)
and tier, compute base-year-employment-weighted log growth of average annual
pay over three windows: 2015->2019 (placebo), 2019->2021, 2021->2025 (main;
annual averages stand in for the paper's monthly Jan-2022-Dec-2025 window).

Nominal pay: a national CPI deflator is common to all states/industries in a
window, so it cancels in every cross-group and cross-tier contrast reported
here; levels are labelled nominal.

Outputs (alongside this script):
  whose_wages_qcew_filtered.csv   state x sector x year pay/employment
  whose_wages_tiers.csv           sector tier assignments + 2021 natl pay
  whose_wages_group_tier.csv      group x tier x window growth table
  whose_wages_by_industry.csv     per-sector growth by group
  whose_wages_firstpass.md        auto-generated summary of the tables
Raw zips land in qcew_scratch/ (delete after run; filtered CSV is the record).

Source: U.S. Bureau of Labor Statistics, Quarterly Census of Employment and
Wages (QCEW), annual single-file CSVs,
https://data.bls.gov/cew/data/files/{year}/csv/{year}_annual_singlefile.zip
"""
import csv, io, math, os, subprocess, sys, zipfile
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SCRATCH = os.path.join(HERE, "qcew_scratch")
YEARS = [2015, 2019, 2021, 2025]

FIPS = {
    "AL": "01000", "AK": "02000", "AZ": "04000", "AR": "05000", "CA": "06000",
    "CO": "08000", "CT": "09000", "DE": "10000", "DC": "11000", "FL": "12000",
    "GA": "13000", "HI": "15000", "ID": "16000", "IL": "17000", "IN": "18000",
    "IA": "19000", "KS": "20000", "KY": "21000", "LA": "22000", "ME": "23000",
    "MD": "24000", "MA": "25000", "MI": "26000", "MN": "27000", "MS": "28000",
    "MO": "29000", "MT": "30000", "NE": "31000", "NV": "32000", "NH": "33000",
    "NJ": "34000", "NM": "35000", "NY": "36000", "NC": "37000", "ND": "38000",
    "OH": "39000", "OK": "40000", "OR": "41000", "PA": "42000", "RI": "44000",
    "SC": "45000", "SD": "46000", "TN": "47000", "TX": "48000", "UT": "49000",
    "VT": "50000", "VA": "51000", "WA": "53000", "WI": "55000", "WY": "56000",
}
AREA2STATE = {v: k for k, v in FIPS.items()}

TITLES = {
    "11": "Agriculture, forestry, fishing and hunting", "21": "Mining, quarrying, oil and gas",
    "22": "Utilities", "23": "Construction", "31-33": "Manufacturing",
    "42": "Wholesale trade", "44-45": "Retail trade",
    "48-49": "Transportation and warehousing", "51": "Information",
    "52": "Finance and insurance", "53": "Real estate and rental and leasing",
    "54": "Professional, scientific, and technical services",
    "55": "Management of companies and enterprises",
    "56": "Administrative and waste services", "61": "Educational services",
    "62": "Health care and social assistance",
    "71": "Arts, entertainment, and recreation",
    "72": "Accommodation and food services", "81": "Other services",
}
EXCLUDE = {"92", "99"}  # government handled via ownership rows; unclassified


def ensure_zip(year):
    path = os.path.join(SCRATCH, f"{year}_annual_singlefile.zip")
    if not os.path.exists(path):
        url = f"https://data.bls.gov/cew/data/files/{year}/csv/{year}_annual_singlefile.zip"
        print(f"downloading {url}", flush=True)
        subprocess.run(["curl", "-s", "--max-time", "600", "-o", path, url], check=True)
    return path


def pull_year(year):
    path = ensure_zip(year)
    z = zipfile.ZipFile(path)
    name = [n for n in z.namelist() if n.endswith(".csv")][0]
    out = []
    with z.open(name) as f:
        r = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8", errors="replace"))
        for row in r:
            if (row["agglvl_code"] == "54" and row["own_code"] == "5"
                    and row["area_fips"] in AREA2STATE
                    and row["industry_code"] not in EXCLUDE
                    and row["disclosure_code"] != "N"):
                emp = row["annual_avg_emplvl"]; pay = row["avg_annual_pay"]
                if emp and pay and int(emp) > 0:
                    out.append({
                        "year": year, "state": AREA2STATE[row["area_fips"]],
                        "industry_code": row["industry_code"],
                        "industry": TITLES.get(row["industry_code"], row["industry_code"]),
                        "emplvl": int(emp), "avg_annual_pay": float(pay),
                    })
    return out


def main():
    os.makedirs(SCRATCH, exist_ok=True)
    rows = []
    for y in YEARS:
        got = pull_year(y)
        print(f"{y}: {len(got)} state-sector rows", flush=True)
        rows.extend(got)

    filt_path = os.path.join(HERE, "whose_wages_qcew_filtered.csv")
    with open(filt_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["year", "state", "industry_code", "industry", "emplvl", "avg_annual_pay"])
        w.writeheader(); w.writerows(rows)

    # --- tiers from 2021 national employment-weighted pay by sector ---
    nat = defaultdict(lambda: [0.0, 0.0])  # industry -> [wages bill, emp]
    for r in rows:
        if r["year"] == 2021:
            nat[r["industry_code"]][0] += r["avg_annual_pay"] * r["emplvl"]
            nat[r["industry_code"]][1] += r["emplvl"]
    natpay = {k: v[0] / v[1] for k, v in nat.items()}
    order = sorted(natpay, key=natpay.get)
    n = len(order)
    tier = {}
    for i, code in enumerate(order):
        tier[code] = "low" if i < n / 3 else ("mid" if i < 2 * n / 3 else "high")
    with open(os.path.join(HERE, "whose_wages_tiers.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["industry_code", "industry", "natl_avg_annual_pay_2021", "tier"])
        for code in order:
            w.writerow([code, TITLES[code], round(natpay[code]), tier[code]])
    print("tiers:", {t: [c for c in order if tier[c] == t] for t in ("low", "mid", "high")})

    # --- frozen groups ---
    groups = {}
    with open(os.path.join(HERE, "prereg_group_assignments.csv")) as f:
        for r in csv.DictReader(f):
            groups[r["State"]] = r["frozen_tercile"]

    # index: (state, industry, year) -> (emp, pay)
    idx = {(r["state"], r["industry_code"], r["year"]): (r["emplvl"], r["avg_annual_pay"]) for r in rows}

    def growth(state, code, y0, y1):
        a = idx.get((state, code, y0)); b = idx.get((state, code, y1))
        if not a or not b:
            return None
        return math.log(b[1] / a[1]), a[0]  # log pay growth, base-year emp weight

    windows = [(2015, 2019, "2015-2019 placebo"), (2019, 2021, "2019-2021"), (2021, 2025, "2021-2025 main")]

    # --- group x tier x window ---
    gt = []
    for gname in ("high", "mid", "low"):
        states = [s for s, g in groups.items() if g == gname]
        for tname in ("low", "mid", "high", "ALL"):
            for (y0, y1, wname) in windows:
                num = den = 0.0; cells = 0
                for s in states:
                    for code in order:
                        if tname != "ALL" and tier[code] != tname:
                            continue
                        g = growth(s, code, y0, y1)
                        if g:
                            num += g[0] * g[1]; den += g[1]; cells += 1
                if den:
                    gt.append({"group": gname, "tier": tname, "window": wname,
                               "wtd_log_growth": round(num / den, 4),
                               "wtd_pct_growth": round(100 * (math.exp(num / den) - 1), 2),
                               "cells": cells})
    with open(os.path.join(HERE, "whose_wages_group_tier.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["group", "tier", "window", "wtd_log_growth", "wtd_pct_growth", "cells"])
        w.writeheader(); w.writerows(gt)

    # --- per industry, high vs low group ---
    bi = []
    for code in order:
        rec = {"industry_code": code, "industry": TITLES[code], "tier": tier[code],
               "natl_pay_2021": round(natpay[code])}
        for gname in ("high", "low"):
            states = [s for s, g in groups.items() if g == gname]
            for (y0, y1, tag) in [(2021, 2025, "main"), (2015, 2019, "plac")]:
                num = den = 0.0
                for s in states:
                    g = growth(s, code, y0, y1)
                    if g:
                        num += g[0] * g[1]; den += g[1]
                rec[f"{gname}_{tag}_pct"] = round(100 * (math.exp(num / den) - 1), 2) if den else None
        rec["diff_main_pp"] = (round(rec["high_main_pct"] - rec["low_main_pct"], 2)
                               if rec.get("high_main_pct") is not None and rec.get("low_main_pct") is not None else None)
        rec["diff_plac_pp"] = (round(rec["high_plac_pct"] - rec["low_plac_pct"], 2)
                               if rec.get("high_plac_pct") is not None and rec.get("low_plac_pct") is not None else None)
        bi.append(rec)
    with open(os.path.join(HERE, "whose_wages_by_industry.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(bi[0].keys())); w.writeheader(); w.writerows(bi)

    # --- summary ---
    def cell(gname, tname, wname):
        for r in gt:
            if r["group"] == gname and r["tier"] == tname and r["window"] == wname:
                return r["wtd_pct_growth"]
        return None
    lines = ["# Whose Wages? -- first pass (auto-generated from QCEW tables)", "",
             "Employment-weighted nominal average-annual-pay growth (%), by frozen state group and 2021 industry wage tier.", ""]
    for wname in ("2021-2025 main", "2019-2021", "2015-2019 placebo"):
        lines.append(f"## Window {wname}")
        lines.append("| group | low tier | mid tier | high tier | low-minus-high (pp) |")
        lines.append("|---|---|---|---|---|")
        for gname in ("high", "mid", "low"):
            lo, mi, hi = cell(gname, "low", wname), cell(gname, "mid", wname), cell(gname, "high", wname)
            spread = round(lo - hi, 2) if lo is not None and hi is not None else None
            lines.append(f"| {gname} | {lo} | {mi} | {hi} | {spread} |")
        lines.append("")
    with open(os.path.join(HERE, "whose_wages_firstpass.md"), "w") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
