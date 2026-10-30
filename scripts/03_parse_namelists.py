"""Extract the per-member name lists printed under each open-vote result.

For every vote in data/processed/votes.csv whose PDF is in data/pdfs/, read the
pages from `pdf_page` onward, split them into the printed lists

    (Kabul edenler) / (Reddedenler) / (Çekinserler) / (Oya katılmayanlar)

grouped under upper-case province headers, and write
data/interim/namelists/<vote_id>.csv with columns
    vote_id, choice, province, name, name_raw, pdf_page
plus data/interim/namelist_checks.csv comparing parsed counts with the
printed tallies. A list is only used downstream when its counts match
(status 'ok'); others need hand checking.

The 1965-02-11 list that was already cleaned by hand
(data/raw/TBMM_1965_land_reform_committee_vote_by_deputy.xlsx) is imported as is.

    python3 03_parse_namelists.py
"""
import re
import subprocess

import pandas as pd

from common import ELITES_CSV, NAMELISTS, PDF_DIR, PROCESSED, INTERIM, VOTE1965_XLSX, fold, province_key

SECTION = [
    ("yes", r"kabul\s+edenler"),
    ("no", r"redd?edenler|ret\s+edenler"),
    ("abstain", r"çekinser|cekinser"),
    ("not_voting", r"oy[ae]?\s+kat[ıi]lmayanlar|oylamaya\s+kat[ıi]lmayanlar"),
    ("vacant", r"aç[ıi]k\s+(üyelik|milletvekillik|bulunan)|münhal"),
]
END = re.compile(r"verilen\s+oy(lar[ıi]n|\s+)sonucu|^\s*BİRLEŞİM|^\s*\d+\s*[.]\s*—", re.I)
NOTES = re.compile(r"\((B[aş]{1,2}k[.\s]*V?\.?|Başkan|Bakan|Bşk\.?\s*V\.?|İ\.\s*A\.)\)|\(.*?\)")
PAGES_AFTER = 6  # a 450-member list spans at most four pages


def province_names() -> dict[str, str]:
    e = pd.read_csv(ELITES_CSV, sep="\t", usecols=["province_old"], low_memory=False)
    keys = {province_key(p): p for p in e.province_old.dropna().unique()}
    # Senate-only groupings without a province.
    for extra in ["TABİİ ÜYELER", "CUMHURBAŞKANINCA S. Ü.", "CUMHURBAŞKANINCA SEÇİLEN ÜYELER"]:
        keys[province_key(extra)] = extra
    return keys


def pdf_text(pdf, first, last) -> list[tuple[int, str]]:
    out = []
    for p in range(first, last + 1):
        r = subprocess.run(["pdftotext", "-f", str(p), "-l", str(p), str(pdf), "-"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            break
        out.append((p, r.stdout))
    if sum(len(t.strip()) for _, t in out) < 200:
        raise RuntimeError(f"{pdf.name}: no text layer on pages {first}-{last}; OCR (tesseract -l tur) needed")
    return out


def parse_pages(pages, provinces):
    rows, choice, prov, started = [], None, None, False
    for page, text in pages:
        for line in text.splitlines():
            s = line.strip()
            if not s:
                continue
            low = s.lower()
            if started and END.search(s) and choice is not None and rows:
                return rows
            hit = next((c for c, rx in SECTION if re.search(rx, low)), None)
            if hit and len(s) < 40 and not re.search(r"\d", s):
                choice, prov, started = hit, None, True
                continue
            if not started or choice == "vacant":
                continue
            k = province_key(s)
            if k in provinces:
                prov = provinces[k]
                continue
            if re.search(r"\d{2,}|üye\s+sayısı|oy\s+verenler|kabul\s+edenler|c\.\s*senatosu|m\.\s*meclisi", low):
                continue  # tallies and running headers
            name = NOTES.sub("", s).strip(" .,'-")
            if len(fold(name).split()) >= 2:
                rows.append({"choice": choice, "province": prov, "name": name, "name_raw": s, "pdf_page": page})
    return rows


def import_1965(votes):
    v = votes[(votes.session_id == "mm01035055") & (votes.pdf_page == 50)].vote_id.iat[0]
    d = pd.read_excel(VOTE1965_XLSX, sheet_name=0)
    choice = {"Yes (Kabul)": "yes", "No (Ret)": "no", "Abstain (Çekinser)": "abstain",
              "Not voting (Oya katılmayan)": "not_voting"}
    return v, pd.DataFrame({"vote_id": v, "choice": d.Vote.map(choice), "province": d.Province,
                            "name": d["Name (cleaned)"], "name_raw": d["Name as scanned"],
                            "pdf_page": d["PDF page"], "source": "hand-cleaned list (raw xlsx)"})


def main():
    NAMELISTS.mkdir(parents=True, exist_ok=True)
    votes = pd.read_csv(PROCESSED / "votes.csv")
    provinces = province_names()
    checks = []

    v1965, df1965 = import_1965(votes)
    df1965.to_csv(NAMELISTS / f"{v1965}.csv", index=False)

    for v in votes.itertuples():
        out = NAMELISTS / f"{v.vote_id}.csv"
        if v.vote_id == v1965:
            df = df1965
        elif out.exists() and "source" in pd.read_csv(out, nrows=1).columns and \
                pd.read_csv(out, nrows=1).source.iat[0] != "pdftotext parser":
            df = pd.read_csv(out)  # hand-corrected file: never overwrite
        else:
            pdf = PDF_DIR / f"{v.session_id}.pdf"
            if not pdf.exists():
                checks.append({"vote_id": v.vote_id, "status": "pdf missing"})
                continue
            try:
                rows = parse_pages(pdf_text(pdf, int(v.pdf_page), int(v.pdf_page) + PAGES_AFTER), provinces)
            except RuntimeError as e:
                checks.append({"vote_id": v.vote_id, "status": "no text layer", "note": str(e)})
                continue
            df = pd.DataFrame(rows).assign(vote_id=v.vote_id, source="pdftotext parser")
            df.to_csv(out, index=False)
        got = df.choice.value_counts()
        row = {"vote_id": v.vote_id}
        mism = []
        for c in ["yes", "no", "abstain", "not_voting"]:
            printed = getattr(v, c)
            row[f"{c}_printed"], row[f"{c}_parsed"] = printed, int(got.get(c, 0))
            if pd.notna(printed) and int(printed) != row[f"{c}_parsed"]:
                mism.append(c)
        row["status"] = "ok" if not mism else "count mismatch: " + ",".join(mism)
        checks.append(row)

    ch = pd.DataFrame(checks)
    ch.to_csv(INTERIM / "namelist_checks.csv", index=False)
    print(ch.status.str.split(":").str[0].value_counts().to_string())


if __name__ == "__main__":
    main()
