"""Per-member lists of the 1943-46 TBMM open votes, with the 1960s parser adapted to the
old print style: names are initials plus an upper-case surname ('A. MENDERES', 'Dr. M. GERMEN'),
so an upper-case line that carries an initial is a name, not a province or group header.

Output: data/interim/tbmm_1945_namelists.csv (vote_id, choice, province, name, name_raw, note, pdf_page)
and data/interim/tbmm_1945_namelists_check.csv (names parsed against the tallies).
"""
import importlib.util
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("pn", ROOT / "scripts" / "03_parse_namelists.py")
pn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pn)

INITIAL = re.compile(r"(^|\s)(Dr|Gl|Org?l|Korg?r?l|Kur|Prof|Doç|Op|[A-ZÇÖÜİŞĞ0-9]{1,2})\s?[.,]")
_upper = pn.is_upper


def is_upper(text):
    return False if INITIAL.search(text) else _upper(text)


pn.is_upper = is_upper
# 1940s lists carry printed, bracketed section headers; OCR noise read as a late-alphabet province
# ('URFA') must not start a new section by the alphabet-restart rule of the 1960s parser.
pn.province_rank = lambda label: 0.0
# Older vocabulary for the 'no' and 'not voting' lists.
pn.SECTIONS["no"] += ["kabul etmiyenler", "kabul etmeyenler", "kabul etmiyen"]
pn.SECTIONS["not_voting"] += ["reye istirak etmiyenler", "oya katilmiyanlar", "oya katilmiyan"]
pn.SECTIONS["abstain"] += ["mustenkifler", "mustenkif"]
NOTE = re.compile(r"\(([^)]{1,12})\)")


def provinces():
    p = pn.province_names()
    p.update({"seyhan": "ADANA", "coruh": "ÇORUH", "afyonkarahisar": "AFYONKARAHİSAR", "gaziantep": "GAZİANTEP",
              "gaziantb": "GAZİANTEP", "maras": "MARAŞ", "kahramanmaras": "MARAŞ", "icel": "İÇEL", "mersin": "İÇEL",
              "urfa": "URFA", "sanliurfa": "URFA"})
    return p


def main(term=7, volumes=(16, 20)):
    v = pd.read_csv(ROOT / "data/interim/tbmm_1943_60_votes.csv")
    v = v[(v.term == term) & v.volume.between(*volumes)]
    prov = provinces()
    out, chk = [], []
    for r in v.itertuples():
        doc = r.doc.split("_")[0]
        pdf = ROOT / "data/pdfs_tbmm" / f"{doc}.pdf"
        if not pdf.exists():
            continue
        exp = {k: (None if pd.isna(getattr(r, k)) else int(getattr(r, k))) for k in ["yes", "no", "abstain", "not_voting"]}
        try:
            rows, tally = pn.parse_vote(pdf, int(r.page), r.title, prov, pn.npages(pdf), exp)
        except Exception as e:  # noqa: BLE001
            print(r.doc, "failed:", e)
            continue
        d = pd.DataFrame(rows)
        if d.empty:
            continue
        d["vote_id"] = r.doc
        d["note"] = d.name_raw.str.extract(NOTE)[0]
        out.append(d)
        got = d.choice.value_counts()
        chk.append({"vote_id": r.doc, **{f"tally_{k}": exp[k] for k in exp},
                    **{f"names_{k}": int(got.get(k, 0)) for k in exp}, "title": r.title[-110:]})
    pd.concat(out).to_csv(ROOT / "data/interim/tbmm_1945_namelists.csv", index=False)
    c = pd.DataFrame(chk)
    c.to_csv(ROOT / "data/interim/tbmm_1945_namelists_check.csv", index=False)
    print(c[[k for k in c if k != "title"]].to_string())


if __name__ == "__main__":
    main()
