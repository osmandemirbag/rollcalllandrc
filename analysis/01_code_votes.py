"""Code every roll call by policy type, and every member-vote by party and government status.

Outputs (analysis/output/):
  votes_coded.csv   one row per roll call: policy_type, subtype, stage, cabinet, aggregate patterns
  member_votes.csv  one row per member x vote with party_at_vote, government, covariates

Policy types
  land_reform          Toprak (ve Tarım) Reformu law and motions
  land_reform_budget   annual budgets of the Land and Agrarian Reform Undersecretariat (1974-80)
  land_tax             Arazi Vergisi (1964), Emlâk Vergisi (1970-72)
  land_titling         Tapulama (cadastral titling) law, İskân (settlement), AOÇ land sale,
                       forest-land definition (Orman Kanunu) and forest-crime amnesty
  farm_benefit         laws that hand resources to farmers; subtypes: debt_relief, tax_relief,
                       disaster_relief, credit, input_subsidy, commodity_support
  agri_institution     regulation and organisation (seed law, cooperatives, village law, ministries)
  agency_budget        annual budgets and appropriation changes of agricultural/rural agencies
  final_accounts       kesinhesap / bilanço of past years (accounting approval)
  international        treaties and conventions
  excluded             not agricultural on inspection (MPs' allowances, border treaty, university staff)
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from common import ELITES_CSV, PROCESSED, fold  # noqa: E402

OUT = ROOT / "analysis" / "output"

# ---------------------------------------------------------------- policy coding
RULES = [  # (policy_type, subtype, regex on folded title); first match wins
    ("excluded", "", r"uyelerinin (odenek|olenek)|odeneklerinden|oleneklerinden|hudut hat|universitesi kurulus|universitesi kadro"),
    ("final_accounts", "", r"kesin ?hesa|bilanco|bilancos"),
    ("land_reform_budget", "", r"toprak ve tarim reformu mustesarl"),
    ("land_reform", "", r"toprak (ve tarim )?reform"),
    ("land_tax", "", r"arazi vergisi|emlak vergisi"),
    ("land_titling", "titling", r"tapulama"),
    ("land_titling", "settlement", r"iskan kanun"),
    ("land_titling", "state_land_sale", r"orman ciftligi arazisi|ataturk orman ciftligi"),
    ("land_titling", "forest_land", r"orman kanun|orman suclarinin aff"),
    ("farm_benefit", "debt_relief", r"borclar|borclarinin"),
    ("farm_benefit", "tax_relief", r"zirai gelir"),
    ("farm_benefit", "disaster_relief", r"tabii afet|muhtac durumda"),
    ("farm_benefit", "credit", r"ziraat bankasi kanun|tarim kredi kooperatifleri ve birlik|ziraat bakanligi kanun"),
    ("farm_benefit", "input_subsidy", r"gubre|traktor"),
    ("farm_benefit", "commodity_support", r"cay (isletmeleri )?kurum|tutun ve tutun tekeli|sut endustrisi"),
    ("international", "", r"milletlerarasi|uluslararasi|sozlesme|andlasma|anlasma|amerika birlesik|protokol"),
    ("agency_budget", "", r"butce|cetvel|yilligi kanun"),
    ("agri_institution", "", r"."),
]

STAGES = [("budget", r"butce|cetvel"), ("final_accounts", r"kesin ?hesa|bilanco"),
          ("motion", r"onerge"), ("article", r"\d+\s*(nci|ncu|nc|inci|uncu|ncü|ncı)? ?maddes|gecici \d|ek \d+ ")]

# Cabinets (start date, name, governing parties). Technocratic 'above-party' cabinets of 1971-74
# list the parties that supplied ministers; Irmak (1974-75) had no party ministers.
CABINETS = [
    ("1961-11-20", "İnönü VIII", {"CHP", "AP"}),
    ("1962-06-25", "İnönü IX", {"CHP", "YTP", "CKMP"}),
    ("1963-12-25", "İnönü X", {"CHP"}),
    ("1965-02-20", "Ürgüplü", {"AP", "YTP", "CKMP", "MP"}),
    ("1965-10-27", "Demirel I-III", {"AP"}),
    ("1971-03-26", "Erim I", {"AP", "CHP", "CGP"}),
    ("1971-12-11", "Erim II", {"AP", "CGP"}),
    ("1972-05-22", "Melen", {"AP", "CHP", "CGP"}),
    ("1973-04-15", "Talu", {"AP", "CGP"}),
    ("1974-01-26", "Ecevit I", {"CHP", "MSP"}),
    ("1974-11-17", "Irmak", set()),
    ("1975-03-31", "Nationalist Front I", {"AP", "MSP", "CGP", "MHP"}),
    ("1977-06-21", "Ecevit II", {"CHP"}),
    ("1977-07-21", "Nationalist Front II", {"AP", "MSP", "MHP"}),
    ("1978-01-05", "Ecevit III", {"CHP", "CGP", "DP"}),
    ("1979-11-12", "Demirel VI", {"AP"}),
]
TECHNOCRATIC = {"Erim I", "Erim II", "Melen", "Talu", "Irmak"}

# Party families. Güven Partisi (1967) -> Milli Güven Partisi -> Cumhuriyetçi Güven Partisi (1973).
FAMILY = {"GP": "CGP", "MGP": "CGP", "CP": "CGP", "CGP": "CGP", "CMKP": "CKMP", "MNP": "MSP",
          "BAĞIMSIZ": "IND", "BAGIMSIZ": "IND", "NP": "MSP"}

# Known party splits: (cohort, first party, later party) -> date the members changed side.
SWITCH = {(1965, "CHP", "CGP"): "1967-05-12", (1969, "AP", "DP"): "1970-12-18",
          (1969, "CHP", "CGP"): "1972-11-01", (1969, "MSP", "MSP"): "1972-10-11",
          (1973, "DP", "AP"): "1975-06-01", (1977, "AP", "CHP"): "1978-01-01",
          (1977, "CHP", "AP"): "1979-10-01"}
TERM_MID = {1961: "1963-10-15", 1965: "1967-10-15", 1969: "1971-10-15", 1973: "1975-08-15", 1977: "1979-01-01"}

# East and Southeast provinces where large landholdings by tribal landlords (ağa) were common.
EAST_SE = {"AĞRI", "BİNGÖL", "BİTLİS", "DİYARBAKIR", "HAKKARİ", "MARDİN", "MUŞ", "SİİRT", "TUNCELİ",
           "URFA", "ŞANLIURFA", "VAN", "ADIYAMAN", "KARS", "ERZURUM", "ELAZIĞ", "MALATYA", "GAZİANTEP"}


def code_vote(title):
    t = fold(title)
    for ptype, sub, rx in RULES:
        if re.search(rx, t):
            break
    stage = next((s for s, rx in STAGES if re.search(rx, t)), "final_passage")
    return ptype, sub, stage


def cabinet_on(date):
    cur = CABINETS[0]
    for c in CABINETS:
        if str(date)[:10] >= c[0]:
            cur = c
    return cur


def party_tokens(career):
    toks = [FAMILY.get(t.strip().upper(), t.strip().upper()) for t in re.split(r"/+", str(career)) if t.strip()]
    return toks or ["?"]


def party_at_vote(career, cohort, date):
    toks = party_tokens(career)
    first = toks[0]
    later = [t for t in toks[1:] if t != "IND"]
    if len(toks) == 1 or (not later and "IND" not in toks[1:]):
        return first, False
    final = later[-1] if later else "IND"
    when = SWITCH.get((cohort, first, final), TERM_MID.get(cohort, "1970-01-01"))
    return (first if str(date)[:10] < when else final), True


def main():
    votes = pd.read_csv(PROCESSED / "votes_quality.csv", parse_dates=["date"])
    coded = votes.title.map(code_vote)
    votes["policy_type"] = [c[0] for c in coded]
    votes["subtype"] = [c[1] for c in coded]
    votes["stage"] = [c[2] for c in coded]
    # Votes that the hand-checked list already put in land categories keep that group.
    land_cat = votes.category.str.startswith(("Land", "Settlement", "State farmland"))
    votes.loc[land_cat & ~votes.policy_type.str.startswith("land"), "policy_type"] = "land_titling"
    cab = votes.date.map(cabinet_on)
    votes["cabinet"] = [c[1] for c in cab]
    votes["gov_parties"] = ["+".join(sorted(c[2])) for c in cab]
    votes["technocratic"] = votes.cabinet.isin(TECHNOCRATIC)

    long = pd.read_csv(PROCESSED / "rollcall_long.csv.gz", low_memory=False,
                       usecols=["vote_id", "chamber", "choice", "person_key", "elite_row", "senate_person_id",
                                "list_province", "row_status"])
    elites = pd.read_csv(ELITES_CSV, sep="\t", low_memory=False)
    cov = elites[["party", "year", "province_old", "rural_population_pct", "age", "education", "law_education",
                  "military_education", "local", "pastexp", "female", "dist_to_ankara", "id"]]
    m = long.merge(votes[["vote_id", "date", "policy_type", "subtype", "stage", "cabinet", "gov_parties",
                          "technocratic", "mm_term", "quality", "outcome_class"]], on="vote_id")
    m = m.merge(cov, left_on="elite_row", right_index=True, how="left")
    is_mm = m.chamber == "MM"
    pv = [party_at_vote(c, y, d) if mm and pd.notna(c) else (np.nan, False)
          for c, y, d, mm in zip(m.party, m.year, m.date, is_mm)]
    m["party_at_vote"] = [p[0] for p in pv]
    m["switcher"] = [p[1] for p in pv]
    m["government"] = [(p in g.split("+")) if isinstance(p, str) else np.nan
                       for p, g in zip(m.party_at_vote, m.gov_parties)]
    m["east_se"] = m.province_old.str.upper().isin(EAST_SE)
    m["agri_degree"] = m.education.fillna("").str.contains("Ziraat|Orman|Veteriner", regex=True)
    m["senate_group"] = np.where(m.chamber == "CS",
                                 np.select([m.list_province == "TABİİ ÜYELER",
                                            m.list_province == "CUMHURBAŞKANINCA S. Ü."],
                                           ["natural (NUC)", "presidential quota"], "elected"), None)
    m["yes"] = (m.choice == "yes").astype(int)
    m["voted"] = m.choice.isin(["yes", "no", "abstain", "invalid"]).astype(int)

    # vote-level aggregates
    g = m.groupby("vote_id")
    agg = pd.DataFrame({
        "members_listed": g.size(),
        "participation": g.voted.mean(),
        "yes_share_of_cast": g.apply(lambda x: (x.choice == "yes").sum() / max(1, x.choice.isin(["yes", "no", "abstain"]).sum())),
    })
    votes = votes.merge(agg, left_on="vote_id", right_index=True, how="left")
    votes["lopsided"] = (votes.yes_share_of_cast >= 0.9) | (votes.yes_share_of_cast <= 0.1)
    votes.to_csv(OUT / "votes_coded.csv", index=False)
    m.to_csv(OUT / "member_votes.csv.gz", index=False)
    print(votes.groupby(["policy_type"]).size().to_string())
    print(votes[votes.policy_type == "farm_benefit"].groupby("subtype").size().to_string())
    print(m[m.chamber == "MM"].party_at_vote.value_counts().head(12).to_string())


if __name__ == "__main__":
    main()
