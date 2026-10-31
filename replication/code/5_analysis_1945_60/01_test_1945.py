"""Did the future Democrat Party founders stay away from the 1945 land-distribution law on purpose?

Units: deputies of the 1943 TBMM. Votes: every open (named) vote of April 1945 - January 1946
whose parsed lists do not overflow the printed tallies (54 of 57).
Treated: deputies who later sat for, or were listed with, the DP (party string or any 1946-57 row).
Estimand: for treated deputies, the excess probability of not voting on the 11 June 1945
Çiftçiyi Topraklandırma Kanunu over their own not-voting rate on the other votes of the same
months, relative to the same difference among all other deputies (a deputy-by-vote DiD).
Inference: randomization over votes (which of the votes is 'the' land law) and over deputies.

Output: output/h1945_land_law.json, output/h1945_deputy_votes.csv
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

LAND = "tbmm07018072_p022"
BUDGET = "tbmm07017065_p040"  # 1945 seven-month budget, 368-5: the five 'no' votes
RNG = np.random.default_rng(1945)


def roster():
    e = pd.read_csv(ELITES_CSV, sep="\t", low_memory=False)
    c = e[e.year == 1943].copy()
    later_dp = set(e[(e.year.between(1946, 1957)) & e.party.astype(str).str.contains(r"\bDP\b")].id)
    c["later_dp"] = c.party.str.contains(r"\bDP\b") | c.id.isin(later_dp)
    c["short"] = c.name.str.replace(r"\(.*", "", regex=True).str.strip()
    c["surname"] = c.short.map(lambda s: " ".join(t for t in s.split() if t.isupper() and len(t) > 1))
    c["initials"] = c.short.map(lambda s: "".join(fold(t)[:1] for t in s.split() if not t.isupper()))
    c["pkey"] = c.province_old.map(province_key)
    return c.drop_duplicates("id")


def split_name(raw):
    raw = re.sub(r"\([^)]*\)?", "", str(raw))
    toks = re.sub(r"^(Dr|Gl|Org?l|Korg?r?l|Prof|Kur)\W+", "", raw.strip()).split()
    sur = [t for t in toks if not re.search(r"[.,]", t) and len(fold(t)) > 1]
    ini = [t for t in toks if re.search(r"[.,]", t) or len(fold(t)) <= 1]
    return fold(" ".join(sur)), "".join(fold(t)[:1] for t in ini)


def match(names, ros):
    """Province + surname (fuzzy, initials break ties); falls back to a near-exact surname anywhere."""
    ros = ros.assign(fs=ros.surname.map(fold))
    pools = {k: g for k, g in ros.groupby("pkey")}
    cache = {}

    def one(raw, province):
        sur, ini = split_name(raw)
        if not sur:
            return None
        pool = pools.get(province_key(province)) if isinstance(province, str) else None
        for cand, cut in ((pool, 0.78), (ros, 0.92)):
            if cand is None:
                continue
            sc = [fuzz.ratio(sur, x) / 100 for x in cand.fs]
            sc = [s + (0.05 if ini and i.endswith(ini[-1:]) else 0) for s, i in zip(sc, cand.initials)]
            j = int(np.argmax(sc))
            if sc[j] >= cut:
                return cand.id.iloc[j]
        return None
    return [cache.setdefault((r.name_raw, r.province), one(r.name_raw, r.province)) for r in names.itertuples()]


def vote_dates(votes):
    dates = {}
    for vid in votes:
        doc, page = vid.split("_p")
        t = subprocess.run(["pdftotext", "-f", page, "-l", page, f"data/pdfs_tbmm/{doc}.pdf", "-"],
                           capture_output=True, text=True, cwd=ROOT).stdout
        m = re.search(r"(\d{1,2})\s*[.,]\s*(\d{1,2})\s*[.,]\s*(19\d\d)", t)
        dates[vid] = f"{m[3]}-{int(m[2]):02d}-{int(m[1]):02d}" if m else None
    return dates


def main():
    chk = pd.read_csv(ROOT / "data/interim/tbmm_1945_namelists_check.csv")
    # A vote is used when no list overflows its tally (names filed under the wrong list) and the
    # lists are mostly there; names lost to OCR are simply missing (deputy-vote cells left empty).
    nv = chk.tally_not_voting.fillna(0)
    ok = chk[(chk.names_yes <= 1.03 * chk.tally_yes) & (chk.names_not_voting <= 1.03 * nv + 2)
             & (chk.names_yes >= 0.4 * chk.tally_yes) & (chk.names_not_voting >= 0.8 * nv)]
    n = pd.read_csv(ROOT / "data/interim/tbmm_1945_namelists.csv")
    n = n[n.vote_id.isin(ok.vote_id) & n.choice.isin(["yes", "no", "not_voting"])]
    ros = roster()
    n["id"] = match(n, ros)
    rate = n.id.notna().mean()
    n = n.dropna(subset=["id"]).drop_duplicates(["vote_id", "id"])
    n["absent"] = (n.choice == "not_voting").astype(int)
    n["excused"] = n.note.fillna("").str.contains(r"^[İIi1lt]\.?$|^[ÖöO]\.?$|Bakan|Başkan|vekil|Has|Cumhurba", regex=True)
    dates = vote_dates(n.vote_id.unique())
    n["date"] = n.vote_id.map(dates)
    n = n.merge(ros[["id", "short", "province_old", "party", "later_dp"]], on="id")
    n.to_csv(ROOT / "output/h1945_deputy_votes.csv", index=False)

    # Unexcused deputies only: ministers, officers and those on leave (İ.) are absent by office.
    d = n[~n.excused]
    w = d.pivot_table(index="id", columns="vote_id", values="absent")
    tr = ros.set_index("id").later_dp.reindex(w.index).fillna(False).astype(bool)

    def did(col, treated):
        other = w.drop(columns=col)
        own = w[col] - other.mean(axis=1)
        return own[treated].mean() - own[~treated].mean()
    est = did(LAND, tr)
    by_vote = {c: did(c, tr) for c in w.columns}
    p_vote = np.mean([abs(x) >= abs(est) for x in by_vote.values()])
    perm = [did(LAND, pd.Series(RNG.permutation(tr.values), index=tr.index)) for _ in range(5000)]
    p_dep = float(np.mean(np.abs(perm) >= abs(est)))

    # The founders' withdrawal began after they voted against the budget (session 65, 29 May 1945):
    # compare the land law with the other votes after that date only.
    post = [c for c in w.columns if (int(c[6:9]), int(c[9:12])) > (17, 65)]
    f5 = pd.Series(w.index.isin(n[n.short.str.contains("MENDERES|SAZAK|KÖPRÜLÜ|KORALTAN|BAYAR")].id), index=w.index)

    def did_post(col, treated):
        own = w[col] - w[[c for c in post if c != col]].mean(axis=1)
        return own[treated].mean() - own[~treated].mean()
    post_est = {lab: did_post(LAND, g) for lab, g in [("five", f5), ("later_dp", tr)]}
    post_p = {lab: float(np.mean([abs(did_post(c, g)) >= abs(post_est[lab]) for c in post]))
              for lab, g in [("five", f5), ("later_dp", tr)]}
    rest = ~tr
    window = {"five_absent_post_other": float(w.loc[f5, [c for c in post if c != LAND]].stack().mean()),
              "five_absent_pre": float(w.loc[f5, [c for c in w.columns if c not in post]].stack().mean()),
              "others_absent_post_other": float(w.loc[rest, [c for c in post if c != LAND]].stack().mean())}

    five = ["Adnan MENDERES", "Fuat KÖPRÜLÜ", "Refik KORALTAN", "Mahmut Celâl BAYAR", "Emin SAZAK"]
    ff = n[n.short.isin(five) | n.short.str.contains("SAZAK")]
    timeline = ff.pivot_table(index="vote_id", columns="short", values="choice", aggfunc="first")
    timeline.insert(0, "date", timeline.index.map(dates))
    timeline = timeline.sort_values("date")
    all5 = timeline.drop(columns="date").eq("not_voting").all(axis=1)
    res = {
        "votes": int(w.shape[1]), "deputies": int(w.shape[0]), "treated": int(tr.sum()),
        "treated_names": ros.set_index("id").short.reindex(w.index[tr]).tolist(), "match_rate": float(rate),
        "land_absent_treated": float(w.loc[tr, LAND].mean()), "land_absent_control": float(w.loc[~tr, LAND].mean()),
        "other_absent_treated": float(w.loc[tr].drop(columns=LAND).stack().mean()),
        "other_absent_control": float(w.loc[~tr].drop(columns=LAND).stack().mean()),
        "did": float(est), "p_votes": float(p_vote), "p_deputies": p_dep,
        "did_rank": int(sorted(by_vote.values(), reverse=True).index(est) + 1),
        "post_votes": len(post), "post_did": post_est, "post_p_votes": post_p, **window,
        "votes_all_five_absent": int(all5.sum()), "votes_with_all_five_listed": int(timeline.drop(columns="date").notna().all(axis=1).sum()),
        "timeline": timeline.reset_index().fillna("").to_dict("records"),
    }
    (ROOT / "output/h1945_land_law.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str))
    print(json.dumps({k: v for k, v in res.items() if k != "timeline"}, ensure_ascii=False, default=str))
    print(timeline.to_string())


if __name__ == "__main__":
    main()
