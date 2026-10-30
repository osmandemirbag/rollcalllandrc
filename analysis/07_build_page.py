"""Build the paper page analysis/site/cabinets-not-countryside.html from analysis/output/*."""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis" / "output"
SITE = ROOT / "analysis" / "site"


def main():
    p = json.loads((OUT / "paper.json").read_text())
    twfe = pd.read_csv(OUT / "d1_within_deputy_government_effect.csv").set_index("outcome")
    gate = pd.read_csv(OUT / "d2_quorum_gatekeeping.csv").set_index("sample")
    q = pd.read_csv(ROOT / "data/processed/votes_quality.csv")
    data = {
        "points": [{k: r[k] for k in ("term", "name", "party", "party_last", "province", "d1", "d2", "switched")}
                   for r in p["points"]],
        "fit": p["fit"],
        "angles": pd.DataFrame(p["vote_angles"]).groupby("policy_type").angle_deg.agg(["median", "size"]).reset_index()
                    .rename(columns={"size": "n"}).round(1).to_dict("records"),
        "did_yes": p["did_yes"], "did_turnout": p["did_turnout"],
        "twfe_yes": float(twfe.loc["all agency budgets: yes", "effect_of_government"]),
        "twfe_turnout": float(twfe.loc["agency budgets: turnout", "effect_of_government"]),
        "ap_dp": p["ap_dp"], "memo": p["memo"], "msp": p["msp"],
        "gate": float(gate.loc["excluding excused", "effect_of_government_on_turnout"]),
        "tip": p["tip"], "gp": p["gp"], "quotes": p["quotes"], "quorum": p["quorum"],
        "n_votes": int(len(q)), "exact": float((q.names_off_vs_tally == 0).mean()),
        "within2": float((q.names_off_vs_tally <= 2).mean()),
    }
    html = (Path(__file__).parent / "page_template.html").read_text()
    html = html.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    SITE.mkdir(exist_ok=True)
    (SITE / "cabinets-not-countryside.html").write_text(html)
    print("wrote", SITE / "cabinets-not-countryside.html", len(html) // 1024, "KB")


if __name__ == "__main__":
    main()
