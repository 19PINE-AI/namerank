"""East/West model variance: do Chinese-aligned models recognize different
entities than Western-aligned ones?

Writes data/analysis/east_west_per_entity.csv  (per-entity W mean, C mean, delta)
       data/analysis/east_west_per_cohort.csv  (cohort-level median delta).
"""
from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict

from _paths import ANALYSIS, INPUTS
from panel import WESTERN, CHINESE


def main() -> None:
    ents = {e["id"]: e for e in json.loads((INPUTS / "pilot_entities.json").read_text())}
    matrix = json.loads((ANALYSIS / "namerank_matrix.json").read_text())

    rows = []
    for eid, model_scores in matrix.items():
        e = ents.get(eid, {})
        w = [model_scores[m] for m in WESTERN if m in model_scores]
        c = [model_scores[m] for m in CHINESE if m in model_scores]
        if not w or not c:
            continue
        wmean = statistics.mean(w)
        cmean = statistics.mean(c)
        rows.append({
            "entity_id": eid,
            "entity_name": e.get("name", ""),
            "cohort": e.get("cohort", "?"),
            "western_mean": round(wmean, 4),
            "chinese_mean": round(cmean, 4),
            "delta_chinese_minus_western": round(cmean - wmean, 4),
            "abs_delta": round(abs(cmean - wmean), 4),
        })

    with open(ANALYSIS / "east_west_per_entity.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    by_cohort: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        by_cohort[r["cohort"]].append(r["delta_chinese_minus_western"])
    cohort_rows = []
    for c, deltas in sorted(by_cohort.items(), key=lambda x: -statistics.median(x[1])):
        cohort_rows.append({
            "cohort": c, "n": len(deltas),
            "median_delta_C_minus_W": round(statistics.median(deltas), 4),
            "frac_east_higher": round(sum(1 for d in deltas if d > 0) / len(deltas), 3),
            "frac_abs_delta_geq_015": round(sum(1 for d in deltas if abs(d) >= 0.15) / len(deltas), 3),
        })
    with open(ANALYSIS / "east_west_per_cohort.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(cohort_rows[0].keys()))
        w.writeheader()
        w.writerows(cohort_rows)
    print(f"Wrote east_west_per_entity.csv ({len(rows)}) and east_west_per_cohort.csv ({len(cohort_rows)})")


if __name__ == "__main__":
    main()
