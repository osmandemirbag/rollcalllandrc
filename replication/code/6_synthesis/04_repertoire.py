"""The repertoire of the parliamentary opposition on the government's key land bills, 1950-73.

For each key land vote and the main opposition party (the party outside the cabinet whose stance
the debate identifies as critical of the bill):
  selective absence index (SAI) = log(attendance on this vote / the party's attendance on the other
      agrarian roll calls of the same era); negative = stayed away
  recorded opposition = share of the party's present members voting no
  pivotal = the party could have defeated the bill holding everyone else's votes fixed, i.e. if all
      its absent members had come and voted no: no + absent >= yes
  kind = distribution (transfers or registers land) or taxation (taxes land or property)
The 1966 titling law first failed for want of a quorum on 5 May 1966 (39 votes cast, mm02006092 p. 86);
the final vote of 6 May is used.
Output: output/repertoire.csv
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".replication_root").exists())
OUT = ROOT / "output"
SPEC = [("tbmm08025070_p086", "DP", "distribution", "1950 dilution of the 1945 land law"),
        ("tbmm08025066_p040", "DP", "distribution", "1950 titling law"),
        ("tbmm10007078_p139", "CHP", "distribution", "1955 land-law amendment"),
        ("mm02006093_p021", "CHP", "distribution", "1966 titling law (final vote)"),
        ("mm03038125_p153", "CHP", "distribution", "1973 Land and Agrarian Reform Law"),
        ("mm01035055_p050", "AP", "distribution", "1965 motion on İnönü's land reform bill"),
        ("mm01030096_p062", "AP", "taxation", "1964 land tax, article 9"),
        ("mm03007115_p075", "CHP", "taxation", "1970 property tax"),
        ("mm03026116_p050", "DP", "taxation", "1972 property-tax amendment")]


def main():
    d = pd.read_csv(ROOT / "data/processed/rollcall_1945_1980_long.csv.gz", low_memory=False)
    d = d[d.status_note.isna()]
    base = d.groupby(["era", "party_at_vote"]).voted.mean()
    rows = []
    for vid, party, kind, label in SPEC:
        x = d[d.vote_id == vid]
        yes, no = (x.choice == "yes").sum(), (x.choice == "no").sum()
        g = x[x.party_at_vote == party]
        present = g[g.voted == 1]
        absent = int((g.voted == 0).sum())
        att = g.voted.mean()
        b = base[(x.era.iloc[0], party)]
        rows.append({"vote_id": vid, "label": label, "kind": kind, "party": party, "yes_listed": int(yes), "no_listed": int(no),
                     "party_listed": len(g), "party_present": len(present), "attendance": att, "baseline": b,
                     "sai": float(np.log(att / b)), "recorded_no": float((present.choice == "no").mean()) if len(present) else np.nan,
                     "pivotal": bool(no + absent >= yes)})
    r = pd.DataFrame(rows)
    r.to_csv(OUT / "repertoire.csv", index=False)
    print(r.drop(columns=["vote_id"]).round(2).to_string())


if __name__ == "__main__":
    main()
