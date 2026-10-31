"""Two descriptive analyses parallel to Rohr and Martin (2025):
  (1) variance in vote choice explained by party and by province, per contested roll call, averaged by era.
      Province first, party on the remainder, as in Rohr and Martin; and province beyond party, net of the
      share that province labels permuted within party explain by chance. Before 1961 provinces elected
      whole party lists, so province and party are nearly collinear and only the second order is informative;
  (2) social characteristics of deputies by party and period (album occupations, elites dataset).
Output: output/variance_decomposition.csv, output/characteristics_by_party.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".replication_root").exists())
sys.path.insert(0, str(ROOT / "code" / "lib"))
from common import ELITES_CSV  # noqa: E402

OUT = ROOT / "output"


def r2(y, groups):
    """Share of variance of y explained by group means."""
    m = y.groupby(groups).transform("mean")
    tss = ((y - y.mean()) ** 2).sum()
    return 1 - ((y - m) ** 2).sum() / tss if tss > 0 else np.nan


RNG = np.random.default_rng(1945)


def decomposition(d):
    c = d[d.choice.isin(["yes", "no", "abstain"]) & d.contested & d.status_note.isna()].dropna(subset=["party_at_vote", "province"])
    rows = []
    for vid, g in c.groupby("vote_id"):
        if g.yes.nunique() < 2 or len(g) < 30:
            continue
        p = r2(g.yes, g.province)
        both = r2(g.yes, [g.province, g.party_at_vote])
        party_only = r2(g.yes, g.party_at_vote)
        # Province dummies explain some variance by chance (67 provinces, a few hundred votes): the
        # baseline is the same quantity with province labels permuted within party, mean of 20 draws.
        perm = []
        for _ in range(20):
            sh = g.groupby("party_at_vote").province.transform(lambda s_: pd.Series(RNG.permutation(s_.values), index=s_.index))
            perm.append(r2(g.yes, [sh, g.party_at_vote]) - party_only)
        rows.append({"vote_id": vid, "era": g.era.iloc[0], "province": p, "party_after_province": both - p,
                     "party_only": party_only, "province_after_party": both - party_only,
                     "province_after_party_chance": float(np.mean(perm)), "n": len(g)})
    r = pd.DataFrame(rows)
    out = r.groupby("era").agg(roll_calls=("vote_id", "size"), province=("province", "mean"),
                               party_after_province=("party_after_province", "mean"), party_only=("party_only", "mean"),
                               province_after_party=("province_after_party", "mean"),
                               province_after_party_chance=("province_after_party_chance", "mean")).reset_index()
    out["province_net"] = out.province_after_party - out.province_after_party_chance
    out["residual"] = 1 - out.party_only - out.province_net
    return out


def characteristics(d):
    e = pd.read_csv(ELITES_CSV, sep="\t", low_memory=False,
                    usecols=["id", "year", "age", "rural_population_pct", "law_education", "military_education", "college", "local"])
    e = e.drop_duplicates(["id", "year"])
    o = pd.read_csv(ROOT / "data/processed/elites_occupation.csv").drop_duplicates(["id", "year"])
    dep = d.dropna(subset=["party_at_vote"]).sort_values("date").drop_duplicates(["id", "year"])[["id", "year", "era_src", "party_at_vote"]]
    dep = dep.merge(e, on=["id", "year"], how="left").merge(o[["id", "year", "farmer", "agri_education", "merchant", "lawyer", "officer", "ulema"]],
                                                           on=["id", "year"], how="left")
    dep["period"] = np.where(dep.year < 1946, "1943 Assembly", np.where(dep.year < 1960, "1946-60", "1961-80"))
    dep["party"] = dep.party_at_vote.where(dep.party_at_vote.isin(["CHP", "DP", "AP"]), "Other")
    g = dep.groupby(["period", "party"])
    t = g.agg(deputies=("id", "nunique"), age=("age", "mean"), farmer=("farmer", "mean"), merchant=("merchant", "mean"),
              lawyer=("lawyer", "mean"), officer=("officer", "mean"), ulema=("ulema", "mean"), agri_education=("agri_education", "mean"),
              law_education=("law_education", "mean"), military_education=("military_education", "mean"),
              local=("local", "mean"), rural=("rural_population_pct", "mean")).reset_index()
    return t


def main():
    d = pd.read_csv(ROOT / "data/processed/rollcall_1945_1980_long.csv.gz", low_memory=False, parse_dates=["date"])
    v = decomposition(d)
    v.to_csv(OUT / "variance_decomposition.csv", index=False)
    print(v.round(3).to_string())
    c = characteristics(d)
    c.to_csv(OUT / "characteristics_by_party.csv", index=False)
    print(c.round(3).to_string())


if __name__ == "__main__":
    main()
