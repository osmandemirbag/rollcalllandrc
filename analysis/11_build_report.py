"""Build the 1945-1980 report (analysis/site/land-and-cabinet-1945-1980.html) from analysis/output/*.

Charts take their data from synthesis.json (10_synthesis_1945_80.py), speech_land_salience.csv,
occupation_farmer_effects.csv and h1945_land_law.json; the prose numbers were checked against them.
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis/output"
SHORT = {"1945 single party": "1945", "1946-50 CHP government, DP opposition": "1946–50",
         "1950-60 DP government": "1950–60", "1961-65 coalitions": "1961–65", "1965-71 AP majority": "1965–71",
         "1971-73 military-supervised cabinets": "1971–73", "1973-80 competitive coalitions": "1973–80"}
# The side that opposed each key land bill, and whether the bill transfers land or taxes it.
OPPONENT = [("tbmm08025070_p086", "DP", "distribution", "1950 dilution of the land law"),
            ("tbmm08025066_p040", "DP", "distribution", "1950 titling law"),
            ("tbmm10007078_p139", "CHP", "distribution", "1955 land law amendment"),
            ("mm02006092_p086", "CHP", "distribution", "1966 titling amendment"),
            ("mm03038125_p153", "CHP", "distribution", "1973 land reform law"),
            ("mm01035055_p050", "AP", "winnable motion", "1965 motion on İnönü's land bill"),
            ("mm01030096_p062", "AP", "taxation", "1964 land tax"),
            ("mm03007115_p075", "CHP", "taxation", "1970 property tax"),
            ("mm03026116_p050", "DP", "taxation", "1972 property tax amendment")]


def main():
    s = json.loads((OUT / "synthesis.json").read_text())
    eras = [{"era": SHORT[e["era"]], **{k: e[k] for k in ("roll_calls", "deputy_votes", "contested_share", "no_share_of_cast",
                                                        "participation", "gov_yes", "opp_yes", "gov_premium_yes",
                                                        "farmer_effect", "farmer_se", "farmer_deputies")}} for e in s["eras"]]
    lv = pd.DataFrame(s["land_votes"])
    land = []
    for vid, party, kind, label in OPPONENT:
        r = lv[(lv.vote_id == vid) & (lv.party == party)].iloc[0]
        land.append({"label": label, "party": party, "kind": kind, "present": r.present, "base": r.era_baseline_present,
                     "ratio": r.present / r.era_baseline_present, "no_of_present": r.no_of_present})
    sal = pd.read_csv(OUT / "speech_land_salience.csv")
    speech = {b: sal[sal.legislative_body == b][["start", "land_reform"]].values.tolist() for b in ["TBMM", "CS", "MM"]}
    exits = [{"name": k, **{x: v.get(x) for x in ("from", "to", "estimate", "ri_p", "treated", "control")}}
             for k, v in s["exits"].items()]
    data = {"eras": eras, "land": land, "speech": speech, "exits": exits,
            "totals": {"rows": s["rows"], "roll_calls": s["roll_calls"], "deputies": s["deputies"]}}
    html = (ROOT / "analysis/report_template.html").read_text()
    html = html.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=float))
    out = ROOT / "analysis/site/land-and-cabinet-1945-1980.html"
    out.write_text(html)
    print("wrote", out, len(html) // 1024, "KB")
    print(json.dumps(land, ensure_ascii=False, default=float)[:1500])


if __name__ == "__main__":
    main()
