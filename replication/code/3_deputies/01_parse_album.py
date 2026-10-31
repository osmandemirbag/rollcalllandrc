"""Deputies' occupations from the TBMM Albümü 1920-2010 (TBMM 2010), volumes 1 (1920-50) and 2 (1950-80),
downloaded from acikerisim.tbmm.gov.tr (hdl 11543/2343).

Each page holds two columns of entries: province, name, then a biography of the form
'Birthplace - year, father - mother - education - languages - profession - career - terms - family.
Ölüm Tarihi: ...'. Pages carry the term header ('IX. YASAMA DÖNEMİ / 1950 - 1954').

Occupation flags read from the biography:
  farmer: çiftçi/çiftçilik, çiftlik sahibi, ziraatçı, zürra, arazi/toprak sahibi, bağcı, hayvancı(lık)
  (schooling in agriculture, 'Ziraat Okulu', is kept apart as agri_education)
Output: data/processed/album_deputies.csv (term_start, province, name, bio, flags)
"""
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".replication_root").exists())
sys.path.insert(0, str(ROOT / "code" / "lib"))
from common import fold, province_key  # noqa: E402

VOLS = {"c1": ROOT / "data/albums/c1.pdf", "c2": ROOT / "data/albums/c2.pdf"}
TERM = re.compile(r"([IVXL]+)\.\s*(?:\(([IVXL]+)\)\s*)?YASAMA\s+DÖNEMİ\s*/\s*(\d{4})\s*-\s*(\d{4})")
FARMER = re.compile(r"[Çç]ift[çc]i|[Çç]iftlik\s+(sahibi|işlet)|[Zz]iraat[çc][ıi]|[Zz]ürra|[Aa]razi\s+sahibi|"
                    r"[Tt]oprak\s+sahibi|[Bb]a[ğg][çc][ıi]l[ıi]k|[Hh]ayvanc[ıi]|[Mm]üstahsil|[Tt]arım(sal)?\s+işlet|"
                    r"[Zz]iraat\s+ile\s+meşgul|[Zz]iraatle\s+meşgul")
AGRI_EDU = re.compile(r"[Zz]iraat\s+(Okul|Mektep|Mektebi|Fakülte|Enstitü)|[Tt]arım\s+(Okul|Fakülte)|[Zz]iraat\s+Mühendis|"
                      r"[Vv]eteriner|[Bb]aytar")
MERCHANT = re.compile(r"[Tt]üccar|[Tt]icaret(le)?\s*(meşgul)?|[Ss]anayici|[Mm]üteahhit|[Ee]snaf")
LAWYER = re.compile(r"[Aa]vukat|[Hh]âkim|[Hh]akim|[Ss]avcı")
OFFICER = re.compile(r"[Ss]ubay|[Kk]urmay|[Pp]aşa|[Gg]eneral|[Aa]lbay|[Bb]inbaşı|[Mm]iralay|[Kk]aymakam\s+\(asker")
ULEMA = re.compile(r"[Mm]üftü|[Mm]üderris|[Vv]aiz|[Ii]mam\b|[Hh]oca")


def provinces():
    e = pd.read_csv(ROOT / "data/raw/The_Turkish_Political_Elites_Dataset.csv", sep="\t", usecols=["province_old"])
    ks = {province_key(p) for p in e.province_old.dropna().unique()}
    return ks | {"seyhan", "icel", "coruh", "maras", "urfa", "gaziantep", "siird", "tokad", "yozgad", "sinob", "bitlis",
                 "kocaeli", "zonguldak", "genz", "cebelibereket", "ergani", "gelibolu", "mersin", "artvin"}


def column_text(pdf, page, x, w, h):
    return subprocess.run(["pdftotext", "-f", str(page), "-l", str(page), "-x", str(x), "-y", "0", "-W", str(w),
                           "-H", str(h), pdf, "-"], capture_output=True, text=True).stdout


def entries(vol, pdf, provs):
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout)[1])
    out, term = [], None
    for p in range(1, n + 1):
        full = subprocess.run(["pdftotext", "-f", str(p), "-l", str(p), pdf, "-"], capture_output=True, text=True).stdout
        m = TERM.search(full)
        if m:
            term = (m[1], m[2], int(m[3]), int(m[4]))
        if term is None:
            continue
        for x in (0, 312):
            lines = [l.strip() for l in column_text(pdf, p, x, 312, 879).splitlines()]
            cur = None
            for l in lines:
                if not l or TERM.search(l):
                    continue
                if l.isupper() and province_key(l) in provs:
                    cur = {"vol": vol, "page": p, "term_roman": term[0], "mm_term": term[1], "term_start": term[2],
                           "term_end": term[3], "province": l, "name": None, "bio": ""}
                    out.append(cur)
                    continue
                if cur is None:
                    continue
                if cur["name"] is None:
                    cur["name"] = re.sub(r"(?<=[A-ZÇĞİÖŞÜ])\d+\b", "", l).strip()
                elif re.match(r"^\d{1,4}\s+\D", l) and cur["bio"].rstrip().endswith((".", ")")):
                    cur = None  # footnotes under the last entry
                else:
                    cur["bio"] += " " + l
    return out


def main():
    provs = provinces()
    rows = []
    for vol, pdf in VOLS.items():
        rows += entries(vol, str(pdf), provs)
        print(vol, len(rows))
    d = pd.DataFrame(rows)
    d["bio"] = d.bio.str.replace(r"(\w)­\s*(\w)", r"\1\2", regex=True).str.replace(r"\s+", " ", regex=True).str.strip()
    # Joined names continue on a second line when a long name breaks: '(Mustafa Halit ÜNERMAN)'.
    d["also"] = d.bio.str.extract(r"^\(([^)]{3,60})\)")[0]
    d["bio"] = d.bio.str.replace(r"^\([^)]{3,60}\)\s*", "", regex=True)
    work = d.bio.str.replace(r"Ölüm Tarihi.*", "", regex=True)
    for k, rx in [("farmer", FARMER), ("agri_education", AGRI_EDU), ("merchant", MERCHANT), ("lawyer", LAWYER),
                  ("officer", OFFICER), ("ulema", ULEMA)]:
        d[k] = work.str.contains(rx)
    d = d[d.name.notna() & (d.bio.str.len() > 40)]
    d.to_csv(ROOT / "data/processed/album_deputies.csv", index=False)
    print(len(d), d.groupby("term_start")[["farmer", "merchant", "lawyer", "officer"]].mean().round(3))


if __name__ == "__main__":
    main()
