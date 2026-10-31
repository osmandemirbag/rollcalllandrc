"""Ideal points and design-based estimates for the paper page (output/paper.json).

1. Two-dimensional Bayesian IRT ideal points per Assembly term (Clinton-Jackman-Rivers model,
   MAP estimates with N(0,1) priors; rotated so dimension 1 is the main axis of the points).
2. DID_M (de Chaisemartin & D'Haultfoeuille 2020) for the effect of the deputy's party entering
   or leaving the cabinet, on consecutive budget roll calls; placebo on the preceding pair;
   deputy-clustered bootstrap.
3. AP -> DP exit (Dec 1970): event study and randomization inference over AP deputies.
4. 1971 memorandum: AP-CHP distance before/after, against placebo break dates in other terms.
5. Pre-split land-tax dissent (Fisher exact test); MSP partner switch (counts).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".replication_root").exists())
OUT = ROOT / "output"
RNG = np.random.default_rng(20261030)
PARTIES = ["AP", "CHP", "DP", "MSP", "CGP", "MHP", "YTP", "CKMP", "MP", "TİP"]
BUDGETS = ["agency_budget", "land_reform_budget"]


def load():
    v = pd.read_csv(OUT / "votes_coded.csv")
    m = pd.read_csv(OUT / "member_votes.csv.gz", low_memory=False)
    e = pd.read_csv(ROOT / "data/raw/The_Turkish_Political_Elites_Dataset.csv", sep="\t", low_memory=False)
    m["date"] = pd.to_datetime(m.date)
    m["gov"] = m.government.map({True: 1.0, False: 0.0, "True": 1.0, "False": 0.0})
    m["excused"] = m.status_note.fillna("").ne("")
    mm = m[(m.chamber == "MM") & m.party_at_vote.notna() & m.date.notna()].copy()
    mm["party"] = mm.party_at_vote.where(mm.party_at_vote.isin(PARTIES), "OTHER")
    mm = mm.merge(e[["name", "switchedparties"]].rename(columns={"name": "elite_name"}),
                  left_on="elite_row", right_index=True, how="left")
    return v, mm


# ------------------------------------------------------------------ 1. ideal points
def irt2d(Y, iters=3000, lr=0.05, prior=1.0):
    """MAP fit of P(y=1) = sigmoid(a_j + x_i . b_j) on a members x votes matrix with NaNs."""
    obs = ~np.isnan(Y)
    y = np.nan_to_num(Y)
    n, k = Y.shape
    Z = np.where(obs, Y - np.nanmean(Y, 0), 0)
    U, S, Vt = np.linalg.svd(Z, full_matrices=False)
    x = U[:, :2] * np.sqrt(n)
    b = Vt[:2].T * S[:2] / np.sqrt(n)
    a = np.zeros(k)
    params = [x, b, a]
    mom = [np.zeros_like(p) for p in params]
    vel = [np.zeros_like(p) for p in params]
    for t in range(1, iters + 1):
        eta = a + x @ b.T
        p = 1 / (1 + np.exp(-eta))
        r = np.where(obs, y - p, 0)
        grads = [-(r @ b) + x / prior, -(r.T @ x) + b / 25, -r.sum(0) + a / 25]
        for i, g in enumerate(grads):
            mom[i] = 0.9 * mom[i] + 0.1 * g
            vel[i] = 0.999 * vel[i] + 0.001 * g * g
            params[i] -= lr * (mom[i] / (1 - 0.9 ** t)) / (np.sqrt(vel[i] / (1 - 0.999 ** t)) + 1e-8)
        x, b, a = params
    # rotate: dimension 1 = main axis of the ideal points
    xc = x - x.mean(0)
    _, _, R = np.linalg.svd(xc, full_matrices=False)
    x2, b2 = xc @ R.T, b @ R.T
    p = 1 / (1 + np.exp(-(a + x @ b.T)))
    acc = ((p > 0.5) == (y > 0.5))[obs].mean()
    base = np.maximum(np.nanmean(Y, 0), 1 - np.nanmean(Y, 0))
    apre = 1 - (1 - acc) / (1 - (base * obs.sum(0)).sum() / obs.sum())
    return x2, b2, acc, apre


def ideal_points(v, mm):
    # Only roll calls whose lists are within 2 names of the printed tally: a few badly parsed votes
    # (sections swapped by the OCR) otherwise create a spurious second dimension.
    q = pd.read_csv(ROOT / "data/processed/votes_quality.csv")
    good = set(q[q.names_off_vs_tally <= 2].vote_id)
    cast = mm[mm.choice.isin(["yes", "no"]) & mm.vote_id.isin(good)]
    pts, votes, fit = [], [], []
    for term, g in cast.groupby("mm_term"):
        share = g.groupby("vote_id").yes.mean()
        keep = share[(share > 0.025) & (share < 0.975)].index
        Y = g[g.vote_id.isin(keep)].pivot_table(index="person_key", columns="vote_id", values="yes", aggfunc="first")
        Y = Y.loc[:, Y.notna().sum(0) >= 20]
        Y = Y[Y.notna().sum(1) >= min(10, max(3, Y.shape[1] // 2))]
        if Y.shape[1] < 5:
            print(f"{term}: only {Y.shape[1]} usable roll calls, not scaled")
            continue
        x, b, acc, apre = irt2d(Y.to_numpy(dtype=float))
        info = g.sort_values("date").groupby("person_key").agg(
            party=("party", "first"), party_last=("party", "last"), name=("elite_name", "first"),
            province=("province_old", "first"), gov=("gov", "mean"), rural=("rural_population_pct", "first"),
            east=("east_se", "first"), switched=("switchedparties", "first")).reindex(Y.index)
        # orient: AP on the positive side of dimension 1
        s1 = np.sign(np.nanmean(x[info.party.to_numpy() == "AP", 0]) or 1)
        s2 = 1.0
        x[:, 0] *= s1
        b[:, 0] *= s1
        # orient dimension 2: positive = side of the deputies who later left their party
        sw = info.switched.fillna(0).to_numpy() == 1
        if sw.any():
            s2 = np.sign(x[sw, 1].mean() - x[~sw, 1].mean()) or 1
            x[:, 1] *= s2
            b[:, 1] *= s2
        d = info.assign(d1=x[:, 0], d2=x[:, 1], term=term).reset_index()
        pts.append(d)
        vt = v.set_index("vote_id").loc[Y.columns]
        votes.append(pd.DataFrame({"vote_id": Y.columns, "term": term, "policy_type": vt.policy_type.to_numpy(),
                                   "b1": b[:, 0], "b2": b[:, 1], "date": vt.date.to_numpy(),
                                   "title": vt.title.str[:90].to_numpy()}))
        # within-party correlates of dimension 2
        d["d2w"] = d.d2 - d.groupby("party").d2.transform("mean")
        d["d1w"] = d.d1 - d.groupby("party").d1.transform("mean")
        sw01 = d.switched.fillna(0).to_numpy()
        r_obs = abs(np.corrcoef(d.d2w, sw01)[0, 1]) if sw01.std() > 0 else np.nan
        perm = []
        for _ in range(2000):  # shuffle the switch indicator within party
            shuf = d.groupby("party").switched.transform(lambda z: RNG.permutation(z.fillna(0).to_numpy()))
            perm.append(abs(np.corrcoef(d.d2w, shuf)[0, 1]) if shuf.std() > 0 else 0)
        fit.append({"term": term, "members": len(Y), "roll_calls": Y.shape[1], "accuracy": acc, "apre": apre,
                    "abs_corr_d2w_switch": r_obs, "perm_p_switch": float(np.mean(np.array(perm) >= r_obs)),
                    "within_party_share_d2": float(d.d2w.var() / d.d2.var()),
                    "var_share_dim2": float(np.var(x[:, 1]) / (np.var(x[:, 0]) + np.var(x[:, 1]))),
                    "corr_d2w_rural": float(d[["d2w", "rural"]].corr().iloc[0, 1]),
                    "corr_d2w_east": float(np.corrcoef(d.d2w, d.east.astype(float))[0, 1])})
    pts, votes, fit = pd.concat(pts), pd.concat(votes), pd.DataFrame(fit)
    votes["angle_deg"] = np.degrees(np.arctan2(np.abs(votes.b2), np.abs(votes.b1)))
    return pts, votes, fit


# ------------------------------------------------------------------ 2. DID_M
def did_m(mm, outcome="yes", cast_only=True, B=499):
    d = mm[mm.policy_type.isin(BUDGETS) & ~mm.technocratic.astype(bool) & ~mm.excused
           & ~mm.row_status.astype(str).str.startswith("derived")]
    if cast_only:
        d = d[d.choice.isin(["yes", "no", "abstain"])]
    d = d[["person_key", "vote_id", "date", "mm_term", outcome, "gov"]].dropna()
    order = d.drop_duplicates("vote_id").sort_values("date")
    seq = {t: list(g.vote_id) for t, g in order.groupby("mm_term")}
    W = d.pivot_table(index="person_key", columns="vote_id", values=outcome, aggfunc="first")
    G = d.pivot_table(index="person_key", columns="vote_id", values="gov", aggfunc="first")
    cells = []  # (t-2, t-1, t) triples
    for term, vs in seq.items():
        for i in range(1, len(vs)):
            cells.append((vs[i - 2] if i >= 2 else None, vs[i - 1], vs[i]))

    def estimate(ids):
        num, den, pnum, pden = 0.0, 0.0, 0.0, 0.0
        Wi, Gi = W.loc[ids], G.loc[ids]
        for pre, a, b in cells:
            ga, gb, ya, yb = Gi[a], Gi[b], Wi[a], Wi[b]
            ok = ga.notna() & gb.notna() & ya.notna() & yb.notna()
            for g0, g1, sign in [(0, 1, 1), (1, 0, -1)]:
                sw = ok & (ga == g0) & (gb == g1)
                st = ok & (ga == g0) & (gb == g0)
                if sw.sum() == 0 or st.sum() == 0:
                    continue
                diff = (yb[sw] - ya[sw]).mean() - (yb[st] - ya[st]).mean()
                num += sign * diff * sw.sum()
                den += sw.sum()
                if pre is not None:  # placebo: same groups, previous pair, no change in status yet
                    gp, yp = Gi[pre], Wi[pre]
                    okp = sw & gp.notna() & yp.notna() & (gp == g0)
                    okq = st & gp.notna() & yp.notna() & (gp == g0)
                    if okp.sum() and okq.sum():
                        pd_ = (ya[okp] - yp[okp]).mean() - (ya[okq] - yp[okq]).mean()
                        pnum += sign * pd_ * okp.sum()
                        pden += okp.sum()
        return num / den if den else np.nan, den, pnum / pden if pden else np.nan, pden

    ids = W.index.to_numpy()
    est, n_sw, plc, n_plc = estimate(ids)
    boots = []
    for _ in range(B):
        s = RNG.choice(ids, size=len(ids), replace=True)
        Wb = W.loc[s]
        Wb.index = range(len(s))
        Gb = G.loc[s]
        Gb.index = range(len(s))
        boots.append(_est_on(Wb, Gb, cells))
    boots = np.array(boots)
    return {"estimate": est, "ci": list(np.nanpercentile(boots[:, 0], [2.5, 97.5])), "switcher_obs": int(n_sw),
            "placebo": plc, "placebo_ci": list(np.nanpercentile(boots[:, 1], [2.5, 97.5])), "placebo_obs": int(n_plc),
            "deputies": len(ids)}


def _est_on(W, G, cells):
    num = den = pnum = pden = 0.0
    for pre, a, b in cells:
        ga, gb, ya, yb = G[a], G[b], W[a], W[b]
        ok = ga.notna() & gb.notna() & ya.notna() & yb.notna()
        for g0, g1, sign in [(0, 1, 1), (1, 0, -1)]:
            sw = ok & (ga == g0) & (gb == g1)
            st = ok & (ga == g0) & (gb == g0)
            if sw.sum() == 0 or st.sum() == 0:
                continue
            num += sign * ((yb[sw] - ya[sw]).mean() - (yb[st] - ya[st]).mean()) * sw.sum()
            den += sw.sum()
            if pre is not None:
                gp, yp = G[pre], W[pre]
                okp = sw & gp.notna() & yp.notna() & (gp == g0)
                okq = st & gp.notna() & yp.notna() & (gp == g0)
                if okp.sum() and okq.sum():
                    pnum += sign * ((ya[okp] - yp[okp]).mean() - (ya[okq] - yp[okq]).mean()) * okp.sum()
                    pden += okp.sum()
    return (num / den if den else np.nan, pnum / pden if pden else np.nan)


# ------------------------------------------------------------------ 3. AP -> DP exit
def ap_dp(v, mm, R=5000):
    contested = set(v[~v.lopsided].vote_id)
    d = mm[(mm.mm_term == "d03") & mm.policy_type.isin(BUDGETS) & mm.choice.isin(["yes", "no", "abstain"])
           & mm.vote_id.isin(contested) & ~mm.excused]
    first = d.sort_values("date").groupby("person_key").party.first()
    last = d.sort_values("date").groupby("person_key").party.last()
    ap = first.index[first == "AP"]
    treated = set(last.index[(first == "AP") & (last == "DP")])
    d = d[d.person_key.isin(ap) & last.reindex(d.person_key).isin(["AP", "DP"]).to_numpy()].copy()
    split = pd.Timestamp("1970-12-18")
    d["post"] = d.date >= split
    # event time = budget roll-call index relative to the split
    vs = d.drop_duplicates("vote_id").sort_values("date").vote_id.tolist()
    first_post = next(i for i, x in enumerate(vs) if d[d.vote_id == x].post.iloc[0])
    d["k"] = d.vote_id.map({x: i - first_post for i, x in enumerate(vs)})

    def did(tr):
        t = d.person_key.isin(tr)
        return ((d[t & d.post].yes.mean() - d[t & ~d.post].yes.mean())
                - (d[~t & d.post].yes.mean() - d[~t & ~d.post].yes.mean()))
    est = did(treated)
    pool = d.person_key.unique()
    nt = len(treated & set(pool))
    perm = np.array([did(set(RNG.choice(pool, nt, replace=False))) for _ in range(R)])
    ev = d.assign(group=np.where(d.person_key.isin(treated), "left AP for DP", "stayed in AP")).groupby(
        ["k", "group"]).yes.mean().unstack().reset_index()
    # pre-split land-tax dissent
    t70 = mm[mm.vote_id == "mm03007115_p075"].set_index("person_key")
    base = t70[t70.party == "AP"]
    later = last.reindex(base.index)
    sw = base[later == "DP"]
    st = base[later == "AP"]
    tab = [[(sw.choice == "no").sum(), (sw.choice != "no").sum()], [(st.choice == "no").sum(), (st.choice != "no").sum()]]
    return {"estimate": est, "ri_p": float((np.abs(perm) >= abs(est)).mean()), "perm_sd": float(perm.std()),
            "treated": nt, "controls": len(pool) - nt, "event": ev.to_dict("records"),
            "landtax_1970": {"switchers_n": len(sw), "switchers_no": float((sw.choice == "no").mean()),
                             "switchers_yes": float((sw.choice == "yes").mean()), "stayers_n": len(st),
                             "stayers_no": float((st.choice == "no").mean()), "stayers_yes": float((st.choice == "yes").mean()),
                             "fisher_p": float(fisher_exact(tab)[1])}}


# ------------------------------------------------------------------ 4. memorandum
def memorandum(v, mm):
    c = mm[mm.choice.isin(["yes", "no"]) & mm.party.isin(["AP", "CHP"])]
    s = c.groupby(["vote_id", "party"]).yes.mean().unstack().dropna()
    t = v.set_index("vote_id").loc[s.index].assign(gap=(s.AP - s.CHP).abs())
    t = t[t.chamber == "MM"].dropna(subset=["date"]).sort_values("date")
    t["date"] = pd.to_datetime(t.date)

    def jump(x, when, w=None):
        pre, post = x[x.date < when], x[x.date >= when]
        if w:
            pre, post = pre.tail(w), post.head(w)
        if len(pre) < 10 or len(post) < 10:
            return np.nan
        return post.gap.mean() - pre.gap.mean()
    d03 = t[t.mm_term == "d03"]
    actual_window = d03[d03.date < "1972-05-01"]
    est = jump(actual_window, pd.Timestamp("1971-03-12"))
    plac = []
    for term, x in t[t.mm_term != "d03"].groupby("mm_term"):
        for when in x.date.iloc[10:-10]:
            plac.append(jump(x, when, w=30))
    plac = np.array([p for p in plac if np.isfinite(p)])
    series = t[t.mm_term == "d03"][["date", "gap", "policy_type", "cabinet"]].assign(date=lambda z: z.date.dt.strftime("%Y-%m-%d"))
    return {"estimate": est, "placebo_n": len(plac), "placebo_p": float((plac <= est).mean()),
            "placebo_min": float(plac.min()), "series": series.to_dict("records")}


def msp(v, mm):
    rows = []
    for _, r in v[(v.policy_type == "land_reform_budget") & (v.chamber == "MM")].sort_values("date").iterrows():
        x = mm[(mm.vote_id == r.vote_id) & (mm.party == "MSP")]
        rows.append({"date": r.date[:10], "cabinet": r.cabinet, "in_cabinet": "MSP" in str(r.gov_parties),
                     "yes": int((x.choice == "yes").sum()), "no": int((x.choice == "no").sum()),
                     "absent": int((x.voted == 0).sum())})
    return rows


def main():
    v, mm = load()
    pts, votes, fit = ideal_points(v, mm)
    print(fit.round(3).to_string())
    print(votes.groupby("policy_type").angle_deg.median().round(1).to_string())
    res = {"fit": fit.to_dict("records")}
    res["points"] = pts[["term", "person_key", "name", "party", "party_last", "province", "gov", "d1", "d2",
                         "switched"]].round(3).fillna("").to_dict("records")
    res["vote_angles"] = votes[["term", "policy_type", "b1", "b2", "angle_deg", "date", "title"]].round(3).to_dict("records")
    res["did_yes"] = did_m(mm, "yes", True)
    res["did_turnout"] = did_m(mm, "voted", False)
    print("DID_M yes", res["did_yes"])
    print("DID_M turnout", res["did_turnout"])
    res["ap_dp"] = ap_dp(v, mm)
    print("AP->DP", {k: res["ap_dp"][k] for k in ["estimate", "ri_p", "perm_sd", "treated", "controls"]},
          res["ap_dp"]["landtax_1970"])
    res["memo"] = memorandum(v, mm)
    print("memo", {k: res["memo"][k] for k in ["estimate", "placebo_n", "placebo_p", "placebo_min"]})
    res["msp"] = msp(v, mm)
    pts.to_csv(OUT / "ideal_points.csv", index=False)
    votes.to_csv(OUT / "vote_discrimination.csv", index=False)
    (OUT / "paper.json").write_text(json.dumps(res, default=lambda o: o.item() if hasattr(o, "item") else str(o)))


if __name__ == "__main__":
    main()
