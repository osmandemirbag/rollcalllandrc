"""Link album entries to the elites dataset rows (same election year and province; fuzzy name).

Output: data/processed/elites_occupation.csv: one row per elites (id, year) with the album flags,
and a deputy-level 'ever_farmer' (any album entry of that id lists farming).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from common import ELITES_CSV, fold, province_key  # noqa: E402

# Old province names in the album -> the elites dataset's names.
OLD = {"seyhan": "adana", "siird": "siirt", "tokad": "tokat", "yozgad": "yozgat", "sinob": "sinop", "gazianteb": "gaziantep",
       "coruh": "artvin", "gumusane": "gumushane", "elaziz": "elazig", "mersin": "icel"}
FLAGS = ["farmer", "agri_education", "merchant", "lawyer", "officer", "ulema"]


def key(name):
    return fold(str(name).split("(")[0])


def main():
    a = pd.read_csv(ROOT / "data/processed/album_deputies.csv")
    e = pd.read_csv(ELITES_CSV, sep="\t", low_memory=False, usecols=["id", "year", "name", "province_old", "party"])
    e = e[e.year <= 1977].copy()
    a["pk"] = a.province.map(lambda p: OLD.get(province_key(p), province_key(p)))
    e["pk"] = e.province_old.map(lambda p: OLD.get(province_key(p), province_key(p)))
    a["nk"], e["nk"] = a.name.map(key), e.name.map(key)
    out = []
    for (yr, pk), g in e.groupby(["year", "pk"]):
        cand = a[(a.term_start == yr) & (a.pk == pk)]
        used = set()
        for r in g.itertuples():
            if cand.empty:
                out.append((r.Index, None, 0))
                continue
            sc = np.array([max(fuzz.token_set_ratio(r.nk, x), fuzz.ratio(r.nk, x)) for x in cand.nk])
            j = int(sc.argmax())
            out.append((r.Index, cand.index[j] if sc[j] >= 80 and cand.index[j] not in used else None, sc[j]))
            used.add(cand.index[j])
    m = pd.DataFrame(out, columns=["e_idx", "a_idx", "score"]).set_index("e_idx")
    e = e.join(m)
    e = e.join(a[FLAGS + ["bio"]], on="a_idx")
    print("matched share by year:", e.groupby("year").a_idx.apply(lambda s: s.notna().mean()).round(2).to_dict())
    ever = e.groupby("id").farmer.max().rename("ever_farmer")
    e = e.join(ever, on="id")
    e.drop(columns=["pk", "nk", "a_idx"]).to_csv(ROOT / "data/processed/elites_occupation.csv", index=False)
    print(e.groupby("year")[["farmer", "ever_farmer"]].mean().round(3).T)


if __name__ == "__main__":
    main()
