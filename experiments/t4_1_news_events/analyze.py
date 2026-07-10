"""News-event extension: does NameRank track the recorded attention an event received?

Inputs (this experiment's inputs/ and outputs/):
  inputs/event_metadata.csv     per-event salience + classification
  outputs/event_summary.csv     per-(event, model) judged records
  outputs/gdelt.json            secondary news-coverage salience (optional)

Analyses:
  1. Dose-response: NameRank ~ log10(total attention), full-sample and
     repeated 10-fold CV R^2 (20 repeats, seed 42 — same protocol as the
     paper's external-validity regressions).
  2. Peak vs persistence: log10(total) decomposes exactly into
     log10(peak) + log10(effective duration). Joint regression compares the
     two channels; the h-index analogy predicts duration >> peak.
  3. Region gradient at matched attention (region dummies + log views).
  4. Event-year vintage effect at matched attention.
  5. Refusal / silent-zone structure by attention band.
  6. GDELT cross-check of the salience measure.

Outputs: outputs/event_namerank.csv, outputs/analysis.json, stdout report.
"""
from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
INP, OUT = HERE / "inputs", HERE / "outputs"

REGION_BASE = "Anglo-America & Oceania"


def ols(X: np.ndarray, y: np.ndarray):
    """OLS with intercept; returns (beta, r2, resid)."""
    X1 = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(X1, y, rcond=None)
    yhat = X1 @ beta
    ss_res = float(((y - yhat) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return beta, 1 - ss_res / ss_tot, y - yhat


def cv_r2(X: np.ndarray, y: np.ndarray, repeats=20, folds=10, seed=42):
    """Repeated k-fold CV R^2 (paper protocol)."""
    rng = np.random.default_rng(seed)
    n = len(y)
    scores = []
    for _ in range(repeats):
        idx = rng.permutation(n)
        for f in range(folds):
            test = idx[f::folds]
            train = np.setdiff1d(idx, test)
            X1 = np.column_stack([np.ones(len(train)), X[train]])
            beta, *_ = np.linalg.lstsq(X1, y[train], rcond=None)
            yhat = np.column_stack([np.ones(len(test)), X[test]]) @ beta
            ss_res = float(((y[test] - yhat) ** 2).sum())
            ss_tot = float(((y[test] - y[train].mean()) ** 2).sum())
            scores.append(1 - ss_res / ss_tot if ss_tot > 0 else 0.0)
    return float(np.mean(scores)), float(np.std(scores))


def hc1_se(X: np.ndarray, y: np.ndarray):
    """OLS with HC1 robust SEs; returns beta, se (incl. intercept col 0)."""
    X1 = np.column_stack([np.ones(len(y)), X])
    XtXi = np.linalg.inv(X1.T @ X1)
    beta = XtXi @ X1.T @ y
    u = y - X1 @ beta
    n, k = X1.shape
    meat = X1.T @ (X1 * (u ** 2)[:, None])
    V = XtXi @ meat @ XtXi * n / (n - k)
    return beta, np.sqrt(np.diag(V))


def main() -> None:
    meta = {r["id"]: r for r in csv.DictReader(
        open(INP / "event_metadata.csv", encoding="utf-8"))}

    per_ent: dict[str, list] = defaultdict(list)
    refusals: dict[str, list] = defaultdict(list)
    covs: dict[str, list] = defaultdict(list)
    accs: dict[str, list] = defaultdict(list)
    for r in csv.DictReader(open(OUT / "event_summary.csv", encoding="utf-8")):
        per_ent[r["entity_id"]].append(float(r["score"]))
        refusals[r["entity_id"]].append(int(r["is_refusal"]))
        covs[r["entity_id"]].append(float(r["coverage"]))
        accs[r["entity_id"]].append(float(r["accuracy"]))

    rows = []
    for eid, scores in per_ent.items():
        if eid not in meta or len(scores) < 25:
            continue
        m = meta[eid]
        rows.append({
            "id": eid, "title": m["title"],
            "namerank": float(np.mean(scores)),
            "nr_std": float(np.std(scores)),
            "refusal_rate": float(np.mean(refusals[eid])),
            "mean_cov": float(np.mean(covs[eid])),
            "mean_acc": float(np.mean(accs[eid])),
            "n_models": len(scores),
            "region_group": m["region_group"], "region": m["region"],
            "country": m["country"], "category": m["category"],
            "start_year": int(m["start_year"]),
            "start_month": int(m["start_month"]),
            "peak_views": int(m["peak_views"]),
            "total_views": int(m["total_views"]),
            "eff_duration": float(m["eff_duration"]),
            "days_above_10": int(m["days_above_10"]),
            "tail_daily": float(m["tail_daily"]),
            "gold_words": int(m["gold_words"]),
        })
    rows.sort(key=lambda r: -r["namerank"])
    print(f"n = {len(rows)} events with full panel records\n")

    with open(OUT / "event_namerank.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    y = np.array([r["namerank"] for r in rows])
    lt = np.array([math.log10(r["total_views"]) for r in rows])
    lp = np.array([math.log10(max(r["peak_views"], 1)) for r in rows])
    ld = np.array([math.log10(max(r["eff_duration"], 1.0)) for r in rows])
    ltail = np.array([math.log10(r["tail_daily"] + 1) for r in rows])
    ld10 = np.array([math.log10(max(r["days_above_10"], 1)) for r in rows])

    res: dict = {"n": len(rows)}

    # ── 1. dose-response ──────────────────────────────────────────
    print("=== 1. Dose-response: NameRank ~ log10(attention) ===")
    for name, x in [("total_views", lt), ("peak_views", lp),
                    ("eff_duration", ld), ("days_above_10", ld10),
                    ("tail_daily", ltail)]:
        beta, r2, _ = ols(x[:, None], y)
        cvm, cvs = cv_r2(x[:, None], y)
        res[f"r2_{name}"] = round(r2, 3)
        res[f"cv_{name}"] = [round(cvm, 3), round(cvs, 3)]
        print(f"  {name:15s} R2={r2:.3f}  CV={cvm:.2f}±{cvs:.2f}  slope={beta[1]:+.3f}")

    # decile table by total views
    print("\n  Deciles by total_views:")
    order = np.argsort(lt)
    dec_rows = []
    for d in range(10):
        chunk = order[d * len(rows) // 10:(d + 1) * len(rows) // 10]
        mt = 10 ** float(np.mean(lt[chunk]))
        dec_rows.append({"decile": d + 1, "n": len(chunk),
                         "geomean_views": int(mt),
                         "mean_nr": round(float(np.mean(y[chunk])), 3),
                         "refusal": round(float(np.mean(
                             [rows[i]["refusal_rate"] for i in chunk])), 3)})
        print(f"    D{d+1:<3} n={len(chunk):<4} views~{int(mt):>11,}  "
              f"NR={dec_rows[-1]['mean_nr']:.3f}  refusal={dec_rows[-1]['refusal']:.2f}")
    res["deciles"] = dec_rows

    # gold-length confound control (cf. main-run t1_1). Gold density scales
    # with event size (bigger events -> denser Wikipedia intros -> a 150-word
    # response covers less of the gold), attenuating the raw dose-response.
    gw = np.array([r["gold_words"] for r in rows], dtype=float)
    zgw = (gw - gw.mean()) / gw.std()
    _, r2_base, _ = ols(lt[:, None], y)
    _, r2_gw_only, _ = ols(zgw[:, None], y)
    b_gl, r2_gl, _ = ols(np.column_stack([lt, zgw]), y)
    b_gl2, se_gl2 = hc1_se(np.column_stack([lt, zgw]), y)
    print(f"\n  Gold-length control: R2 {r2_base:.3f} -> {r2_gl:.3f} "
          f"(gw alone {r2_gw_only:.3f}); slope(log views | gw) = "
          f"{b_gl2[1]:+.3f} (se {se_gl2[1]:.3f}), beta(gw) = {b_gl2[2]:+.3f}")
    res["gold_length_control"] = {"r2_base": round(r2_base, 3),
                                  "r2_with_gw": round(r2_gl, 3),
                                  "r2_gw_only": round(r2_gw_only, 3),
                                  "slope_lt_given_gw": round(float(b_gl2[1]), 3),
                                  "se_lt_given_gw": round(float(se_gl2[1]), 3),
                                  "beta_gw": round(float(b_gl2[2]), 3)}

    # coverage/accuracy channel decomposition per attention decile
    cov_m = np.array([r["mean_cov"] for r in rows])
    acc_m = np.array([r["mean_acc"] for r in rows])
    print("\n  Channel decomposition by total-views decile (cov, acc):")
    chan = []
    for d in range(10):
        chunk = order[d * len(rows) // 10:(d + 1) * len(rows) // 10]
        chan.append({"decile": d + 1,
                     "cov": round(float(np.mean(cov_m[chunk])), 3),
                     "acc": round(float(np.mean(acc_m[chunk])), 3)})
        print(f"    D{d+1:<3} cov={chan[-1]['cov']:.3f} acc={chan[-1]['acc']:.3f}")
    res["channels"] = chan

    # ── 2. peak vs persistence ────────────────────────────────────
    print("\n=== 2. Peak vs persistence (log total = log peak + log duration) ===")
    zp = (lp - lp.mean()) / lp.std()
    zd = (ld - ld.mean()) / ld.std()
    beta, r2j, _ = ols(np.column_stack([zp, zd]), y)
    b_j, se_j = hc1_se(np.column_stack([zp, zd]), y)
    _, r2p, _ = ols(zp[:, None], y)
    _, r2d, _ = ols(zd[:, None], y)
    cvj = cv_r2(np.column_stack([zp, zd]), y)
    print(f"  joint R2={r2j:.3f} (CV {cvj[0]:.2f}±{cvj[1]:.2f})")
    print(f"  std beta peak    ={b_j[1]:+.3f} (se {se_j[1]:.3f})")
    print(f"  std beta duration={b_j[2]:+.3f} (se {se_j[2]:.3f})")
    print(f"  marginal R2: peak|dur={r2j - r2d:+.3f}   dur|peak={r2j - r2p:+.3f}")
    res["peak_vs_duration"] = {
        "beta_peak": round(float(b_j[1]), 3), "se_peak": round(float(se_j[1]), 3),
        "beta_dur": round(float(b_j[2]), 3), "se_dur": round(float(se_j[2]), 3),
        "r2_joint": round(r2j, 3), "cv_joint": [round(v, 3) for v in cvj],
        "marg_peak": round(r2j - r2d, 3), "marg_dur": round(r2j - r2p, 3)}

    # matched-peak contrast: within peak-tercile, top vs bottom duration tercile
    print("\n  Within peak-tercile, duration-tercile NameRank means:")
    terc = np.digitize(lp, np.quantile(lp, [1/3, 2/3]))
    contrast = []
    for t in range(3):
        mask = terc == t
        ldm = ld[mask]
        dt = np.digitize(ldm, np.quantile(ldm, [1/3, 2/3]))
        means = [float(np.mean(y[mask][dt == k])) for k in range(3)]
        ns = [int((dt == k).sum()) for k in range(3)]
        contrast.append({"peak_tercile": t + 1, "nr_by_dur_tercile":
                         [round(v, 3) for v in means], "n": ns})
        print(f"    peak T{t+1}: dur T1={means[0]:.3f} T2={means[1]:.3f} "
              f"T3={means[2]:.3f}  (n={ns})")
    res["matched_peak_contrast"] = contrast

    # ── 2b. name uniqueness: series instances vs singular events ──
    fpath = OUT / "recurring_flags.json"
    if fpath.exists():
        print("\n=== 2b. Series instances vs singular events (name uniqueness) ===")
        flags = json.loads(fpath.read_text())
        rec = np.array([1.0 if flags.get(r["id"], {}).get("recurring") else 0.0
                        for r in rows])
        n_rec = int(rec.sum())
        raw_rec = float(np.mean(y[rec == 1]))
        raw_sing = float(np.mean(y[rec == 0]))
        b, se = hc1_se(np.column_stack([lt, rec]), y)
        print(f"  n_recurring={n_rec}, n_singular={len(rows) - n_rec}")
        print(f"  raw means: singular={raw_sing:.3f}, recurring={raw_rec:.3f}")
        print(f"  adj delta (recurring, log-views ctrl) = {b[2]:+.3f} (se {se[2]:.3f})")
        # robustness: does the duration effect survive the recurring control?
        zp = (lp - lp.mean()) / lp.std()
        zd = (ld - ld.mean()) / ld.std()
        b3, se3 = hc1_se(np.column_stack([zp, zd, rec, zgw]), y)
        print(f"  peak/dur betas with recurring + gold-length ctrl: "
              f"peak={b3[1]:+.3f} (se {se3[1]:.3f}), dur={b3[2]:+.3f} (se {se3[2]:.3f}), "
              f"recurring={b3[3]:+.3f} (se {se3[3]:.3f})")
        res["recurring"] = {
            "n_recurring": n_rec, "raw_recurring": round(raw_rec, 3),
            "raw_singular": round(raw_sing, 3),
            "adj_delta": round(float(b[2]), 3), "se": round(float(se[2]), 3),
            "peak_dur_ctrl": {"beta_peak": round(float(b3[1]), 3),
                              "se_peak": round(float(se3[1]), 3),
                              "beta_dur": round(float(b3[2]), 3),
                              "se_dur": round(float(se3[2]), 3),
                              "beta_rec": round(float(b3[3]), 3),
                              "se_rec": round(float(se3[3]), 3)}}

    # ── 3. region gradient at matched attention ───────────────────
    print("\n=== 3. Region gradient (controls: log total views) ===")
    groups = sorted({r["region_group"] for r in rows})
    groups = [REGION_BASE] + [g for g in groups if g != REGION_BASE]
    G = np.zeros((len(rows), len(groups) - 1))
    for i, r in enumerate(rows):
        if r["region_group"] != REGION_BASE:
            G[i, groups.index(r["region_group"]) - 1] = 1.0
    X = np.column_stack([lt, G])
    b, se = hc1_se(X, y)
    print(f"  baseline: {REGION_BASE}")
    region_rows = []
    for gi, g in enumerate(groups[1:]):
        n_g = sum(1 for r in rows if r["region_group"] == g)
        raw = float(np.mean([r["namerank"] for r in rows if r["region_group"] == g]))
        region_rows.append({"group": g, "n": n_g, "raw_mean": round(raw, 3),
                            "coef": round(float(b[2 + gi]), 3),
                            "se": round(float(se[2 + gi]), 3)})
        print(f"    {g:28s} n={n_g:<4} raw={raw:.3f}  "
              f"adj delta={b[2+gi]:+.3f} (se {se[2+gi]:.3f})")
    base_n = sum(1 for r in rows if r["region_group"] == REGION_BASE)
    base_raw = float(np.mean([r["namerank"] for r in rows
                              if r["region_group"] == REGION_BASE]))
    print(f"    {REGION_BASE:28s} n={base_n:<4} raw={base_raw:.3f}  (baseline)")
    res["region"] = {"baseline": REGION_BASE, "base_n": base_n,
                     "base_raw": round(base_raw, 3), "rows": region_rows}

    # ── 4. event-year vintage ─────────────────────────────────────
    print("\n=== 4. Event-year effect (controls: log total views) ===")
    yr = np.array([r["start_year"] for r in rows])
    Xy = np.column_stack([lt, (yr == 2022).astype(float),
                          (yr == 2023).astype(float)])
    b, se = hc1_se(Xy, y)
    for lab, coef, s in [("2022 vs 2021", b[2], se[2]), ("2023 vs 2021", b[3], se[3])]:
        print(f"  {lab}: {coef:+.3f} (se {s:.3f})")
    raws = {int(v): round(float(np.mean(y[yr == v])), 3) for v in (2021, 2022, 2023)}
    print(f"  raw means by year: {raws}")
    res["year"] = {"delta_2022": round(float(b[2]), 3), "se_2022": round(float(se[2]), 3),
                   "delta_2023": round(float(b[3]), 3), "se_2023": round(float(se[3]), 3),
                   "raw": raws}

    # ── 5. category means (attention-adjusted) ────────────────────
    print("\n=== 5. Category (residual after log-views control) ===")
    _, _, resid = ols(lt[:, None], y)
    cat_rows = []
    for c in sorted({r["category"] for r in rows}):
        idx = [i for i, r in enumerate(rows) if r["category"] == c]
        if len(idx) < 5:
            continue
        cat_rows.append({"category": c, "n": len(idx),
                         "raw": round(float(np.mean(y[idx])), 3),
                         "resid": round(float(np.mean(resid[idx])), 3)})
        print(f"  {c:24s} n={len(idx):<4} raw={cat_rows[-1]['raw']:.3f} "
              f"resid={cat_rows[-1]['resid']:+.3f}")
    res["category"] = cat_rows

    # ── 6. GDELT cross-check ──────────────────────────────────────
    gpath = OUT / "gdelt.json"
    if gpath.exists():
        print("\n=== 6. GDELT news-volume cross-check ===")
        g = json.loads(gpath.read_text())
        pairs = [(math.log10(g[r["id"]]["gdelt_sum"]),
                  math.log10(r["total_views"]), r["namerank"])
                 for r in rows if r["id"] in g and g[r["id"]]["gdelt_sum"] > 0]
        if len(pairs) > 30:
            gx = np.array([p[0] for p in pairs])
            wx = np.array([p[1] for p in pairs])
            gy = np.array([p[2] for p in pairs])
            r_gw = float(np.corrcoef(gx, wx)[0, 1])
            _, r2g, _ = ols(gx[:, None], gy)
            print(f"  n={len(pairs)} events with nonzero GDELT volume")
            print(f"  corr(log gdelt, log wiki views) = {r_gw:.3f}")
            print(f"  NameRank ~ log gdelt: R2 = {r2g:.3f}")
            res["gdelt"] = {"n": len(pairs), "corr_wiki": round(r_gw, 3),
                            "r2_nr": round(r2g, 3)}

    # ── extremes for prose ────────────────────────────────────────
    res["top"] = [{"t": r["title"], "nr": round(r["namerank"], 3),
                   "views": r["total_views"]} for r in rows[:8]]
    res["bottom"] = [{"t": r["title"], "nr": round(r["namerank"], 3),
                      "views": r["total_views"], "refusal": r["refusal_rate"]}
                     for r in rows[-8:]]

    (OUT / "analysis.json").write_text(json.dumps(res, indent=1))
    print(f"\nWrote {OUT/'event_namerank.csv'} and {OUT/'analysis.json'}")


if __name__ == "__main__":
    main()
