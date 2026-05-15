"""Chinese-prompt sub-run vs English-prompt main run.

Reads both record-level CSVs (en and zh), aligns by (entity, model), reports
per-entity and per-cohort deltas, and writes
data/analysis/cross_language_per_entity.csv.
"""
from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict

from _paths import ANALYSIS, INPUTS, open_text, raw_records_path
from panel import WESTERN, CHINESE


def load(lang: str):
    m: dict[str, dict[str, float]] = defaultdict(dict)
    with open_text(raw_records_path(lang)) as fh:
        for r in csv.DictReader(fh):
            m[r["entity_id"]][r["model_id"]] = float(r.get("score") or 0.0)
    return m


def mean_filter(d: dict[str, float], allow: set[str] | None = None) -> float:
    if allow:
        v = [d[k] for k in d if k in allow]
    else:
        v = list(d.values())
    return statistics.mean(v) if v else 0.0


def main() -> None:
    ents = {e["id"]: e for e in json.loads((INPUTS / "pilot_entities.json").read_text())}
    en = load("en")
    zh = load("zh")

    common = set(en.keys()) & set(zh.keys())
    print(f"Common entities probed in both languages: {len(common)}")

    rows = []
    for eid in common:
        e = ents.get(eid, {})
        rows.append({
            "entity_id": eid,
            "entity_name": e.get("name", ""),
            "cohort": e.get("cohort", "?"),
            "en_all": round(mean_filter(en[eid]), 3),
            "zh_all": round(mean_filter(zh[eid]), 3),
            "delta_zh_minus_en": round(mean_filter(zh[eid]) - mean_filter(en[eid]), 3),
            "en_western": round(mean_filter(en[eid], WESTERN), 3),
            "en_chinese": round(mean_filter(en[eid], CHINESE), 3),
            "zh_western": round(mean_filter(zh[eid], WESTERN), 3),
            "zh_chinese": round(mean_filter(zh[eid], CHINESE), 3),
            "western_lang_lift": round(mean_filter(zh[eid], WESTERN) - mean_filter(en[eid], WESTERN), 3),
            "chinese_lang_lift": round(mean_filter(zh[eid], CHINESE) - mean_filter(en[eid], CHINESE), 3),
        })

    out = ANALYSIS / "cross_language_per_entity.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {out} ({len(rows)} entities)")

    by_cohort: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_cohort[r["cohort"]].append(r)
    print(f"\n{'cohort':<35} {'n':<5} {'en':<8} {'zh':<8} {'delta':<8}")
    for c, items in sorted(by_cohort.items(),
                           key=lambda x: -statistics.mean(r["delta_zh_minus_en"] for r in x[1])):
        if len(items) < 3:
            continue
        en_m = statistics.mean(r["en_all"] for r in items)
        zh_m = statistics.mean(r["zh_all"] for r in items)
        delta = statistics.mean(r["delta_zh_minus_en"] for r in items)
        print(f"{c:<35} {len(items):<5} {en_m:<8.3f} {zh_m:<8.3f} {delta:+.3f}")


if __name__ == "__main__":
    main()
