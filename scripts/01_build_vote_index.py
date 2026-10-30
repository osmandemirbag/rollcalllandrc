"""Build the index of land and agricultural roll-call votes, 1961-1980.

Inputs : data/raw/TBMM_land_roll_calls_1961-1980.xlsx
           sheet 'Land votes'               (73 hand-checked land votes)
           sheet 'All recorded votes 1961-80' (6,446 OCR-detected open votes)
Output : data/processed/votes.csv           one row per roll call
         data/interim/agri_candidates_rejected.csv  keyword hits dropped by the rules

The 73 land votes keep their hand-assigned category. Agricultural votes are
added from the full list by the topic rules below; each rule is anchored on
an institution or a policy object so that, for example, 'topraklarından'
in a river treaty or 'köy' inside a place name does not qualify.
"""
import re

import pandas as pd

from common import INTERIM, PROCESSED, ROLLCALL_XLSX

TITLE = "Vote title (as printed, OCR)"

# (category, regex). The first matching rule wins, so order matters.
AGRI_RULES = [
    ("Land reform: law and motions", r"toprak\s+(ve\s+tar[ıi]m\s+)?reform"),
    ("Land titling (Tapulama law)", r"tapulama|kadastro"),
    ("Land taxation", r"arazi\s+vergisi|eml[âa]k\s+vergisi"),
    ("Settlement (İskân law)", r"\d+\s*sayılı\s+iskân|iskân\s+kanun"),
    ("Agricultural credit and cooperatives",
     r"ziraat\s+banka|tar[ıi]m\s+(kredi|satış|satis)\s+kooperatif|tar[ıi]msal\s+kredi"
     r"|çiftçi.{0,60}borç|tar[ıi]m\s+kooperatif"),
    ("Crops and commodity boards",
     r"t[üu]t[üu]n|şeker|pancar|f[ıi]nd[ıi]k|pamuk|zeytin|hububat|\bçay\b|çay\s+kanun"
     r"|çay\s+kurum|toprak\s+mahsulleri|üzüm|kuru\s+meyve|tiftik|afyon\s+(ekim|haşhaş)|haşhaş"),
    ("Livestock, veterinary and pasture",
     r"hayvan|veteriner|\bmera\b|meralar|et\s+ve\s+bal[ıi]k|yem\s+sanayi|s[üu]t\s+end[üu]strisi"),
    ("State farms and agricultural agencies",
     r"devlet\s+[üu]retme\s+çiftlik|topraksu|zirai\s+m[üu]cadele|zirai\s+karantina|ziraat\s+işleri"
     r"|tohum|g[üu]bre|tar[ıi]m\s+alet|traktör"),
    ("Ministry of Agriculture / Food-Agriculture-Livestock",
     r"tar[ıi]m\s+bakanl|g[ıi]da[,\s-]+tar[ıi]m|tar[ıi]m\s+ve\s+hayvanc|tar[ıi]m\s+orman"),
    ("Farmers: disaster relief, labour and support",
     r"çiftçi|tar[ıi]m\s+işçi|tar[ıi]mda|zirai|ziraat|tar[ıi]msal|k[üu]çük\s+çiftçi"),
    ("Village affairs and rural development", r"k[öo]y\s+işleri|k[öo]y\s+kanun|k[öo]ylerin|k[öo]ylere"),
    ("Irrigation and water (DSİ)", r"su\s+işleri|sulama|dsi\b|DSİ"),
    ("Forestry", r"orman|kavakç[ıi]l[ıi]k"),
    ("Cooperatives (general law)", r"^kooperatifler\s+kanun"),
    ("Expropriation and state land", r"kamulaştırma|istiml[âa]k|hazine(ye)?\s+ait\s+(arazi|taşınmaz)|devlet\s+arazi"),
]

# Titles that hit a rule but are not agricultural policy.
EXCLUDE = (r"ödenek|odenek|mütevellit|vergilendirme|köy\s+(eğitmen|enstit)|imar\s+ve\s+iskân"
           r"|milli\s+savunma|millî\s+savunma")

# Rough net used only to report what the rules drop, so false negatives can be reviewed.
BROAD = (r"tar[ıi]m|zira|çiftç|toprak|arazi|tapu|mera|orman|k[öo]y|sulama|su işleri|t[üu]t[üu]n|"
         r"şeker|pancar|f[ıi]nd[ıi]k|pamuk|zeytin|hububat|hayvan|veteriner|g[üu]bre|tohum|"
         r"kooperatif|mahsul|iskân|eml[âa]k|kamulaştırma|istiml[âa]k|\bçay\b|kadastro")

# Agencies whose link to agriculture is indirect; flagged so users can drop them.
PERIPHERAL = {"Village affairs and rural development", "Irrigation and water (DSİ)",
              "Cooperatives (general law)",
              "Forestry", "Expropriation and state land"}

CS_FIRST_YEAR = 1961  # Senate legislative year t01 = Nov 1961 - Oct 1962


def clean_title(title) -> str:
    t = str(title)
    # Closing remarks of the previous sitting sometimes precede the real title.
    t = re.split(r"Kapanma\s+saati\s*:\s*\d+[,.]\d+\s*", t)[-1]
    return t.strip(" |")


def outcome_class(outcome) -> str:
    o = str(outcome).lower() if isinstance(outcome, str) else ""
    if re.search(r"yok|sağlanamam|saglanamam|tekrar", o):
        return "no quorum / majority not reached"
    if re.search(r"redd|ret\b", o):
        return "rejected"
    if re.search(r"kabul|kanunlaş|sağlanmış|vardır", o):
        return "passed"
    return "unknown"


def classify(title: str):
    t = clean_title(title)
    if re.search(EXCLUDE, t, flags=re.I):
        return None
    # Strip running page headers the OCR glued onto titles.
    t = re.sub(r"^.*?O\s*:\s*\d+\s+", "", t) if re.match(r"^(C\.|M\.|G\.)", t) else t
    for cat, rx in AGRI_RULES:
        if re.search(rx, t, flags=re.I):
            return cat
    return None


def repair_dates(df: pd.DataFrame) -> pd.DataFrame:
    """OCR garbles years (1066, 1924 ...). Rebuild them from the session id."""
    df = df.copy()
    dt = pd.to_datetime(df["Date"], errors="coerce")
    ok = dt.dt.year.between(1961, 1980)
    df["year_raw"] = dt.dt.year
    df["vol"] = df["Session ID"].str[:7]
    good = df[ok].assign(y=dt[ok].dt.year, m=dt[ok].dt.month)
    by_sid = good.groupby("Session ID")["y"].agg(lambda s: s.mode().iat[0])
    by_vol_month = good.groupby(["vol", "m"])["y"].agg(lambda s: s.mode().iat[0])
    by_vol = good.groupby("vol")["y"].agg(lambda s: s.mode().iat[0])

    years, how = [], []
    for i, r in df.iterrows():
        if ok[i]:
            years.append(int(dt[i].year)); how.append("as printed")
            continue
        m = dt[i].month if pd.notna(dt[i]) else None
        sid, vol = r["Session ID"], r["vol"]
        if sid in by_sid.index:
            years.append(int(by_sid[sid])); how.append("year from same sitting")
        elif m and (vol, m) in by_vol_month.index:
            years.append(int(by_vol_month[(vol, m)])); how.append("year from same volume and month")
        elif sid.startswith("cs") and m:
            t = int(sid[3:5])
            years.append(CS_FIRST_YEAR + t - 1 + (0 if m >= 11 else 1)); how.append("year from Senate legislative year")
        elif vol in by_vol.index:
            years.append(int(by_vol[vol])); how.append("year from same volume")
        else:
            years.append(None); how.append("unrepaired")
    df["date_fix"] = [
        (pd.Timestamp(year=y, month=dt[i].month, day=dt[i].day) if y and pd.notna(dt[i]) else pd.NaT)
        for i, y in zip(df.index, years)
    ]
    df["date_source"] = how
    # Undated rows: read the running page header glued to the title ('B : 42 15 : 3 . 1977'),
    # else borrow the full date of the same sitting.
    for i in df.index[df.date_fix.isna()]:
        m = re.search(r"B\s*:\s*\d+\s+(\d{1,2})\s*[.:]\s*(\d{1,2})\s*[.:]\s*(19[67]\d)", str(df.at[i, TITLE]))
        if m:
            df.at[i, "date_fix"] = pd.Timestamp(int(m[3]), int(m[2]), int(m[1]))
            df.at[i, "date_source"] = "date from running page header"
    sid_date = df.dropna(subset=["date_fix"]).groupby("Session ID")["date_fix"].agg(lambda s: s.mode().iat[0])
    nodate = df.date_fix.isna() & df["Session ID"].isin(sid_date.index)
    df.loc[nodate, "date_fix"] = df.loc[nodate, "Session ID"].map(sid_date)
    df.loc[nodate, "date_source"] = "date from same sitting"
    return df


def chamber_code(sid: str) -> str:
    return {"mm": "MM", "cs": "CS", "bt": "BT"}[sid[:2]]


def main():
    land = pd.read_excel(ROLLCALL_XLSX, sheet_name="Land votes")
    allv = pd.read_excel(ROLLCALL_XLSX, sheet_name="All recorded votes 1961-80")
    allv = repair_dates(allv)

    # Join the 73 hand-checked land votes to the full list (session + PDF page).
    allv["key"] = allv["Session ID"] + "_" + allv["PDF page"].astype(str)
    land["key"] = land["Session ID"] + "_" + land["PDF page"].astype(str)
    missing = set(land.key) - set(allv.key)
    if missing:
        print(f"note: {len(missing)} land votes not in the full list (added by hand): {sorted(missing)}")

    land_rows = pd.DataFrame({
        "key": land.key,
        "category": land["Category"],
        "date": pd.to_datetime(land["Date"]),
        "date_source": "hand-checked",
        "title": land["Bill / motion voted on"],
        "outcome": land["Recorded outcome"],
        "yes": land["Yes"], "no": land["No"], "abstain": land["Abstain"],
        "not_voting": land["Not voting"], "votes_cast": land["Votes cast"], "seats": land["Seats"],
        "pdf_page": land["PDF page"], "pdf_url": land["PDF (TBMM)"], "session_id": land["Session ID"],
        "selection": "land list (hand-checked)",
    })

    rest = allv[~allv.key.isin(land.key)].copy()
    rest["category"] = rest[TITLE].map(classify)
    broad = rest[TITLE].str.contains(BROAD, case=False, regex=True, na=False)
    rejected = rest[broad & rest.category.isna()]
    rejected[["Session ID", "PDF page", "date_fix", TITLE]].to_csv(
        INTERIM / "agri_candidates_rejected.csv", index=False)
    agri = rest[rest.category.notna()]
    agri_rows = pd.DataFrame({
        "key": agri.key, "category": agri.category, "date": agri.date_fix,
        "date_source": agri.date_source, "title": agri[TITLE].map(clean_title), "outcome": agri["Recorded outcome"],
        "yes": agri["Yes"], "no": agri["No"], "abstain": agri["Abstain"],
        "not_voting": agri["Not voting"], "votes_cast": agri["Votes cast"], "seats": agri["Seats"],
        "pdf_page": agri["PDF page"], "pdf_url": agri["PDF (TBMM)"], "session_id": agri["Session ID"],
        "selection": "agriculture keyword rules (OCR title)",
    })

    votes = pd.concat([land_rows, agri_rows], ignore_index=True)
    votes["chamber"] = votes.session_id.map(chamber_code)
    votes["mm_term"] = "d" + votes.session_id.where(votes.chamber == "MM").str[2:4]
    votes["topic_group"] = votes.category.map(
        lambda c: "land" if c.startswith(("Land", "Settlement", "State farmland"))
        else ("rural/peripheral" if c in PERIPHERAL else "agriculture"))
    votes["outcome_class"] = votes.outcome.map(outcome_class)
    votes["unanimous"] = (votes["no"].fillna(0) == 0) & (votes["abstain"].fillna(0) == 0)
    votes = votes.sort_values(["date", "chamber", "session_id", "pdf_page"]).reset_index(drop=True)
    votes.insert(0, "vote_id", [f"{s}_p{int(p):03d}" for s, p in zip(votes.session_id, votes.pdf_page)])
    assert votes.vote_id.is_unique
    votes.drop(columns="key").to_csv(PROCESSED / "votes.csv", index=False)

    print(f"{len(votes)} votes: {len(land_rows)} land (hand-checked) + {len(agri_rows)} agricultural")
    print(votes.groupby(["topic_group", "category"]).size().to_string())
    print(votes.chamber.value_counts().to_string())
    print(f"rejected keyword hits for review: {len(rejected)}")


if __name__ == "__main__":
    main()
