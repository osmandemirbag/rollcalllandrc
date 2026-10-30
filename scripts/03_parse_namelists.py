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
import sys
from difflib import SequenceMatcher

import pandas as pd

from common import ELITES_CSV, NAMELISTS, PDF_DIR, PROCESSED, INTERIM, VOTE1965_XLSX, fold, province_key
from layout import column_lines, group_rows, read_pages, row_text

SECTIONS = {
    "yes": ["kabul edenler"],
    "no": ["reddedenler", "red edenler", "ret edenler"],
    "abstain": ["cekinserler", "cekimserler", "cekinser"],
    "not_voting": ["oya katilmayanlar", "oya katilmiyanlar", "oylamaya katilmayanlar", "oya katilmayan"],
    "vacant": ["acik uyelikler", "acik milletvekillikleri", "acik uyelik", "acik milletvekilligi",
               "acik bulunan", "munhal"],
}
TITLE_ROW = re.compile(r"sonu\S?u\b|sonuç|oyla?r[ıi]n\s+sonu|neticesi", re.I)
DIGIT_FIX = str.maketrans({"0": "O", "1": "İ", "3": "B", "4": "A", "5": "S", "6": "G", "8": "B"})
RUNNING_HEAD = re.compile(r"(Senatos|Mecl[iı]s|Meclis)\w*\W.*\bB\b|\d+\s*[.,]\s*\d+\s*[.,]\s*19[67]\d|^\W*[0-9 ]+\W*$", re.I)
NOTES = re.compile(r"\([^)]{0,25}\)|\[[^\]]{0,25}\]")
GROUP_NOISE = {"genel", "oyla", "secilen", "seci", "len", "uyeler", "uyeleri"}
MANUAL = INTERIM / "namelists_manual"  # hand-corrected lists override the parser
PAGES_AFTER = 6  # a 450-member list spans at most four pages


def province_names() -> dict[str, str]:
    e = pd.read_csv(ELITES_CSV, sep="\t", usecols=["province_old"], low_memory=False)
    keys = {province_key(p): p for p in e.province_old.dropna().unique()}
    keys.update({"icel": "İÇEL", "hakkari": "HAKKARİ", "elazig": "ELAZIĞ", "gumushane": "GÜMÜŞHANE"})
    return keys


def section_of(text):
    """'[Kabul edenler]' -> 'yes'. Tally lines ('Kabul edenler : 120') do not count."""
    if re.search(r"[:\d]", text):
        return None
    text = re.sub(r"^\W*\w?\W*(?=[\[(]|[A-ZÇÖÜİŞĞ])", "", text.strip()) or text  # 'f Oya ...]' -> 'Oya ...]'
    f = fold(text)
    f = " ".join(t for t in f.split() if len(t) > 1)  # stray 'J' / 'f' from brackets
    if not f or len(f.split()) > 4:
        return None
    best, score = None, 0.0
    for c, names in SECTIONS.items():
        for n in names:
            r = SequenceMatcher(None, f, n).ratio()
            if r > score:
                best, score = c, r
    if not re.search(r"(l[ae]r|lık|lik|ler\W*)$", f.split()[-1]) and score < 0.85:
        return None  # outcome lines such as '(Kabul edilmiştir.)'
    return best if score >= (0.6 if is_bracketed(text) else 0.8) else None


def is_bracketed(text):
    t = text.strip()
    return t[:1] in "[(" or t[-1:] in "])" or t[:2].lstrip()[:1] in "[("


TALLY_LABELS = {"uye sayisi": "members", "oy verenler": "votes_cast", "kabul edenler": "yes",
                "reddedenler": "no", "cekinserler": "abstain", "oya katilmayanlar": "not_voting",
                "oya katilmiyanlar": "not_voting", "acik uyelikler": "vacant"}


def tally_of(text):
    """'Kabul edenler : 287' -> ('yes', 287)."""
    m = re.match(r"^(.*?[^\d\s:;.])[\s:;.]+(\d[\d ]{0,4})\s*$", text.strip())
    if not m or len(m[2].replace(" ", "")) > 3:
        return None
    f = fold(m[1])
    best = max(TALLY_LABELS, key=lambda k: SequenceMatcher(None, f, k).ratio())
    if SequenceMatcher(None, f, best).ratio() >= 0.75:
        return TALLY_LABELS[best], int(m[2].replace(" ", ""))
    return None


TR_ALPHA = "abcçdefgğhıijklmnoöprsştuüvyz"


def province_rank(label):
    if label == "TABİİ ÜYELER":
        return -1.0
    if label == "CUMHURBAŞKANINCA S. Ü.":
        return 99.0
    s = str(label).translate(str.maketrans({"İ": "i", "I": "ı"})).lower()
    key = [TR_ALPHA.index(c) for c in s if c in TR_ALPHA][:3] + [0, 0, 0]
    return key[0] + key[1] / 30 + key[2] / 900


def is_upper(text):
    letters = [c for c in text if c.isalpha()]
    return len(letters) >= 3 and sum(c.isupper() for c in letters) / len(letters) >= 0.75


def province_of(text, provinces):
    k = province_key(NOTES.sub("", text))
    if k in provinces:
        return provinces[k]
    if "tab" in k[:4] and "uye" in k:
        return "TABİİ ÜYELER"
    if "baskaninca" in k or k.startswith("cumhurba") or k in {"csu", "cbsu"}:
        return "CUMHURBAŞKANINCA S. Ü."
    best = max(provinces, key=lambda p: SequenceMatcher(None, k, p).ratio())
    return provinces[best] if SequenceMatcher(None, k, best).ratio() >= 0.84 else None


def is_prose(row, width):
    if len(row) < 7:
        return False
    gaps = [b.x0 - a.x1 for a, b in zip(row, row[1:])]
    return max(gaps) < 18 and (row[-1].x1 - row[0].x0) > 0.6 * width


def pick_title(rows, title):
    """Index of the result header ('... verilen oyların sonucu') belonging to this vote."""
    cands = [i for i, r in enumerate(rows) if TITLE_ROW.search(row_text(r))]
    if not cands:
        return None
    if len(cands) == 1:
        return cands[0]
    want = fold(title)[-120:]

    def score(i):
        ctx = fold(" ".join(row_text(r) for r in rows[max(0, i - 4):i + 1]))
        return SequenceMatcher(None, want, ctx[-len(want) - 40:]).ratio()
    return max(cands, key=score)


def parse_vote(pdf, first, title, provinces, npages, expected):
    pages = read_pages(pdf, first, min(first + PAGES_AFTER, npages))
    if sum(len(p.words) for p in pages) < 50:
        raise RuntimeError("no text layer; OCR (tesseract -l tur) needed")
    out, choice, prov, started, pending = [], None, None, False, ""
    tally, inferred = {}, False
    order = ["yes", "no", "abstain", "not_voting"]

    def next_section():
        """Section that follows `choice` when its printed header was lost."""
        exp = {**expected, **tally}
        for c in order[order.index(choice) + 1:]:
            if exp.get(c) is None or exp.get(c, 0) > 0:
                return c
        return None

    def emit_line(text, page):
        nonlocal prov, pending, choice, inferred
        text = text.strip()
        if not text:
            return
        if pending:
            text, pending = pending + text, ""
        if text.endswith("-") and not text.endswith(" -"):
            pending = text[:-1]
            return
        if is_upper(text):
            p = province_of(text, provinces)
            if p:
                # Lists print provinces alphabetically: a jump from late in the alphabet
                # back to the start means a new list began whose header the OCR lost.
                if prov and choice in order and province_rank(prov) >= 14 and province_rank(p) <= 3 \
                        and province_rank(p) < province_rank(prov):
                    nxt = next_section()
                    if nxt:
                        choice, inferred = nxt, True
                prov = p
                return
            toks = [t for t in text.split() if fold(t) not in GROUP_NOISE]
            if all(is_upper(t) or len(t) < 3 for t in toks):
                return  # group header ('GENEL OYLA SEÇİLEN ÜYELER') or noise
            text = " ".join(toks)
        name = NOTES.sub("", text).strip(" .,;:'\"-_|*•")
        if tally_of(name) or re.fullmatch(r"[\d\W]*", name):
            return
        if re.search(r"\d", name):
            # OCR digits inside a name ('1. Ş. Atasağun', 'Turgut 051e'): keep as letters.
            if sum(c.isdigit() for c in name) > 3:
                return
            name = name.translate(DIGIT_FIX)
        f = fold(name)
        if len(f.split()) == 1 and out and out[-1]["pdf_page"] == page and name[:1].islower():
            out[-1]["name"] += name  # continuation whose hyphen the OCR dropped
            out[-1]["name_raw"] += " " + text
            return
        if len(f.split()) >= 2 and len(f) <= 45:
            out.append({"choice": choice, "province": prov, "name": name, "name_raw": text, "pdf_page": page,
                        "section_inferred": inferred})

    for page in pages:
        rows = [r for r in group_rows(page.words) if not RUNNING_HEAD.search(row_text(r))]
        t0 = pick_title(rows, title) if (not started and page.number == first) else None
        if not started and page.number == first and t0 is None:
            started = True  # page starts directly with the lists
        seg = []

        def flush():
            if seg and started and choice not in (None, "vacant"):
                words = [w for r in seg for w in r]
                for line in column_lines(words, 0, page.width):
                    emit_line(row_text(line), page.number)
            seg.clear()

        for i, r in enumerate(rows):
            text = row_text(r)
            if not started:
                if i == t0:
                    started = True
                continue
            if choice is None:
                t = tally_of(text)
                if t:
                    tally.setdefault(t[0], t[1])
                    continue
            if choice is not None and (TITLE_ROW.search(text) or re.match(r"\W*[ÜU]ye\s+say", text)):
                flush()
                return out, tally  # next vote's result block
            sec = section_of(text)
            # The tally block repeats the section names; the first list header is bracketed.
            if sec and choice is None and not is_bracketed(text):
                continue
            if choice is None and not sec and tally:
                # First list header garbled ('[Kabvil edmUr]') or missing: the first bracketed
                # line, or the first province name, after the tallies opens the first list.
                first_word = r[0].text if r else ""
                opens_list = (is_bracketed(text) and len(text.split()) <= 4 and not re.search(r"\d", text)) or \
                    (is_upper(first_word) and province_of(first_word, provinces))
                if opens_list:
                    choice = next(c for c in order if (expected.get(c) or tally.get(c) or 1) > 0)
                    inferred = True
                    if not is_bracketed(text):
                        seg.append(r)
                    continue
            if sec:
                flush()
                choice, prov, inferred = sec, None, False
                continue
            if choice is not None and is_prose(r, page.width):
                flush()
                return out, tally
            seg.append(r)
        flush()
    return out, tally


def derived_targets(v, tally):
    """Counts implied by the tally identities, for when one printed number is misread:
    votes cast = yes + no + abstain;  not voting = members - vacancies - votes cast."""
    vals = {}
    for c in ["yes", "no", "abstain", "not_voting", "members", "vacant", "votes_cast"]:
        cand = {tally.get(c)}
        if c in ("yes", "no", "abstain", "not_voting"):
            x = getattr(v, c)
            cand.add(None if pd.isna(x) else int(x))
        if c == "votes_cast" and pd.notna(v.votes_cast):
            cand.add(int(v.votes_cast))
        if c == "members" and pd.notna(v.seats):
            cand.add(int(v.seats))
        vals[c] = {x for x in cand if x is not None}
    out = {c: set() for c in ["yes", "no", "abstain", "not_voting"]}
    sec = ["yes", "no", "abstain"]
    for vc in vals["votes_cast"]:
        for m in vals["members"]:
            for va in vals["vacant"] or {0}:
                out["not_voting"].add(m - va - vc)
        for c in sec:
            others = [o for o in sec if o != c]
            for a in vals[others[0]] or {0}:
                for b in vals[others[1]] or {0}:
                    out[c].add(vc - a - b)
    return {c: sorted(x for x in xs if x >= 0) for c, xs in out.items()}


def check_counts(v, df, tally):
    """Compare parsed list sizes with the tallies (index sheet and the PDF's own tally block).

    Either source may be misread by OCR, so a list counts as correct when it matches either.
    When the Assembly lacked a quorum the not-voting list is often not printed."""
    got = df.choice.value_counts()
    row, mism, diff = {"vote_id": v.vote_id}, [], 0
    derived = derived_targets(v, tally)
    for c in ["yes", "no", "abstain", "not_voting"]:
        idx = getattr(v, c)
        idx = None if pd.isna(idx) else int(idx)
        pdf_t = tally.get(c)
        parsed = int(got.get(c, 0))
        row.update({f"{c}_index": idx, f"{c}_pdf": pdf_t, f"{c}_parsed": parsed})
        targets = [t for t in (idx, pdf_t) if t is not None] + derived.get(c, [])
        targets = targets or [0]
        if c == "not_voting" and parsed == 0:
            continue
        if parsed not in targets:
            mism.append(c)
            diff += min(abs(parsed - t) for t in targets)
    nv_missing = int(got.get("not_voting", 0)) == 0 and any(
        (t or 0) > 0 for t in (row["not_voting_index"], row["not_voting_pdf"]))
    row["not_voting_list_printed"] = not nv_missing
    row["abs_diff"] = diff
    row["inferred_breaks"] = int(df.get("section_inferred", pd.Series(dtype=bool)).fillna(False).astype(bool).sum())
    row["status"] = ("ok" if not mism else "count mismatch: " + ",".join(mism)) + \
        (" (not-voting list not printed)" if nv_missing else "")
    return row


def npages(pdf):
    r = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True)
    return int(re.search(r"Pages:\s+(\d+)", r.stdout)[1])


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
    checks, tallies = [], {}

    v1965, df1965 = import_1965(votes)
    df1965.to_csv(NAMELISTS / f"{v1965}.csv", index=False)

    only = sys.argv[1:]
    for v in votes.itertuples():
        if only and v.vote_id not in only:
            continue
        out = NAMELISTS / f"{v.vote_id}.csv"
        if v.vote_id == v1965:
            df = df1965
        elif (MANUAL / out.name).exists():
            df = pd.read_csv(MANUAL / out.name).assign(vote_id=v.vote_id, source="hand-corrected")
            df.to_csv(out, index=False)
        else:
            pdf = PDF_DIR / f"{v.session_id}.pdf"
            if not pdf.exists():
                checks.append({"vote_id": v.vote_id, "status": "pdf missing"})
                continue
            try:
                expected = {c: (None if pd.isna(getattr(v, c)) else int(getattr(v, c)))
                            for c in ["yes", "no", "abstain", "not_voting"]}
                rows, tally = parse_vote(pdf, int(v.pdf_page), v.title, provinces, npages(pdf), expected)
            except RuntimeError as e:
                checks.append({"vote_id": v.vote_id, "status": "no text layer", "note": str(e)})
                continue
            df = pd.DataFrame(rows, columns=["choice", "province", "name", "name_raw", "pdf_page",
                                             "section_inferred"]).assign(vote_id=v.vote_id, source="pdftotext parser")
            tallies[v.vote_id] = tally
            df.to_csv(out, index=False)
        checks.append(check_counts(v, df, tallies.get(v.vote_id, {})))

    ch = pd.DataFrame(checks)
    ch.to_csv(INTERIM / "namelist_checks.csv", index=False)
    print(ch.status.str.split(":").str[0].value_counts().to_string())


if __name__ == "__main__":
    main()
