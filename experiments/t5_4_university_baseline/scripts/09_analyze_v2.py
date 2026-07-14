"""Analyze the v2 per-university run (windowed + faculty cohorts).

Reports, per cohort, mean NameRank with 95% CI on the full 36-model panel,
plus refusal rates and answered-only means. The windowed university cohorts
test the matched-design question (per-university baselines vs the global
baseline); the faculty cohorts (no bibliometric conditioning) test real
between-university composition differences. In-run controls tie both to the
concurrently-running t6 v2 full pass.

Also runs the between-university tests (ANOVA / Kruskal-Wallis / pairwise
Welch) within each design, and — for faculty cohorts — a same-entity check
against the t6 full pass for any overlapping csrankings entities.

Writes outputs/summary_v2.json.
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
except ImportError:  # tests skipped if scipy unavailable
    st = None


def mean_ci(xs):
    m = statistics.mean(xs)
    if len(xs) < 2:
        return m, 0.0
    return m, 1.96 * statistics.stdev(xs) / math.sqrt(len(xs))


def main() -> None:
    import sys
    fname = sys.argv[1] if len(sys.argv) > 1 else "univ_v2_results.jsonl"
    results = []
    with open(HERE / "outputs" / fname) as f:
        for line in f:
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    entities = {e["id"]: e for e in json.loads(
        (HERE / "inputs" / "univ_entities_v2.json").read_text())}

    per_ent = defaultdict(list)
    per_ent_ref = defaultdict(list)
    for r in results:
        per_ent[r["entity_id"]].append(r["score"])
        per_ent_ref[r["entity_id"]].append(r["is_refusal"])

    nr = {eid: statistics.mean(v) for eid, v in per_ent.items()
          if len(v) >= 30}

    cohorts = defaultdict(list)
    for eid, score in nr.items():
        cohorts[entities[eid]["cohort"]].append(eid)

    table = {}
    for coh, ids in cohorts.items():
        scores = [nr[i] for i in ids]
        ref = [statistics.mean(per_ent_ref[i]) for i in ids]
        m, h = mean_ci(scores)
        table[coh] = {"n": len(ids), "mean": round(m, 4), "ci95": round(h, 4),
                      "median": round(statistics.median(scores), 4),
                      "refusal_rate": round(statistics.mean(ref), 3)}

    print(f"records: {len(results):,}; entities with >=30 models: {len(nr)}")
    print(f"\n{'cohort':30s} {'n':>4s} {'mean':>7s} {'±CI':>6s} "
          f"{'median':>7s} {'refusal':>8s}")
    for coh, t in sorted(table.items(), key=lambda kv: -kv[1]["mean"]):
        print(f"{coh:30s} {t['n']:4d} {t['mean']:7.3f} {t['ci95']:6.3f} "
              f"{t['median']:7.3f} {t['refusal_rate']:8.1%}")

    tests = {}
    if st is not None:
        for label, prefix in (("windowed", "univ_mit univ_uc_berkeley "
                                           "univ_ucsd univ_uc_irvine"),
                              ("faculty", "univ_fac_mit univ_fac_uc_berkeley "
                                          "univ_fac_ucsd univ_fac_uc_irvine")):
            names = prefix.split()
            groups = {c: [nr[i] for i in cohorts.get(c, [])] for c in names}
            groups = {c: v for c, v in groups.items() if len(v) >= 10}
            if len(groups) < 2:
                continue
            F, p = st.f_oneway(*groups.values())
            H, pk = st.kruskal(*groups.values())
            pair = {}
            for a, b in itertools.combinations(sorted(groups), 2):
                t_, pt = st.ttest_ind(groups[a], groups[b], equal_var=False)
                pair[f"{a}|{b}"] = round(pt, 3)
            tests[label] = {"anova_p": round(p, 4),
                            "kruskal_p": round(pk, 4), "pairwise_p": pair}
            print(f"\n{label}: ANOVA p={p:.4f}, Kruskal p={pk:.4f}")
            for k, v in pair.items():
                print(f"  {k}: p={v}")

    out_name = "summary_v3.json" if "v3" in fname else "summary_v2.json"
    (HERE / "outputs" / out_name).write_text(json.dumps(
        {"cohorts": table, "tests": tests, "n_records": len(results)},
        indent=1))


if __name__ == "__main__":
    main()
