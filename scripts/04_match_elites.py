"""Link every name in the parsed roll-call lists to a person, then reconcile counts.

National Assembly (MM): names are matched to the elites roster of the same
term (elites `year` = election year of the term).

Senate (CS): the elites dataset has no senators, so a senator roster is built
from the lists themselves: names are matched vote by vote against the
senators seen so far, and new ones are added (`senate_person_id`). Each
senator is then linked to an elites row when they also served as a deputy
(same name, high similarity).

Matching is one-to-one within a vote. Pairs are scored with a string
similarity on the folded name without spaces (best of the spellings the
elites file gives), or on surname + first name when the surnames agree, plus
a bonus when the province agrees, and taken greedily from the best score
down. An unmatched line of four or more words is retried as two names.

Reconciliation, per vote, with the counts in data/interim/namelist_checks.csv:
  * a list that is too long by k, and holds exactly k names that match nobody,
    loses those k lines (OCR fragments) -> row_status 'dropped'
  * a list that is too short by k, when every other list is right and exactly k
    members who were sitting at the time are absent from all lists, gets those
    members -> row_status 'added (by elimination)'. Sitting = on a list of this
    chamber both within 120 days before and after the vote.

Outputs: data/interim/matches.csv, data/interim/senate_persons.csv,
         data/interim/reconciliation.csv, data/interim/unmatched_for_review.csv
"""
import numpy as np
import pandas as pd
from rapidfuzz import fuzz
from rapidfuzz.process import cdist

from common import ELITES_CSV, INTERIM, MM_TERMS, NAMELISTS, PROCESSED, fold, name_variants, province_key, surname

ACCEPT_SAME_PROV = 78
ACCEPT_OTHER_PROV = 88
PROV_BONUS = 12
SECTIONS = ["yes", "no", "abstain", "not_voting"]
SITTING_WINDOW = pd.Timedelta(days=120)


# ---------------------------------------------------------------- scoring
def variant_table(names, pkeys):
    """One row per spelling: owner index, spelling without spaces, surname, first name."""
    rows = []
    for k, (vs, pk) in enumerate(zip(names, pkeys)):
        for v in vs:
            if v:
                rows.append((k, v.replace(" ", ""), surname(v), v.split()[0], pk))
    return pd.DataFrame(rows, columns=["owner", "ns", "sur", "first", "pkey"])


def score_matrix(lst_f, lst_pk, vt, n_owner):
    """Best score of each list name against each owner (people x spellings reduced)."""
    if vt.empty or not lst_f:
        return np.zeros((len(lst_f), n_owner)), np.zeros((len(lst_f), n_owner), bool)
    ns = [f.replace(" ", "") for f in lst_f]
    full = cdist(ns, vt.ns.tolist(), scorer=fuzz.ratio, workers=-1)
    sur = cdist([surname(f) for f in lst_f], vt.sur.tolist(), scorer=fuzz.ratio, workers=-1)
    first = cdist([f.split()[0] if f else "" for f in lst_f], vt["first"].tolist(), scorer=fuzz.ratio, workers=-1)
    alt = np.where(sur > 80, 0.6 * sur + 0.4 * first, 0)
    s = np.maximum(full, alt)
    owners = vt.owner.to_numpy()
    best = np.zeros((len(lst_f), n_owner))
    np.maximum.at(best.T, owners, s.T)
    same = np.zeros((len(lst_f), n_owner), bool)
    vpk = vt.groupby("owner").pkey.first().reindex(range(n_owner)).to_numpy()
    for i, pk in enumerate(lst_pk):
        same[i] = vpk == pk
    return best, same


def assign(best, same, taken=()):
    """Greedy one-to-one assignment; returns {list idx: (owner, score, same_province)}."""
    ok = np.where(same, best >= ACCEPT_SAME_PROV, best >= ACCEPT_OTHER_PROV)
    ii, jj = np.nonzero(ok)
    key = best[ii, jj] + np.where(same[ii, jj], PROV_BONUS, 0)
    order = np.argsort(-key, kind="stable")
    used_i, used_j, out = set(), set(taken), {}
    for k in order:
        i, j = int(ii[k]), int(jj[k])
        if i in used_i or j in used_j:
            continue
        used_i.add(i); used_j.add(j)
        out[i] = (j, round(float(best[i, j]), 1), bool(same[i, j]))
    return out


def match_list(lst, vt, n_owner):
    """Match one vote's names to owners; handles merged OCR lines and a surname fallback."""
    lst = lst.reset_index(drop=True).copy()
    f = lst.name.map(fold).tolist()
    pk = lst.province.map(province_key).tolist()
    best, same = score_matrix(f, pk, vt, n_owner)
    got = assign(best, same)
    lst["owner"] = [got[i][0] if i in got else -1 for i in lst.index]
    lst["match_score"] = [got[i][1] if i in got else np.nan for i in lst.index]
    lst["match_method"] = ["name+province" if i in got and got[i][2] else
                           "name only (province differs)" if i in got else "unmatched" for i in lst.index]

    # Two names run together on one OCR line.
    extra = []
    for i in lst.index[lst.match_method == "unmatched"]:
        toks = str(lst.at[i, "name"]).split()
        if len(toks) < 4:
            continue
        taken = set(lst.owner[lst.owner >= 0])
        for k in range(2, len(toks) - 1):
            parts = [" ".join(toks[:k]), " ".join(toks[k:])]
            bf, sf = score_matrix([fold(p) for p in parts], [pk[i]] * 2, vt, n_owner)
            g = assign(bf, sf, taken)
            if len(g) == 2:
                for t, ptxt in enumerate(parts):
                    r = lst.loc[i].copy()
                    r["name"], r["owner"], r["match_score"] = ptxt, g[t][0], g[t][1]
                    r["match_method"] = ("name+province" if g[t][2] else "name only (province differs)") + \
                        "; split merged OCR line"
                    extra.append(r)
                lst = lst.drop(index=i)
                break
    if extra:
        lst = pd.concat([lst, pd.DataFrame(extra)], ignore_index=True)

    # Badly scanned line: the only free member of that province with a close surname.
    taken = set(lst.owner[lst.owner >= 0])
    vt_sur = vt.groupby("owner").agg(sur=("sur", list), pkey=("pkey", "first"))
    for i in lst.index[lst.match_method == "unmatched"]:
        f_i = fold(lst.at[i, "name"])
        if len(f_i.split()) < 2:
            continue
        pk_i = province_key(lst.at[i, "province"])
        cand = [o for o, r in vt_sur[vt_sur.pkey == pk_i].iterrows()
                if o not in taken and max(fuzz.ratio(surname(f_i), s) for s in r.sur) >= 80]
        if len(cand) == 1:
            lst.at[i, "owner"] = cand[0]
            lst.at[i, "match_method"] = "surname+province (low confidence)"
            taken.add(cand[0])
    return lst


# ---------------------------------------------------------------- reconciliation
def targets_for(check):
    """Most plausible printed count per section: the candidate closest to the parse."""
    out = {}
    for c in SECTIONS:
        cands = [check.get(f"{c}_index"), check.get(f"{c}_pdf")]
        cands = [int(x) for x in cands if pd.notna(x)]
        der = check.get(f"{c}_derived")
        if isinstance(der, str) and der.strip():
            cands += [int(x) for x in der.split()]
        elif pd.notna(der) and not isinstance(der, str):
            cands.append(int(der))
        out[c] = sorted(set(cands))
    return out


def rescue_unmatched(m, variants, dates, min_score=50, margin=8):
    """Match garbled lines ('Ali Etfbdk') to the sitting members missing from the same vote.

    The candidate set is small (members sitting at the time but on no list of this vote),
    so a loose similarity is safe; the best candidate must also clearly beat the runner-up."""
    n = 0
    for vid in m.vote_id[(m.match_method == "unmatched")].unique():
        rows = m.index[(m.vote_id == vid) & (m.match_method == "unmatched")]
        rows = [i for i in rows if len(fold(m.at[i, "name"]).split()) >= 2]
        if not rows:
            continue
        here = set(m.person_key[(m.vote_id == vid)].dropna())
        miss = sorted(sitting_members(m, vid, dates[vid]) - here)
        if not miss:
            continue
        cand = [(p, v.replace(" ", "")) for p in miss for v in variants.get(p, [])]
        if not cand:
            continue
        sc = cdist([fold(m.at[i, "name"]).replace(" ", "") for i in rows], [c[1] for c in cand],
                   scorer=fuzz.ratio, workers=-1)
        owners = [c[0] for c in cand]
        pairs = []
        for a, i in enumerate(rows):
            best = {}
            for b, p in enumerate(owners):
                best[p] = max(best.get(p, 0), sc[a, b])
            ranked = sorted(best.items(), key=lambda x: -x[1])
            top, second = ranked[0], (ranked[1][1] if len(ranked) > 1 else 0)
            if top[1] >= min_score and top[1] - second >= margin:
                pairs.append((top[1], i, top[0]))
        used = set()
        for score, i, p in sorted(pairs, reverse=True):
            if p in used:
                continue
            used.add(p)
            m.at[i, "person_key"] = p
            m.at[i, "match_score"] = round(float(score), 1)
            m.at[i, "match_method"] = "rescued (garbled name of a sitting member)"
            ref = m[m.person_key == p].iloc[0]
            for c in ("elite_row", "senate_person_id", "person_name"):
                m.at[i, c] = ref[c]
            n += 1
    print(f"rescued {n} garbled names")
    return m


def reconcile(m, checks, chamber_dates):
    m = m.copy()
    m["row_status"] = "kept"
    log = []
    key = "person_key"
    for vid, g in m.groupby("vote_id", sort=False):
        ch = checks.get(vid, {})
        if not ch:
            continue
        if str(ch.get("status", "")).startswith("ok"):
            log.append({"vote_id": vid, "final_status": "ok", "changes": ""})
            continue
        tg = targets_for(ch)
        nv_printed = bool(ch.get("not_voting_list_printed", True))
        counts = g.choice.value_counts()
        status = []
        # 1. drop junk lines from lists that are too long
        for c in SECTIONS:
            if c == "not_voting" and not nv_printed:
                continue
            n = int(counts.get(c, 0))
            if not tg[c] or n in tg[c]:
                continue
            over = n - min(tg[c], key=lambda t: abs(t - n))
            junk = g.index[(g.choice == c) & (g.match_method == "unmatched")]
            if over > 0 and len(junk) == over:
                m.loc[junk, "row_status"] = "dropped (OCR fragment)"
                status.append(f"dropped {over} from {c}")
            elif over > 0 and len(junk) > over and NAME_BANK.get(vid[:2]):
                # Drop the lines least like any member's name, if they are clearly not names.
                bank = NAME_BANK[vid[:2]]
                sc = cdist([fold(x).replace(" ", "") for x in m.loc[junk, "name"]], bank,
                           scorer=fuzz.ratio, workers=-1).max(axis=1)
                worst = [junk[i] for i in np.argsort(sc)[:over] if sc[i] < 60]
                if len(worst) == over:
                    m.loc[worst, "row_status"] = "dropped (OCR fragment)"
                    status.append(f"dropped {over} least name-like from {c}")
        # 2. add sitting members absent from every list, when one list is short
        g = m.loc[m.vote_id == vid]
        g = g[g.row_status == "kept"]
        counts = g.choice.value_counts()
        short = {}
        for c in SECTIONS:
            if c == "not_voting" and not nv_printed:
                continue
            n = int(counts.get(c, 0))
            if tg[c] and n not in tg[c]:
                t = min(tg[c], key=lambda t: abs(t - n))
                short[c] = t - n
        if len(short) == 1 and list(short.values())[0] > 0:
            c, k = next(iter(short.items()))
            d = chamber_dates[vid]
            sitting = sitting_members(m, vid, d)
            missing = sitting - set(g[key].dropna())
            if len(missing) == k:
                add = []
                for p in sorted(missing):
                    ref = m[(m[key] == p)].iloc[0]
                    add.append({"vote_id": vid, "choice": c, "province": ref.province, "name": ref.person_name,
                                "name_raw": "", "pdf_page": np.nan, "section_inferred": False,
                                "source": "inferred", key: p, "elite_row": ref.elite_row,
                                "senate_person_id": ref.senate_person_id, "person_name": ref.person_name,
                                "match_score": np.nan, "match_method": "inferred by elimination",
                                "row_status": "added (by elimination)"})
                m = pd.concat([m, pd.DataFrame(add)], ignore_index=True)
                status.append(f"added {k} to {c}")
        g = m[(m.vote_id == vid) & (m.row_status != "dropped (OCR fragment)")]
        counts = g.choice.value_counts()
        exact = all((not tg[c]) or int(counts.get(c, 0)) in tg[c] or (c == "not_voting" and not nv_printed)
                    for c in SECTIONS)
        log.append({"vote_id": vid, "final_status": ("ok" if exact else "count mismatch") +
                    (" after reconciliation" if status and exact else ""), "changes": "; ".join(status)})
    return m, pd.DataFrame(log)


_SEEN = {}
NAME_BANK = {}  # chamber -> spellings of matched names


def sitting_members(m, vid, d):
    """People on a list of the same chamber both shortly before and after date d."""
    ch = vid[:2]
    if ch not in _SEEN:
        k = m[(m.vote_id.str[:2] == ch) & m.person_key.notna()]
        _SEEN[ch] = k.groupby("person_key").date.agg(["min", "max"])
    s = _SEEN[ch]
    s = s[(s["min"] <= d) & (s["max"] >= d) & (s["min"] >= d - 8 * SITTING_WINDOW)]
    # Present on some list in the window on both sides.
    k = m[(m.vote_id.str[:2] == ch) & m.person_key.isin(s.index) & (m.vote_id != vid)]
    before = set(k[(k.date < d) & (k.date >= d - SITTING_WINDOW)].person_key)
    after = set(k[(k.date > d) & (k.date <= d + SITTING_WINDOW)].person_key)
    same_day = set(k[k.date == d].person_key)
    return (before & after) | (same_day & (before | after))


def merge_rare_senators(m, min_votes=3):
    """A senator 'seen' in one or two votes is mostly an OCR fragment of a real one.

    Re-match those rows against the established senators (seen in >= min_votes
    votes) not already on that vote's lists, with a looser threshold; rows that
    still match nobody become unmatched so reconciliation can drop them."""
    s = m.senate_person_id.notna()
    n = m[s].groupby("senate_person_id").vote_id.nunique()
    solid = n.index[n >= min_votes]
    rare_rows = m.index[s & m.senate_person_id.isin(n.index[n < min_votes])]
    ref = m[s & m.senate_person_id.isin(solid)]
    prof = ref.groupby("senate_person_id").agg(names=("name", lambda x: list({fold(v) for v in x})[:12]),
                                               province=("province", lambda x: x.mode().iat[0] if x.notna().any() else None))
    ids = prof.index.tolist()
    vt = variant_table(prof.names.tolist(), prof.province.map(province_key).tolist())
    on_vote = ref.groupby("vote_id").senate_person_id.agg(set).to_dict()
    for vid, g in m.loc[rare_rows].groupby("vote_id"):
        taken = {ids.index(p) for p in on_vote.get(vid, set())}
        f = g.name.map(fold).tolist()
        best, same = score_matrix(f, g.province.map(province_key).tolist(), vt, len(ids))
        best = np.where(same, best + 8, best)  # looser: an OCR-garbled copy of a known senator
        got = assign(best, same, taken)
        for k, idx in enumerate(g.index):
            if k in got:
                m.at[idx, "senate_person_id"] = ids[got[k][0]]
                m.at[idx, "match_score"] = got[k][1]
                m.at[idx, "match_method"] = "known senator (OCR-garbled)"
            else:
                m.at[idx, "senate_person_id"] = np.nan
                m.at[idx, "match_method"] = "unmatched"
    m["person_key"] = m.person_key.where(~s, m.senate_person_id)
    return m


# ---------------------------------------------------------------- main
def load_elites():
    e = pd.read_csv(ELITES_CSV, sep="\t", low_memory=False,
                    usecols=["province_old", "name", "party", "year", "id", "donem"])
    e["elite_row"] = e.index
    e["variants"] = e.name.map(name_variants)
    e["pkey"] = e.province_old.map(province_key)
    return e


def main():
    votes = pd.read_csv(PROCESSED / "votes.csv", parse_dates=["date"]).set_index("vote_id")
    elites = load_elites()
    term_year = {t: y for t, (y, _, _) in MM_TERMS.items()}
    checks = pd.read_csv(INTERIM / "namelist_checks.csv").set_index("vote_id")
    lists = {f.stem: pd.read_csv(f) for f in sorted(NAMELISTS.glob("*.csv"))}
    lists = {k: v for k, v in lists.items() if len(v) and k in votes.index}
    frames = []

    # Assembly
    for term, year in term_year.items():
        roster = elites[elites.year == year].reset_index(drop=True)
        vt = variant_table(roster.variants, roster.pkey)
        for vid in votes.index[(votes.chamber == "MM") & (votes.mm_term == term)]:
            if vid not in lists:
                continue
            r = match_list(lists[vid], vt, len(roster))
            r["elite_row"] = r.owner.map(lambda o: roster.at[o, "elite_row"] if o >= 0 else np.nan)
            r["person_key"] = r.elite_row.map(lambda x: f"E{int(x)}" if pd.notna(x) else np.nan)
            r["person_name"] = r.owner.map(lambda o: roster.at[o, "name"] if o >= 0 else np.nan)
            r["senate_person_id"] = np.nan
            r["vote_id"] = vid
            frames.append(r.drop(columns="owner"))
            print(f"{vid}: {len(r)} names, {(r.match_method != 'unmatched').mean():.1%} matched")

    # Senate: build the roster from the lists, in date order.
    persons = []  # dicts: id, name, province, variants
    for vid in votes[votes.chamber != "MM"].sort_values("date").index:
        if vid not in lists:
            continue
        lst = lists[vid]
        vt = variant_table([p["variants"] for p in persons], [p["pkey"] for p in persons])
        r = match_list(lst, vt, len(persons))
        for i in r.index[r.owner < 0]:
            f = fold(r.at[i, "name"])
            if len(f.split()) < 2:
                continue
            persons.append({"id": len(persons), "name": r.at[i, "name"], "province": r.at[i, "province"],
                            "pkey": province_key(r.at[i, "province"]), "variants": [f]})
            r.at[i, "owner"] = persons[-1]["id"]
            r.at[i, "match_method"] = "new senator"
        for i in r.index[r.owner >= 0]:
            p = persons[int(r.at[i, "owner"])]
            f = fold(r.at[i, "name"])
            if f not in p["variants"] and len(p["variants"]) < 12:
                p["variants"].append(f)  # learn OCR spellings
        r["senate_person_id"] = r.owner.map(lambda o: f"S{int(o):04d}" if o >= 0 else np.nan)
        r["person_key"] = r.senate_person_id
        r["vote_id"] = vid
        frames.append(r.drop(columns="owner"))
        print(f"{vid}: {len(r)} names, {(r.match_method != 'unmatched').mean():.1%} matched")

    m = pd.concat(frames, ignore_index=True)
    m = merge_rare_senators(m)

    # Senator display name = most frequent spelling; link to elites when also a deputy.
    sp = m[m.senate_person_id.notna()]
    spn = sp.groupby("senate_person_id").agg(person_name=("name", lambda s: s.mode().iat[0]),
                                             province=("province", lambda s: s.mode().iat[0] if s.notna().any() else None),
                                             n_votes=("vote_id", "nunique"))
    ev = variant_table(elites.variants, elites.pkey)
    best, same = score_matrix(spn.person_name.map(fold).tolist(), spn.province.map(province_key).tolist(),
                              ev, len(elites))
    link = np.where(same, best >= 92, best >= 97)
    spn["elite_row"] = [int(elites.at[int(np.argmax(np.where(link[i], best[i], -1))), "elite_row"])
                        if link[i].any() else np.nan for i in range(len(spn))]
    spn.to_csv(INTERIM / "senate_persons.csv")
    is_s = m.senate_person_id.notna()
    m.loc[is_s, "person_name"] = m.loc[is_s, "senate_person_id"].map(spn.person_name)
    m.loc[is_s, "elite_row"] = m.loc[is_s, "senate_person_id"].map(spn.elite_row)

    m["date"] = m.vote_id.map(votes.date)
    dates = votes.date.to_dict()
    variants = {}
    for p, nm in m[m.person_key.notna()].groupby("person_key").name:
        variants[p] = list({fold(x) for x in nm})[:15]
    for _, e in elites.iterrows():
        k = f"E{e.elite_row}"
        if k in variants:
            variants[k] += e.variants
    m = rescue_unmatched(m, variants, dates)
    for ch in ("mm", "cs"):
        k = m[(m.vote_id.str[:2] == ch) & m.person_key.notna()]
        NAME_BANK[ch] = sorted({fold(x).replace(" ", "") for x in k.name.dropna()})[:20000]
    m, log = reconcile(m, checks.to_dict("index"), dates)
    m = m.drop(columns="date")
    m["list_status"] = m.vote_id.map(checks.status)
    m.to_csv(INTERIM / "matches.csv", index=False)
    log.to_csv(INTERIM / "reconciliation.csv", index=False)
    m[(m.match_method == "unmatched") & (m.row_status == "kept")].to_csv(
        INTERIM / "unmatched_for_review.csv", index=False)
    print(log.final_status.value_counts().to_string())


if __name__ == "__main__":
    main()
