"""Final analysis: detection-rate headline + depth diagnostic.

Headline metric (per user decision 2026-07-12): NameRank-detect = fraction
of panel models whose response demonstrates recognition (>=1 specific,
non-guessable, beyond-context fact corroborated by the gold; refusals count
as not recognized). Depth diagnostic: mean graded coverage*accuracy among
recognizing models (appendix-level).

Reports per-cohort detection rates with CIs, between-university tests on
both designs, the regression-fix validation cases, and the guessability
diagnostic (contradiction rates).

Writes outputs/summary_final.json.
"""
from __future__ import annotations

import itertools
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

try:
    from scipy import stats as st
except ImportError:
    st = None

VALIDATION_CASES = [
    "univ_fac_uc_berkeley_pieter_abbeel", "univ_fac_mit_antonio_torralba",
    "univ_fac_mit_russ_tedrake", "univ_fac_uc_berkeley_matei_a_zaharia",
    "univ_fac_mit_patrick_henry_winston",
]


def mean_ci(xs):
    m = statistics.mean(xs)
    if len(xs) < 2:
        return m, 0.0
    return m, 1.96 * statistics.stdev(xs) / math.sqrt(len(xs))


def main() -> None:
    recs = []
    for fname in ("univ_v3judge_results.jsonl", "univ_v3judge_topup.jsonl"):
        path = HERE / "outputs" / fname
        if not path.exists():
            continue
        with open(path) as f:
            for line in f:
                try:
                    recs.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    entities = {e["id"]: e for e in json.loads(
        (HERE / "inputs" / "univ_entities_v2.json").read_text())}
    meta = json.loads((HERE / "inputs" / "univ_gold_v3.meta.json").read_text())
    ungrounded = {k for k, m in meta.items() if m.get("n_sources") == 0}

    per = defaultdict(list)
    for r in recs:
        per[r["entity_id"]].append(r)

    detect, depth, refusal = {}, {}, {}
    for eid, v in per.items():
        if len(v) < 30:
            continue
        detect[eid] = statistics.mean(1.0 if r["recognized"] else 0.0
                                      for r in v)
        rec_scores = [r["score"] for r in v if r["recognized"]]
        depth[eid] = statistics.mean(rec_scores) if rec_scores else 0.0
        refusal[eid] = statistics.mean(1.0 if r["is_refusal"] else 0.0
                                       for r in v)

    cohorts = defaultdict(list)
    for eid in detect:
        cohorts[entities[eid]["cohort"]].append(eid)

    table = {}
    for coh, ids in cohorts.items():
        d = [detect[i] for i in ids]
        m, h = mean_ci(d)
        grounded = [detect[i] for i in ids if i not in ungrounded]
        table[coh] = {
            "n": len(ids),
            "detect_mean": round(m, 4), "detect_ci95": round(h, 4),
            "detect_median": round(statistics.median(d), 4),
            "detect_grounded_only": round(statistics.mean(grounded), 4)
            if grounded else None,
            "n_ungrounded_gold": len(ids) - len(grounded),
            "depth_mean": round(statistics.mean(depth[i] for i in ids), 4),
            "refusal_rate": round(statistics.mean(refusal[i] for i in ids), 3),
        }

    print(f"{len(recs):,} detection records; {len(detect)} entities "
          f"with >=30 models\n")
    print(f"{'cohort':30s} {'n':>4s} {'detect':>7s} {'±CI':>6s} "
          f"{'median':>7s} {'grnd-only':>9s} {'depth':>6s} {'refusal':>8s}")
    for coh, t in sorted(table.items(), key=lambda kv: -kv[1]["detect_mean"]):
        go = (f"{t['detect_grounded_only']:9.3f}"
              if t["detect_grounded_only"] is not None else "        -")
        print(f"{coh:30s} {t['n']:4d} {t['detect_mean']:7.3f} "
              f"{t['detect_ci95']:6.3f} {t['detect_median']:7.3f} {go} "
              f"{t['depth_mean']:6.3f} {t['refusal_rate']:8.1%}")

    tests = {}
    if st is not None:
        for label, names in (
                ("windowed", ["univ_mit", "univ_uc_berkeley", "univ_ucsd",
                              "univ_uc_irvine"]),
                ("faculty", ["univ_fac_mit", "univ_fac_uc_berkeley",
                             "univ_fac_ucsd", "univ_fac_uc_irvine"])):
            groups = {c: [detect[i] for i in cohorts.get(c, [])]
                      for c in names}
            groups = {c: v for c, v in groups.items() if len(v) >= 10}
            if len(groups) < 2:
                continue
            F, p = st.f_oneway(*groups.values())
            H, pk = st.kruskal(*groups.values())
            pair = {f"{a}|{b}": round(st.ttest_ind(groups[a], groups[b],
                                                   equal_var=False)[1], 3)
                    for a, b in itertools.combinations(sorted(groups), 2)}
            tests[label] = {"anova_p": round(p, 4), "kruskal_p": round(pk, 4),
                            "pairwise_p": pair}
            print(f"\n{label}: ANOVA p={p:.4f}, Kruskal p={pk:.4f}")
            for k, v in pair.items():
                print(f"  {k}: p={v}")

    print("\nRegression-fix validation (famous-name cases):")
    val = {}
    for eid in VALIDATION_CASES:
        if eid in detect:
            val[eid] = {"detect": round(detect[eid], 3),
                        "depth": round(depth[eid], 3)}
            print(f"  {entities[eid]['name']:30s} detect={detect[eid]:.3f} "
                  f"depth={depth[eid]:.3f}")

    (HERE / "outputs" / "summary_final.json").write_text(json.dumps(
        {"cohorts": table, "tests": tests, "validation": val,
         "n_records": len(recs)}, indent=1))


if __name__ == "__main__":
    main()
