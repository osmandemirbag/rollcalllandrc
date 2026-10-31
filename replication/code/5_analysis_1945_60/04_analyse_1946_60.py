"""Agrarian roll calls 1946-60: matching to deputies, and three designs.

Votes: data/interim/tbmm_1946_60_farm_namelists.csv (02_parse_lists.py farm), used when no list
overflows its tally. Deputies: elites rows of the 1946, 1950, 1954 and 1957 cohorts, matched by
province + fuzzy full name. Occupation from the TBMM Albümü.

Party at vote: the first party of the elites party string, and its last after the split date
of that cohort's party switches (Millet Partisi, 20 July 1948; Hürriyet Partisi dissidents left
the DP group 15 October 1955). Deputies of the 1950 cohort who switched (dates unknown) are
left out of party analyses.

Designs (outcome: yes among those casting a vote, contested roll calls = losing side >= 5%):
  1. 1950 turnover: deputies elected in both 1946 and 1950; DP moved from opposition to
     government, CHP the reverse. DiD of yes, Fisher randomization over deputies' party labels.
  2. 1955 DP -> Hürriyet exit: 1954 DP deputies who left for the HP vs those who stayed;
     DiD around 15 Oct 1955, randomization over deputies.
  3. Farmers: farmer vs other deputies of the same party on the same roll call.
Output: output/h1950s_member_votes.csv.gz, output/h1950s_results.json
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from rapidfuzz import fuzz

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".replication_root").exists())
sys.path.insert(0, str(ROOT / "code" / "lib"))
from common import ELITES_CSV, fold, province_key  # noqa: E402

COHORT = {8: 1946, 9: 1950, 10: 1954, 11: 1957}
SPLIT = {1946: "1948-07-20", 1954: "1955-10-15"}
TURNOVER = pd.Timestamp("1950-05-22")
RNG = np.random.default_rng(1950)
PROV_FIX = {"seyhan": "adana", "siird": "siirt", "tokad": "tokat", "yozgad": "yozgat", "sinob": "sinop",
            "gumusane": "gumushane", "gaziantep": "gaziantep", "gazianteb": "gaziantep", "coruh": "artvin"}


def pk(p):
    k = province_key(p)
    return PROV_FIX.get(k, k)


def vote_date(doc, page):
    """Sitting date from the running header ('B : 103 7.6.1949 O : 3') of the page or its neighbours."""
    for p in (page, page - 1, page + 1, 1, 2):
        t = subprocess.run(["pdftotext", "-f", str(max(p, 1)), "-l", str(max(p, 1)), str(ROOT / f"data/pdfs_tbmm/{doc}.pdf"),
                            "-"], capture_output=True, text=True).stdout
        for m in re.finditer(r"(\d{1,2})\s*[.,]\s*(\d{1,2})\s*[.,]\s*(19[456]\d)", t):
            if 1 <= int(m[2]) <= 12 and 1 <= int(m[1]) <= 31:
                return f"{m[3]}-{int(m[2]):02d}-{int(m[1]):02d}"
    return None


def roster():
    e = pd.read_csv(ELITES_CSV, sep="\t", low_memory=False)
    e = e[e.year.isin(COHORT.values())].copy()
    e["pk"] = e.province_old.map(pk)
    e["nk"] = e.name.map(lambda s: fold(str(s).replace("(", " ").replace(")", " ")))
    occ = pd.read_csv(ROOT / "data/processed/elites_occupation.csv").drop_duplicates(["id", "year"])
    e = e.merge(occ[["id", "year", "farmer"]], on=["id", "year"], how="left")
    parts = e.party.astype(str).str.split(r"\s*[-–]\s*")
    e["party_first"], e["party_last"] = parts.str[0].str.strip(), parts.str[-1].str.strip()
    return e


def match(n, ros):
    pools = {k: g for k, g in ros.groupby(["year", "pk"])}
    cache = {}

    def one(name, prov, year):
        f = fold(re.sub(r"^(Dr|Gl|Org?l|Korg?r?l|Prof|Doç|Op|Amiral|Kur)\W+", "", str(name)))
        for cand, cut in ((pools.get((year, pk(prov))) if isinstance(prov, str) else None, 80),
                          (ros[ros.year == year], 92)):
            if cand is None or cand.empty:
                continue
            sc = np.array([fuzz.token_set_ratio(f, x) for x in cand.nk])
            j = int(sc.argmax())
            if sc[j] >= cut:
                return cand.index[j]
        return None
    return [cache.setdefault((r.name, r.province, r.year), one(r.name, r.province, r.year)) for r in n.itertuples()]


def did_ri(d, treated, post, R=5000):
    d = d.assign(t=d.person_key.isin(treated), p=post)

    def est(t):
        g = d.assign(t=d.person_key.isin(t)).groupby(["t", "p"]).yes.mean()
        return (g.get((True, True)) - g.get((True, False))) - (g.get((False, True)) - g.get((False, False)))
    cells = d.groupby(["t", "p"]).size()
    if len(cells) < 4:
        return {"estimate": None, "note": "a group has no votes before or after", "cells": {str(k): int(v) for k, v in cells.items()}}
    e = est(treated)
    pool = d.person_key.unique()
    k = len(set(treated) & set(pool))
    perm = np.array([est(set(RNG.choice(pool, k, replace=False))) for _ in range(R)])
    means = d.groupby(["t", "p"]).yes.mean()
    return {"estimate": float(e), "ri_p": float((np.abs(perm) >= abs(e)).mean()), "treated": int(k),
            "control": int(len(pool) - k), "member_votes": int(len(d)),
            "means": {f"{'treated' if t else 'control'}_{'post' if p else 'pre'}": float(x) for (t, p), x in means.items()}}


def main():
    chk = pd.read_csv(ROOT / "data/interim/tbmm_1946_60_farm_namelists_check.csv").set_index("vote_id")
    # Tallies checked by hand on the PDF where GNACT's are wrong or missing.
    for r in pd.read_csv(ROOT / "data/interim/tbmm_1946_60_tally_fixes.csv").itertuples():
        chk.loc[r.vote_id, f"tally_{r.field}"] = r.value
    chk = chk.reset_index()
    nv = chk.tally_not_voting
    # Usable: no list holds more names than its tally (names filed under the wrong list), and
    # the lists are mostly there (OCR losses leave deputy-vote cells empty, not wrong).
    ok = chk[(chk.names_yes <= 1.03 * chk.tally_yes + 2) & ((chk.names_not_voting <= 1.03 * nv + 2) | nv.isna())
             & (chk.names_no <= 1.03 * chk.tally_no.fillna(0) + 2)
             & (chk.names_abstain <= 1.03 * chk.tally_abstain.fillna(0) + 2)
             & (chk.names_yes >= 0.4 * chk.tally_yes) & ((chk.names_not_voting >= 0.4 * nv) | nv.isna())]
    # GNACT's page must exist in the TBMM PDF (for a few documents it does not, and the list
    # cannot be checked).
    pages = {d: int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", str(ROOT / f"data/pdfs_tbmm/{d}.pdf")],
                                                                capture_output=True, text=True).stdout)[1])
             for d in ok.vote_id.str[:12].unique()}
    ok = ok[[int(x.split("_p")[1]) <= pages[x[:12]] for x in ok.vote_id]]
    v = pd.read_csv(ROOT / "data/interim/tbmm_1946_60_farm_votes.csv").rename(columns={"doc": "vote_id"})
    v = v[v.vote_id.isin(ok.vote_id)].copy()
    v["date"] = [vote_date(x.split("_")[0], int(x.split("_p")[1])) for x in v.vote_id]
    print(f"usable votes {len(v)} of {len(chk)}; dated {v.date.notna().mean():.2f}")
    n = pd.read_csv(ROOT / "data/interim/tbmm_1946_60_farm_namelists.csv")
    n = n[n.vote_id.isin(v.vote_id) & n.choice.isin(["yes", "no", "abstain", "not_voting"])].copy()
    n["year"] = n.vote_id.str[4:6].astype(int).map(COHORT)
    ros = roster()
    n["e_idx"] = match(n, ros)
    print(f"matched {n.e_idx.notna().mean():.3f} of {len(n)} names")
    n = n.dropna(subset=["e_idx"]).drop_duplicates(["vote_id", "e_idx"])
    n = n.join(ros[["id", "party", "party_first", "party_last", "farmer"]], on="e_idx")
    n = n.merge(v[["vote_id", "date", "policy_type", "title", "yes", "no"]].rename(columns={"yes": "t_yes", "no": "t_no"}),
                on="vote_id")
    n["date"] = pd.to_datetime(n.date)
    split = n.year.map(SPLIT).pipe(pd.to_datetime)
    n["party_at_vote"] = np.where(split.notna() & (n.date >= split), n.party_last, n.party_first)
    n.loc[(n.year == 1950) & (n.party_first != n.party_last), "party_at_vote"] = None
    n["person_key"] = n.id
    n["yes"] = (n.choice == "yes").astype(int)
    n["voted"] = (n.choice != "not_voting").astype(int)
    n["government"] = np.where(n.date < TURNOVER, n.party_at_vote == "CHP", n.party_at_vote == "DP")
    lose = n.groupby("vote_id").apply(lambda g: min(g.t_yes.iloc[0], (g.t_no.iloc[0] if g.t_no.iloc[0] == g.t_no.iloc[0] else 0)))
    n["contested"] = n.vote_id.map(lose / n.groupby("vote_id").t_yes.first()) >= 0.05
    n.to_csv(ROOT / "output/h1950s_member_votes.csv.gz", index=False)
    cast = n[n.choice.isin(["yes", "no", "abstain"]) & n.contested]

    res = {"votes": int(n.vote_id.nunique()), "contested_votes": int(cast.vote_id.nunique()),
           "member_votes": int(len(n)), "by_type": v.policy_type.value_counts().to_dict()}
    res["party_yes"] = (cast.assign(period=np.where(cast.date < TURNOVER, "1946-50", "1950-60"))
                        .groupby(["period", "party_at_vote"]).yes.agg(["mean", "size"]).round(3).reset_index()
                        .query("size >= 30").to_dict("records"))

    # 1. 1950 turnover: same deputies, same party, before and after.
    ids46, ids50 = set(ros[ros.year == 1946].id), set(ros[ros.year == 1950].id)
    first = ros.drop_duplicates("id").set_index("id")
    panel = ids46 & ids50
    stay = {i for i in panel if {first.party_first[i], first.party_last[i]} <= {"DP"} or
            {first.party_first[i], first.party_last[i]} <= {"CHP"}}
    p50 = cast[cast.id.isin(stay)]
    dp = {i for i in stay if first.party_first[i] == "DP"}
    res["turnover_1950"] = did_ri(p50, dp, p50.date >= TURNOVER)

    # 2. 1955 DP -> HP exit. The 1954-55 house had no contested agrarian vote before the split
    # (the opposition held about 31 of 541 seats), so all votes cast are used.
    allcast = n[n.choice.isin(["yes", "no", "abstain"])]
    c54 = allcast[(allcast.year == 1954) & (allcast.party_first == "DP")]
    hp = set(c54[c54.party.str.contains("HP", na=False)].id)
    stayers = set(c54[c54.party.str.strip() == "DP"].id)
    c54 = c54[c54.id.isin(hp | stayers)]
    res["dp_hp_1955"] = did_ri(c54, hp, c54.date >= pd.Timestamp(SPLIT[1954]))
    res["dp_hp_1955"]["votes_pre_post"] = c54.groupby(c54.date >= pd.Timestamp(SPLIT[1954])).vote_id.nunique().to_dict()
    # Same exit on agency budgets only (the votes the 1970 AP -> DP test used).
    b54 = c54[c54.policy_type == "agency_budget"]
    res["dp_hp_1955_budgets"] = did_ri(b54, hp, b54.date >= pd.Timestamp(SPLIT[1954]))

    # 3. Farmers within party on the same roll call.
    f = cast.dropna(subset=["party_at_vote"]).assign(cell=lambda d: d.vote_id + d.party_at_vote,
                                                    farmer=lambda d: d.farmer.fillna(False).astype(bool))
    f = f[f.groupby("cell").farmer.transform("std") > 0]
    yd = f.yes - f.groupby("cell").yes.transform("mean")
    xd = f.farmer.astype(float) - f.groupby("cell").farmer.transform("mean")
    b = (xd * yd).sum() / (xd ** 2).sum()
    g = (xd * (yd - b * xd)).groupby(f.id).sum()
    res["farmer_within_party"] = {"effect": float(b), "se": float(np.sqrt((g ** 2).sum()) / (xd ** 2).sum()),
                                  "n": int(len(f)), "farmer_deputies": int(f[f.farmer].id.nunique())}
    # Recorded opposition on the land-law and forest-law votes: who voted no.
    key = n[n.policy_type.isin(["land_reform", "forest_law", "commodity_board"]) & (n.choice == "no")]
    res["no_votes_key_laws"] = key.groupby(["vote_id", "title"]).apply(
        lambda g: g.party_at_vote.fillna("?").value_counts().to_dict()).reset_index().assign(
        title=lambda d: d.title.str[-110:]).rename(columns={0: "no_by_party"}).to_dict("records")
    (ROOT / "output/h1950s_results.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str))
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str)[:6000])


if __name__ == "__main__":
    main()
