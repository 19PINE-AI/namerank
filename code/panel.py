"""Single source of truth for the 37-model panel partition.

Defines the Western / Chinese split (used for East-West variance analysis and
the cross-language sub-run), plus a parameter-size table (used for the refusal
vs. model-size regression). All downstream scripts import from here so that
adding or relabelling a panel model only requires one edit.

The partition is by vendor country of origin, not by training data: meta,
openai, anthropic, google, mistral, microsoft, xai are labelled Western;
deepseek, alibaba, moonshot, zhipu, baidu, minimax are labelled Chinese.
mistralai (Ministral) shares the Mistral classification.
"""
from __future__ import annotations

import json
from pathlib import Path

from _paths import INPUTS

WESTERN_VENDORS = {
    "openai", "anthropic", "google", "meta", "mistral", "mistralai",
    "microsoft", "xai",
}
CHINESE_VENDORS = {
    "deepseek", "alibaba", "moonshot", "zhipu", "baidu", "minimax",
}

# Approximate parameter count in billions. For mixture-of-experts models we
# record total-parameters (not active). Used only by refusal_patterns.py for
# the refusal-rate vs. log(size) regression.
PARAMS_B: dict[str, float] = {
    "llama-3.2-1b": 1, "ministral-3b": 3, "gemma-3-4b": 4,
    "qwen3-8b-think": 8, "llama-3.1-8b": 8,
    "gemma-3-12b": 12, "phi-4": 14, "gpt-oss-20b-think": 20,
    "mistral-small-24b": 24, "gemma-4-31b": 31,
    "qwen3-32b-think": 32, "glm-4-32b": 32,
    "llama-3.3-70b": 70, "mistral-medium-3.1": 100,
    "deepseek-v4-flash-think": 100, "mistral-large": 123,
    "minimax-m2.7-think": 230, "qwen3-235b-a22b-think": 235,
    "ernie-4.5-300b-a47b": 300, "glm-4.7-think": 358, "glm-5.1-think": 358,
    "qwen3.5-397b-a17b-think": 397, "llama-4-maverick": 400,
    "deepseek-v3.2-think": 671,
    "deepseek-v4-pro-think": 1000, "kimi-k2": 1000, "kimi-k2.6-think": 1000,
}


def load_models(path: Path | None = None) -> list[dict]:
    p = path or (INPUTS / "model_set.json")
    return json.loads(p.read_text())


def _partition() -> tuple[set[str], set[str]]:
    western: set[str] = set()
    chinese: set[str] = set()
    for m in load_models():
        vendor = (m.get("vendor") or "").lower()
        mid = m["id"]
        if vendor in WESTERN_VENDORS:
            western.add(mid)
        elif vendor in CHINESE_VENDORS:
            chinese.add(mid)
        else:
            raise ValueError(f"unclassified vendor '{vendor}' for model {mid!r}; "
                             "update panel.WESTERN_VENDORS / CHINESE_VENDORS")
    return western, chinese


WESTERN, CHINESE = _partition()
ALL_MODELS = sorted(WESTERN | CHINESE)


if __name__ == "__main__":
    print(f"Western (n={len(WESTERN)}):")
    for m in sorted(WESTERN):
        print(f"  {m}")
    print(f"\nChinese (n={len(CHINESE)}):")
    for m in sorted(CHINESE):
        print(f"  {m}")
    print(f"\nTotal: {len(WESTERN) + len(CHINESE)} models")
    missing_size = sorted(set(ALL_MODELS) - set(PARAMS_B))
    if missing_size:
        print(f"\nNo PARAMS_B entry for: {missing_size}")
