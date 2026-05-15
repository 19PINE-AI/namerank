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
