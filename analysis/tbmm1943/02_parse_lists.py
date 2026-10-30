"""Per-member lists of the 1943-46 TBMM open votes, with the 1960s parser adapted to the
old print style: names are initials plus an upper-case surname ('A. MENDERES', 'Dr. M. GERMEN'),
so an upper-case line that carries an initial is a name, not a province or group header.

Run with 'farm' for the 1946-60 agrarian votes (data/interim/tbmm_1946_60_farm_namelists.csv).

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
_rank = pn.province_rank
pn.province_rank = lambda label: 0.0
# Older vocabulary for the 'no' and 'not voting' lists.
pn.SECTIONS["no"] += ["kabul etmiyenler", "kabul etmeyenler", "kabul etmiyen"]
pn.SECTIONS["not_voting"] += ["reye istirak etmiyenler", "oya katilmiyanlar", "oya katilmiyan"]
pn.SECTIONS["abstain"] += ["mustenkifler", "mustenkif"]
pn.SECTIONS["vacant"] += ["boslar", "bos"]

# A bracketed line that is no known header, province or name is a header the OCR garbled
# ('[0]](h ıvatılnrHjanjarl'): it opens the next list that the tallies say is not empty.
_section_of = pn.section_of
STATE = {"exp": {}, "last": None}
ORDER = ["yes", "no", "abstain", "not_voting"]


def section_of(text):
    sec = _section_of(text)
    if sec:
        STATE["last"] = sec
        return sec
    t = text.strip()
    f = pn.fold(t)
    bracketed = t[:1] in "[(" or t[-1:] in "])"
    if re.search(r"edil|kabul\s+ol|kanunla", t, re.I) or (not bracketed and all(w[:1].isupper() for w in t.split())):
        return None  # outcome lines ('(Kanun kabul edilmiştir.)') and names ('Abdullah İzmen')
    if STATE["last"] in ORDER and 1 <= len(t.split()) <= (8 if bracketed else 3) and len(f) >= 10 \
            and (bracketed or not INITIAL.search(t)) and not pn.is_upper(t):
        for c in ORDER[ORDER.index(STATE["last"]) + 1:]:
            if (STATE["exp"].get(c) or 0) > 0 and max(
                    pn.SequenceMatcher(None, f.replace(" ", ""), n.replace(" ", "")).ratio() for n in pn.SECTIONS[c]) >= 0.6:
                return c
    if (t[:1] in "[(" or t[-1:] in "])") and STATE["last"] in ORDER and not INITIAL.search(t) \
            and len(t.split()) <= 4 and not re.search(r"\d{2}", t) and sum(c.isalpha() for c in t) >= 6 \
            and not pn.province_of(t, PROVINCES):
        # No state change here: the parser also calls this while scanning a page for its gutters.
        for c in ORDER[ORDER.index(STATE["last"]) + 1:]:
            if (STATE["exp"].get(c) or 0) > 0:
                return c
    return None


pn.section_of = section_of
NOTE = re.compile(r"\(([^)]{1,12})\)")


PROVINCES = {}


def provinces():
    p = pn.province_names()
    p.update({"seyhan": "ADANA", "coruh": "ÇORUH", "afyonkarahisar": "AFYONKARAHİSAR", "gaziantep": "GAZİANTEP",
              "gaziantb": "GAZİANTEP", "maras": "MARAŞ", "kahramanmaras": "MARAŞ", "icel": "İÇEL", "mersin": "İÇEL",
              "urfa": "URFA", "sanliurfa": "URFA"})
    return p


def off_by(d, exp):
    got = d.choice.value_counts() if len(d) else pd.Series(dtype=int)
    return sum(abs(int(got.get(k, 0)) - (exp[k] or 0)) for k in exp)


def best_parse(pdf, r, prov, exp):
    """Parse with printed headers only; if the lists miss the tallies, retry letting a restart of
    the province alphabet open the next list (a header the OCR lost), and keep the closer parse."""
    out = []
    for rank in (lambda label: 0.0, _rank):
        pn.province_rank = rank
        STATE.update(exp=exp, last=None)
        rows, tally = pn.parse_vote(pdf, int(r.page), r.title, prov, pn.npages(pdf), exp)
        out.append(pd.DataFrame(rows))
        # Tallies read from the PDF page itself win over GNACT's (its OCR read 167 as 17).
        # Only when GNACT's tallies do not add up to the house (about 450 seats).
        fixed = {**exp, **{k: tally[k] for k in exp if tally.get(k) is not None}}
        if not 430 <= sum(v or 0 for v in exp.values()) <= 456 and 430 <= sum(v or 0 for v in fixed.values()) <= 456:
            exp.update(fixed)
        if off_by(out[-1], exp) <= 0.05 * sum(v or 0 for v in exp.values()):
            break
    pn.province_rank = lambda label: 0.0
    d = min(out, key=lambda d: off_by(d, exp))
    # A list filed under a section the tallies say is empty belongs to the section left short.
    got = d.choice.value_counts()
    for c in ORDER:
        if got.get(c, 0) > (exp.get(c) or 0) + 5 and (exp.get(c) or 0) <= 2:
            short = [k for k in ORDER if k != c and (exp.get(k) or 0) - got.get(k, 0) >= 0.8 * got[c]]
            if short:
                d.loc[d.choice == c, "choice"] = short[0]
    return d


def main(votes="data/interim/tbmm_1943_60_votes.csv", out_name="tbmm_1945", term=7, volumes=(16, 20)):
    v = pd.read_csv(ROOT / votes)
    if term is not None:
        v = v[(v.term == term) & v.volume.between(*volumes)]
    prov = provinces()
    PROVINCES.update(prov)
    out, chk = [], []
    for r in v.itertuples():
        doc = r.doc.split("_")[0]
        pdf = ROOT / "data/pdfs_tbmm" / f"{doc}.pdf"
        if not pdf.exists():
            continue
        exp = {k: (None if pd.isna(getattr(r, k)) else int(getattr(r, k))) for k in ["yes", "no", "abstain", "not_voting"]}
        try:
            d = best_parse(pdf, r, prov, exp)
        except Exception as e:  # noqa: BLE001
            print(r.doc, "failed:", e)
            continue
        if d.empty:
            continue
        d["vote_id"] = r.doc
        d["note"] = d.name_raw.str.extract(NOTE)[0]
        out.append(d)
        got = d.choice.value_counts()
        chk.append({"vote_id": r.doc, **{f"tally_{k}": exp[k] for k in exp},
                    **{f"names_{k}": int(got.get(k, 0)) for k in exp}, "title": r.title[-110:]})
    pd.concat(out).to_csv(ROOT / f"data/interim/{out_name}_namelists.csv", index=False)
    c = pd.DataFrame(chk)
    c.to_csv(ROOT / f"data/interim/{out_name}_namelists_check.csv", index=False)
    print(c[[k for k in c if k != "title"]].to_string())


if __name__ == "__main__":
    if sys.argv[1:] == ["farm"]:  # 1946-60 agrarian votes (06_farm_votes_1946_60.py)
        main("data/interim/tbmm_1946_60_farm_votes.csv", "tbmm_1946_60_farm", term=None)
    else:
        main()
