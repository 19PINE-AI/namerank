"""Per-cohort summary of the NameRank distribution.

Writes data/analysis/cohort_summary.csv with mean / median / quantiles / silent
fraction per cohort. Reads data/analysis/namerank_per_entity.csv.
"""
from __future__ import annotations

import csv
import statistics
from collections import defaultdict

from _paths import ANALYSIS


def main() -> None:
    rows = list(csv.DictReader(open(ANALYSIS / "namerank_per_entity.csv", encoding="utf-8")))
    for r in rows:
        r["namerank"] = float(r["namerank"])
        r["refusal_rate"] = float(r.get("refusal_rate") or 0.0)

    by_cohort: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_cohort[r["cohort"]].append(r)

    summary_rows = []
    for c, ent_rows in sorted(by_cohort.items()):
        scores = sorted(r["namerank"] for r in ent_rows)
        refusals = [r["refusal_rate"] for r in ent_rows]
        n = len(scores)
        summary_rows.append({
            "cohort": c, "n": n,
            "mean": round(statistics.mean(scores), 3),
            "median": round(statistics.median(scores), 3),
            "sd": round(statistics.stdev(scores) if n > 1 else 0.0, 3),
            "p10": round(scores[int(0.10 * n)], 3),
            "p25": round(scores[int(0.25 * n)], 3),
            "p75": round(scores[int(0.75 * n)], 3),
            "p90": round(scores[min(int(0.90 * n), n - 1)], 3),
            "frac_recognized": round(sum(1 for s in scores if s >= 0.5) / n, 3),
            "frac_silent": round(sum(1 for s in scores if s <= 0.05) / n, 3),
            "refusal_rate": round(statistics.mean(refusals), 3),
        })

    out = ANALYSIS / "cohort_summary.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        w.writeheader()
        w.writerows(summary_rows)
    print(f"Wrote {len(summary_rows)} cohorts -> {out}")


if __name__ == "__main__":
    main()
