"""Data quality audit, inductive exploration, and within-unit designs.

Writes output/q*.csv (quality), x*.csv (exploration), d*.csv (designs) and prints them.
The hand audit of 75 sampled links is described in the online supplement, Part A.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".replication_root").exists())
OUT = ROOT / "output"
PARTIES = ["AP", "CHP", "DP", "MSP", "CGP", "MHP", "YTP", "CKMP", "MP", "TİP"]


def show(name, t):
    t.to_csv(OUT / f"{name}.csv")
    print(f"\n===== {name}\n{t.round(3).to_string()}")


def twoway(d, y, x, a="person_key", b="vote_id", it=60):
    """OLS of y on x after removing person and vote means (alternating projections)."""
    d = d[[y, x, a, b]].dropna().copy()
    for col in (y, x):
        r = d[col].astype(float).to_numpy().copy()
        for _ in range(it):
            r = r - d.assign(r=r).groupby(a).r.transform("mean").to_numpy()
            r = r - d.assign(r=r).groupby(b).r.transform("mean").to_numpy()
        d[col + "_dm"] = r
    changed = int(d.groupby(a)[x].nunique().gt(1).sum())
    if changed == 0:
        return np.nan, np.nan, len(d), 0
    f = sm.OLS(d[y + "_dm"], d[[x + "_dm"]]).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d[a])[0]})
    return f.params.iloc[0], f.bse.iloc[0], len(d), changed


def main():
    q = pd.read_csv(ROOT / "data/processed/votes_quality.csv")
    v = pd.read_csv(OUT / "votes_coded.csv")
    m = pd.read_csv(OUT / "member_votes.csv.gz", low_memory=False)
    m["gov"] = m.government.map({True: 1.0, False: 0.0, "True": 1.0, "False": 0.0})
    m["excused"] = m.status_note.fillna("").ne("")
    mm = m[(m.chamber == "MM") & m.party_at_vote.notna()].copy()
    mm["party"] = mm.party_at_vote.where(mm.party_at_vote.isin(PARTIES), "OTHER")

    # ---------------- quality
    q["period"] = pd.cut(pd.to_datetime(q.date).dt.year, [1960, 1965, 1969, 1973, 1977, 1981],
                         labels=["1961-65", "1965-69", "1969-73", "1973-77", "1977-80"])
    show("q1_count_accuracy", q.groupby(["chamber", "period"], observed=True).names_off_vs_tally.agg(
        votes="size", exact=lambda s: (s == 0).mean(), within_2=lambda s: (s <= 2).mean(),
        median_off=lambda s: s.median()))
    full = pd.read_csv(ROOT / "data/processed/rollcall_long.csv.gz", low_memory=False,
                       usecols=["vote_id", "chamber", "match_method", "row_status", "person_key"])
    show("q2_link_methods", full.groupby("chamber").match_method.value_counts(normalize=True).unstack(0).fillna(0))
    show("q3_row_status", full.row_status.value_counts().to_frame("rows"))
    dup = full[full.person_key.notna()].duplicated(["vote_id", "person_key"]).sum()
    show("q4_integrity", pd.Series({"person listed twice in a vote": dup,
                                    "rows without a person": int(full.person_key.isna().sum()),
                                    "member-votes with approximated party (switchers), Assembly":
                                        round(mm.switcher.astype(bool).mean(), 3)}).to_frame("value"))

    # ---------------- exploration
    cast = mm[mm.choice.isin(["yes", "no"])]
    rows = []
    for term, g in cast.groupby("mm_term"):
        share = g.groupby("vote_id").yes.mean()
        keep = share[(share > 0.05) & (share < 0.95)].index
        X = g[g.vote_id.isin(keep)].pivot_table(index="person_key", columns="vote_id", values="yes", aggfunc="first")
        X = X[X.notna().sum(1) >= 5]
        if X.shape[1] < 3:
            continue
        U, S, _ = np.linalg.svd(X.sub(X.mean()).fillna(0).to_numpy(), full_matrices=False)
        ev = S ** 2 / (S ** 2).sum()
        info = g.drop_duplicates("person_key").set_index("person_key").reindex(X.index)
        w = pd.DataFrame({"d1": U[:, 0] * S[0], "d2": U[:, 1] * S[1], "party": info.party_at_vote.to_numpy(),
                          "gov": g.groupby("person_key").gov.mean().reindex(X.index).to_numpy(),
                          "rural": info.rural_population_pct.to_numpy(),
                          "east": info.east_se.astype(float).to_numpy()})
        w["d2_within"] = w.d2 - w.groupby("party").d2.transform("mean")
        rows.append({"term": term, "contested_votes": X.shape[1], "members": X.shape[0],
                     "variance_dim1": ev[0], "variance_dim2": ev[1],
                     "|corr dim1, time in government|": abs(w[["d1", "gov"]].corr().iloc[0, 1]),
                     "corr dim2 (within party), rural": w[["d2_within", "rural"]].corr().iloc[0, 1],
                     "corr dim2 (within party), East/SE": w[["d2_within", "east"]].corr().iloc[0, 1]})
    show("x1_scaling", pd.DataFrame(rows).set_index("term"))

    v["year"] = v.date.str[:4]
    t = v[v.chamber == "MM"].groupby("year").agg(
        roll_calls=("vote_id", "size"), turnout=("participation", "mean"),
        failed_quorum=("outcome_class", lambda s: (s == "no quorum / majority not reached").mean()))
    pl = []
    for vid, x in cast[cast.party.isin(["AP", "CHP"])].groupby("vote_id"):
        s = x.groupby("party").yes.mean()
        if len(s) == 2:
            pl.append((vid, (s["AP"] - 0.5) * (s["CHP"] - 0.5) < 0))
    pl = pd.DataFrame(pl, columns=["vote_id", "party_line"]).merge(v[["vote_id", "year"]])
    t["AP_vs_CHP_party_line"] = pl.groupby("year").party_line.mean()
    show("x2_trends_assembly", t)

    nv = mm[mm.choice == "not_voting"]
    show("x3_absence_types", pd.Series(np.select(
        [nv.row_status.str.startswith("derived"), nv.excused], ["derived (list not printed)", "excused (office or leave)"],
        "plain absence")).value_counts(normalize=True).to_frame("share"))
    show("x4_inventory", pd.crosstab(v.policy_type, v.stage, margins=True))

    # ---------------- designs
    rows = []
    for lab, pts, dv in [("land reform budgets: yes", ["land_reform_budget"], "yes"),
                         ("all agency budgets: yes", ["agency_budget", "land_reform_budget"], "yes"),
                         ("land tax: yes", ["land_tax"], "yes"),
                         ("farm benefits: yes", ["farm_benefit"], "yes"),
                         ("land reform budgets: turnout", ["land_reform_budget"], "voted"),
                         ("agency budgets: turnout", ["agency_budget", "land_reform_budget"], "voted"),
                         ("farm benefits: turnout", ["farm_benefit"], "voted")]:
        d = mm[mm.policy_type.isin(pts) & ~mm.technocratic.astype(bool) & ~mm.excused]
        if dv == "yes":
            d = d[d.choice.isin(["yes", "no", "abstain"])]
        b, se, n, ch = twoway(d, dv, "gov")
        rows.append({"outcome": lab, "effect_of_government": b, "se": se, "n": n, "members_whose_status_changed": ch})
    show("d1_within_deputy_government_effect", pd.DataFrame(rows).set_index("outcome"))

    rows = []
    for lab, d in [("all", mm), ("excluding excused", mm[~mm.excused])]:
        d = d[(d.policy_type == "farm_benefit") & (d.outcome_class == "no quorum / majority not reached")]
        f = smf.ols("voted ~ C(vote_id) + gov + C(party)", d).fit(
            cov_type="cluster", cov_kwds={"groups": pd.factorize(d.person_key)[0]})
        rows.append({"sample": lab, "effect_of_government_on_turnout": f.params["gov"], "p": f.pvalues["gov"], "n": len(d)})
    show("d2_quorum_gatekeeping", pd.DataFrame(rows).set_index("sample"))

    rows = []
    for _, r in v[(v.policy_type == "land_reform_budget") & (v.chamber == "MM")].sort_values("date").iterrows():
        x = mm[(mm.vote_id == r.vote_id) & (mm.party == "MSP")]
        rows.append({"date": r.date[:10], "cabinet": r.cabinet, "MSP_in_cabinet": "MSP" in str(r.gov_parties),
                     "yes": (x.choice == "yes").sum(), "no": (x.choice == "no").sum(), "absent": int((x.voted == 0).sum())})
    show("d3_msp_partner_switch", pd.DataFrame(rows).set_index("date"))

    t70 = mm[mm.vote_id == "mm03007115_p075"].set_index("person_key")
    t72 = mm[mm.vote_id == "mm03026116_p050"].set_index("person_key")
    base = t70[t70.party == "AP"]
    j = pd.DataFrame({"y70": base.choice, "y72": t72.choice.reindex(base.index),
                      "party_1972": t72.party.reindex(base.index)}).dropna()
    j = j[j.party_1972.isin(["AP", "DP"])]
    rows = []
    for p, x in j.groupby("party_1972"):
        rows.append({"group": f"AP in 1970 -> {p} in 1972", "n": len(x),
                     "1970 yes": (x.y70 == "yes").mean(), "1970 no": (x.y70 == "no").mean(),
                     "1972 yes": (x.y72 == "yes").mean(), "1972 no": (x.y72 == "no").mean()})
    show("d4_ap_dp_split_land_tax", pd.DataFrame(rows).set_index("group"))


if __name__ == "__main__":
    main()
