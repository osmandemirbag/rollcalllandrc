"""One record, 1945-1980: harmonized deputy-by-vote panel and the same statistics for every era.

Sources: 1945 (5_analysis_1945_60/01_test_1945.py), 1946-60 farm votes (5_analysis_1945_60/04_analyse_1946_60.py),
Millet Meclisi 1961-80 (output/member_votes.csv.gz). The Senate (1961-80) is left out:
its members' parties are not observed.

Harmonized definitions
  contested: the losing side holds at least 5% of votes cast (from the printed tallies)
  government: the deputy's party at the vote holds cabinet posts (1945-50 CHP; 1950-60 DP;
              1961-80 the cabinet's parties, technocratic cabinets coded as in 01_code_votes)
  yes: yes among votes cast (yes, no, abstain); voted: cast any vote

Statistics per era (same estimator throughout)
  government premium: mean over contested roll calls of (yes share of government deputies
      minus yes share of opposition deputies)
  participation gap: same, for taking part, over all roll calls
  farmer effect: farmer minus other deputies within party x roll call (contested; SE by deputy)
  exits: DiD of yes for deputies leaving a party vs those staying, randomization over deputies
     1948 DP -> Millet Partisi (opposition -> opposition), 1955 DP -> Hürriyet (government ->
     opposition), 1967 CHP -> GP (opposition -> opposition), 1970 AP -> DP (government -> opposition)

Output: data/processed/rollcall_1945_1980_long.csv.gz, output/synthesis.json
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".replication_root").exists())
OUT = ROOT / "output"
RNG = np.random.default_rng(1980)
ERAS = [("1945 single party", "1943-03-01", "1946-07-21"),
        ("1946-50 CHP government, DP opposition", "1946-07-21", "1950-05-22"),
        ("1950-60 DP government", "1950-05-22", "1960-05-27"),
        ("1961-65 coalitions", "1961-10-15", "1965-10-10"),
        ("1965-71 AP majority", "1965-10-10", "1971-03-12"),
        ("1971-73 military-supervised cabinets", "1971-03-12", "1973-10-14"),
        ("1973-80 competitive coalitions", "1973-10-14", "1980-09-12")]


def era_of(d):
    for name, a, b in ERAS:
        if pd.Timestamp(a) <= d < pd.Timestamp(b):
            return name
    return None


def contested(yes, no, abstain):
    cast = yes + no.fillna(0) + abstain.fillna(0)
    lose = np.minimum(yes, no.fillna(0) + abstain.fillna(0))
    return (lose / cast) >= 0.05


def load():
    occ = pd.read_csv(ROOT / "data/processed/elites_occupation.csv").drop_duplicates(["id", "year"])
    # 1945
    a = pd.read_csv(OUT / "h1945_deputy_votes.csv")
    idx = pd.read_csv(ROOT / "data/interim/tbmm_1943_60_votes.csv").rename(columns={"doc": "vote_id"}).drop_duplicates("vote_id").set_index("vote_id")
    a = a.assign(era_src="1945", chamber="TBMM", year=1943, name=a.short, province=a.province_old,
                 party_at_vote=np.where(a.party.str.startswith("CHP"), "CHP", "Bağımsız"),
                 policy_type=np.where(a.vote_id == "tbmm07018072_p022", "land_reform",
                                      np.where(a.vote_id.map(idx.title).str.contains("Bütçe|cetvel", na=False), "agency_budget", "other")),
                 contested=a.vote_id.map(contested(idx.yes, idx.no, idx.abstain)))
    a["voted"] = (a.choice != "not_voting").astype(int)
    a["yes"] = (a.choice == "yes").astype(int)
    a["status_note"] = np.where(a.excused, "excused", None)
    a = a.merge(occ[["id", "year", "farmer"]], on=["id", "year"], how="left")
    # 1946-60
    b = pd.read_csv(OUT / "h1950s_member_votes.csv.gz", low_memory=False)
    fv = pd.read_csv(ROOT / "data/interim/tbmm_1946_60_farm_votes.csv").rename(columns={"doc": "vote_id"}).drop_duplicates("vote_id").set_index("vote_id")
    b = b.assign(era_src="1946-60", chamber="TBMM", contested=b.vote_id.map(contested(fv.yes, fv.no, fv.abstain)),
                 status_note=np.where(b.note.fillna("").str.contains(r"^[İIi1lt]\.?$|Bakan|Başkan|vekil|Has", regex=True),
                                      "excused", None))
    # 1961-80 Millet Meclisi
    c = pd.read_csv(OUT / "member_votes.csv.gz", low_memory=False)
    c = c[(c.chamber == "MM") & c.id.notna()]
    v = pd.read_csv(OUT / "votes_coded.csv").set_index("vote_id")
    c = c.assign(era_src="1961-80", contested=c.vote_id.map(contested(v.yes, v.no, v.abstain)),
                 name=c.list_name_raw, province=c.province_old, title=c.vote_id.map(v.title))
    c = c.merge(occ[["id", "year", "farmer"]], on=["id", "year"], how="left")
    cols = ["era_src", "chamber", "vote_id", "date", "title", "policy_type", "contested", "id", "year", "name", "province",
            "party_at_vote", "government", "farmer", "status_note", "choice", "yes", "voted"]
    a["title"] = a.vote_id.map(idx.title).str[-200:]
    a["government"] = a.party_at_vote == "CHP"
    d = pd.concat([x.reindex(columns=cols) for x in (a, b, c)], ignore_index=True)
    d["date"] = pd.to_datetime(d.date, errors="coerce")
    d["era"] = d.date.map(era_of)
    d.loc[d.era_src == "1945", "era"] = "1945 single party"  # some 1945 sittings carry no readable date
    d["farmer"] = d.farmer.fillna(False).astype(bool)
    d["government"] = d.government.fillna(False).astype(bool)
    d["contested"] = d.contested.fillna(False).astype(bool)
    return d


def premium(g, y):
    s = g.groupby(["vote_id", "government"])[y].mean().unstack()
    s = s.dropna()
    return float((s[True] - s[False]).mean()) if len(s) else None, int(len(s))


def farmer_effect(d):
    f = d.dropna(subset=["party_at_vote"]).assign(cell=lambda x: x.vote_id + "|" + x.party_at_vote.astype(str))
    f = f[f.groupby("cell").farmer.transform("std") > 0]
    if f.empty:
        return None, None, 0
    yd = f.yes - f.groupby("cell").yes.transform("mean")
    xd = f.farmer.astype(float) - f.groupby("cell").farmer.transform("mean")
    b = (xd * yd).sum() / (xd ** 2).sum()
    g = (xd * (yd - b * xd)).groupby(f.id).sum()
    return float(b), float(np.sqrt((g ** 2).sum()) / (xd ** 2).sum()), int(f[f.farmer].id.nunique())


def era_table(d):
    rows = []
    for name, _, _ in ERAS:
        e = d[(d.era == name) & d.status_note.isna()]
        if e.empty:
            continue
        cast = e[e.choice.isin(["yes", "no", "abstain"])]
        con = cast[cast.contested]
        gp, ngp = premium(con, "yes") if con.government.nunique() == 2 else (None, 0)
        pp, _ = premium(e, "voted") if e.government.nunique() == 2 else (None, 0)
        fe, fse, fn = farmer_effect(con)
        votes = e.groupby("vote_id").agg(cont=("contested", "first"))
        rows.append({"era": name, "roll_calls": int(e.vote_id.nunique()), "deputy_votes": int(len(e)),
                     "deputies": int(e.id.nunique()), "contested_share": float(votes.cont.mean()),
                     "participation": float(e.voted.mean()), "no_share_of_cast": float((cast.choice != "yes").mean()),
                     "gov_premium_yes": gp, "gov_premium_votes": ngp, "gov_premium_participation": pp,
                     "gov_yes": float(con[con.government].yes.mean()) if len(con) else None,
                     "opp_yes": float(con[~con.government].yes.mean()) if (len(con) and (~con.government).any()) else None,
                     "farmer_effect": fe, "farmer_se": fse, "farmer_deputies": fn,
                     "farmer_share": float(e.drop_duplicates("id").farmer.mean())})
    return rows


def did_fast(d, treated, split, R=5000):
    """DiD of yes (treated minus control, post minus pre) with randomization over deputies."""
    d = d.assign(post=d.date >= pd.Timestamp(split))
    p = d.groupby(["id", "post"]).yes.agg(["sum", "count"]).unstack(fill_value=0)
    ids = p.index.values
    t = np.isin(ids, list(treated))
    S1, N1, S0, N0 = p[("sum", True)].values, p[("count", True)].values, p[("sum", False)].values, p[("count", False)].values

    def est(tt):
        return (S1[tt].sum() / N1[tt].sum() - S0[tt].sum() / N0[tt].sum()) - \
               (S1[~tt].sum() / N1[~tt].sum() - S0[~tt].sum() / N0[~tt].sum())
    e = est(t)
    perm = np.array([est(RNG.permutation(t)) for _ in range(R)])
    return {"estimate": float(e), "ri_p": float((np.abs(perm) >= abs(e) - 1e-12).mean()), "treated": int(t.sum()),
            "control": int((~t).sum()), "pre_treated": float(S0[t].sum() / N0[t].sum()),
            "post_treated": float(S1[t].sum() / N1[t].sum()), "pre_control": float(S0[~t].sum() / N0[~t].sum()),
            "post_control": float(S1[~t].sum() / N1[~t].sum())}


def exits(d):
    out = {}
    b = pd.read_csv(OUT / "h1950s_member_votes.csv.gz", low_memory=False)
    b["date"] = pd.to_datetime(b.date)
    cast = b[b.choice.isin(["yes", "no", "abstain"])]
    c46 = cast[(cast.year == 1946) & (cast.party_first == "DP")]
    mp = set(c46[c46.party.str.contains("MP|MDG", na=False)].id)
    stay = set(c46[c46.party.str.strip() == "DP"].id)
    c46 = c46[c46.id.isin(mp | stay)]
    con = c46[c46.contested]
    out["1948 DP -> Millet Partisi"] = {"from": "opposition", "to": "opposition", "votes": "contested agrarian",
                                       **did_fast(con, mp, "1948-01-01")}
    out["1948 DP -> Millet Partisi"]["split_july_1948"] = did_fast(con, mp, "1948-07-20")["estimate"]
    c54 = cast[(cast.year == 1954) & (cast.party_first == "DP") & (cast.policy_type == "agency_budget")]
    hp = set(c54[c54.party.str.contains("HP", na=False)].id)
    c54 = c54[c54.id.isin(hp | set(c54[c54.party.str.strip() == "DP"].id))]
    out["1955 DP -> Hürriyet Partisi"] = {"from": "government", "to": "opposition", "votes": "agency budgets",
                                         **did_fast(c54, hp, "1955-10-15")}
    p = json.loads((OUT / "paper.json").read_text())
    gp = p["gp"]
    out["1967 CHP -> Güven Partisi"] = {"from": "opposition", "to": "opposition", "votes": "contested agency budgets",
                                       "estimate": gp["estimate"], "ri_p": gp["ri_p"], "treated": gp["founders"],
                                       "control": gp["stayers"]}
    out["1970 AP -> Demokratik Parti"] = {"from": "government", "to": "opposition", "votes": "agency budgets",
                                         "estimate": p["ap_dp"]["estimate"], "ri_p": p["ap_dp"]["ri_p"],
                                         "treated": p["ap_dp"]["treated"], "control": p["ap_dp"]["controls"]}
    return out


def main():
    d = load()
    d.to_csv(ROOT / "data/processed/rollcall_1945_1980_long.csv.gz", index=False)
    res = {"rows": int(len(d)), "roll_calls": int(d.vote_id.nunique()), "deputies": int(d.id.nunique()),
           "by_source": d.groupby("era_src").agg(roll_calls=("vote_id", "nunique"), rows=("vote_id", "size")).reset_index().to_dict("records"),
           "eras": era_table(d), "exits": exits(d)}
    # Benefits and land: near-unanimity by era (share of roll calls contested), by policy type.
    pt = d.drop_duplicates("vote_id").assign(pt=lambda x: x.policy_type.replace(
        {"land_reform_budget": "land_reform", "land_tax": "land_reform", "debt_relief": "farm_benefit", "agri_credit": "farm_benefit"}))
    res["contested_by_type_era"] = (pt[pt.pt.isin(["land_reform", "farm_benefit", "agency_budget", "commodity_board", "forest_law",
                                                     "infrastructure"])]
                                    .groupby(["era", "pt"]).contested.agg(["mean", "size"]).round(3).reset_index().to_dict("records"))
    (OUT / "synthesis.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str))
    print(json.dumps({k: v for k, v in res.items() if k != "contested_by_type_era"}, ensure_ascii=False, indent=1, default=str)[:9000])



KEY_LAND = {"tbmm07018072_p022": "1945 Land distribution law (final)",
            "tbmm08025070_p086": "1950 Amendment diluting the 1945 law",
            "tbmm08025066_p040": "1950 Titling (Tapulama) law",
            "tbmm10007078_p139": "1955 Land law amendment",
            "mm01030096_p062": "1964 Land tax, article 9",
            "mm01035055_p050": "1965 Motion: land reform bill to a joint committee",
            "mm02006092_p086": "1966 Titling law amendment",
            "mm03007115_p075": "1970 Property (land) tax law",
            "mm03026116_p050": "1972 Property tax amendment",
            "mm03038125_p153": "1973 Land and Agrarian Reform Law (final)"}


def land_votes(d):
    """Per key land vote and party: share present, and yes/no among those present, against the
    party's own participation on the other agrarian roll calls of the same era."""
    rows = []
    base = d[d.status_note.isna()].groupby(["era", "party_at_vote"]).voted.mean()
    for vid, label in KEY_LAND.items():
        x = d[(d.vote_id == vid) & d.status_note.isna()]
        if x.empty:
            continue
        era = x.era.iloc[0]
        for party, g in x.groupby("party_at_vote"):
            if len(g) < 8:
                continue
            present = g[g.voted == 1]
            rows.append({"vote": label, "vote_id": vid, "era": era, "party": party, "government": bool(g.government.iloc[0]),
                         "members_listed": int(len(g)), "present": float(g.voted.mean()),
                         "era_baseline_present": float(base.get((era, party), np.nan)),
                         "yes_of_present": float((present.choice == "yes").mean()) if len(present) else None,
                         "no_of_present": float((present.choice == "no").mean()) if len(present) else None})
    return rows


def main2():
    d = pd.read_csv(ROOT / "data/processed/rollcall_1945_1980_long.csv.gz", low_memory=False, parse_dates=["date"])
    res = json.loads((OUT / "synthesis.json").read_text())
    res["land_votes"] = land_votes(d)
    (OUT / "synthesis.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str))
    print(pd.DataFrame(res["land_votes"]).round(2).to_string())


if __name__ == "__main__":
    main()
    main2()
