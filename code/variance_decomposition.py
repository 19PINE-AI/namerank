"""Variance decomposition: entity vs model vs cohort vs residual.

Reads the record-level CSV and reports SS for each factor. Confirms
sigma2_entity / sigma2_model = ~3.3 in the paper.
"""
from __future__ import annotations

import csv
import json
import statistics
from collections import Counter, defaultdict

from _paths import INPUTS, open_text, raw_records_path


def main() -> None:
    ents = {e["id"]: e for e in json.loads((INPUTS / "pilot_entities.json").read_text())}

    data = []
    with open_text(raw_records_path("en")) as fh:
        for r in csv.DictReader(fh):
            eid = r["entity_id"]
            e = ents.get(eid, {})
            data.append({
                "entity": eid,
                "model": r["model_id"],
                "cohort": e.get("cohort", "?"),
                "score": float(r.get("score") or 0.0),
            })

    n = len(data)
    print(f"n records   = {n}")
    print(f"n entities  = {len(set(d['entity'] for d in data))}")
    print(f"n models    = {len(set(d['model'] for d in data))}")
    print(f"n cohorts   = {len(set(d['cohort'] for d in data))}")

    grand_mean = statistics.mean(d["score"] for d in data)
    total_ss = sum((d["score"] - grand_mean) ** 2 for d in data)
    print(f"grand mean  = {grand_mean:.3f}")
    print(f"total SS    = {total_ss:.0f}")

    def marginal(key):
        mp = defaultdict(list)
        for d in data:
            mp[d[key]].append(d["score"])
        return {k: statistics.mean(v) for k, v in mp.items()}, Counter(d[key] for d in data)

    for key in ("entity", "model", "cohort"):
        means, counts = marginal(key)
        ss = sum(counts[k] * (means[k] - grand_mean) ** 2 for k in means)
        print(f"  {key:<8} SS = {ss:.0f}  ({100*ss/total_ss:.1f}% of total)")


if __name__ == "__main__":
    main()
