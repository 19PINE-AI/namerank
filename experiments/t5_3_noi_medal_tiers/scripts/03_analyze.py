"""Analyze the NOI 2009 medal-tier run.

Questions:
1. Do gold/silver/bronze differ in NameRank? (tier means/CIs vs the ~0.20
   short-boilerplate synthetic floor; Kruskal-Wallis + pairwise Mann-Whitney
   with Cliff's delta)
2. Is there a dose-response on the underlying contest score/rank, beyond the
   tier cut? (Spearman + OLS within and across tiers)
3. Covariates: grade at contest time, gender, province.
4. Panel anchor: the 29 main-run NOI golds and 30 OpenAlex controls re-probed
   here vs their released main-run values (level shift + rank correlation).
5. The within-person triple (Li Bojie): bronze-roster boilerplate gold vs
   MSRA-fellowship framing vs dense reference gold.

Writes outputs/tier_per_entity.csv and outputs/tier_analysis.json; prints a
readable report.
"""
from __future__ import annotations

import csv
import json
import math
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
OUT = HERE / "outputs"

FLOOR_SHORT_GOLD = 0.199   # synthetic-null IMO-archetype floor (App. M)


def mean_ci(xs, B=4000, seed=7):
    rng = random.Random(seed)
    m = st.mean(xs)
    if len(xs) < 2:
        return m, m, m
    boots = sorted(st.mean(rng.choices(xs, k=len(xs))) for _ in range(B))
    return m, boots[int(0.025 * B)], boots[int(0.975 * B)]


def mannwhitney_p(a, b):
    """Normal-approximation two-sided Mann-Whitney p (fine at these n)."""
    n1, n2 = len(a), len(b)
    allv = sorted((v, 0) for v in a) + sorted((v, 1) for v in b)
    allv.sort()
    ranks, i = {}, 0
    vals = [v for v, _ in allv]
    while i < len(vals):
        j = i
        while j < len(vals) and vals[j] == vals[i]:
            j += 1
        r = (i + j + 1) / 2
        for k in range(i, j):
            ranks[k] = r
        i = j
    r1 = sum(ranks[k] for k, (_, g) in enumerate(allv) if g == 0)
    u1 = r1 - n1 * (n1 + 1) / 2
    mu = n1 * n2 / 2
    sd = math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
    if sd == 0:
        return 1.0
    z = (u1 - mu) / sd
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return p


def cliffs_delta(a, b):
    gt = sum(1 for x in a for y in b if x > y)
    lt = sum(1 for x in a for y in b if x < y)
    return (gt - lt) / (len(a) * len(b))


def kruskal_p(groups):
    allv = [(v, gi) for gi, g in enumerate(groups) for v in g]
    allv.sort()
    n = len(allv)
    ranks, i = [0.0] * n, 0
    vals = [v for v, _ in allv]
    while i < n:
        j = i
        while j < n and vals[j] == vals[i]:
            j += 1
        r = (i + j + 1) / 2
        for k in range(i, j):
            ranks[k] = r
        i = j
    rsum = defaultdict(float)
    for k, (_, gi) in enumerate(allv):
        rsum[gi] += ranks[k]
    h = 12 / (n * (n + 1)) * sum(
        rsum[gi] ** 2 / len(g) for gi, g in enumerate(groups)) - 3 * (n + 1)
    # chi2 survival, df = len(groups)-1, via Wilson-Hilferty approximation
    df = len(groups) - 1
    zz = ((h / df) ** (1 / 3) - (1 - 2 / (9 * df))) / math.sqrt(2 / (9 * df))
    p = 1 - 0.5 * (1 + math.erf(zz / math.sqrt(2)))
    return h, p


def ols(xs, ys):
    n = len(xs)
    mx, my = st.mean(xs), st.mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return 0.0, my, 0.0
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    a = my - b * mx
    ss_res = sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys))
    ss_tot = sum((y - my) ** 2 for y in ys)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return b, a, r2


def spearman(xs, ys):
    def rk(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j < len(v) and v[order[j]] == v[order[i]]:
                j += 1
            for k in range(i, j):
                r[order[k]] = (i + j + 1) / 2
            i = j
        return r
    rx, ry = rk(xs), rk(ys)
    mx, my = st.mean(rx), st.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) *
                    sum((b - my) ** 2 for b in ry))
    return num / den if den else 0.0


def main() -> None:
    entities = {e["id"]: e for e in json.loads(
        (HERE / "inputs" / "tier_entities.json").read_text())}
    records = json.loads((OUT / "pilot_results_tiers.json").read_text())
    clean = [r for r in records if not r["response"].startswith("[ERROR")]
    n_err = len(records) - len(clean)

    per_model = defaultdict(dict)
    by_ent = defaultdict(list)
    refusals = defaultdict(list)
    for r in clean:
        by_ent[r["entity_id"]].append(r["score"])
        refusals[r["entity_id"]].append(r["is_refusal"])
        per_model[r["model_id"]][r["entity_id"]] = r["score"]

    ent_rows = []
    for eid, scores in by_ent.items():
        e = entities[eid]
        ent_rows.append({
            "entity_id": eid, "entity_name": e["name"],
            "cohort": e["cohort"], "tier": e.get("tier"),
            "control": e["control"],
            "noi_score": e.get("noi_score"), "noi_rank": e.get("noi_rank"),
            "grade": e.get("grade"), "province": e.get("province"),
            "gender": e.get("gender"),
            "n_models": len(scores),
            "namerank": st.mean(scores),
            "namerank_sd": st.stdev(scores) if len(scores) > 1 else 0.0,
            "refusal_rate": st.mean(refusals[eid]),
        })
    ent_rows.sort(key=lambda r: -r["namerank"])
    with open(OUT / "tier_per_entity.csv", "w", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(ent_rows[0].keys()))
        w.writeheader()
        w.writerows(ent_rows)

    tiers = {t: [r for r in ent_rows if r["tier"] == t and not r["control"]]
             for t in ("gold", "silver", "bronze")}
    report = {"n_records_clean": len(clean), "n_records_error": n_err,
              "floor_short_gold": FLOOR_SHORT_GOLD, "tiers": {}}

    print(f"records: {len(clean)} clean, {n_err} error\n")
    print("== Tier distribution (panel-mean NameRank) ==")
    for t, rows in tiers.items():
        xs = [r["namerank"] for r in rows]
        m, lo, hi = mean_ci(xs)
        above = sum(1 for x in xs if x > FLOOR_SHORT_GOLD)
        report["tiers"][t] = {
            "n": len(xs), "mean": m, "ci95": [lo, hi],
            "median": st.median(xs), "sd": st.stdev(xs),
            "min": min(xs), "max": max(xs),
            "n_above_floor": above,
            "mean_refusal": st.mean([r["refusal_rate"] for r in rows]),
        }
        print(f"  {t:7s} n={len(xs):3d} mean={m:.3f} [{lo:.3f},{hi:.3f}] "
              f"median={st.median(xs):.3f} sd={st.stdev(xs):.3f} "
              f"range={min(xs):.3f}-{max(xs):.3f} "
              f">floor(0.20): {above}/{len(xs)}")

    g, s, b = (sorted(r["namerank"] for r in tiers[t])
               for t in ("gold", "silver", "bronze"))
    h, p = kruskal_p([g, s, b])
    report["kruskal"] = {"H": h, "p": p}
    print(f"\nKruskal-Wallis across tiers: H={h:.2f}, p={p:.4f}")
    for (n1, a), (n2, bb) in [(("gold", g), ("silver", s)),
                              (("silver", s), ("bronze", b)),
                              (("gold", g), ("bronze", b))]:
        pv = mannwhitney_p(a, bb)
        d = cliffs_delta(a, bb)
        report[f"mw_{n1}_vs_{n2}"] = {"p": pv, "cliffs_delta": d}
        print(f"  {n1} vs {n2}: MW p={pv:.4f}, Cliff's delta={d:+.3f}")

    print("\n== Dose-response on contest score/rank ==")
    med = [r for t in tiers.values() for r in t]
    xs = [r["noi_score"] for r in med]
    ys = [r["namerank"] for r in med]
    bsl, _, r2 = ols(xs, ys)
    rho = spearman(xs, ys)
    report["dose_response_all"] = {
        "ols_slope_per_100pts": bsl * 100, "r2": r2, "spearman": rho}
    print(f"  all 103: NameRank ~ contest score: slope {bsl*100:+.3f}/100pts, "
          f"R2={r2:.3f}, Spearman rho={rho:+.3f}")
    for t, rows in tiers.items():
        xs = [r["noi_score"] for r in rows]
        ys = [r["namerank"] for r in rows]
        _, _, r2t = ols(xs, ys)
        report["tiers"][t]["within_tier_score_r2"] = r2t
        report["tiers"][t]["within_tier_spearman"] = spearman(xs, ys)
        print(f"  within {t}: R2={r2t:.3f}, rho={spearman(xs, ys):+.3f}")

    print("\n== Covariates (medalists only) ==")
    for key in ("grade", "gender"):
        groups = defaultdict(list)
        for r in med:
            groups[r[key]].append(r["namerank"])
        report[f"by_{key}"] = {k: {"n": len(v), "mean": st.mean(v)}
                               for k, v in groups.items()}
        line = "  " + key + ": " + "  ".join(
            f"{k} n={len(v)} m={st.mean(v):.3f}"
            for k, v in sorted(groups.items()))
        print(line)

    print("\n== Panel anchor vs released main run ==")
    released = {}
    with open(REPO / "data" / "analysis" / "namerank_per_entity.csv") as f:
        for row in csv.DictReader(f):
            released[row["entity_id"]] = float(row["namerank"])
    shared = [(r["namerank"], released[r["entity_id"]], r["entity_id"])
              for r in ent_rows if r["entity_id"] in released]
    if shared:
        here = [a for a, _, _ in shared]
        main = [c for _, c, _ in shared]
        rho = spearman(here, main)
        shift = st.mean([a - c for a, c, _ in shared])
        report["anchor"] = {"n": len(shared), "spearman": rho,
                            "mean_shift": shift}
        print(f"  {len(shared)} shared entities: Spearman rho={rho:.3f}, "
              f"mean shift here-minus-main {shift:+.3f}")
        noi_shared = [(a, c) for a, c, e in shared if e.startswith("noi_")]
        if len(noi_shared) > 2:
            print(f"  NOI golds only (n={len(noi_shared)}): "
                  f"rho={spearman([a for a,_ in noi_shared], [c for _,c in noi_shared]):.3f}, "
                  f"shift {st.mean([a-c for a,c in noi_shared]):+.3f}")

    print("\n== Within-person triple (Li Bojie) ==")
    for eid in ("noi_b_li_bojie_2009", "msra_bojie_li_2017", "bojie_li"):
        row = next((r for r in ent_rows if r["entity_id"] == eid), None)
        if row:
            rel = released.get(eid)
            report.setdefault("bojie_triple", {})[eid] = {
                "namerank": row["namerank"], "released": rel}
            print(f"  {eid:24s} here={row['namerank']:.3f} "
                  f"refusal={row['refusal_rate']:.2f} "
                  f"released={'%.3f' % rel if rel is not None else '—'}")

    print("\n== Top 15 medalists this run ==")
    for r in [r for r in ent_rows if r["tier"]][:15]:
        print(f"  {r['namerank']:.3f} {r['tier']:6s} rank{r['noi_rank']:>3} "
              f"{r['entity_name']}")

    (OUT / "tier_analysis.json").write_text(json.dumps(report, indent=1))
    print(f"\nwrote {OUT/'tier_per_entity.csv'} and {OUT/'tier_analysis.json'}")


if __name__ == "__main__":
    main()
