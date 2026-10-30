"""Do deputies respond to harvest failures in their province? Harvest-shock design, 1961-80.

Shock: area-weighted mean over crops of log(observed yield / province-crop fitted trend) in the
most recent completed harvest before the vote (harvest year = vote year if the vote is in Aug-Dec,
else the year before). Negative = bad harvest. Source: data/raw/agri (province panel, 1930-2024).

Estimand: within-deputy effect of a one-SD worse harvest in the deputy's province on turnout and on
the probability of voting yes, on farm-benefit roll calls, compared with the same deputy's
behaviour on other roll calls (deputy and roll-call fixed effects; SEs clustered by province).
"""
import sys
from importlib import import_module
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadr
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from common import province_key  # noqa: E402

OUT = ROOT / "analysis" / "output"
TO_AGRI = {"gaziantep": "antep", "kahramanmaras": "maras", "mersin": "icel", "sanliurfa": "urfa",
           "afyonkarahisar": "afyon", "artvin": "coruh"}


def shocks():
    p = pyreadr.read_r(ROOT / "data/raw/agri/panel_p1.rds")[None]
    t = pyreadr.read_r(ROOT / "data/raw/agri/prov_trend_fitted.rds")[None].rename(columns={"yield": "trend"})
    d = p.merge(t, on=["crop", "province", "year"]).dropna(subset=["yield", "trend", "area"])
    d = d[(d["yield"] > 0) & (d.trend > 0)]
    d["dev"] = np.log(d["yield"] / d.trend)
    s = d.groupby(["province", "year"]).apply(lambda g: np.average(g.dev, weights=g.area)).rename("shock").reset_index()
    s["shock_z"] = (s.shock - s.shock.mean()) / s.shock.std()
    return s


def demean(d, cols, a, b, it=60):
    for c in cols:
        r = d[c].astype(float).to_numpy().copy()
        for _ in range(it):
            r = r - d.assign(r=r).groupby(a).r.transform("mean").to_numpy()
            r = r - d.assign(r=r).groupby(b).r.transform("mean").to_numpy()
        d[c + "_dm"] = r
    return d


def est(d, y, x):
    d = demean(d[[y, x, "person_key", "vote_id", "pk"]].dropna().copy(), [y, x], "person_key", "vote_id")
    f = sm.OLS(d[y + "_dm"], d[[x + "_dm"]]).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d.pk)[0]})
    return {"estimate": float(f.params.iloc[0]), "se": float(f.bse.iloc[0]), "n": len(d),
            "provinces": int(d.pk.nunique())}


def main():
    s = shocks()
    m = pd.read_csv(OUT / "member_votes.csv.gz", low_memory=False)
    m = m[(m.chamber == "MM") & m.party_at_vote.notna() & ~m.status_note.fillna("").ne("")
          & ~m.row_status.astype(str).str.startswith("derived")].copy()
    m["date"] = pd.to_datetime(m.date)
    m = m[m.date.notna()]
    m["pk"] = m.province_old.map(lambda x: TO_AGRI.get(province_key(x), province_key(x)) if isinstance(x, str) else None)
    m["hyear"] = np.where(m.date.dt.month >= 8, m.date.dt.year, m.date.dt.year - 1)
    m = m.merge(s, left_on=["pk", "hyear"], right_on=["province", "year"], how="left")
    print("member-votes with a shock:", m.shock_z.notna().mean().round(3), "provinces matched:", m[m.shock_z.notna()].pk.nunique())
    m["bad"] = -m.shock_z  # +1 = one SD worse harvest
    res = {}
    for grp, pts in [("farm benefits", ["farm_benefit"]), ("land (reform, tax, titling)", ["land_reform", "land_reform_budget", "land_tax", "land_titling"]),
                     ("agency budgets (placebo)", ["agency_budget"]), ("final accounts (placebo)", ["final_accounts"])]:
        d = m[m.policy_type.isin(pts)]
        d["x"] = d.bad
        res[(grp, "turnout")] = est(d, "voted", "x")
        c = d[d.choice.isin(["yes", "no", "abstain"])]
        res[(grp, "yes")] = est(c, "yes", "x")
    # interaction: farm-benefit votes vs all other votes, within deputy and vote
    m["x"] = m.bad * m.policy_type.eq("farm_benefit")
    m2 = m.dropna(subset=["bad"])
    res[("farm benefits minus other votes", "turnout")] = est(m2, "voted", "x")
    out = pd.DataFrame(res).T
    out["t"] = out.estimate / out.se
    print(out.round(3).to_string())
    out.to_csv(OUT / "h1_harvest_shocks.csv")
    s.to_csv(OUT / "province_harvest_shocks.csv", index=False)


if __name__ == "__main__":
    main()
