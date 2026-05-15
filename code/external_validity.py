"""External validity: NameRank vs OpenAlex citations / h-index.

Reports the within-cohort R² for log(citations) and log(h-index), the joint
regression where citations contribute zero marginal R² beyond h-index, and a
decile breakdown. Stdout-only — the table appears in Section 6 and Appendix E
of the paper.
"""
from __future__ import annotations

import csv
import json
import math
import statistics
from collections import defaultdict

from _paths import ANALYSIS, INPUTS


def pearson(x, y):
    n = len(x)
    if n < 3:
        return 0.0
    mx, my = statistics.mean(x), statistics.mean(y)
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    sx = sum((xi - mx) ** 2 for xi in x) ** 0.5
    sy = sum((yi - my) ** 2 for yi in y) ** 0.5
    return num / (sx * sy) if sx * sy > 0 else 0.0


def rank(xs):
    sorted_pairs = sorted(enumerate(xs), key=lambda p: p[1])
    ranks = [0] * len(xs)
    for r, (i, _) in enumerate(sorted_pairs):
        ranks[i] = r
    return ranks


def spearman(x, y):
    return pearson(rank(x), rank(y))


def correlate(ents, nr, cohort_name, metric_field):
    xs, ys = [], []
    for eid, e in ents.items():
        if e.get("cohort") != cohort_name:
            continue
        m = e.get(metric_field)
        if m is None or m <= 0 or eid not in nr:
            continue
        xs.append(m)
        ys.append(nr[eid])
    return xs, ys


def main() -> None:
    ents = {e["id"]: e for e in json.loads((INPUTS / "pilot_entities.json").read_text())}
    nr = {row["entity_id"]: float(row["namerank"])
          for row in csv.DictReader(open(ANALYSIS / "namerank_per_entity.csv", encoding="utf-8"))}

    for cohort, metric in [
        ("long_tail_researcher_openalex", "cited_by_count"),
        ("long_tail_researcher_openalex", "h_index"),
        ("long_tail_paper", "cited_by_count"),
    ]:
        xs, ys = correlate(ents, nr, cohort, metric)
        if not xs:
            print(f"{cohort} x {metric}: NO DATA")
            continue
        log_xs = [math.log1p(x) for x in xs]
        r_raw = pearson(xs, ys)
        r_log = pearson(log_xs, ys)
        print(f"{cohort} x {metric} (n={len(xs)}):")
        print(f"  Pearson(raw, NR)      = {r_raw:+.3f}, R² = {r_raw**2:.3f}")
        print(f"  Pearson(log1p, NR)    = {r_log:+.3f}, R² = {r_log**2:.3f}")
        print(f"  Spearman              = {spearman(xs, ys):+.3f}")

        pairs = sorted(zip(xs, ys))
        ds = max(1, len(pairs) // 10)
        print(f"  Deciles by {metric}:")
        for d in range(10):
            chunk = pairs[d * ds:(d + 1) * ds]
            if chunk:
                mx = statistics.mean([p[0] for p in chunk])
                my = statistics.mean([p[1] for p in chunk])
                print(f"    D{d+1:<2} n={len(chunk):<4} mean_{metric}={mx:<12.1f} mean_NR={my:.3f}")
        print()


if __name__ == "__main__":
    main()
