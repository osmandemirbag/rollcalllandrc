"""Shared paths and text normalisation helpers."""
import re
import unicodedata
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".replication_root").exists())
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"
PDF_DIR = ROOT / "data" / "pdfs"
NAMELISTS = INTERIM / "namelists"

ROLLCALL_XLSX = RAW / "TBMM_land_roll_calls_1961-1980.xlsx"
VOTE1965_XLSX = RAW / "TBMM_1965_land_reform_committee_vote_by_deputy.xlsx"
ELITES_CSV = RAW / "The_Turkish_Political_Elites_Dataset.csv"

# National Assembly terms (dönem) 1961-1980 and the election year used as
# `year` in the elites dataset.
MM_TERMS = {
    "d01": (1961, "1961-10-25", "1965-10-09"),
    "d02": (1965, "1965-10-10", "1969-10-11"),
    "d03": (1969, "1969-10-12", "1973-10-13"),
    "d04": (1973, "1973-10-14", "1977-06-04"),
    "d05": (1977, "1977-06-05", "1980-09-12"),
}

# Voteview-style cast codes used in the wide matrix; 8 = invalid ballot ('geçersiz oy').
CAST_CODES = {"yes": 1, "no": 6, "abstain": 7, "invalid": 8, "not_voting": 9}

_TR_UPPER = str.maketrans({"i": "İ", "ı": "I"})
_TR_LOWER = str.maketrans({"İ": "i", "I": "ı"})


def tr_upper(s: str) -> str:
    return s.translate(_TR_UPPER).upper()


def fold(s) -> str:
    """Lower-case, strip Turkish/OCR diacritics, keep only a-z and spaces."""
    if s is None or (isinstance(s, float) and s != s):
        return ""
    s = str(s).translate(_TR_LOWER).lower()
    s = s.replace("ı", "i").replace("ş", "s").replace("ğ", "g")
    s = s.replace("ç", "c").replace("ö", "o").replace("ü", "u")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def province_key(s) -> str:
    """'AFYON KARAHİSAR' and 'AFYONKARAHİSAR' -> 'afyonkarahisar'."""
    k = fold(s).replace(" ", "")
    return {"icel": "mersin", "maras": "kahramanmaras", "urfa": "sanliurfa",
            "antep": "gaziantep", "afyon": "afyonkarahisar", "gumusane": "gumushane"}.get(k, k)


def name_variants(elite_name: str) -> list[str]:
    """'M. Arif ATALAY (Mehmet Arif ATALAY)' -> both spellings, folded."""
    out = []
    for part in re.split(r"[()\[\]]", str(elite_name)):
        f = fold(part)
        if f:
            out.append(f)
    return out


def surname(folded: str) -> str:
    toks = folded.split()
    return toks[-1] if toks else ""


def mm_term_for_date(date) -> str | None:
    d = str(date)[:10]
    for term, (_, start, end) in MM_TERMS.items():
        if start <= d <= end:
            return term
    return None
