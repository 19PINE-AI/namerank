"""T5.4 analysis: self-reported recognition vs behavioral NameRank.

Two stacked measurements, reported separately per model:

1. Binary self-knowledge -- on pairs where the model's OWN main-run labels
   say one side is known (score >= 0.15, no refusal) and the other unknown
   (refusal or score < 0.05): does the model pick the known side?
   Plus the trap arm: fictional entity vs model-known real entity -- any
   verdict that favors the fictional side (win or EQUAL) is a false
   recognition claim.

2. Graded introspection -- restricted to both-known pairs:
   (a) directional accuracy vs the model's own score gap (margins 0.15/0.30);
   (b) Davidson tie-model Bradley-Terry fit on all decided real-real pairs;
       Spearman of BT theta vs the model's own behavioral score (primary),
       vs panel NameRank (secondary), over model-known entities with >= 5
       decided comparisons. Pair-bootstrap CIs.

Also: position-bias consistency on the reversed-duplicate subset, and
abstention (NEITHER) rates by stratum.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import spearmanr

HERE = Path(__file__).parent
REPO = HERE.parent.parent
MODELS = ["gpt-5.5-think", "claude-opus-4.6-think", "gemini-3.1-pro"]
KNOWN_T, UNKNOWN_T = 0.15, 0.05
N_BOOT = 200
SEED = 42


def load():
    ents = {e["id"]: e for e in json.loads((HERE / "inputs/entities.json").read_text())}
    res = json.loads((HERE / "outputs/pairwise_results.json").read_text())
    return ents, res


def own_label(e: dict, m: str) -> str:
    """known / unknown / mid / fictional by the model's own main-run record."""
    if e["kind"] == "fictional":
        return "fictional"
    s, rf = e[f"score__{m}"], e[f"refusal__{m}"]
    if rf or s < UNKNOWN_T:
        return "unknown"
    if s >= KNOWN_T:
        return "known"
    return "mid"


def fit_davidson(pairs, ids, rng=None):
    """Davidson (1970) BT with ties, vectorized with analytic gradient.

    pairs: list of (i, j, outcome), outcome in {1: i wins, 0: j wins, 2: tie}.
    Model: P(i wins) = e^ti / Z, P(j wins) = e^tj / Z,
           P(tie) = nu * e^{(ti+tj)/2} / Z,  Z = e^ti + e^tj + nu e^{(ti+tj)/2}.
    Returns dict id -> theta (mean-centered)."""
    idx = {e: k for k, e in enumerate(ids)}
    P = np.array([(idx[a], idx[b], o) for a, b, o in pairs], dtype=np.int64)
    if rng is not None:
        P = P[rng.integers(0, len(P), len(P))]
    I, J, O = P[:, 0], P[:, 1], P[:, 2]
    n = len(ids)
    w_i, w_j, w_t = (O == 1), (O == 0), (O == 2)

    def nll_grad(x):
        th, lognu = x[:n], x[n]
        ti, tj = th[I], th[J]
        mid = 0.5 * (ti + tj)
        z = np.logaddexp(np.logaddexp(ti, tj), lognu + mid)
        ll = np.where(w_i, ti, np.where(w_j, tj, lognu + mid)) - z
        pi, pj, pt = np.exp(ti - z), np.exp(tj - z), np.exp(lognu + mid - z)
        # d ll / d th_I and th_J per pair
        gi = np.where(w_i, 1.0, np.where(w_t, 0.5, 0.0)) - (pi + 0.5 * pt)
        gj = np.where(w_j, 1.0, np.where(w_t, 0.5, 0.0)) - (pj + 0.5 * pt)
        gnu = np.where(w_t, 1.0, 0.0) - pt
        g = np.zeros(n + 1)
        np.add.at(g, I, gi)
        np.add.at(g, J, gj)
        g[n] = gnu.sum()
        # ridge pins the gauge and regularizes never-loses entities
        f = -ll.sum() + 1e-3 * np.sum(th ** 2)
        g = -g
        g[:n] += 2e-3 * th
        return f, g

    x0 = np.zeros(n + 1)
    r = minimize(nll_grad, x0, jac=True, method="L-BFGS-B",
                 options={"maxiter": 1000})
    th = r.x[:n] - r.x[:n].mean()
    return {e: float(th[idx[e]]) for e in ids}


def panel_components(ents: dict) -> tuple[dict, dict]:
    """Full-37-model decomposition: prevalence P(score>=0.15) and
    conditional coverage level (mean score among knowing models)."""
    raw = pd.read_csv(REPO / "data/raw/pilot_summary_en.csv.gz")
    raw = raw[raw.entity_id.isin(ents)]
    pk = raw.assign(k=raw.score >= KNOWN_T).groupby("entity_id").k.mean()
    cond = raw[raw.score >= KNOWN_T].groupby("entity_id").score.mean()
    return pk.to_dict(), cond.to_dict()


def analyze_model(m: str, ents: dict, res: list[dict],
                  pknown: dict, cond: dict) -> dict:
    R = [r for r in res if r["model_id"] == m]
    out: dict = {"model": m, "n_presentations": len(R)}
    out["verdict_counts"] = dict(Counter(r["verdict"] for r in R))

    # --- position bias on reversed duplicates ---
    orig = {r["pair_id"]: r for r in R if r["rev_of"] is None}
    by_pid = {}
    for r in res:  # map pair_id -> pair meta from any model row
        by_pid.setdefault(r["pair_id"], r)
    flip = {"A": "B", "B": "A", "EQUAL": "EQUAL", "NEITHER": "NEITHER"}
    agree = tot = 0
    firstpos_wins = firstpos_tot = 0
    for r in R:
        if r["rev_of"] and r["rev_of"] in orig:
            o = orig[r["rev_of"]]
            if r["verdict"] in flip and o["verdict"] in flip:
                tot += 1
                agree += int(r["verdict"] == flip[o["verdict"]])
    for r in R:
        if r["verdict"] in ("A", "B"):
            firstpos_tot += 1
            firstpos_wins += int(r["verdict"] == "A")
    out["position_consistency"] = round(agree / tot, 3) if tot else None
    out["n_reversed_scored"] = tot
    out["first_position_winrate"] = round(firstpos_wins / firstpos_tot, 3)

    # exclude reversed duplicates and errors from all analyses below
    RR = [r for r in R if r["rev_of"] is None
          and r["verdict"] in ("A", "B", "EQUAL", "NEITHER")]

    def lab(r, side):
        return own_label(ents[r[side]], m)

    # --- 1a. binary self-knowledge (own-label known vs unknown pairs) ---
    kn_unk = [r for r in RR
              if {lab(r, "a"), lab(r, "b")} == {"known", "unknown"}]
    ok = eq = nei = wrong = 0
    for r in kn_unk:
        known_side = "A" if lab(r, "a") == "known" else "B"
        if r["verdict"] == known_side:
            ok += 1
        elif r["verdict"] == "EQUAL":
            eq += 1
        elif r["verdict"] == "NEITHER":
            nei += 1
        else:
            wrong += 1
    out["binary"] = {"n": len(kn_unk),
                     "picked_known": round(ok / len(kn_unk), 3),
                     "picked_unknown": round(wrong / len(kn_unk), 3),
                     "equal": round(eq / len(kn_unk), 3),
                     "neither": round(nei / len(kn_unk), 3)}

    # --- 1b. traps: fictional vs model-known real ---
    traps = [r for r in RR if r["stratum"] == "trap_real"
             and {lab(r, "a"), lab(r, "b")} == {"fictional", "known"}]
    fp = 0
    for r in traps:
        fict_side = "A" if lab(r, "a") == "fictional" else "B"
        fp += int(r["verdict"] in (fict_side, "EQUAL"))
    out["trap"] = {"n": len(traps),
                   "false_recognition": round(fp / len(traps), 3) if traps else None}
    ff = [r for r in RR if r["stratum"] == "trap_fict"]
    out["trap_fict_neither_rate"] = round(
        sum(r["verdict"] == "NEITHER" for r in ff) / len(ff), 3) if ff else None

    # --- abstention by stratum ---
    out["neither_rate_by_stratum"] = {
        s: round(np.mean([r["verdict"] == "NEITHER" for r in RR
                          if r["stratum"] == s]), 3)
        for s in sorted({r["stratum"] for r in RR})}

    # --- 2a. graded directional accuracy on both-known pairs ---
    bk = [r for r in RR if lab(r, "a") == "known" and lab(r, "b") == "known"]
    out["graded"] = {}
    for margin in (0.15, 0.30):
        sub = [r for r in bk
               if abs(ents[r["a"]][f"score__{m}"]
                      - ents[r["b"]][f"score__{m}"]) >= margin]
        cor = eq = 0
        for r in sub:
            hi = "A" if (ents[r["a"]][f"score__{m}"]
                         > ents[r["b"]][f"score__{m}"]) else "B"
            if r["verdict"] == hi:
                cor += 1
            elif r["verdict"] == "EQUAL":
                eq += 1
        dec = len(sub) - eq
        out["graded"][f"margin_{margin}"] = {
            "n": len(sub), "equal_rate": round(eq / len(sub), 3),
            "acc_decided": round(cor / dec, 3) if dec else None,
            "acc_with_equal_half": round((cor + 0.5 * eq) / len(sub), 3)}
    out["n_both_known_pairs"] = len(bk)

    # --- 2b. Davidson BT on decided real-real pairs ---
    rng = np.random.default_rng(SEED)
    bt_pairs = []
    for r in RR:
        if ents[r["a"]]["kind"] != "real" or ents[r["b"]]["kind"] != "real":
            continue
        if r["verdict"] == "A":
            bt_pairs.append((r["a"], r["b"], 1))
        elif r["verdict"] == "B":
            bt_pairs.append((r["a"], r["b"], 0))
        elif r["verdict"] == "EQUAL":
            bt_pairs.append((r["a"], r["b"], 2))
    deg = Counter()
    for a, b, _ in bt_pairs:
        deg[a] += 1
        deg[b] += 1
    ids = sorted({e for e in deg})
    theta = fit_davidson(bt_pairs, ids)

    eligible = [e for e in ids if deg[e] >= 5]
    known_elig = [e for e in eligible if own_label(ents[e], m) == "known"]

    def spear(subset, target):
        x = [theta[e] for e in subset]
        y = [ents[e][target] for e in subset]
        return spearmanr(x, y)

    own_col, nr_col = f"score__{m}", "panel_nr"
    rho_own = spear(known_elig, own_col)
    rho_own_all = spear(eligible, own_col)
    rho_nr = spear(known_elig, nr_col)
    rho_nr_all = spear(eligible, nr_col)

    # pair bootstrap for the two headline correlations
    boots_own, boots_nr = [], []
    for _ in range(N_BOOT):
        th_b = fit_davidson(bt_pairs, ids, rng=rng)
        xb = [th_b[e] for e in known_elig]
        boots_own.append(spearmanr(xb, [ents[e][own_col] for e in known_elig])[0])
        xb2 = [th_b[e] for e in eligible]
        boots_nr.append(spearmanr(xb2, [ents[e][nr_col] for e in eligible])[0])
    out["bt"] = {
        "n_pairs": len(bt_pairs), "n_entities": len(ids),
        "n_eligible": len(eligible), "n_known_eligible": len(known_elig),
        "rho_own_known": round(float(rho_own[0]), 3),
        "rho_own_known_ci": [round(float(rho_own[0]) + s * 1.96
                                   * float(np.std(boots_own)), 3)
                             for s in (-1, 1)],
        "rho_own_all": round(float(rho_own_all[0]), 3),
        "rho_panel_known": round(float(rho_nr[0]), 3),
        "rho_panel_all": round(float(rho_nr_all[0]), 3),
        "rho_panel_all_ci": [round(float(rho_nr_all[0]) + s * 1.96
                                   * float(np.std(boots_nr)), 3)
                             for s in (-1, 1)],
    }
    # --- 2c. what component does self-report read? ---
    ids_c = [e for e in eligible if e in cond]
    out["decomposition"] = {
        "rho_bt_prevalence": round(float(spearmanr(
            [theta[e] for e in eligible],
            [pknown[e] for e in eligible])[0]), 3),
        "rho_bt_cond_level": round(float(spearmanr(
            [theta[e] for e in ids_c], [cond[e] for e in ids_c])[0]), 3),
        "rho_own_cond_level_known": round(float(spearmanr(
            [ents[e][own_col] for e in known_elig if e in cond],
            [cond[e] for e in known_elig if e in cond])[0]), 3),
        "rho_own_prevalence_known": round(float(spearmanr(
            [ents[e][own_col] for e in known_elig],
            [pknown[e] for e in known_elig])[0]), 3),
    }

    # --- 2d. directional accuracy against the panel ordering ---
    pdir = {}
    for margin in (0.15,):
        sub = [r for r in bk
               if abs(ents[r["a"]]["panel_nr"] - ents[r["b"]]["panel_nr"])
               >= margin and r["verdict"] in ("A", "B")]
        cor = sum(r["verdict"] == ("A" if ents[r["a"]]["panel_nr"]
                                   > ents[r["b"]]["panel_nr"] else "B")
                  for r in sub)
        pdir[f"margin_{margin}"] = {"n": len(sub),
                                    "acc_decided": round(cor / len(sub), 3)}
    out["graded_vs_panel"] = pdir

    # --- 3. introspection on fame-(in)congruent boundary pairs ---
    intro = {}
    for grp in ("congruent", "incongruent"):
        intro[grp] = {"n": 0, "picked_own_known": 0, "picked_unknown": 0,
                      "equal": 0, "neither": 0}
    for r in RR:
        la, lb = lab(r, "a"), lab(r, "b")
        if {la, lb} != {"known", "unknown"}:
            continue
        ka, ua = ("a", "b") if la == "known" else ("b", "a")
        gap = ents[r[ka]]["panel_nr"] - ents[r[ua]]["panel_nr"]
        if abs(gap) < 0.05:
            continue
        grp = "congruent" if gap > 0 else "incongruent"
        ks = "A" if ka == "a" else "B"
        us = "B" if ka == "a" else "A"
        d = intro[grp]
        d["n"] += 1
        if r["verdict"] == ks:
            d["picked_own_known"] += 1
        elif r["verdict"] == us:
            d["picked_unknown"] += 1
        elif r["verdict"] == "EQUAL":
            d["equal"] += 1
        else:
            d["neither"] += 1
    for grp, d in intro.items():
        n = d["n"]
        for k in ("picked_own_known", "picked_unknown", "equal", "neither"):
            d[k] = round(d[k] / n, 3) if n else None
    out["introspection_boundary"] = intro

    out["_theta"] = {e: round(theta[e], 4) for e in ids}
    return out


def main() -> None:
    ents, res = load()
    pknown, cond = panel_components(ents)
    summary = {}
    theta_rows = []
    for m in MODELS:
        print(f"=== {m} ===", flush=True)
        s = analyze_model(m, ents, res, pknown, cond)
        th = s.pop("_theta")
        for e, t in th.items():
            theta_rows.append({"entity_id": e, "model_id": m, "bt_theta": t,
                               "own_score": ents[e].get(f"score__{m}"),
                               "panel_nr": ents[e].get("panel_nr"),
                               "own_label": own_label(ents[e], m)})
        summary[m] = s
        print(json.dumps({k: v for k, v in s.items()
                          if k not in ("neither_rate_by_stratum",)}, indent=2))

    # inter-model agreement of self-report rankings
    tdf = pd.DataFrame(theta_rows)
    piv = tdf.pivot(index="entity_id", columns="model_id",
                    values="bt_theta").dropna()
    agree = {}
    for i, a in enumerate(MODELS):
        for b in MODELS[i + 1:]:
            agree[f"{a}__vs__{b}"] = round(
                float(spearmanr(piv[a], piv[b])[0]), 3)
    summary["_inter_model_bt_spearman"] = agree

    (HERE / "outputs/summary.json").write_text(json.dumps(summary, indent=2))
    tdf.to_csv(HERE / "outputs/bt_theta.csv", index=False)
    print("inter-model BT agreement:", agree)
    print("\nwrote outputs/summary.json, outputs/bt_theta.csv")


if __name__ == "__main__":
    main()
