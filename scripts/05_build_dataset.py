"""Assemble the final land and agriculture roll-call dataset merged with the elites data.

Outputs (data/processed/):
  rollcall_long.csv        one row per member x vote, vote metadata + elite covariates
  rollcall_wide_elites.csv the elites rows for the 1961-1977 Assembly cohorts, all
                           original columns, plus one column per Assembly roll call
                           with a parsed name list (codes below)
  TBMM_land_agri_rollcalls_1961-1980.xlsx  the same tables in one workbook + codebook

Wide-matrix codes (Voteview convention):
  1 yes   6 no   7 abstain   9 not voting (listed as absent)
  0 not a member of the Assembly in that term
  blank: member of that term but not on the printed lists (vacancy, minister in the chair, OCR loss)
"""
import pandas as pd

from common import CAST_CODES, ELITES_CSV, INTERIM, MM_TERMS, PROCESSED

ELITE_COVARIATES = ["id", "name", "party", "province_old", "year", "donem", "government",
                    "coalition", "female", "age", "birthdate", "education", "majororoccupation",
                    "law_education", "military_education", "religious_education", "rural_population_pct",
                    "parliamentaryexperience", "switchedparties", "local"]


def main():
    votes = pd.read_csv(PROCESSED / "votes.csv")
    elites = pd.read_csv(ELITES_CSV, sep="\t", low_memory=False)
    elites.index.name = "elite_row"
    matches = pd.read_csv(INTERIM / "matches.csv")
    checks = pd.read_csv(INTERIM / "namelist_checks.csv")

    # ---- long -------------------------------------------------------------
    cov = elites[ELITE_COVARIATES].add_prefix("elite_")
    long = (matches.rename(columns={"name": "list_name", "province": "list_province", "name_raw": "list_name_raw"})
            .merge(votes, on="vote_id", how="left")
            .merge(cov, left_on="elite_row", right_index=True, how="left"))
    long["elite_party_at_election"] = long.elite_party.str.split("/").str[0].str.strip()
    long["cast_code"] = long.choice.map(CAST_CODES)
    lead = ["vote_id", "date", "chamber", "category", "topic_group", "title", "outcome_class",
            "choice", "cast_code", "list_province", "list_name", "list_name_raw", "pdf_page_x",
            "elite_row", "elite_id", "elite_name", "elite_party", "elite_party_at_election",
            "match_score", "match_method", "list_status"]
    long = long.rename(columns={"pdf_page_y": "vote_pdf_page"})
    long = long[lead + [c for c in long.columns if c not in lead]].rename(columns={"pdf_page_x": "list_pdf_page"})
    long = long.sort_values(["date", "vote_id", "choice", "list_province", "list_name"])
    long.to_csv(PROCESSED / "rollcall_long.csv", index=False)

    # ---- wide (Assembly only; the elites data covers deputies) -------------
    cohorts = [y for y, _, _ in MM_TERMS.values()]
    wide = elites[elites.year.isin(cohorts)].copy()
    term_of_year = {y: t for t, (y, _, _) in MM_TERMS.items()}
    mm = long[(long.chamber == "MM") & long.elite_row.notna()]
    vote_cols = []
    for vid, g in mm.groupby("vote_id", sort=False):
        term = votes.loc[votes.vote_id == vid, "mm_term"].iat[0]
        col = f"v_{vid}"
        codes = g.drop_duplicates("elite_row").set_index("elite_row").cast_code
        wide[col] = pd.Series(codes, dtype="Int64").reindex(wide.index)
        wide.loc[wide.year.map(term_of_year) != term, col] = 0
        vote_cols.append(col)
    wide = wide.reset_index()
    wide.to_csv(PROCESSED / "rollcall_wide_elites.csv", index=False)

    # ---- workbook -----------------------------------------------------------
    parsed = set(checks.loc[checks.status == "ok", "vote_id"])
    votes["name_list_status"] = votes.vote_id.map(checks.set_index("vote_id").status).fillna("not processed")
    votes["in_wide_matrix"] = votes.vote_id.map(lambda v: f"v_{v}" in vote_cols)
    codebook = pd.DataFrame({"item": [
        "Coverage", "Votes", "Name lists", "Matching", "Wide codes", "Party", "Senate",
        "Sources", "Rebuild"], "description": [
        "All recorded (open, by-name) votes on land and agricultural matters in the Millet Meclisi (MM) and "
        "Cumhuriyet Senatosu (CS), Oct 1961 - Sep 1980. Show-of-hands votes left no record of individual votes.",
        f"{len(votes)} roll calls: 73 hand-checked land votes + {len(votes) - 73} agricultural votes "
        "selected by topic rules on the OCR vote titles (scripts/01_build_vote_index.py). topic_group "
        "'rural/peripheral' = forestry, DSİ water/irrigation, village affairs, general cooperatives law: "
        "drop it for a narrow agricultural set.",
        f"Per-member choices are available for {len(parsed)} vote(s); see sheet 'votes' column name_list_status. "
        "The other lists must be read from the TBMM PDFs (scripts/02-03).",
        "Names are linked to rows of the Turkish Political Elites Dataset by fuzzy name match within "
        "term and province (match_method, match_score). 'low confidence' and 'province differs' rows deserve a look.",
        "1 yes, 6 no, 7 abstain, 9 not voting, 0 not a member in that term, blank = member but not on the lists.",
        "elite_party is the full career string of the elites data (e.g. 'CHP/BAĞIMSIZ/GP'); "
        "elite_party_at_election is its first element. Party at the vote date is not recorded in the source.",
        "The elites dataset covers deputies only. Senate votes appear in rollcall_long; senators are linked "
        "only when they also served as deputies.",
        "TBMM Tutanak Dergisi PDFs (links in sheet 'votes'); vote detection from GNACT OCR corpus "
        "(Boğaziçi TABILab, CC BY-NC-SA 4.0); Turkish Political Elites Dataset.",
        "python3 scripts/01_build_vote_index.py && 02_fetch_pdfs.py && 03_parse_namelists.py && "
        "04_match_elites.py && 05_build_dataset.py"]})

    with pd.ExcelWriter(PROCESSED / "TBMM_land_agri_rollcalls_1961-1980.xlsx", engine="openpyxl") as xw:
        codebook.to_excel(xw, sheet_name="codebook", index=False)
        votes.to_excel(xw, sheet_name="votes", index=False)
        long.to_excel(xw, sheet_name="member_votes_long", index=False)
        wide[["elite_row", "id", "name", "party", "province_old", "year", "donem"] + vote_cols].to_excel(
            xw, sheet_name="matrix_wide", index=False)
        checks.to_excel(xw, sheet_name="list_checks", index=False)
        pd.read_csv(INTERIM / "unmatched_for_review.csv").to_excel(xw, sheet_name="unmatched", index=False)

    print(f"long: {len(long)} rows; wide: {wide.shape}; vote columns: {len(vote_cols)}")


if __name__ == "__main__":
    main()
