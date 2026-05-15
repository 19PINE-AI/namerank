"""Per-model and per-cohort refusal-rate breakdown.

Reads the record-level CSV; prints tables that appear in Section 7.2 and
Appendix C of the paper.
"""
from __future__ import annotations

import csv
import json
import math
import statistics
from collections import defaultdict

from _paths import INPUTS, open_text, raw_records_path


MODEL_SIZE = {
    "llama-3.2-1b": 1, "ministral-3b": 3, "gemma-3-4b": 4, "qwen3-8b-think": 8, "llama-3.1-8b": 8,
    "gemma-3-12b": 12, "phi-4": 14, "gpt-oss-20b-think": 20, "mistral-small-24b": 24, "gemma-4-31b": 31,
    "qwen3-32b-think": 32, "glm-4-32b": 32,
    "llama-3.3-70b": 70, "mistral-medium-3.1": 100, "mistral-large": 123,
    "minimax-m2.7-think": 230, "qwen3-235b-a22b-think": 235, "ernie-4.5-300b-a47b": 300,
    "deepseek-v3.2-think": 671, "deepseek-v4-pro-think": 1000, "qwen3.5-397b-a17b-think": 397,
    "kimi-k2": 1000, "kimi-k2.6-think": 1000,
    "deepseek-v4-flash-think": 100, "llama-4-maverick": 400,
    "glm-4.7-think": 358, "glm-5.1-think": 358,
}


def main() -> None:
    ents = {e["id"]: e for e in json.loads((INPUTS / "pilot_entities.json").read_text())}
    per_model: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    per_cohort: dict[str, list[int]] = defaultdict(lambda: [0, 0])

    total = total_ref = 0
    with open_text(raw_records_path("en")) as fh:
        for r in csv.DictReader(fh):
            total += 1
            ref = r.get("is_refusal") in ("1", "true", "True")
            if ref:
                total_ref += 1
            per_model[r["model_id"]][1] += 1
            per_model[r["model_id"]][0] += int(ref)
            c = ents.get(r["entity_id"], {}).get("cohort", "?")
            per_cohort[c][1] += 1
            per_cohort[c][0] += int(ref)

    print(f"Total records: {total:,}")
    print(f"Total refusals: {total_ref:,} ({100*total_ref/total:.1f}%)")

    print("\nPer-model refusal rate (sorted desc):")
    rows = sorted([(m, r/t if t else 0, r, t) for m, (r, t) in per_model.items()], key=lambda x: -x[1])
    for m, rate, r, t in rows:
        print(f"  {m:<35} {rate:.3f}  ({r:,}/{t:,})")

    print("\nPer-cohort refusal rate (sorted desc):")
    rows_c = sorted([(c, r/t, r, t) for c, (r, t) in per_cohort.items()], key=lambda x: -x[1])
    for c, rate, r, t in rows_c:
        print(f"  {c:<35} {rate:.3f}  ({r:,}/{t:,})")

    # Refusal rate vs model size
    sized = [(MODEL_SIZE[m], rate) for m, rate, _, _ in rows if m in MODEL_SIZE]
    if sized:
        log_sz = [math.log(s) for s, _ in sized]
        rates = [r for _, r in sized]
        mx, my = statistics.mean(log_sz), statistics.mean(rates)
        num = sum((x - mx) * (y - my) for x, y in zip(log_sz, rates))
        sx = (sum((x - mx) ** 2 for x in log_sz)) ** 0.5
        sy = (sum((y - my) ** 2 for y in rates)) ** 0.5
        r = num / (sx * sy) if sx * sy > 0 else 0.0
        print(f"\nPearson(log_params, refusal_rate) = {r:+.3f}")


if __name__ == "__main__":
    main()
