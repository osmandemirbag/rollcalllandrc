"""Test general and Turkey-specific theories of agrarian politics on the coded roll calls.

Reads output/{votes_coded.csv, member_votes.csv.gz}; writes output/*.csv and
figures, and prints descriptive tables.

Estimation: linear probability models with roll-call fixed effects and standard errors
clustered by member (Assembly only: the elites data, and so party, covers deputies).
"""
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

OUT = next(p for p in Path(__file__).resolve().parents if (p / ".replication_root").exists()) / "output"
GROUPS = {
    "land reform (law, motion)": ["land_reform"],
    "land reform agency budgets": ["land_reform_budget"],
    "land tax": ["land_tax"],
    "land titling / settlement / forest land": ["land_titling"],
    "farm subsidies & benefits": ["farm_benefit"],
    "agency budgets (baseline)": ["agency_budget"],
    "final accounts (baseline)": ["final_accounts"],
}
MAJOR = ["AP", "CHP", "DP", "MSP", "CGP", "MHP", "YTP", "CKMP", "MP", "TİP"]


def group_of(pt):
    return next((g for g, pts in GROUPS.items() if pt in pts), None)


def lpm(df, formula, cluster="person_key"):
    used = [c for c in df.columns if re_word(c).search(formula)]
    d = df.dropna(subset=used)
    fit = smf.ols(formula, data=d).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d[cluster])[0]})
    return fit, len(d)


def re_word(name):
    import re
    return re.compile(rf"(?<![\w]){re.escape(name)}(?![\w])")


def coef_row(fit, term):
    if term not in fit.params:
        return (np.nan, np.nan)
    return fit.params[term], fit.pvalues[term]


def stars(p):
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""


def main():
    v = pd.read_csv(OUT / "votes_coded.csv")
    m = pd.read_csv(OUT / "member_votes.csv.gz", low_memory=False)
    v["group"] = v.policy_type.map(group_of)
    m["group"] = m.policy_type.map(group_of)
    m = m[m.group.notna()]
    mm = m[(m.chamber == "MM") & m.party_at_vote.notna()].copy()
    mm["government"] = mm.government.astype(float)
    mm["east_se"] = mm.east_se.astype(float)
    mm["agri_degree"] = mm.agri_degree.astype(float)
    mm["party"] = np.where(mm.party_at_vote.isin(MAJOR), mm.party_at_vote, "OTHER")
    mm["cast"] = mm.choice.isin(["yes", "no", "abstain"])
    results = {}

    # ---- 1. typology: how contested is each kind of vote? ------------------------------
    t1 = v[v.group.notna()].groupby("group").agg(
        votes=("vote_id", "size"), assembly=("chamber", lambda s: (s == "MM").sum()),
        senate=("chamber", lambda s: (s == "CS").sum()),
        no_quorum=("outcome_class", lambda s: (s == "no quorum / majority not reached").mean()),
        participation=("participation", "mean"), yes_share_of_cast=("yes_share_of_cast", "mean"),
        lopsided=("lopsided", "mean")).reindex(GROUPS)
    noshare = m[m.cast | (m.choice == "abstain")] if "cast" in m else None
    cast = m[m.choice.isin(["yes", "no", "abstain"])]
    t1["no_votes_share"] = cast.groupby("group").apply(lambda g: (g.choice == "no").mean()).reindex(GROUPS)
    results["t1_typology"] = t1

    # ---- 2. government vs party: what explains a yes? -----------------------------------
    rows = []
    for g in GROUPS:
        d = mm[(mm.group == g) & mm.cast]
        contested = v[(v.group == g) & ~v.lopsided & (v.chamber == "MM")].vote_id
        d = d[d.vote_id.isin(contested)]
        if d.vote_id.nunique() < 1 or len(d) < 100:
            rows.append({"group": g, "contested_votes": d.vote_id.nunique()})
            continue
        f0, n = lpm(d, "yes ~ C(vote_id)")
        fg, _ = lpm(d, "yes ~ C(vote_id) + government")
        fp, _ = lpm(d, "yes ~ C(vote_id) + C(party)")
        fgp, _ = lpm(d, "yes ~ C(vote_id) + government + C(party)")
        b, p = coef_row(fgp, "government")
        rows.append({"group": g, "contested_votes": d.vote_id.nunique(), "n": n,
                     "R2_votes_only": f0.rsquared, "R2_+government": fg.rsquared, "R2_+party": fp.rsquared,
                     "R2_+both": fgp.rsquared, "gov_effect_within_party": b, "p": p})
    results["t2_gov_vs_party"] = pd.DataFrame(rows).set_index("group")

    # ---- 3. party flips: AP and CHP yes-rate in government vs opposition ----------------
    rows = []
    for g in GROUPS:
        d = mm[(mm.group == g) & mm.cast & mm.party.isin(["AP", "CHP"])]
        d = d[~d.vote_id.isin(v[v.technocratic].vote_id)]
        for p in ["AP", "CHP"]:
            for gov in [1.0, 0.0]:
                x = d[(d.party == p) & (d.government == gov)]
                rows.append({"group": g, "party": p, "in_government": bool(gov),
                             "yes_rate": x.yes.mean() if len(x) else np.nan, "votes": x.vote_id.nunique()})
    results["t3_flips"] = pd.DataFrame(rows).pivot_table(index="group", columns=["party", "in_government"],
                                                         values="yes_rate").reindex(GROUPS)

    # ---- 4. cohesion: Rice index by party ---------------------------------------------------
    def rice(x):
        y, n = (x.choice == "yes").sum(), (x.choice == "no").sum()
        return abs(y - n) / (y + n) if y + n >= 5 else np.nan
    c = mm[mm.cast].groupby(["group", "vote_id", "party"]).apply(rice).rename("rice").reset_index()
    results["t4_cohesion"] = c[c.party.isin(["AP", "CHP", "DP", "MSP"])].pivot_table(
        index="group", columns="party", values="rice").reindex(GROUPS)
    # party-line votes: majorities of AP and CHP on opposite sides
    pl = []
    for vid, x in mm[mm.cast & mm.party.isin(["AP", "CHP"])].groupby("vote_id"):
        s = x.groupby("party").yes.mean()
        if len(s) == 2:
            pl.append((vid, (s["AP"] - 0.5) * (s["CHP"] - 0.5) < 0))
    pl = pd.DataFrame(pl, columns=["vote_id", "party_line"]).merge(v[["vote_id", "group"]])
    results["t4_party_line"] = pl.groupby("group").party_line.agg(["mean", "size"]).reindex(GROUPS)

    # ---- 5. participation as strategy (quorum control) --------------------------------------
    rows = []
    for g in GROUPS:
        d = mm[mm.group == g]
        if d.vote_id.nunique() < 2:
            continue
        f, n = lpm(d, "voted ~ C(vote_id) + government + C(party)")
        b, p = coef_row(f, "government")
        fq = d[d.outcome_class == "no quorum / majority not reached"]
        bq, pq = (np.nan, np.nan)
        if fq.vote_id.nunique() >= 2:
            f2, _ = lpm(fq, "voted ~ C(vote_id) + government + C(party)")
            bq, pq = coef_row(f2, "government")
        rows.append({"group": g, "n": n, "gov_effect_on_turnout": b, "p": p,
                     "gov_effect_on_quorum_failures": bq, "p_q": pq,
                     "turnout_gov": d[d.government == 1].voted.mean(),
                     "turnout_opp": d[d.government == 0].voted.mean()})
    results["t5_participation"] = pd.DataFrame(rows).set_index("group")

    # ---- 6. constituency and background, within party (vote + party FE) ---------------------
    rows = []
    covs = "rural_population_pct + east_se + agri_degree + law_education + military_education + local + age"
    for g in GROUPS:
        d = mm[(mm.group == g)]
        for dv, sample in [("yes", d[d.cast]), ("voted", d)]:
            contested = v[(v.group == g) & ~v.lopsided].vote_id if dv == "yes" else sample.vote_id
            s = sample[sample.vote_id.isin(contested)]
            if s.vote_id.nunique() < 1 or len(s) < 200:
                continue
            f, n = lpm(s, f"{dv} ~ C(vote_id) + government + C(party) + {covs}")
            r = {"group": g, "dv": dv, "n": n}
            for term in ["rural_population_pct", "east_se", "agri_degree", "law_education", "military_education", "local"]:
                b, p = coef_row(f, term)
                r[term] = f"{b:+.3f}{stars(p)}"
            rows.append(r)
    results["t6_constituency"] = pd.DataFrame(rows).set_index(["group", "dv"])

    # ---- 7. East/Southeast deputies on the land-reform law votes (landlord hypothesis) ------
    rows = []
    for vid in v[(v.policy_type.isin(["land_reform", "land_tax"])) & (v.chamber == "MM")].vote_id:
        d = mm[mm.vote_id == vid]
        for p in ["AP", "CHP"]:
            for e in [1.0, 0.0]:
                x = d[(d.party == p) & (d.east_se == e)]
                rows.append({"vote_id": vid, "date": v.loc[v.vote_id == vid, "date"].iat[0][:10],
                             "party": p, "east_se": bool(e), "n": len(x),
                             "yes_of_members": (x.choice == "yes").mean() if len(x) else np.nan,
                             "no_of_members": (x.choice == "no").mean() if len(x) else np.nan,
                             "absent": 1 - x.voted.mean() if len(x) else np.nan})
    results["t7_east"] = pd.DataFrame(rows)

    # ---- 8. Senate: military (NUC) and presidential-quota senators vs elected ---------------
    cs = m[(m.chamber == "CS") & m.group.notna()]
    t8 = cs.groupby(["group", "senate_group"]).apply(
        lambda x: pd.Series({"yes_of_cast": (x.choice == "yes").sum() / max(1, x.choice.isin(["yes", "no", "abstain"]).sum()),
                             "turnout": x.voted.mean(), "member_votes": len(x)})).unstack("senate_group")
    results["t8_senate"] = t8

    # ---- 9. farm benefits: who never says no, who shows up ---------------------------------
    fb = mm[mm.group == "farm subsidies & benefits"]
    t9 = fb.groupby(["subtype", "government"]).agg(
        votes=("vote_id", "nunique"), turnout=("voted", "mean"),
        no_share=("choice", lambda s: (s == "no").mean())).unstack("government")
    results["t9_benefits"] = t9

    for k, t in results.items():
        t.to_csv(OUT / f"{k}.csv")
        print(f"\n===== {k}\n{t.round(3).to_string()}")


if __name__ == "__main__":
    main()
