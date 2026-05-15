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
from panel import PARAMS_B as MODEL_SIZE


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
