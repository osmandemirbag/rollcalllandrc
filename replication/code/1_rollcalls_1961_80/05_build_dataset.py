"""Assemble the final land and agriculture roll-call dataset merged with the elites data.

Outputs (data/processed/):
  votes_quality.csv          one row per roll call: metadata, printed and parsed counts, quality flag
  rollcall_long.csv          one row per member x vote (vote metadata + person + elite covariates)
  rollcall_wide_elites.csv   elites rows for the 1961-1977 Assembly cohorts, all original columns,
                             plus one column per Assembly roll call (codes below)
  rollcall_wide_senate.csv   one row per senator, one column per Senate roll call
  TBMM_land_agri_rollcalls_1961-1980.xlsx  the tables above (long table without covariates) + codebook

Matrix codes (Voteview convention):
  1 yes   6 no   7 abstain   9 not voting
  0 not a member in that term (Assembly) / not seen in the Senate at the time
  blank: member of that term but on none of the printed lists (vacancy, OCR loss)
"""
import importlib.util

import numpy as np
import pandas as pd

import sys as _sys
from pathlib import Path as _P
_sys.path.insert(0, str(next(p for p in _P(__file__).resolve().parents if (p / ".replication_root").exists()) / "code" / "lib"))
from common import CAST_CODES, ELITES_CSV, INTERIM, MM_TERMS, PROCESSED, ROOT

ELITE_COVARIATES = ["id", "name", "party", "province_old", "year", "donem", "government",
                    "coalition", "female", "age", "birthdate", "education", "majororoccupation",
                    "law_education", "military_education", "religious_education", "rural_population_pct",
                    "parliamentaryexperience", "switchedparties", "local"]
SECTIONS = ["yes", "no", "abstain", "not_voting"]


def load_matcher():
    spec = importlib.util.spec_from_file_location("m04", Path(__file__).resolve().parent / "04_match_elites.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def derive_not_voting(m, votes, checks):
    """Assembly votes that failed for lack of quorum often omit the not-voting list.
    Everyone sitting at the time and on none of the printed lists did not vote."""
    m04 = load_matcher()
    tmp = m.assign(date=m.vote_id.map(votes.set_index("vote_id").date))
    add = []
    for vid in checks.index[~checks.not_voting_list_printed.astype(bool)]:
        if not vid.startswith("mm"):
            continue
        d = votes.loc[votes.vote_id == vid, "date"].iat[0]
        here = set(tmp.person_key[tmp.vote_id == vid].dropna())
        for p in sorted(m04.sitting_members(tmp, vid, d) - here):
            ref = tmp[tmp.person_key == p].iloc[0]
            add.append({"vote_id": vid, "choice": "not_voting", "province": ref.province,
                        "name": ref.person_name, "person_key": p, "elite_row": ref.elite_row,
                        "person_name": ref.person_name, "match_method": "derived",
                        "row_status": "derived (not-voting list not printed)", "source": "derived"})
    return pd.concat([m, pd.DataFrame(add)], ignore_index=True)


def main():
    votes = pd.read_csv(PROCESSED / "votes.csv", parse_dates=["date"])
    elites = pd.read_csv(ELITES_CSV, sep="\t", low_memory=False)
    elites.index.name = "elite_row"
    checks = pd.read_csv(INTERIM / "namelist_checks.csv").set_index("vote_id")
    recon = pd.read_csv(INTERIM / "reconciliation.csv").set_index("vote_id")
    senators = pd.read_csv(INTERIM / "senate_persons.csv")
    m = pd.read_csv(INTERIM / "matches.csv", low_memory=False)
    m = m[m.row_status != "dropped (OCR fragment)"]
    m = derive_not_voting(m, votes, checks)

    # ---- vote-level quality --------------------------------------------------
    cnt = pd.crosstab(m.vote_id, m.choice).reindex(columns=SECTIONS, fill_value=0)
    q = votes.set_index("vote_id")
    for c in SECTIONS:
        q[f"{c}_listed"] = cnt[c].reindex(q.index).fillna(0).astype(int)
    q["quality"] = recon.final_status.reindex(q.index).fillna("no name list")
    q["reconciliation_changes"] = recon.changes.reindex(q.index)
    q["not_voting_list_printed"] = checks.not_voting_list_printed.reindex(q.index)
    off = []
    for vid, ch in checks.iterrows():
        n = cnt.loc[vid] if vid in cnt.index else pd.Series(0, index=SECTIONS)
        tot = 0
        for c in SECTIONS:
            cands = [int(x) for x in (ch[f"{c}_index"], ch[f"{c}_pdf"]) if pd.notna(x)]
            der = ch.get(f"{c}_derived")
            if isinstance(der, str) and der.strip():
                cands += [int(x) for x in der.split()]
            if cands and int(n[c]) not in cands:
                tot += min(abs(int(n[c]) - t) for t in cands)
        off.append((vid, tot))
    q["names_off_vs_tally"] = pd.Series(dict(off)).reindex(q.index)
    q.loc[q.quality.str.startswith("ok"), "names_off_vs_tally"] = 0
    q = q.reset_index()
    q.to_csv(PROCESSED / "votes_quality.csv", index=False)

    # ---- long -------------------------------------------------------------------
    cov = elites[ELITE_COVARIATES].add_prefix("elite_")
    long = (m.rename(columns={"name": "list_name", "province": "list_province", "name_raw": "list_name_raw",
                              "pdf_page": "list_pdf_page"})
            .merge(q[["vote_id", "date", "chamber", "mm_term", "category", "topic_group", "title",
                      "outcome_class", "quality"]], on="vote_id", how="left")
            .merge(cov, left_on="elite_row", right_index=True, how="left"))
    long["elite_party_at_election"] = long.elite_party.str.split("/").str[0].str.strip()
    long["cast_code"] = long.choice.map(CAST_CODES)
    # Office or leave printed beside the name; tells excused from plain absence.
    raw = long.list_name_raw.fillna("")
    long["status_note"] = np.select(
        [raw.str.contains(r"Başbakan", regex=True),
         raw.str.contains(r"B[sş]k\.?\s*V|Başkan\s*V|\(Başkan\)", regex=True),
         raw.str.contains(r"\(\s*B\s*\.?\s*\)|\(Bakan|Bakan\)", regex=True),
         raw.str.contains(r"\(\s*[İI1lt]\s*\.\s*\)|İ\.\s*[AÜ]\.?\)", regex=True)],
        ["prime minister", "presiding officer", "minister", "on leave"], "")
    lead = ["vote_id", "date", "chamber", "category", "topic_group", "title", "outcome_class", "quality",
            "choice", "cast_code", "person_key", "person_name", "elite_row", "senate_person_id",
            "list_province", "list_name", "list_name_raw", "list_pdf_page", "match_method", "match_score",
            "row_status", "status_note", "elite_id", "elite_party", "elite_party_at_election"]
    drop = ["source", "list_status", "section_inferred"]
    long = long[lead + [c for c in long.columns if c not in lead + drop]]
    long = long.sort_values(["date", "vote_id", "choice", "list_province", "list_name"])
    long.to_csv(PROCESSED / "rollcall_long.csv", index=False)

    # ---- wide: Assembly x elites ----------------------------------------------------
    cohorts = [y for y, _, _ in MM_TERMS.values()]
    wide = elites[elites.year.isin(cohorts)].copy()
    term_of_year = {y: t for t, (y, _, _) in MM_TERMS.items()}
    mm = long[(long.chamber == "MM") & long.elite_row.notna()]
    cols = {}
    for vid, g in mm.groupby("vote_id", sort=False):
        term = q.loc[q.vote_id == vid, "mm_term"].iat[0]
        codes = g.drop_duplicates("elite_row").set_index("elite_row").cast_code
        col = pd.Series(codes, dtype="Int64").reindex(wide.index)
        col[wide.year.map(term_of_year) != term] = 0
        cols[f"v_{vid}"] = col
    order = [c for c in (f"v_{v}" for v in q.sort_values("date").vote_id) if c in cols]
    wide = pd.concat([wide, pd.DataFrame({c: cols[c] for c in order})], axis=1).reset_index()
    wide.to_csv(PROCESSED / "rollcall_wide_elites.csv", index=False)

    # ---- wide: Senate ------------------------------------------------------------------
    cs = long[(long.chamber == "CS") & long.senate_person_id.notna()]
    span = cs.groupby("senate_person_id").date.agg(["min", "max"])
    sw = senators.set_index("senate_person_id")[["person_name", "province", "n_votes", "elite_row"]]
    sw = sw.join(span.rename(columns={"min": "first_seen", "max": "last_seen"}))
    scols = {}
    for vid, g in cs.sort_values("date").groupby("vote_id", sort=False):
        d = g.date.iat[0]
        col = g.drop_duplicates("senate_person_id").set_index("senate_person_id").cast_code.astype("Int64")
        col = col.reindex(sw.index)
        col[(sw.first_seen > d) | (sw.last_seen < d)] = 0
        scols[f"v_{vid}"] = col
    sorder = [f"v_{v}" for v in q.sort_values("date").vote_id if f"v_{v}" in scols]
    sw = pd.concat([sw, pd.DataFrame({c: scols[c] for c in sorder})], axis=1).reset_index()
    sw.to_csv(PROCESSED / "rollcall_wide_senate.csv", index=False)

    # ---- workbook -----------------------------------------------------------------------
    n_ok = q.quality.str.startswith("ok").sum()
    codebook = pd.DataFrame({"item": [
        "Coverage", "Votes", "Per-member lists", "Quality", "Persons", "Matrix codes", "Party",
        "Not-voting lists", "Sources", "Rebuild"], "description": [
        "All recorded (open, by-name) votes on land and agricultural matters in the Millet Meclisi (MM) and "
        "Cumhuriyet Senatosu (CS), Oct 1961 - Sep 1980. Show-of-hands votes left no record of individual votes.",
        f"{len(q)} roll calls: 73 hand-checked land votes + {len(q) - 73} agricultural votes selected by topic "
        "rules on the OCR vote titles. topic_group 'rural/peripheral' = forestry, DSİ water/irrigation, "
        "village affairs, general cooperatives law: drop it for a narrow agricultural set.",
        f"Every vote's printed name lists were read from the TBMM PDFs ({int((q.quality != 'no name list').sum())} "
        "votes). Each name keeps the printed spelling (list_name) and its PDF page.",
        f"{n_ok} votes reproduce the printed tallies exactly (quality 'ok...'). For the others, "
        "names_off_vs_tally gives how many names the lists differ from the closest printed/derived tally; "
        "most are off by 1-3 names because of OCR damage. Use quality to filter.",
        "Deputies are linked to rows of the Turkish Political Elites Dataset (elite_row, person_key 'E<row>'); "
        "senators get a senate_person_id built from the lists, linked to elites when they also served as "
        "deputies. match_method says how each name was linked; 'rescued' and 'low confidence' deserve a look.",
        "1 yes, 6 no, 7 abstain, 9 not voting, 0 not a member at the time, blank = member but on no list.",
        "elite_party is the elites career string (e.g. 'CHP/BAĞIMSIZ/GP'); elite_party_at_election is its "
        "first element. Party at the vote date is not recorded in the sources.",
        "Assembly votes without a quorum often omit the not-voting list; those members are derived as the "
        "sitting members on no printed list (row_status 'derived ...').",
        "TBMM Tutanak Dergisi PDFs (links in sheet 'votes'); vote detection from GNACT OCR corpus "
        "(Boğaziçi TABILab, CC BY-NC-SA 4.0); Turkish Political Elites Dataset.",
        "cd scripts; python3 01_build_vote_index.py; python3 02_fetch_pdfs.py; python3 03_parse_namelists.py; "
        "python3 04_match_elites.py; python3 05_build_dataset.py"]})
    slim = ["vote_id", "date", "chamber", "category", "choice", "cast_code", "person_key", "person_name",
            "elite_row", "senate_person_id", "list_province", "list_name", "list_pdf_page", "match_method",
            "match_score", "row_status", "elite_party", "elite_party_at_election", "quality"]
    with pd.ExcelWriter(PROCESSED / "TBMM_land_agri_rollcalls_1961-1980.xlsx", engine="openpyxl") as xw:
        codebook.to_excel(xw, sheet_name="codebook", index=False)
        q.to_excel(xw, sheet_name="votes", index=False)
        long[slim].to_excel(xw, sheet_name="member_votes", index=False)
        wide[["elite_row", "id", "name", "party", "province_old", "year"] + order].to_excel(
            xw, sheet_name="matrix_assembly", index=False)
        sw.to_excel(xw, sheet_name="matrix_senate", index=False)
        pd.read_csv(INTERIM / "unmatched_for_review.csv", low_memory=False).to_excel(
            xw, sheet_name="unmatched", index=False)

    print(f"long: {len(long)} rows; assembly matrix {wide.shape}; senate matrix {sw.shape}")
    print(q.quality.value_counts().to_string())
    print(pd.cut(q.names_off_vs_tally, [-1, 0, 1, 2, 5, 10, 1000]).value_counts().sort_index().to_string())


if __name__ == "__main__":
    main()
