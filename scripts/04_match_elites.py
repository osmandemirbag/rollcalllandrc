"""Link every name in the parsed roll-call lists to a row of the elites dataset.

National Assembly votes are matched against the elites roster of the same
term (elites `year` = election year of the term). Senate votes are matched
against every elites person (many senators sat in the Assembly before or
after); unmatched senators stay in the data with `elite_row` empty.

Matching is one-to-one within a vote: all (list name, roster member) pairs
are scored with a string similarity on the folded full name (best of the
spellings the elites file gives, e.g. 'M. Arif ATALAY (Mehmet Arif ATALAY)'),
plus a bonus when the province agrees, and pairs are taken greedily from the
best score down. OCR sometimes runs two names together on one line; an
unmatched line of four or more words is retried as two names.

Output: data/interim/matches.csv
"""
from difflib import SequenceMatcher

import pandas as pd

from common import ELITES_CSV, INTERIM, MM_TERMS, NAMELISTS, PROCESSED, fold, name_variants, province_key, surname

ACCEPT_SAME_PROV = 0.78
ACCEPT_OTHER_PROV = 0.88
PROV_BONUS = 0.12


def load_roster():
    e = pd.read_csv(ELITES_CSV, sep="\t", low_memory=False,
                    usecols=["province_old", "name", "party", "year", "id", "donem"])
    e["elite_row"] = e.index
    e["variants"] = e.name.map(name_variants)
    e["pkey"] = e.province_old.map(province_key)
    return e


def sim(a: str, variants: list[str]) -> float:
    a_ns = a.replace(" ", "")
    best = 0.0
    for v in variants:
        r = SequenceMatcher(None, a_ns, v.replace(" ", "")).ratio()
        # Initials ('M. Arif') and dropped middle names: compare on surname + first given name too.
        sa, sv = surname(a), surname(v)
        if sa and sv:
            s_r = SequenceMatcher(None, sa, sv).ratio()
            g_r = SequenceMatcher(None, a.split()[0], v.split()[0]).ratio()
            r = max(r, 0.6 * s_r + 0.4 * g_r) if s_r > 0.8 else r
        best = max(best, r)
    return best


def match_vote(lst: pd.DataFrame, roster: pd.DataFrame) -> pd.DataFrame:
    lst = lst.reset_index(drop=True).copy()
    lst["fname"] = lst.name.map(fold)
    lst["pkey"] = lst.province.map(province_key)
    pairs = []
    for i, r in lst.iterrows():
        for j, m in roster.iterrows():
            same = r.pkey == m.pkey
            # Outside the province only consider names sharing a surname-ish string.
            if not same and SequenceMatcher(None, surname(r.fname), surname(m.variants[0]) if m.variants else "").ratio() < 0.75:
                continue
            s = sim(r.fname, m.variants)
            if s >= (ACCEPT_SAME_PROV if same else ACCEPT_OTHER_PROV):
                pairs.append((s + (PROV_BONUS if same else 0), s, same, i, j))
    pairs.sort(reverse=True)
    used_i, used_j, out = set(), set(), {}
    for score, s, same, i, j in pairs:
        if i in used_i or j in used_j:
            continue
        used_i.add(i); used_j.add(j)
        out[i] = (j, round(s, 3), "name+province" if same else "name only (province differs)")
    lst["elite_row"] = [roster.at[out[i][0], "elite_row"] if i in out else pd.NA for i in lst.index]
    lst["match_score"] = [out[i][1] if i in out else pd.NA for i in lst.index]
    lst["match_method"] = [out[i][2] if i in out else "unmatched" for i in lst.index]
    return lst.drop(columns=["fname", "pkey"])


def surname_fallback(lst, roster):
    """Badly scanned lines ('Solun us Arsîan' = Şehmus Arslan): accept a still-free
    member of the same province when exactly one has a close surname."""
    used = set(lst.elite_row.dropna())
    for i, r in lst[lst.match_method == "unmatched"].iterrows():
        f, pk = fold(r["name"]), province_key(r.province)
        if len(f.split()) < 2:
            continue
        cand = [m for m in roster[(roster.pkey == pk) & ~roster.elite_row.isin(used)].itertuples()
                if max(SequenceMatcher(None, surname(f), surname(v)).ratio() for v in m.variants) >= 0.8]
        if len(cand) == 1:
            lst.at[i, "elite_row"] = cand[0].elite_row
            lst.at[i, "match_score"] = round(sim(f, cand[0].variants), 3)
            lst.at[i, "match_method"] = "surname+province (low confidence)"
            used.add(cand[0].elite_row)
    return lst


def split_merged(lst, roster):
    """Retry unmatched 4+-word lines as two names ('Şevket Raşit Hatipoğlu Cemil Karahan')."""
    extra = []
    for i, r in lst[lst.match_method == "unmatched"].iterrows():
        toks = str(r["name"]).split()
        if len(toks) < 4:
            continue
        for k in range(2, len(toks) - 1):
            a, b = " ".join(toks[:k]), " ".join(toks[k:])
            trial = pd.DataFrame([dict(r, name=a), dict(r, name=b)]).drop(
                columns=["elite_row", "match_score", "match_method"])
            free = roster[~roster.elite_row.isin(lst.elite_row.dropna())]
            got = match_vote(trial, free)
            if (got.match_method != "unmatched").all():
                got["match_method"] += "; split merged OCR line"
                extra.append((i, got))
                break
    for i, got in extra:
        lst = pd.concat([lst.drop(index=i), got], ignore_index=True)
    return lst


def main():
    votes = pd.read_csv(PROCESSED / "votes.csv").set_index("vote_id")
    elites = load_roster()
    term_year = {t: y for t, (y, _, _) in MM_TERMS.items()}
    checks = pd.read_csv(INTERIM / "namelist_checks.csv").set_index("vote_id")
    frames = []
    for f in sorted(NAMELISTS.glob("*.csv")):
        vid = f.stem
        lst = pd.read_csv(f)
        v = votes.loc[vid]
        if v.chamber == "MM":
            roster = elites[elites.year == term_year[v.mm_term]].reset_index(drop=True)
        else:
            roster = elites.drop_duplicates("id").reset_index(drop=True)
        m = surname_fallback(split_merged(match_vote(lst, roster), roster), roster)
        m["vote_id"] = vid
        m["list_status"] = checks.status.get(vid, "unchecked")
        frames.append(m)
        rate = (m.match_method != "unmatched").mean()
        print(f"{vid}: {len(m)} names, {rate:.1%} matched")
    out = pd.concat(frames, ignore_index=True)
    out.to_csv(INTERIM / "matches.csv", index=False)
    out[out.match_method == "unmatched"].to_csv(INTERIM / "unmatched_for_review.csv", index=False)


if __name__ == "__main__":
    main()
