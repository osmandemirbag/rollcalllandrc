"""Speaker turns in the 1945 debate on the Çiftçiyi Topraklandırma Kanunu, from GNACT page text.

Sessions: general debate 14-21 May 1945 (B. 54-58) and the articles 4-11 June (B. 67-70, 72);
the budget sessions in between are left out. A turn starts at a printed speaker line
('E. SAZAK (Eskişehir) —'); 'Devamla' continues the previous speaker. Speakers are matched to the
1943 roster by province + surname. GNACT's OCR can invent text: quotations used in the write-up
are checked against the TBMM PDF page (pdf_page = GNACT page_num).

Output: analysis/output/h1945_debate_turns.csv, analysis/output/h1945_debate_speakers.csv
"""
import importlib.util
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("t45", Path(__file__).parent / "03_test_1945.py")
t45 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t45)

SESSIONS = {f"tbmm07017{s:03d}" for s in range(54, 59)} | {f"tbmm07018{s:03d}" for s in (67, 68, 69, 70, 72)}
SPEAKER = re.compile(r"^(?:BAŞKAN\s*[—–-]+|(?P<who>[A-ZÇĞİÖŞÜÂ][A-ZÇĞİÖŞÜÂa-zçğıöşüâ.\s]{1,70}?)\s*\((?P<prov>[^)]{2,25})\)\s*[—–-]+)\s*", re.M)
# The chair's lines, the next sitting's header and the vote lists end a turn.
STOP = re.compile(r"^(BAŞKAN\s*[—–-]|.{0,40}verilen\s+oyların\s+sonucu|\s*[İI]K[İI]NC[İI]\s+OTURUM|\s*B[İI]R[İI]NC[İI]\s+OTURUM)", re.M)
OFFICE = re.compile(r"(BAKANI|BAŞBAKAN|SÖZCÜ|KOMİSYON|BAŞKANI|Ko\.)\s*", re.I)
PROV_FIX = {"Tokad": "TOKAT", "Siird": "SİİRT", "Seyhan": "ADANA", "Afyon": "AFYONKARAHİSAR", "Maras": "MARAŞ",
            "Gazianteb": "GAZİANTEP", "İran": None}


# Transparent stance lexicon: arguments for owners and producers vs for redistribution.
PROPERTY = r"m[üu]lkiyet|hakk?[ıi] tasarruf|toprak emniyeti|i[şs] emniyeti|orta i[şs]letme|d[üu]zenli i[şs]letme|" \
           r"te[şs]ebb[üu]s[üu] [şs]ahsi|anayasa|istihsal|zarar|kamula[şs]t[ıi]rma bedeli|hakiki de[ğg]er|makine"
REDIST = r"topraks[ıi]z|az toprakl[ıi]|ortak[çc][ıi]|maraba|a[ğg]a|inkil[âa]p|devrim|serf|esir|sosyal adalet|k[öo]yl[üu]y[üu] toprak"


def turns():
    t = pq.read_table(ROOT / "data/gnact/pages_1943_1980.parquet",
                      filters=[("legislative_body", "=", "TBMM"), ("term", "=", 7)],
                      columns=["document_id", "page_num", "text"]).to_pandas()
    t["doc"] = t.document_id.str[:12]
    t = t[t.doc.isin(SESSIONS)].sort_values(["doc", "page_num"])
    out, cur = [], None
    last_doc = None
    for r in t.itertuples():
        s, pos = r.text or "", 0
        if r.doc != last_doc:
            cur, last_doc = None, r.doc
        for m in SPEAKER.finditer(s):
            if cur is not None:
                cur["text"] += " " + s[pos:m.start()]
            if not m["who"]:  # the chair speaks: the turn ends
                cur, pos = None, m.end()
                continue
            who, prov = m["who"].strip(), m["prov"].strip()
            if prov.lower().startswith("devam") and cur is not None:
                pos = m.end()
                continue
            cur = {"doc": r.doc, "pdf_page": r.page_num, "speaker_raw": who, "province_raw": prov,
                   "office": bool(OFFICE.search(who)), "text": ""}
            out.append(cur)
            pos = m.end()
        if cur is not None:
            stop = STOP.search(s, pos)
            cur["text"] += " " + s[pos:stop.start() if stop else None]
            if stop:
                cur = None
    d = pd.DataFrame(out)
    d["text"] = d.text.str.replace(r"\s+", " ", regex=True).str.strip()
    d["words"] = d.text.str.split().str.len()
    return d


def main():
    d = turns()
    ros = t45.roster()
    names = pd.DataFrame({"name_raw": d.speaker_raw.str.replace(r"^.*?(SÖZCÜSÜ|BAKANI|BAŞKANI|BAŞBAKAN)\s+", "", regex=True),
                          "province": [PROV_FIX.get(p, p.upper()) for p in d.province_raw]})
    d["id"] = t45.match(names, ros)
    d = d.merge(ros[["id", "short", "province_old", "later_dp"]], on="id", how="left")
    d["later_dp"] = d.later_dp.fillna(False).astype(bool)
    low = d.text.str.lower()
    d["property_terms"] = low.str.count(PROPERTY)
    d["redist_terms"] = low.str.count(REDIST)
    d.to_csv(ROOT / "analysis/output/h1945_debate_turns.csv", index=False)
    s = (d.dropna(subset=["id"]).groupby(["id", "short", "province_old", "later_dp"])
         .agg(turns=("words", "size"), words=("words", "sum"), office=("office", "max"),
              property_terms=("property_terms", "sum"), redist_terms=("redist_terms", "sum")).reset_index()
         .sort_values("words", ascending=False))
    s["property_share"] = s.property_terms / (s.property_terms + s.redist_terms).where(lambda x: x > 0)
    s.to_csv(ROOT / "analysis/output/h1945_debate_speakers.csv", index=False)
    sub = s[(s.words >= 500) & ~s.office]
    print("speakers >=500 words, not speaking for government or commission:")
    print(sub.groupby("later_dp").agg(n=("words", "size"), words=("words", "sum"),
                                      property_share=("property_share", "mean")).round(2))
    rng = np.random.default_rng(1945)
    est = sub[sub.later_dp].property_share.mean() - sub[~sub.later_dp].property_share.mean()
    perm = [(lambda g: sub.property_share[g].mean() - sub.property_share[~g].mean())(rng.permutation(sub.later_dp.values))
            for _ in range(5000)]
    print(f"difference {est:.2f}, permutation p {np.mean(np.abs(perm) >= abs(est)):.3f}")
    print(f"later-DP share of all words {d[d.later_dp].words.sum() / d.words.sum():.2f}")
    print(f"turns {len(d)}, matched {d.id.notna().mean():.2f}, speakers {len(s)}")
    print(s.head(40).to_string())


if __name__ == "__main__":
    main()
