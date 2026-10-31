"""Agrarian roll calls of the TBMM, 1946-60: selection, PDF download, name lists.

Selection: titles naming farmers, land distribution, titling, the grain board (TMO), forests,
sugar, tobacco, state farms (DÜÇ), State Hydraulic Works (DSİ), irrigation, seed loans,
livestock, village water, and FAO aid; titles about other matters that share these words
(coffee monopoly, village institutes, foundations, trade letters) are left out.
Output: data/interim/tbmm_1946_60_farm_votes.csv (with policy_type), PDFs in data/pdfs_tbmm/.
"""
import re
import subprocess
from pathlib import Path

import pandas as pd

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".replication_root").exists())
AGR = (r"[Çç]iftçi|[Tt]opraklandırma|[Tt]apulama|[Tt]oprak [Mm]ahsulleri|[Oo]rman|[Zz]iraat|[Tt]arım|[Şş]eker|"
       r"[Tt]ütün|[Hh]ububat|[Bb]uğday|[Ss]u [İi]şleri|[Ss]ulama|[Hh]ayvan|[Vv]eteriner|Üretme|Toprak|[Kk]öy içme|"
       r"[Bb]araj")
DROP = (r"Kahve|Köy Enstitü|Köymen|Vakıflar|Malzeme Ofisi|ihracata mukabil|Akdeniz mıntakası|mükataalı|Hasankeyf|"
        r"atlı takip|Ziraat Bankası Kanununun 5|Tekel Genel Müdürlüğünce yaptırılacak|bakım ve işleme")
TYPES = [  # first match wins
    ("land_reform", r"raklandır|4753|Toprak ve İskân|Tapulama|[Bb]araj"),
    ("forest_law", r"Orman Kanun|Orman ve Zeytin|Orman Çiftliği"),
    ("commodity_board", r"Toprak Mahsulleri|Şeker|Tütün|[Hh]ububat|[Bb]uğday"),
    ("farm_benefit", r"[Tt]ohumluk|Köy inşaatı|Toprak Mahsulleri Vergisi|[Hh]ayvan|[Kk]öy içme"),
    ("infrastructure", r"[Ss]u [İi]şleri|[Ss]ulama|Toprak Muhafaza"),
    ("agency_budget", r"Bütçe|cetvel|Hesabı Katı|Kesinhesap|Bilân"),
    ("international", r"Teşkilât|Teşkilatı|Kurulu|Protokol|Anlaşma|mektup"),
]


def policy_type(title):
    for k, rx in TYPES:
        if re.search(rx, title):
            return k
    return "other_agri"


def main():
    v = pd.read_csv(ROOT / "data/interim/tbmm_1943_60_votes.csv")
    v = v[(v.term >= 8) & v.title.str.contains(AGR, regex=True, na=False) & ~v.title.str.contains(DROP, regex=True, na=False)].copy()
    v["policy_type"] = v.title.map(policy_type)
    v.to_csv(ROOT / "data/interim/tbmm_1946_60_farm_votes.csv", index=False)
    print(len(v), v.policy_type.value_counts().to_dict())
    for d in sorted({x.split("_")[0] for x in v.doc}):
        f = ROOT / "data/pdfs_tbmm" / f"{d}.pdf"
        if f.exists() and f.stat().st_size > 10000:
            continue
        url = f"https://www5.tbmm.gov.tr/tutanaklar/TUTANAK/TBMM/d{d[4:6]}/c{d[6:9]}/{d}.pdf"
        r = subprocess.run(["curl", "-sSf", "--retry", "3", "-o", str(f), url], capture_output=True, text=True)
        if r.returncode:
            print(d, "download failed", r.stderr[:80])


if __name__ == "__main__":
    main()
