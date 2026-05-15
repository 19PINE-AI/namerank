"""Judge vs embedding-similarity gap analysis.

Reports Pearson(judge_score, embedding_sim) across non-refusal records and the
top "judge low / embedding high" disagreement cases (fluent hallucinations).
This produces the Section 7.3 numbers in the paper.
"""
from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict

from _paths import INPUTS, open_text, raw_records_path


def pearson(x, y):
    n = len(x)
    if n < 3:
        return 0.0
    mx, my = statistics.mean(x), statistics.mean(y)
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    sx = sum((xi - mx) ** 2 for xi in x) ** 0.5
    sy = sum((yi - my) ** 2 for yi in y) ** 0.5
    return num / (sx * sy) if sx * sy > 0 else 0.0


def main() -> None:
    ents = {e["id"]: e for e in json.loads((INPUTS / "pilot_entities.json").read_text())}
    pairs = []
    with open_text(raw_records_path("en")) as fh:
        for r in csv.DictReader(fh):
            if r.get("is_refusal") in ("1", "true", "True"):
                continue
            sc = float(r.get("score") or 0.0)
            es = r.get("embedding_sim")
            if es in (None, ""):
                continue
            pairs.append((sc, float(es), r["entity_id"], r["model_id"]))

    if not pairs:
        print("No non-refusal records found.")
        return

    print(f"n non-refusal aligned records: {len(pairs):,}")
    print(f"Pearson(judge_score, embedding_sim) = {pearson([p[0] for p in pairs], [p[1] for p in pairs]):.3f}")

    print("\nBy judge score bucket:")
    buckets = [(0, 0.1, "0.0-0.1"), (0.1, 0.3, "0.1-0.3"), (0.3, 0.5, "0.3-0.5"),
               (0.5, 0.7, "0.5-0.7"), (0.7, 0.9, "0.7-0.9"), (0.9, 1.01, "0.9-1.0")]
    for lo, hi, label in buckets:
        sub = [e for s, e, *_ in pairs if lo <= s < hi]
        if sub:
            print(f"  {label}: n={len(sub):<7,} mean_emb_sim={statistics.mean(sub):.3f}")

    print("\nTop 20 'judge LOW / embedding HIGH' (fluent hallucinations):")
    disagree = sorted(pairs, key=lambda p: -(p[1] - p[0]))[:20]
    for sc, em, eid, m in disagree:
        name = ents.get(eid, {}).get("name", eid)
        print(f"  {name:<30} {m:<25} judge={sc:.2f}  emb={em:.2f}  gap={em-sc:+.2f}")


if __name__ == "__main__":
    main()
