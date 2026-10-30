"""Figures for analysis/report.md (static PNG, light theme)."""
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = Path(__file__).resolve().parent / "output"
SURFACE, INK, MUTED, GRID = "#fcfcfb", "#1f1f1d", "#6b6a63", "#e6e5df"
AP, CHP = "#2a78d6", "#eb6834"  # categorical slots 1-2, validated (light)

plt.rcParams.update({"font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": SURFACE, "axes.facecolor": SURFACE})


def share_yes(m, vid, party):
    x = m[(m.vote_id == vid) & (m.party_at_vote == party)]
    return (x.choice == "yes").mean()


def fig_budgets(v, m):
    b = v[(v.policy_type == "land_reform_budget") & (v.chamber == "MM")].sort_values("date").reset_index(drop=True)
    b["label"] = pd.to_datetime(b.date).dt.strftime("%b %Y") + "\n" + b.cabinet.str.replace("Nationalist Front", "MC")
    ap = [share_yes(m, x, "AP") for x in b.vote_id]
    chp = [share_yes(m, x, "CHP") for x in b.vote_id]
    fig, ax = plt.subplots(figsize=(8.6, 3.8))
    xs = range(len(b))
    for i, gp in enumerate(b.gov_parties.fillna("")):
        if "CHP" in gp.split("+"):
            ax.axvspan(i - 0.5, i + 0.5, color="#fbe3d9", lw=0)
        elif "AP" in gp.split("+"):
            ax.axvspan(i - 0.5, i + 0.5, color="#dbe8f8", lw=0)
    ax.plot(xs, ap, color=AP, lw=2, marker="o", ms=8, mec=SURFACE, mew=2, label="AP")
    ax.plot(xs, chp, color=CHP, lw=2, marker="o", ms=8, mec=SURFACE, mew=2, label="CHP")
    ax.text(len(b) - 0.6, ap[-1], " AP", color=INK, va="center", ha="left")
    ax.text(len(b) - 0.6, chp[-1], " CHP", color=INK, va="center", ha="left")
    ax.set_xticks(list(xs), b.label, fontsize=8)
    ax.set_ylim(-0.03, 1.03)
    ax.set_xlim(-0.5, len(b) + 0.2)
    ax.set_ylabel("share of party's deputies voting yes")
    ax.yaxis.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.set_title("Land Reform Undersecretariat budgets: support follows government, not ideology\n"
                 "shading: blue = AP-led cabinet, orange = CHP-led cabinet, none = technocratic (Irmak)",
                 loc="left", fontsize=10, color=INK)
    ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.13), ncol=2)
    fig.tight_layout()
    fig.savefig(OUT / "fig1_land_reform_budgets.png", dpi=160)


def fig_debt_relief(v, m):
    d = v[(v.chamber == "MM") & (v.subtype == "debt_relief") & (v.date >= "1976")].sort_values(["date", "vote_id"])
    d = d.reset_index(drop=True)
    rows = []
    for vid in d.vote_id:
        x = m[m.vote_id == vid]
        rows.append({"gov": x[x.government == True].voted.mean(), "opp": x[x.government == False].voted.mean(),  # noqa: E712
                     "n": x.voted.sum()})
    r = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    xs = range(len(d))
    ax.plot(xs, r.opp, color=CHP, lw=2, marker="o", ms=8, mec=SURFACE, mew=2, label="opposition (CHP and others)")
    ax.plot(xs, r.gov, color=AP, lw=2, marker="o", ms=8, mec=SURFACE, mew=2, label="government (AP, MSP, CGP, MHP)")
    for i, (o, n) in enumerate(zip(d.outcome_class, r.n)):
        ax.text(i, -0.08, f"{int(n)}", ha="center", color=MUTED, fontsize=8)
        if o == "passed":
            ax.annotate("passed", (i, r.opp[i]), xytext=(0, 10), textcoords="offset points", ha="center",
                        color=INK, fontsize=8)
    ax.text(-0.6, -0.08, "voters:", ha="right", color=MUTED, fontsize=8)
    ax.set_xticks(list(xs), pd.to_datetime(d.date).dt.strftime("%d %b\n%Y"), fontsize=8)
    ax.set_ylim(-0.12, 1)
    ax.set_ylabel("share of bloc's deputies voting")
    ax.yaxis.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.set_title("Small-farmer debt relief, 1976-77: 13 attempts and almost no 'no' votes\n"
                 "the first 12 failed for lack of quorum (226 needed); the opposition usually turned out more", loc="left", fontsize=10, color=INK)
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "fig2_debt_relief_quorum.png", dpi=160)


def main():
    v = pd.read_csv(OUT / "votes_coded.csv")
    m = pd.read_csv(OUT / "member_votes.csv.gz", low_memory=False)
    m = m[m.chamber == "MM"]
    fig_budgets(v, m)
    fig_debt_relief(v, m)


if __name__ == "__main__":
    main()
