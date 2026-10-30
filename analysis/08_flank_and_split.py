"""The radical flank (TİP, 1965-71) and the second party split (CHP -> GP, May 1967).

Adds to analysis/output/paper.json:
  tip:     ideal points, roll calls where TİP voted against both AP and CHP majorities,
           pivotality (could TİP's votes reverse an outcome or make/break the 226-vote quorum)
  quorum:  check of the 226-voter threshold against recorded outcomes
  gp:      CHP -> GP exit (opposition -> opposition): pre-split titling votes, DiD on contested
           budget roll calls with Fisher randomization inference
  quotes:  speeches located in the minutes (sitting PDF and page), with English summaries
"""
import json
import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis" / "output"
RNG = np.random.default_rng(1965)
QUORUM = 226

# Speeches found in the minutes; the script locates each one's PDF page to cite it.
QUOTES = [
    {"pdf": "mm02006092", "anchor": "Susuz araziler için 100 dönüm", "speaker": "Yahya Kanbolat (TİP, Hatay)",
     "date": "1966-05-05", "bill": "Tapulama (titling) law, article 33",
     "tr": "Tapuda kayıtlı olmıyan gayrimenkullerin zilyedleri adına tescilinde iki ölçü ileri sürmekteyiz: Susuz araziler için 100 dönüm, sulu gayrimenkuller için de 20 dönüm.",
     "en": "TİP's amendment: register untitled land to its possessor only up to 100 dönüm of dry or 20 dönüm of irrigated land, to stop landlords titling large holdings."},
    {"pdf": "mm02006092", "anchor": "Yüzdönümü aşan tapusuz gayrimenkuller", "speaker": "Yahya Kanbolat (TİP, Hatay); ruling by the chair",
     "date": "1966-05-05", "bill": "Tapulama (titling) law, article 38",
     "tr": "«Yüzdönümü aşan tapusuz gayrimenkuller ilk önce Hazine adına tesbit ve tescil ...» — Kabul edenler... Etmiyenler... Değişiklik önergesi kabul edilmemiştir.",
     "en": "Amendment: untitled land above 100 dönüm is first registered to the Treasury. The chair puts it to a show of hands: not adopted. No recorded vote was taken on any of TİP's amendments."},
    {"pdf": "mm02006092", "anchor": "toprak ağalarından yana olmadığını", "speaker": "Yahya Kanbolat (TİP, Hatay), citing the minister",
     "date": "1966-05-05", "bill": "Tapulama (titling) law",
     "tr": "Devlet Bakanı Sayın Refet Sezgin ... 509 sayılı Kanunun toprak ağalarından yana olmadığını ... söylemiştir.",
     "en": "The government's defence, as TİP quoted it: the titling law 'is not on the side of the landlords'."},
    {"pdf": "mm02030028", "anchor": "ekimi serbest bırakmalı, ticaretini Devlet yönetmelidir", "speaker": "Yusuf Ziya Bahadınlı (TİP, Yozgat)",
     "date": "1969-01", "bill": "Tobacco and Tobacco Monopoly law, article 1",
     "tr": "... ekimi serbest bırakmalı, ticaretini Devlet yönetmelidir. Tütün ekicisinin birinci derdi ... tütününün yok pahasına elinden alınmasıdır.",
     "en": "Growing should stay free but the state should run the trade; the grower's first grievance is losing his tobacco for nothing to merchants."},
    {"pdf": "mm02025047", "anchor": "topraksız köylü", "speaker": "Âdil Kurtel (TİP, Kars)",
     "date": "1968-02", "bill": "Village Affairs Ministry budget",
     "tr": "A. P. iktidarı «topraksız köylü» sorununu iki yıldır birtakım yuvarlak sözlerle geçiştiriyor ve «tarım reformu» terimiyle sorunu oyalıyordu.",
     "en": "For two years the AP government has evaded the landless-peasant question with vague words, stalling under the term 'agrarian reform'."},
]


def load():
    v = pd.read_csv(OUT / "votes_coded.csv")
    m = pd.read_csv(OUT / "member_votes.csv.gz", low_memory=False)
    m["date"] = pd.to_datetime(m.date)
    return v, m


def tip(v, m):
    d = m[(m.chamber == "MM") & (m.mm_term == "d02")]
    cast = d[d.choice.isin(["yes", "no"])]
    rows, piv = [], []
    for vid, g in d.groupby("vote_id"):
        t = g[g.party_at_vote == "TİP"]
        s = cast[cast.vote_id == vid].groupby("party_at_vote").yes.mean()
        ty, tn, tabs = (t.choice == "yes").sum(), (t.choice == "no").sum(), int((t.voted == 0).sum())
        y, n, voters = (g.choice == "yes").sum(), (g.choice == "no").sum(), int(g.voted.sum())
        if ty + tn and "AP" in s and "CHP" in s:
            tip_maj = ty / (ty + tn) > 0.5
            if tip_maj != (s["AP"] > 0.5) and tip_maj != (s["CHP"] > 0.5):
                vr = v.set_index("vote_id").loc[vid]
                rows.append({"date": vr.date[:10], "title": vr.title[:80], "policy_type": vr.policy_type,
                             "TİP": f"{ty}–{tn}", "AP_yes": s["AP"], "CHP_yes": s["CHP"]})
        flip = (y > n) and (y - ty <= n - tn + len(t))
        short = QUORUM - voters
        qpiv = (0 < short <= tabs) or (short <= 0 and -short < len(t) - tabs)
        piv.append({"flip": flip, "quorum_pivot": qpiv, "passed": v.set_index("vote_id").loc[vid].outcome_class == "passed"})
    piv = pd.DataFrame(piv)
    pts = pd.read_csv(OUT / "ideal_points.csv")
    p = pts[pts.term == "d02"].groupby("party").d1.agg(["mean", "size"]).round(2)
    turnout = d[d.party_at_vote == "TİP"].voted.mean()
    return {"flank_votes": rows, "roll_calls": len(piv), "outcome_pivotal": int(piv.flip.sum()),
            "quorum_pivotal": int(piv.quorum_pivot.sum()), "quorum_pivotal_passed": int((piv.quorum_pivot & piv.passed).sum()),
            "turnout": float(turnout), "d1_means": p.reset_index().to_dict("records")}


def quorum_check(v, m):
    mm = m[(m.chamber == "MM") & ~m.row_status.astype(str).str.startswith("derived")]
    vt = mm.groupby("vote_id").voted.sum()
    x = v.set_index("vote_id").loc[vt.index].assign(voters=vt)
    x = x[x.outcome_class.isin(["passed", "no quorum / majority not reached"]) & (x.seats == 450)]
    ok = ((x.voters >= QUORUM) == (x.outcome_class == "passed")).sum()
    return {"consistent": int(ok), "total": int(len(x))}


def gp(v, m, R=5000):
    d = m[(m.chamber == "MM") & (m.mm_term == "d02") & ~m.status_note.fillna("").ne("")]
    first = d.sort_values("date").groupby("person_key").party_at_vote.first()
    last = d.sort_values("date").groupby("person_key").party_at_vote.last()
    founders = set(first.index[(first == "CHP") & (last == "CGP")])
    stayers = set(first.index[(first == "CHP") & (last == "CHP")])
    split = pd.Timestamp("1967-05-12")
    tap = {}
    for vid in ["mm02006092_p086", "mm02006093_p021"]:
        x = d[d.vote_id == vid]
        tap[vid] = {g: x[x.person_key.isin(s)].choice.value_counts().to_dict() for g, s in
                    [("founders", founders), ("stayers", stayers)]}
    contested = set(v[~v.lopsided].vote_id)
    b = d[d.policy_type.isin(["agency_budget", "land_reform_budget", "final_accounts"]) & d.choice.isin(["yes", "no", "abstain"])
          & d.vote_id.isin(contested) & d.person_key.isin(founders | stayers)].copy()
    b["post"] = b.date >= split

    def did(tr):
        t = b.person_key.isin(tr)
        return (b[t & b.post].yes.mean() - b[t & ~b.post].yes.mean()) - (b[~t & b.post].yes.mean() - b[~t & ~b.post].yes.mean())
    est = did(founders)
    pool = b.person_key.unique()
    nt = len(founders & set(pool))
    perm = np.array([did(set(RNG.choice(pool, nt, replace=False))) for _ in range(R)])
    means = b.assign(g=np.where(b.person_key.isin(founders), "founders", "stayers")).groupby(["g", "post"]).yes.mean()
    return {"founders": nt, "stayers": len(pool) - nt, "estimate": float(est), "ri_p": float((np.abs(perm) >= abs(est)).mean()),
            "means": {f"{g}_{'post' if p else 'pre'}": float(x) for (g, p), x in means.items()}, "tapulama_1966": tap}


def locate_quotes():
    out = []
    for q in QUOTES:
        page = None
        n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", f"data/pdfs/{q['pdf']}.pdf"], capture_output=True,
                                                             text=True, cwd=ROOT).stdout)[1])
        for p in range(1, n + 1):
            t = subprocess.run(["pdftotext", "-f", str(p), "-l", str(p), f"data/pdfs/{q['pdf']}.pdf", "-"],
                               capture_output=True, text=True, cwd=ROOT).stdout
            t = re.sub(r"\s+", " ", re.sub(r"­\s*\n?", "", t))
            if q["anchor"] in t:
                page = p
                break
        out.append({**q, "page": page})
    return out


def main():
    v, m = load()
    res = json.loads((OUT / "paper.json").read_text())
    res["tip"] = tip(v, m)
    res["quorum"] = quorum_check(v, m)
    res["gp"] = gp(v, m)
    res["quotes"] = locate_quotes()
    (OUT / "paper.json").write_text(json.dumps(res, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    for k in ["tip", "quorum", "gp", "quotes"]:
        print(k, json.dumps(res[k], ensure_ascii=False, default=str)[:1500])


if __name__ == "__main__":
    main()
