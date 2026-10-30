"""Do farmer and landowner deputies vote differently on agrarian roll calls?

Occupation from the TBMM Albümü (analysis/occupation/01-02). 'Farmer' = the biography lists
farming, a farm, land or livestock as an occupation.

Millet Meclisi 1961-80 (named votes on land and agriculture):
  estimand: the difference in voting yes (among those casting a vote) and in taking part,
  between farmer and other deputies of the same party on the same roll call.
  estimator: OLS after removing vote-by-party means (vote x party fixed effects); SEs
  clustered by deputy; separately by policy type, contested votes only for 'yes'.
1945 (TBMM, 7th term): farmer deputies' absence on the land law relative to their own absence
  on the other votes of 1945 (the DiD of 03_test_1945), and their share of debate speech.

Output: analysis/output/occupation_farmer_effects.csv, analysis/output/occupation_1945.json
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "analysis/output"


def within(df, y, x, cell):
    d = df[[y, x, cell, "person_key"]].dropna()
    d = d[d.groupby(cell)[x].transform("std") > 0]  # cells with farmers and non-farmers
    yd = d[y] - d.groupby(cell)[y].transform("mean")
    xd = d[x].astype(float) - d.groupby(cell)[x].transform("mean")
    b = (xd * yd).sum() / (xd ** 2).sum()
    u = yd - b * xd
    g = (xd * u).groupby(d.person_key).sum()
    se = np.sqrt((g ** 2).sum()) / (xd ** 2).sum()
    return b, se, len(d), d.person_key.nunique(), int(d.loc[d[x].astype(bool), "person_key"].nunique())


def mm(rows):
    occ = pd.read_csv(ROOT / "data/processed/elites_occupation.csv")
    occ = occ.drop_duplicates(["id", "year"])[["id", "year", "farmer", "ever_farmer", "lawyer", "merchant"]]
    m = pd.read_csv(OUT / "member_votes.csv.gz", low_memory=False)
    m = m[(m.chamber == "MM") & m.id.notna() & m.status_note.isna()].merge(occ, on=["id", "year"], how="left")
    print("MM member-votes with occupation:", m.farmer.notna().mean().round(3))
    v = pd.read_csv(OUT / "votes_coded.csv").set_index("vote_id")
    m["lopsided"] = m.vote_id.map(v.lopsided)
    m["cell"] = m.vote_id + "|" + m.party_at_vote.astype(str)
    m["farmer"] = m.farmer.fillna(False).astype(bool)
    cast = m[m.choice.isin(["yes", "no", "abstain"])]
    groups = {"land reform & land tax": ["land_reform", "land_tax", "land_reform_budget"],
              "farm benefits": ["farm_benefit", "debt_relief", "agri_credit"],
              "agency budgets": ["agency_budget"], "all agrarian": None}
    for label, types in groups.items():
        sel = (lambda d: d if types is None else d[d.policy_type.isin(types)])
        for outcome, data in [("yes (contested votes)", sel(cast[~cast.lopsided.astype(bool)])),
                              ("took part", sel(m))]:
            y = "yes" if outcome.startswith("yes") else "voted"
            if data.empty:
                continue
            b, se, n, deps, far = within(data, y, "farmer", "cell")
            rows.append({"sample": "Millet Meclisi 1961-80", "votes": label, "outcome": outcome, "farmer_effect": b,
                         "se": se, "n": n, "deputies": deps, "farmer_deputies": far,
                         "roll_calls": data.vote_id.nunique()})


def t1945():
    occ = pd.read_csv(ROOT / "data/processed/elites_occupation.csv")
    f = occ[occ.year == 1943].drop_duplicates("id").set_index("id").farmer.fillna(False).astype(bool)
    n = pd.read_csv(OUT / "h1945_deputy_votes.csv")
    d = n[~n.excused]
    w = d.pivot_table(index="id", columns="vote_id", values="absent")
    tr = f.reindex(w.index).fillna(False)
    land = "tbmm07018072_p022"

    def did(col):
        own = w[col] - w.drop(columns=col).mean(axis=1)
        return own[tr].mean() - own[~tr].mean()
    est = did(land)
    by = [did(c) for c in w.columns]
    sp = pd.read_csv(OUT / "h1945_debate_speakers.csv")
    sp["farmer"] = sp.id.map(f).fillna(False)
    return {"farmers": int(tr.sum()), "deputies": int(len(tr)), "land_absent_farmers": float(w.loc[tr, land].mean()),
            "land_absent_others": float(w.loc[~tr, land].mean()), "did": float(est),
            "p_votes": float(np.mean(np.abs(by) >= abs(est))),
            "farmer_share_of_speakers": float(sp.farmer.mean()), "farmer_share_of_words": float(sp[sp.farmer].words.sum() / sp.words.sum()),
            "farmer_share_of_house": float(tr.mean()),
            "farmer_speakers": sp[sp.farmer].short.tolist()}


def main():
    rows = []
    mm(rows)
    r = pd.DataFrame(rows)
    r.to_csv(OUT / "occupation_farmer_effects.csv", index=False)
    print(r.round(3).to_string())
    res = t1945()
    (OUT / "occupation_1945.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(res)


if __name__ == "__main__":
    main()
