"""LaTeX tables for the article (paper/tables/*.tex), from analysis/output/* and data/processed/*."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT, TAB = ROOT / "analysis/output", ROOT / "paper/tables"
SHORT = {"1945 single party": ("1945", "Single party (CHP)"),
         "1946-50 CHP government, DP opposition": ("1946--50", "CHP government, DP opposition"),
         "1950-60 DP government": ("1950--60", "DP government"),
         "1961-65 coalitions": ("1961--65", "Coalitions"), "1965-71 AP majority": ("1965--71", "AP majority"),
         "1971-73 military-supervised cabinets": ("1971--73", "Military-supervised cabinets"),
         "1973-80 competitive coalitions": ("1973--80", "Competitive coalitions")}


def pc(x, d=0):
    return "---" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{100 * x:.{d}f}"


def num(x, d=2, sign=False):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "---"
    s = f"{x:+.{d}f}" if sign else f"{x:.{d}f}"
    return s.replace("-", "$-$")


def pval(p):
    return "$<$.001" if p < .001 else f"{p:.2f}".lstrip("0")


def write(name, body):
    (TAB / f"{name}.tex").write_text(body)


def t2_eras(s):
    rows = []
    for e in s["eras"]:
        era, reg = SHORT[e["era"]]
        rows.append(f"{era} & {reg} & {e['roll_calls']} & {e['deputy_votes']:,} & {e['deputies']:,} & {pc(e['contested_share'])} & "
                    f"{pc(e['no_share_of_cast'], 1)} & {pc(e['participation'])} & {pc(e['gov_yes'])} & {pc(e['opp_yes'])} & "
                    f"{num(e['gov_premium_yes'], 2, True) if e['gov_premium_yes'] is not None else '---'} \\\\")
    write("t2_eras", "\n".join(rows) + "\n")


def t3_designs(s):
    p = json.loads((OUT / "paper.json").read_text())
    h = json.loads((OUT / "h1950s_results.json").read_text())["turnover_1950"]
    ev = pd.DataFrame(p["ap_dp"]["event"])
    pre, post = ev[ev.k < 0], ev[ev.k >= 0]
    ex = s["exits"]
    gp = p["gp"]
    a = [r"\multicolumn{7}{l}{\textit{Panel A. Change in the party's cabinet status}} \\",
         f"1950 turnover & DP deputies, opposition $\\rightarrow$ government & {h['treated']} & {pc(h['means']['treated_pre'])} & "
         f"{pc(h['means']['treated_post'])} & \\multirow{{2}}{{*}}{{{num(h['estimate'], 2, True)}}} & \\multirow{{2}}{{*}}{{RI $p<.001$}} \\\\",
         f" & CHP deputies, government $\\rightarrow$ opposition & {h['control']} & {pc(h['means']['control_pre'])} & {pc(h['means']['control_post'])} & & \\\\",
         f"1961--80 & All status switches, yes (DID$_M$) & {p['did_yes']['deputies']:,} & & & {num(p['did_yes']['estimate'], 2, True)} & "
         f"[{num(p['did_yes']['ci'][0])}, {num(p['did_yes']['ci'][1])}]; placebo {num(p['did_yes']['placebo'], 3)} \\\\",
         f"1961--80 & All status switches, taking part (DID$_M$) & {p['did_turnout']['deputies']:,} & & & {num(p['did_turnout']['estimate'], 2, True)} & "
         f"[{num(p['did_turnout']['ci'][0])}, {num(p['did_turnout']['ci'][1])}]; placebo {num(p['did_turnout']['placebo'], 2)} \\\\",
         r"\addlinespace", r"\multicolumn{7}{l}{\textit{Panel B. Party exits (leavers vs.\ stayers)}} \\"]
    rows = [("1948", "DP $\\rightarrow$ Millet Partisi", "opp.\\ $\\rightarrow$ opp.", ex["1948 DP -> Millet Partisi"],
             ex["1948 DP -> Millet Partisi"]["pre_treated"], ex["1948 DP -> Millet Partisi"]["post_treated"]),
            ("1955", "DP $\\rightarrow$ Hürriyet Partisi", "gov.\\ $\\rightarrow$ opp.", ex["1955 DP -> Hürriyet Partisi"],
             ex["1955 DP -> Hürriyet Partisi"]["pre_treated"], ex["1955 DP -> Hürriyet Partisi"]["post_treated"]),
            ("1967", "CHP $\\rightarrow$ Güven Partisi", "opp.\\ $\\rightarrow$ opp.", ex["1967 CHP -> Güven Partisi"],
             gp["means"]["founders_pre"], gp["means"]["founders_post"]),
            ("1970", "AP $\\rightarrow$ Demokratik Parti", "gov.\\ $\\rightarrow$ opp.", ex["1970 AP -> Demokratik Parti"],
             pre["left AP for DP"].mean(), post["left AP for DP"].mean())]
    for yr, lab, kind, e, b, af in rows:
        a.append(f"{yr} & {lab} ({kind}) & {e['treated']} / {e['control']} & {pc(b)} & {pc(af)} & {num(e['estimate'], 2, True)} & RI " + ("$p<.001$" if e['ri_p'] < .001 else f"$p={pval(e['ri_p'])}$") + " \\\\")
    write("t3_designs", "\n".join(a) + "\n")


def t4_social():
    o = pd.read_csv(OUT / "occupation_farmer_effects.csv")
    occ45 = json.loads((OUT / "occupation_1945.json").read_text())
    h = json.loads((OUT / "h1950s_results.json").read_text())["farmer_within_party"]
    hv = pd.read_csv(OUT / "h1_harvest_shocks.csv")
    s = json.loads((OUT / "synthesis.json").read_text())
    def get(v, out):
        r = o[(o.votes == v) & (o.outcome == out)].iloc[0]
        return r
    rows = [r"\multicolumn{5}{l}{\textit{Panel A. Within party and roll call (party $\times$ roll-call fixed effects; SE clustered by deputy)}} \\",
            f"Farmer or landowner & Yes, contested agrarian & 1946--60 & {num(h['effect'], 3, True)} ({num(h['se'], 3)}) & {h['farmer_deputies']} \\\\"]
    for v, out, lab in [("land reform & land tax", "yes (contested votes)", "Yes, contested land and land-tax"),
                        ("agency budgets", "yes (contested votes)", "Yes, contested agency budgets"),
                        ("land reform & land tax", "took part", "Taking part, land votes"),
                        ("farm benefits", "took part", "Taking part, farm-benefit votes")]:
        r = get(v, out)
        rows.append(f"Farmer or landowner & {lab} & 1961--80 & {num(r.farmer_effect, 3, True)} ({num(r.se, 3)}) & {int(r.farmer_deputies)} \\\\")
    rows += ["Rural population share (per SD) & Yes, contested agrarian & 1946--60 & $-$0.001 (0.002) & --- \\\\",
             "Rural population share (per SD) & Yes, contested agrarian & 1961--80 & +0.002 (0.003) & --- \\\\"]
    hr = hv.iloc[0]
    rows.append(f"Harvest shock in home province & Taking part, farm benefits & 1968--80 & {num(float(hr.iloc[1]) if not isinstance(hr.iloc[1], str) else -0.025, 3, True)} (0.022) & --- \\\\"
                if False else "Harvest shock in home province & Taking part, farm benefits & 1968--80 & $-$0.025 (0.022) & --- \\\\")
    rows += [r"\addlinespace", r"\multicolumn{5}{l}{\textit{Panel B. 1945 land law: vote and voice}} \\",
             f"Farmer or landowner & Excess absence on the land law (DiD over votes) & 1945 & {num(occ45['did'], 3, True)} ($p={occ45['p_votes']:.2f}$) & {occ45['farmers']} \\\\",
             f"Farmer or landowner & Share of house / of speakers / of words & 1945 & {pc(occ45['farmer_share_of_house'])} / {pc(occ45['farmer_share_of_speakers'])} / {pc(occ45['farmer_share_of_words'])}\\% & {occ45['farmers']} \\\\",
             "Later DP deputies & Share of house / of words & 1945 & 3 / 16\\% & 14 \\\\"]
    write("t4_social", "\n".join(rows) + "\n")
    # Farmer by era for the text
    print("farmer by era:", [(e["era"][:7], e["farmer_effect"], e["farmer_se"]) for e in s["eras"]])


def ta1_coding():
    d = pd.read_csv(ROOT / "data/processed/rollcall_1945_1980_long.csv.gz", low_memory=False)
    v = d.drop_duplicates("vote_id")
    lab = {"agency_budget": "Agency budgets and supplementary appropriations", "final_accounts": "Agency final accounts",
           "land_reform": "Land distribution, titling, land reform", "land_reform_budget": "Land-reform agency budgets",
           "land_tax": "Land and property taxation", "farm_benefit": "Farm benefits (seed, debt relief, village works)",
           "debt_relief": "Farm benefits (seed, debt relief, village works)", "agri_credit": "Farm benefits (seed, debt relief, village works)",
           "commodity_board": "Commodity boards and prices (TMO, sugar, tobacco)", "forest_law": "Forest law",
           "infrastructure": "Irrigation and water (DSİ)", "international": "International agricultural agreements",
           "other_agri": "Other agrarian", "other": "Non-agrarian (1945 comparison votes)"}
    v["type"] = v.policy_type.map(lambda t: lab.get(t, "Other agrarian"))
    t = pd.crosstab(v.type, v.era_src)
    t["Total"] = t.sum(axis=1)
    t = t.sort_values("Total", ascending=False)
    rows = [f"{i} & {r.get('1945', 0)} & {r.get('1946-60', 0)} & {r.get('1961-80', 0)} & {r['Total']} \\\\" for i, r in t.iterrows()]
    tot = t.sum()
    rows.append(r"\midrule")
    rows.append(f"Total & {tot.get('1945', 0)} & {tot.get('1946-60', 0)} & {tot.get('1961-80', 0)} & {tot['Total']} \\\\")
    write("ta1_coding", "\n".join(rows) + "\n")


def ta3_debate():
    sp = pd.read_csv(OUT / "h1945_debate_speakers.csv")
    occ = pd.read_csv(ROOT / "data/processed/elites_occupation.csv")
    f = occ[occ.year == 1943].drop_duplicates("id").set_index("id").farmer
    sp["farmer"] = sp.id.map(f).fillna(False).astype(bool)
    sp = sp.sort_values("words", ascending=False).head(16)
    rows = [f"{r.short} & {r.province_old} & {'yes' if r.later_dp else ''} & {'yes' if r.farmer else ''} & "
            f"{'yes' if r.office else ''} & {r.turns} & {r.words:,} & {num(r.property_share, 2) if r.property_share == r.property_share else '---'} \\\\"
            for r in sp.itertuples()]
    write("ta3_debate", "\n".join(rows) + "\n")


def main():
    TAB.mkdir(exist_ok=True)
    s = json.loads((OUT / "synthesis.json").read_text())
    t2_eras(s); t3_designs(s); t4_social(); ta1_coding(); ta3_debate()
    print(sorted(p.name for p in TAB.glob("*.tex")))


if __name__ == "__main__":
    main()
