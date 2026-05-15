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


WESTERN = {
    "claude-opus-4.6-think", "claude-sonnet-4.6-think",
    "gemini-2.5-pro-think", "gemini-3-flash-think", "gemini-3.1-pro",
    "gemma-3-12b", "gemma-3-4b", "gemma-4-31b",
    "gpt-5.3", "gpt-5.4", "gpt-5.5-think",
    "gpt-oss-20b-think",
    "grok-4", "grok-4.20-think",
    "llama-3.1-8b", "llama-3.2-1b", "llama-3.3-70b", "llama-4-maverick",
    "mistral-large", "mistral-medium-3.1", "mistral-small-24b", "ministral-3b",
    "phi-4",
}
CHINESE = {
    "deepseek-v3.2-think", "deepseek-v4-flash-think", "deepseek-v4-pro-think",
    "ernie-4.5-300b-a47b",
    "glm-4-32b", "glm-4.7-think", "glm-5.1-think",
    "kimi-k2", "kimi-k2.6-think",
    "minimax-m2.7-think",
    "qwen3-235b-a22b-think", "qwen3-32b-think", "qwen3-8b-think", "qwen3.5-397b-a17b-think",
}


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
