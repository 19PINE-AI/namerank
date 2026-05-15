"""Per-model generosity and refusal-rate breakdown.

Reads the record-level CSV and writes data/analysis/per_model_summary.csv with
one row per model: n_records, mean_score, refusal_rate, mean_score_non_refusal,
vendor, family, thinking_mode. This is the source of Appendix C in the paper
and the validation page on the companion site.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict

from _paths import ANALYSIS, INPUTS, open_text, raw_records_path


def main() -> None:
    model_meta = {m["id"]: m for m in json.loads((INPUTS / "model_set.json").read_text())}

    per_model: dict[str, dict] = defaultdict(lambda: {
        "n": 0, "sum_score": 0.0, "sum_score_nr": 0.0, "n_nr": 0, "n_refusal": 0,
    })
    with open_text(raw_records_path("en")) as fh:
        for r in csv.DictReader(fh):
            m = r["model_id"]
            sc = float(r.get("score") or 0.0)
            refused = r.get("is_refusal") in ("1", "true", "True")
            d = per_model[m]
            d["n"] += 1
            d["sum_score"] += sc
            if refused:
                d["n_refusal"] += 1
            else:
                d["n_nr"] += 1
                d["sum_score_nr"] += sc

    rows = []
    for mid, d in per_model.items():
        meta = model_meta.get(mid, {})
        rows.append({
            "model_id": mid,
            "vendor": meta.get("vendor", "?"),
            "family": meta.get("family", "?"),
            "thinking": "1" if meta.get("thinking") else "0",
            "n_records": d["n"],
            "mean_score": round(d["sum_score"] / d["n"], 4) if d["n"] else 0.0,
            "refusal_rate": round(d["n_refusal"] / d["n"], 4) if d["n"] else 0.0,
            "mean_score_non_refusal": round(d["sum_score_nr"] / d["n_nr"], 4) if d["n_nr"] else 0.0,
        })

    rows.sort(key=lambda r: -r["mean_score"])
    out = ANALYSIS / "per_model_summary.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {out} ({len(rows)} models)")
    print(f"  generous range: {rows[0]['mean_score']:.3f} ({rows[0]['model_id']})"
          f" .. {rows[-1]['mean_score']:.3f} ({rows[-1]['model_id']})")


if __name__ == "__main__":
    main()
