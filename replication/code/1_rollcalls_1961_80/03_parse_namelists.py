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

import sys as _sys
from pathlib import Path as _P
_sys.path.insert(0, str(next(p for p in _P(__file__).resolve().parents if (p / ".replication_root").exists()) / "code" / "lib"))
from common import ELITES_CSV, NAMELISTS, PDF_DIR, PROCESSED, INTERIM, VOTE1965_XLSX, fold, province_key
from layout import column_lines, group_rows, gutters, read_pages, row_text

SECTIONS = {
    "yes": ["kabul edenler"],
    "no": ["reddedenler", "red edenler", "ret edenler"],
    "abstain": ["cekinserler", "cekimserler", "cekinser"],
    "not_voting": ["oya katilmayanlar", "oya katilmiyanlar", "oylamaya katilmayanlar", "oya katilmayan"],
    "invalid": ["gecersiz oylar", "gecersiz oy", "gecersiz"],
    "vacant": ["acik uyelikler", "acik milletvekillikleri", "acik uyelik", "acik milletvekilligi",
               "acik bulunan", "munhal"],
}
# The agenda (gündem) or the next sitting follows the lists.
AGENDA = re.compile(r"G[ÜU]NDEM|B[İI]RLE[ŞS][İI]M\b|Komisyonu\s+Rapor|S\.\s*Say[ıi]s|OYA\s+KONULACAK|"
                    r"G[ÖO]R[ÜU][ŞS][ÜU]LECEK\s+[İI][ŞS]LER|BA[ŞS]KANLIK\s+D[İI]VANI", re.I)
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
    text = re.sub(r"^\s*0\s*(?=\D)", "(", text)  # '0 ı/a k atıl...' : '(' read as zero
    if re.search(r"[:\d]", text):
        return None
    text = re.sub(r"^\W*\w?\W*(?=[\[(]|[A-ZÇÖÜİŞĞ])", "", text.strip()) or text  # 'f Oya ...]' -> 'Oya ...]'
    f = fold(text)
    f = " ".join(t for t in f.split() if len(t) > 1)  # stray 'J' / 'f' from brackets
    if not f or len(f.split()) > 4:
        return None
    best, score = None, 0.0
    squeezed = f.replace(" ", "")
    for c, names in SECTIONS.items():
        for n in names:
            r = max(SequenceMatcher(None, f, n).ratio(),
                    SequenceMatcher(None, squeezed, n.replace(" ", "")).ratio())
            if r > score:
                best, score = c, r
    if re.search(r"edil|mis|mış|kanunlas|yok|vardir|saglan|kabul ol|redd?edil", f):
        return None  # outcome lines such as '(Madde kabul edilmiştir.)'
    if not re.search(r"(l[ae]r|lık|lik|ler\W*)$", f.split()[-1]) and score < 0.85 and not is_bracketed(text):
        return None  # outcome lines such as '(Kabul edilmiştir.)'
    return best if score >= (0.6 if is_bracketed(text) else 0.8) else None


def header_is_clear(text):
    f = " ".join(t for t in fold(text).split() if len(t) > 1)
    return max(SequenceMatcher(None, f, n).ratio() for ns in SECTIONS.values() for n in ns) >= 0.85


def relabel_sections(df, targets):
    """A list whose header was lost or garbled may carry the wrong label: if its size fits
    another section that came out empty, move it there."""
    if df.empty or "section_inferred" not in df:
        return df
    counts = df.choice.value_counts()
    for c in ["yes", "no", "abstain", "not_voting"]:
        n = int(counts.get(c, 0))
        if not n or n in targets.get(c, []):
            continue
        rows = df.choice == c
        if not df.loc[rows, "section_inferred"].any():
            continue
        for d in ["yes", "no", "abstain", "not_voting"]:
            if d != c and int(counts.get(d, 0)) == 0 and n in targets.get(d, []):
                df.loc[rows & df.section_inferred.astype(bool), "choice"] = d
                return relabel_sections(df, targets)
    return df


def is_bracketed(text):
    t = text.strip()
    return t[:1] in "[(" or t[-1:] in "])" or t[:2].lstrip()[:1] in "[("


TALLY_LABELS = {"uye sayisi": "members", "oy verenler": "votes_cast", "kabul edenler": "yes",
                "reddedenler": "no", "cekinserler": "abstain", "oya katilmayanlar": "not_voting",
                "oya katilmiyanlar": "not_voting", "acik uyelikler": "vacant", "gecersiz oylar": "invalid"}


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
    lower = sum(w.text[:1].islower() for w in row) / len(row)
    # Names are capitalised; running prose is mostly lower-case words.
    return max(gaps) < 18 and (row[-1].x1 - row[0].x0) > 0.6 * width and lower >= 0.5


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
            if text[:1].isupper() and not text.isupper():
                # The continuation landed elsewhere; keep the stem ('Mithat Şükrü Çavdar').
                stem, pending = pending, ""
                emit_line(stem, page)
            else:
                text, pending = pending + text, ""
        if text.endswith("-") and not text.endswith(" -"):
            pending = text[:-1]
            return
        # A province header glued to a name on the same line ('TEKİRDAĞ Kâmil Coşkunoğlu',
        # 'İhsan Topaloğlu MANİSA'): split it off.
        toks = text.split()
        if len(toks) >= 3 and not is_upper(text):
            for n in (2, 1):
                head, tail = " ".join(toks[:n]), " ".join(toks[n:])
                if is_upper(head) and len(fold(head)) >= 3 and province_of(head, provinces):
                    emit_line(head, page)
                    emit_line(tail, page)
                    return
                head, tail = " ".join(toks[:-n]), " ".join(toks[-n:])
                if is_upper(tail) and len(fold(tail)) >= 3 and province_of(tail, provinces):
                    emit_line(head, page)
                    emit_line(tail, page)
                    return
        if is_upper(text):
            p = province_of(text, provinces)
            if p:
                # Lists print provinces alphabetically: a jump from late in the alphabet
                # back to the start means a new list began whose header the OCR lost.
                # The Senate lists end with the presidential-quota group: any province after it
                # starts a new list. Otherwise require a clear jump back in the alphabet.
                after_quota = prov == "CUMHURBAŞKANINCA S. Ü." and p != prov and province_rank(p) <= 3
                if prov and choice in order and (after_quota or (
                        province_rank(p) <= 3 and province_rank(p) <= province_rank(prov) - 6)):
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
        # Column gutters of the whole page, for bands too short to show their own.
        body = [w for r in rows if not section_of(row_text(r)) and not TITLE_ROW.search(row_text(r))
                and not tally_of(row_text(r)) for w in r]
        page_cuts = gutters(body, 0, page.width)

        def flush():
            if seg and started and choice not in (None, "vacant"):
                words = [w for r in seg for w in r]
                for line in column_lines(words, 0, page.width, page_cuts):
                    emit_line(row_text(line), page.number)
            seg.clear()

        for i, r in enumerate(rows):
            text = row_text(r)
            if not started:
                if i == t0:
                    started = True
                continue
            if choice is None or not out:
                t = tally_of(text)
                if t:
                    # Tallies before any name: a garbled outcome line was taken for a header.
                    seg.clear()
                    choice = None
                    tally.setdefault(t[0], t[1])
                    continue
            if choice is not None and out and (TITLE_ROW.search(text) or re.match(r"\W*[ÜU]ye\s+say", text)
                                               or AGENDA.search(text)):
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
                choice, prov, inferred = sec, None, not header_is_clear(text)
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
    invalid = tally.get("invalid") or 0  # 'Geçersiz oylar' count among the votes cast
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
                    out[c].add(vc - a - b - invalid)
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
        row.update({f"{c}_index": idx, f"{c}_pdf": pdf_t, f"{c}_parsed": parsed,
                    f"{c}_derived": " ".join(map(str, derived.get(c, [])))})
        targets = [t for t in (idx, pdf_t) if t is not None] + derived.get(c, [])
        targets = targets or [0]
        if c == "not_voting" and parsed == 0:
            continue
        if parsed not in targets:
            mism.append(c)
            diff += min(abs(parsed - t) for t in targets)
    row["invalid_parsed"] = int(got.get("invalid", 0))
    row["invalid_pdf"] = tally.get("invalid")
    row["abs_diff"] = diff
    row["inferred_breaks"] = int(df.get("section_inferred", pd.Series(dtype=bool)).fillna(False).astype(bool).sum())
    nv_missing = int(got.get("not_voting", 0)) == 0 and any(
        (t or 0) > 0 for t in (row["not_voting_index"], row["not_voting_pdf"]))
    row["not_voting_list_printed"] = not nv_missing
    # Tallies can be misread while the lists are right: accept when the lists add up to the
    # seats less vacancies and the votes cast agree.
    if mism:
        members = {x for x in (tally.get("members"), None if pd.isna(v.seats) else int(v.seats)) if x}
        vac = tally.get("vacant", 0) or 0
        vc = {x for x in (tally.get("votes_cast"), None if pd.isna(v.votes_cast) else int(v.votes_cast)) if x}
        cast = sum(int(got.get(c, 0)) for c in ["yes", "no", "abstain", "invalid"])
        total = cast + int(got.get("not_voting", 0))
        if not nv_missing and cast in vc and total in {m - vac for m in members}:
            row["identity_ok"] = True
            mism = []
    row["status"] = ("ok" if not mism else "count mismatch: " + ",".join(mism)) + \
        (" (not-voting list not printed)" if nv_missing else "")
    return row


def apply_patches(df, patches, vid):
    """Hand corrections checked against the page images (data/interim/namelist_patches.csv).
    add: insert a name the OCR lost; drop: remove an OCR fragment or merged line;
    link: keep the line, the person is fixed in 04_match_elites.py."""
    df = df.copy()
    for p in patches.itertuples():
        if p.action == "drop":
            hit = df.index[(df.name == p.name) & (df.choice == p.choice)]
            if len(hit) != 1:
                raise ValueError(f"{vid}: patch drop '{p.name}' matches {len(hit)} rows")
            df = df.drop(index=hit)
        elif p.action == "add":
            df = pd.concat([df, pd.DataFrame([{"choice": p.choice, "province": p.province, "name": p.name,
                                               "name_raw": "", "pdf_page": None, "section_inferred": False,
                                               "vote_id": vid, "source": "hand-added (page image)"}])],
                           ignore_index=True)
    return df


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
    patches = pd.read_csv(INTERIM / "namelist_patches.csv") if (INTERIM / "namelist_patches.csv").exists() \
        else pd.DataFrame(columns=["vote_id", "action", "choice", "province", "name", "note"])
    patch_votes = set(patches.vote_id)
    verified = pd.read_csv(INTERIM / "verified_votes.csv").set_index("vote_id") \
        if (INTERIM / "verified_votes.csv").exists() else pd.DataFrame(columns=["verified_counts"])

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
        tally = tallies.get(v.vote_id, {})
        if df.get("source", pd.Series(["x"])).iloc[0] == "pdftotext parser" if len(df) else False:
            der = derived_targets(v, tally)
            tg = {c: [x for x in (None if pd.isna(getattr(v, c)) else int(getattr(v, c)), tally.get(c))
                      if x is not None] + der.get(c, []) for c in ["yes", "no", "abstain", "not_voting"]}
            df = relabel_sections(df, tg)
            df.to_csv(out, index=False)
        if v.vote_id in patch_votes:
            df = apply_patches(df, patches[patches.vote_id == v.vote_id], v.vote_id)
            df.to_csv(out, index=False)
        row = check_counts(v, df, tally)
        if v.vote_id in verified.index:
            want = [int(x) for x in str(verified.at[v.vote_id, "verified_counts"]).split("/")]
            have = [row[f"{c}_parsed"] for c in ["yes", "no", "abstain", "not_voting"]]
            row["status"] = "ok (verified against page images)" if want == have else \
                f"count mismatch: differs from hand-verified {want}"
        checks.append(row)

    ch = pd.DataFrame(checks)
    ch.to_csv(INTERIM / "namelist_checks.csv", index=False)
    print(ch.status.str.split(":").str[0].value_counts().to_string())


if __name__ == "__main__":
    main()
