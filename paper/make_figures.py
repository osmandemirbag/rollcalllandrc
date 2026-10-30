"""Figures for the article (paper/figures/*.pdf, with .png previews), from analysis/output/*."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT, FIG = ROOT / "analysis/output", ROOT / "paper/figures"
plt.rcParams.update({"font.family": "serif", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titlesize": 10, "axes.titleweight": "bold", "legend.frameon": False, "savefig.bbox": "tight"})
NAVY, ORANGE, GRAY, LIGHT, GREEN = "#1f3b73", "#e07b39", "#8c8c8c", "#cfcfcf", "#3a7d5c"
PARTY = {"AP": (NAVY, "o"), "CHP": (ORANGE, "s"), "TİP": ("#b22222", "^"), "MP": ("#6a5acd", "D"), "YTP": ("#2e8b57", "v"),
         "CKMP": ("#8b6914", "P"), "CGP": ("#c71585", "X"), "DP": ("#00868b", "*"), "OTHER": (GRAY, ".")}


def save(fig, name):
    fig.savefig(FIG / f"{name}.pdf")
    fig.savefig(FIG / f"{name}.png", dpi=150)
    plt.close(fig)


def split_maps(terms, name, titles, leavers):
    pts = pd.read_csv(OUT / "ideal_points.csv")
    fit = {f["term"]: f for f in json.loads((OUT / "paper.json").read_text())["fit"]}
    fig, axes = plt.subplots(1, len(terms), figsize=(4.3 * len(terms), 3.7))
    axes = np.atleast_1d(axes)
    for ax, t, title in zip(axes, terms, titles):
        x = pts[pts.term == t]
        lim = 1.08 * np.abs(x[["d1", "d2"]]).quantile(.995).max()
        for party, g in x.groupby("party"):
            c, m = PARTY.get(party, PARTY["OTHER"])
            stay = g[~g.apply(lambda r: (r.party, r.party_last) in leavers.get(t, set()), axis=1)]
            ax.scatter(stay.d1, stay.d2, s=12, c=c, marker=m, lw=0, alpha=.75, label=party if len(stay) >= 3 else None)
        for (a, b) in leavers.get(t, set()):
            g = x[(x.party == a) & (x.party_last == b)]
            if g.empty:
                continue
            ax.scatter(g.d1, g.d2, s=46, facecolors="none", edgecolors="black", lw=.9, marker="o",
                       label=f"{a}→{b} ({len(g)})")
        f = fit[t]
        ax.set_title(title + "\n", loc="left")
        ax.text(0, 1.01, f"Correct classification {f['accuracy']*100:.1f}% | APRE {f['apre']:.2f} | {f['roll_calls']} roll calls",
                transform=ax.transAxes, fontsize=7, va="bottom", color="#444")
        ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_aspect("equal")
        ax.set_xlabel("First dimension"); ax.set_ylabel("Second dimension")
        ax.axhline(0, color=LIGHT, lw=.5); ax.axvline(0, color=LIGHT, lw=.5)
        ax.legend(fontsize=7, loc="upper left", bbox_to_anchor=(1.0, 1.0), handletextpad=.3, borderaxespad=.2)
    fig.tight_layout()
    save(fig, name)


def fig_eras():
    s = json.loads((OUT / "synthesis.json").read_text())
    short = ["1945", "1946–50", "1950–60", "1961–65", "1965–71", "1971–73", "1973–80"]
    e = pd.DataFrame(s["eras"]); e["era"] = short
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.8, 3.3), gridspec_kw={"width_ratios": [1.1, 1], "wspace": .45})
    r = e.dropna(subset=["gov_yes"]).reset_index(drop=True)
    y = np.arange(len(r))[::-1]
    a.hlines(y, r.opp_yes, r.gov_yes, color=GRAY, lw=1.2)
    a.scatter(r.opp_yes, y, color=ORANGE, marker="s", s=28, zorder=3, label="Opposition deputies")
    a.scatter(r.gov_yes, y, color=NAVY, marker="o", s=30, zorder=3, label="Government deputies")
    for yi, row in zip(y, r.itertuples()):
        a.text(1.03, yi, f"+{row.gov_premium_yes:.2f}", va="center", fontsize=7.5)
    a.set_yticks(y, r.era); a.set_xlim(0, 1.12); a.set_xlabel("Yes among votes cast, contested roll calls")
    a.set_title("A. Government premium", loc="left")
    a.legend(fontsize=7, loc="upper center", bbox_to_anchor=(.5, -.2), ncol=2)
    v = pd.read_csv(OUT / "variance_decomposition.csv")
    v["era"] = v.era.map(dict(zip(s_names := [x["era"] for x in s["eras"]], short)))
    v = v.set_index("era").reindex(short[1:])
    x = np.arange(len(v))
    b.bar(x, v.party_only, color="#333", label="Party")
    b.bar(x, v.province_net, bottom=v.party_only, color="#999", label="Province beyond party (net of chance)")
    b.bar(x, v.residual, bottom=v.party_only + v.province_net, color="#e6e6e6", edgecolor="#bbb", lw=.4, label="Residual")
    b.set_xticks(x, v.index, rotation=45, ha="right"); b.set_ylim(0, 1); b.set_ylabel("Share of variance in vote choice")
    b.set_title("B. Party and province", loc="left"); b.legend(fontsize=6.5, loc="upper center", bbox_to_anchor=(.5, -.28), ncol=1)
    save(fig, "fig2_eras")


def fig_exits():
    p = json.loads((OUT / "paper.json").read_text())
    s = json.loads((OUT / "synthesis.json").read_text())
    n = pd.read_csv(OUT / "h1950s_member_votes.csv.gz", low_memory=False, parse_dates=["date"])
    c = n[(n.year == 1954) & (n.party_first == "DP") & n.choice.isin(["yes", "no", "abstain"])
          & (n.policy_type == "agency_budget")].dropna(subset=["date"])
    c = c.assign(leaver=c.party.str.contains("HP", na=False), stay=c.party.str.strip() == "DP")
    c = c[c.leaver | c.stay]
    order = sorted(pd.to_datetime(c.date.unique()))
    split = pd.Timestamp("1955-10-15")
    npre = sum(d < split for d in order)
    k = {d: i - npre for i, d in enumerate(order)}
    c["k"] = c.date.map(k)
    ev = c.groupby(["k", "leaver"]).yes.mean().unstack()
    fig = plt.figure(figsize=(7.4, 5.2))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, .8], hspace=.55, wspace=.25)
    axs = [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, :])]
    a = axs[0]
    a.plot(ev.index, ev[True], "-o", color=NAVY, ms=3, label="Left DP for Hürriyet (36)")
    a.plot(ev.index, ev[False], "-s", color=GRAY, ms=3, label="Stayed in DP")
    a.axvline(-.5, color="black", lw=.6, ls="--"); a.set_ylim(-.05, 1.08)
    a.set_title("A. 1955: DP → Hürriyet", loc="left"); a.set_xlabel("Agency-budget sittings from split"); a.set_ylabel("Yes among votes cast")
    a.legend(fontsize=6.5, loc="lower left")
    evt = pd.DataFrame(p["ap_dp"]["event"])
    b = axs[1]
    b.plot(evt.k, evt["left AP for DP"], "-o", color=NAVY, ms=3, label="Left AP for DP (21)")
    b.plot(evt.k, evt["stayed in AP"], "-s", color=GRAY, ms=3, label="Stayed in AP")
    b.axvline(-.5, color="black", lw=.6, ls="--"); b.set_ylim(-.05, 1.08)
    b.set_title("B. 1970: AP → Demokratik Parti", loc="left"); b.set_xlabel("Budget roll calls from split"); b.legend(fontsize=6.5, loc="lower left")
    d = axs[2]
    ex = s["exits"]
    labs = ["1948 DP→MP", "1955 DP→HP", "1967 CHP→GP", "1970 AP→DP"]
    keys = ["1948 DP -> Millet Partisi", "1955 DP -> Hürriyet Partisi", "1967 CHP -> Güven Partisi", "1970 AP -> Demokratik Parti"]
    vals = [ex[k_]["estimate"] for k_ in keys]
    gov = [ex[k_]["from"] == "government" for k_ in keys]
    yy = np.arange(4)[::-1]
    d.barh(yy, vals, color=[NAVY if g else LIGHT for g in gov], edgecolor="#555", lw=.4, height=.6)
    for yi, v, k_ in zip(yy, vals, keys):
        pval = ex[k_]["ri_p"]
        d.text(0.04 if v < 0 else v + 0.04, yi, f"{v:+.2f} (p{'<.001' if pval < .001 else '='+format(pval, '.2f')})", va="center", fontsize=7)
    d.axvline(0, color="black", lw=.6); d.set_yticks(yy, [l + (" (gov.→opp.)" if g else " (opp.→opp.)") for l, g in zip(labs, gov)])
    d.set_xlim(-1, .7)
    d.set_title("C. Four exits: only leaving the government moves votes", loc="left"); d.set_xlabel("DiD in yes (leavers − stayers)")
    save(fig, "fig3_exits")


def fig_land():
    s = json.loads((OUT / "synthesis.json").read_text())
    lv = pd.DataFrame(s["land_votes"])
    spec = [("tbmm08025070_p086", "DP", "D", "1950 dilution of the 1945 law"), ("tbmm08025066_p040", "DP", "D", "1950 titling law"),
            ("tbmm10007078_p139", "CHP", "D", "1955 land-law amendment"), ("mm02006092_p086", "CHP", "D", "1966 titling amendment"),
            ("mm03038125_p153", "CHP", "D", "1973 Land and Agrarian Reform Law"),
            ("mm01035055_p050", "AP", "W", "1965 motion on İnönü's land bill"),
            ("mm01030096_p062", "AP", "T", "1964 land tax, art. 9"), ("mm03007115_p075", "CHP", "T", "1970 property tax"),
            ("mm03026116_p050", "DP", "T", "1972 property-tax amendment")]
    rows = []
    for vid, party, kind, label in spec:
        r = lv[(lv.vote_id == vid) & (lv.party == party)].iloc[0]
        rows.append((label + f" ({party})", kind, r.present / r.era_baseline_present, r.no_of_present))
    fig, ax = plt.subplots(figsize=(6.6, 3.3))
    col = {"D": ORANGE, "T": NAVY, "W": GRAY}
    mk = {"D": "s", "T": "o", "W": "D"}
    y = np.arange(len(rows))[::-1]
    for yi, (lab, kind, ratio, no) in zip(y, rows):
        ax.hlines(yi, 1, ratio, color=col[kind], lw=1.2)
        ax.scatter(ratio, yi, color=col[kind], marker=mk[kind], s=30, zorder=3)
        ax.text(ratio * (1.08 if ratio >= 1 else .92), yi, f"no {no*100:.0f}%", va="center", ha="left" if ratio >= 1 else "right", fontsize=7)
    ax.set_xscale("log"); ax.set_xlim(.02, 3.5); ax.axvline(1, color="black", lw=.6)
    ax.set_xticks([.05, .1, .25, .5, 1, 2], ["0.05", "0.1", "0.25", "0.5", "1", "2"])
    ax.set_yticks(y, [r[0] for r in rows]); ax.set_xlabel("Opposing party's attendance relative to its own era baseline (log scale)")
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([], [], color=ORANGE, marker="s", ls="", label="Distribution or titling"),
                       Line2D([], [], color=NAVY, marker="o", ls="", label="Taxation"),
                       Line2D([], [], color=GRAY, marker="D", ls="", label="Winnable motion")], fontsize=7, loc="lower left")
    save(fig, "fig4_land_attendance")


def fig_1945():
    n = pd.read_csv(OUT / "h1945_deputy_votes.csv")
    idx = pd.read_csv(ROOT / "data/interim/tbmm_1943_60_votes.csv").drop_duplicates("doc").set_index("doc")
    order = sorted(n.vote_id.unique(), key=lambda v: (int(v[6:9]), int(v[9:12]), int(v.split("_p")[1])))
    five = ["Mahmut Celâl BAYAR", "Adnan MENDERES", "Refik KORALTAN", "Fuat KÖPRÜLÜ", "Emin SAZAK"]
    lab = ["Bayar", "Menderes", "Koraltan", "Köprülü", "Sazak"]
    code = {"yes": 2, "no": 0, "not_voting": 1}
    M = np.full((len(five), len(order)), np.nan)
    for i, nm in enumerate(five):
        g = n[n.short == nm].set_index("vote_id").choice
        for j, v in enumerate(order):
            if v in g.index:
                M[i, j] = code.get(g[v], np.nan)
    house = n[~n.excused].groupby("vote_id").absent.mean().reindex(order)
    fig, (a, b) = plt.subplots(2, 1, figsize=(7.4, 3.2), sharex=True, gridspec_kw={"height_ratios": [1.4, 1]})
    from matplotlib.colors import ListedColormap
    a.imshow(np.ma.masked_invalid(M), aspect="auto", cmap=ListedColormap(["#b22222", "#d9d9d9", NAVY]), vmin=0, vmax=2,
             interpolation="nearest")
    a.set_yticks(range(5), lab)
    budget = order.index("tbmm07017065_p040"); land = order.index("tbmm07018072_p022")
    for ax in (a, b):
        ax.axvline(budget, color="black", lw=.8, ls="--"); ax.axvline(land, color=ORANGE, lw=1.2)
    a.text(budget, -.9, "29 May budget, 368–5", fontsize=7, ha="center"); a.text(land, -.9, "11 June land law", fontsize=7, ha="left", color=ORANGE)
    from matplotlib.patches import Patch
    a.legend(handles=[Patch(color=NAVY, label="yes"), Patch(color="#d9d9d9", label="not voting"), Patch(color="#b22222", label="no")],
             fontsize=7, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    b.plot(range(len(order)), house.values, color=GRAY, lw=1)
    b.set_ylabel("House absent", fontsize=8); b.set_ylim(0, .6)
    b.set_xlabel("Named votes, April 1945 – January 1946, in order (blank cells: name not recovered)")
    save(fig, "figA1_1945_withdrawal")


def fig_memo():
    m = json.loads((OUT / "paper.json").read_text())["memo"]
    s = pd.DataFrame(m["series"]); s["date"] = pd.to_datetime(s.date)
    fig, ax = plt.subplots(figsize=(6.6, 2.6))
    for cab, g in s.groupby("cabinet", sort=False):
        ax.axvspan(g.date.min(), g.date.max(), color="#f0f0f0" if list(s.cabinet.unique()).index(cab) % 2 else "white", zorder=0)
        ax.text(g.date.min(), .97, cab, fontsize=6.5, va="top", color="#555")
    land = s.policy_type.isin(["land_tax", "land_reform"])
    ax.scatter(s[~land].date, s[~land].gap, s=10, color=NAVY, label="Other agrarian roll calls")
    ax.scatter(s[land].date, s[land].gap, s=34, marker="D", color=ORANGE, label="Land tax or land reform")
    ax.axvline(pd.Timestamp("1971-03-12"), color="black", lw=.8, ls="--")
    ax.set_ylim(0, 1); ax.set_ylabel("|AP yes − CHP yes|")
    ax.legend(fontsize=7, loc="upper center", bbox_to_anchor=(.5, -.12), ncol=2)
    save(fig, "figA2_memorandum")


def fig_speech():
    s = pd.read_csv(OUT / "speech_land_salience.csv")
    fig, ax = plt.subplots(figsize=(6.6, 2.6))
    t = s[s.legislative_body == "TBMM"]; cs = s[s.legislative_body == "CS"]; mm = s[s.legislative_body == "MM"]
    ax.plot(t.start + .5, t.land_reform * 100, "-o", ms=2.5, color=GREEN, label="TBMM, by legislative year")
    ax.plot(cs.start + .5, cs.land_reform * 100, "-s", ms=2.5, color=NAVY, label="Senate, by legislative year")
    for r in mm.itertuples():
        ax.hlines(r.land_reform * 100, r.start, 1980 if r.start == 1977 else r.start + 4, color=ORANGE, lw=2.5)
    ax.plot([], [], color=ORANGE, lw=2.5, label="Assembly, by term")
    for x_, y_, l in [(1945.5, 3.85, "1945 land law"), (1950.5, 1.63, "1950 dilution"), (1972.5, 4.41, "1972–74 reform")]:
        ax.annotate(l, (x_, y_), xytext=(0, 6), textcoords="offset points", ha="center", fontsize=7)
    ax.set_ylabel("% of minutes pages"); ax.set_xlim(1943, 1980.5); ax.set_ylim(0, 5.2); ax.legend(fontsize=7, loc="upper left")
    save(fig, "figA3_speech")


def main():
    split_maps(["d02", "d03"], "fig1_split_maps", ["A. Assembly 1965–69", "B. Assembly 1969–73"],
               {"d02": {("CHP", "CGP")}, "d03": {("AP", "DP")}})
    split_maps(["d01", "d04", "d05"], "figA4_split_maps_other", ["A. 1961–65", "B. 1973–77", "C. 1977–80"],
               {"d01": {("AP", "CHP"), ("CHP", "AP")}, "d04": {("DP", "AP")}, "d05": {("CHP", "OTHER")}})
    fig_eras(); fig_exits(); fig_land(); fig_1945(); fig_memo(); fig_speech()
    print(sorted(p.name for p in FIG.glob("*.pdf")))


if __name__ == "__main__":
    main()
