"""Further within-unit and timing designs on the Assembly roll calls.

Writes analysis/output/e*.csv. Sample: Assembly member-votes with a known party, excluding
excused absences (minister, on leave, presiding officer) and derived not-voting rows.
"""
import sys
from importlib import import_module
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
OUT = ROOT / "analysis" / "output"
twoway = import_module("04_quality_and_designs").twoway
PARTIES = ["AP", "CHP", "DP", "MSP", "CGP", "MHP", "YTP", "CKMP", "MP", "TİP"]
TERM_START = {"d01": "1961-10-25", "d02": "1965-10-10", "d03": "1969-10-12", "d04": "1973-10-14", "d05": "1977-06-05"}
ELECTIONS = pd.to_datetime(["1965-10-10", "1969-10-12", "1973-10-14", "1977-06-05", "1981-10-01"])
TEA = ["RİZE", "TRABZON", "ARTVİN"]
TOBACCO_CORE = ["İZMİR", "MANİSA", "SAMSUN", "DENİZLİ", "AYDIN"]  # largest producers
TOBACCO_BROAD = TOBACCO_CORE + ["MUĞLA", "BALIKESİR", "ADIYAMAN", "MALATYA", "BİTLİS", "MUŞ", "TOKAT",
                                "AMASYA", "HATAY", "BURSA", "SAKARYA", "KOCAELİ", "TRABZON"]


def show(name, t):
    t.to_csv(OUT / f"{name}.csv")
    print(f"\n===== {name}\n{t.round(3).to_string()}")


def fe(d, y, x, label):
    b, se, n, ch = twoway(d, y, x)
    return {"design": label, "estimate": b, "se": se, "t": b / se if se else np.nan, "n": n,
            "units_with_variation": ch}


def main():
    v = pd.read_csv(OUT / "votes_coded.csv")
    m = pd.read_csv(OUT / "member_votes.csv.gz", low_memory=False)
    e = pd.read_csv(ROOT / "data/raw/The_Turkish_Political_Elites_Dataset.csv", sep="\t", low_memory=False)
    m["date"] = pd.to_datetime(m.date)
    m["excused"] = m.status_note.fillna("").ne("")
    mm = m[(m.chamber == "MM") & m.party_at_vote.notna() & m.date.notna() & ~m.excused
           & ~m.row_status.astype(str).str.startswith("derived")].copy()
    mm["party"] = mm.party_at_vote.where(mm.party_at_vote.isin(PARTIES), "OTHER")
    mm = mm.merge(e[["ap_v", "chp_v", "switchedparties"]], left_on="elite_row", right_index=True, how="left")
    contested = set(v[~v.lopsided].vote_id)
    rows = []

    # 1. leaving AP for DP (Dec 1970): same deputies, contested agency budgets, vs AP stayers
    d = mm[(mm.mm_term == "d03") & mm.policy_type.isin(["agency_budget", "land_reform_budget"])
           & mm.choice.isin(["yes", "no", "abstain"]) & mm.vote_id.isin(contested)].copy()
    first = d.groupby("person_key").party.first()
    last = d.groupby("person_key").party.last()
    grp = pd.Series(np.select([(first == "AP") & (last == "DP"), (first == "AP") & (last == "AP")],
                              ["switcher", "stayer"], "other"), index=first.index)
    d["grp"] = d.person_key.map(grp)
    d = d[d.grp != "other"]
    d["post"] = d.date >= "1970-12-18"
    d["x"] = ((d.grp == "switcher") & d.post).astype(float)
    rows.append(fe(d, "yes", "x", "leaving AP for DP -> yes on contested agency budgets"))
    show("e1_ap_dp_budget_means", d.groupby(["grp", "post"]).agg(yes=("yes", "mean"), member_votes=("yes", "size"),
                                                                 deputies=("person_key", "nunique")))

    # 2. concentrated benefits: crop-province deputies on their crop's law (turnout)
    for crop, provs, term, word in [("tea", TEA, "d03", "Çay"), ("tobacco, core 5 provinces", TOBACCO_CORE, "d02", "Tütün"),
                                     ("tobacco, broad 18 provinces", TOBACCO_BROAD, "d02", "Tütün")]:
        votes = set(v[(v.chamber == "MM") & v.title.str.contains(word, na=False)].vote_id)
        d = mm[mm.mm_term == term].copy()
        d["x"] = (d.province_old.isin(provs) & d.vote_id.isin(votes)).astype(float)
        r = fe(d, "voted", "x", f"{crop} provinces x {crop.split(',')[0]} votes -> turnout")
        r["units_with_variation"] = d[d.province_old.isin(provs)].person_key.nunique()
        rows.append(r)

    # 3. electoral pressure: close-province deputies in the 9 months before an election
    d = mm.dropna(subset=["ap_v", "chp_v"]).copy()
    d["margin"] = (d.ap_v - d.chp_v).abs()
    d["close"] = d.margin < d.groupby("mm_term").margin.transform("median")
    d["months_to_el"] = d.date.map(lambda t: (min(x for x in ELECTIONS if x > t) - t).days / 30.4)
    d["x"] = (d.close & (d.months_to_el <= 9)).astype(float)
    rows.append(fe(d, "voted", "x", "close-province deputy x 9 months before election -> turnout"))
    show("e2_effects", pd.DataFrame(rows).set_index("design"))

    # 4. dissent in the first year predicts leaving the party later
    cast = mm[mm.choice.isin(["yes", "no"])].copy()
    maj = cast.groupby(["vote_id", "party"]).yes.transform("mean")
    cast["defect"] = ((cast.yes == 1) & (maj < 0.5)) | ((cast.yes == 0) & (maj > 0.5))
    g = []
    for term, start in TERM_START.items():
        w = cast[(cast.mm_term == term) & (cast.date < pd.Timestamp(start) + pd.Timedelta(days=365))
                 & (cast.party != "OTHER")]
        x = w.groupby("person_key").agg(defections=("defect", "sum"), votes=("defect", "size"), party=("party", "first"),
                                        switched=("switchedparties", "first"))
        g.append(x[x.votes >= 5].assign(term=term))
    g = pd.concat(g)
    g["any_defection"] = (g.defections > 0).astype(float)
    f = smf.ols("switched ~ any_defection + C(term):C(party)", g).fit(cov_type="HC1")
    show("e3_dissent_predicts_exit", pd.DataFrame({
        "later switched, never defected": [g[g.any_defection == 0].switched.mean()],
        "later switched, defected at least once": [g[g.any_defection == 1].switched.mean()],
        "adjusted difference (term x party FE)": [f.params["any_defection"]], "p": [f.pvalues["any_defection"]],
        "deputies": [len(g)], "defectors": [int(g.any_defection.sum())]}))

    # 5. the 1971 memorandum: AP-CHP distance by period, same parliament (1969-73)
    c = mm[(mm.mm_term == "d03") & mm.choice.isin(["yes", "no"]) & mm.party.isin(["AP", "CHP"])]
    s = c.groupby(["vote_id", "party"]).yes.mean().unstack().dropna()
    t = v.set_index("vote_id").loc[s.index].assign(gap=(s.AP - s.CHP).abs())
    t["period"] = np.select([t.date < "1971-03-12", t.date < "1972-05-01"],
                            ["1. Demirel (Oct 1969 - Mar 1971)", "2. Erim I-II (Mar 1971 - Apr 1972)"],
                            "3. after Ecevit leads CHP (May 1972 - Oct 1973)")
    f = smf.ols('gap ~ C(period) + C(policy_type)', t).fit(cov_type="HC1")
    tab = t.groupby("period").agg(votes=("gap", "size"), mean_AP_CHP_gap=("gap", "mean"))
    tab["vs period 1, policy-type adjusted"] = [0.0] + list(f.params.filter(like="period").to_numpy())
    tab["p"] = [np.nan] + list(f.pvalues.filter(like="period").to_numpy())
    show("e4_memorandum_gap", tab)
    show("e4_memorandum_by_type", t.pivot_table(index="policy_type", columns="period", values="gap", aggfunc="mean"))


if __name__ == "__main__":
    main()
