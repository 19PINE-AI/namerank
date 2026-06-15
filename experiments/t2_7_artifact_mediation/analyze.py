"""Aggregate the artifact-mediation causal experiment.

Reads outputs_A/pilot_results_en.json and outputs_B/pilot_results_en.json.

Produces:
  mediation_results.csv -- per-pair NR_A, NR_B, delta, refusal_A, refusal_B, n_models
  per_model_lift.csv    -- per-(pair, model) score_A, score_B, delta
  summary.json          -- top-line numbers used by the README
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from statistics import mean, pstdev

ROOT = Path(__file__).parent


def load_results(side: str) -> list[dict]:
    p = ROOT / f"outputs_{side}" / "pilot_results_en.json"
    return json.loads(p.read_text())


def main() -> None:
    res_a = load_results("A")
    res_b = load_results("B")
    print(f"Loaded {len(res_a)} A records, {len(res_b)} B records")

    # Index by (entity_id, model_id)
    idx_a = {(r["entity_id"], r["model_id"]): r for r in res_a}
    idx_b = {(r["entity_id"], r["model_id"]): r for r in res_b}

    # The 11 pairs in canonical order (matches contexts.csv)
    ctx_path = ROOT / "contexts.csv"
    pairs = []
    with open(ctx_path) as f:
        for row in csv.DictReader(f):
            pairs.append((row["id"], row["name"], row["artifact"]))

    # ---- mediation_results.csv (per-pair) ----
    # Drop API-error responses from BOTH sides (provider unavailable, deprecated, etc.)
    # so they do not deflate NR_A and NR_B with zero scores.
    def is_error(r: dict) -> bool:
        return isinstance(r.get("response"), str) and r["response"].startswith("[ERROR:")

    mediation_rows = []
    per_model_rows = []
    all_deltas = []
    overall_a = []
    overall_b = []
    for pid, pname, artifact in pairs:
        a_records = [r for r in res_a if r["entity_id"] == pid and not is_error(r)]
        b_records = [r for r in res_b if r["entity_id"] == pid and not is_error(r)]
        # Use only models present (non-error) in BOTH sides
        models_a = {r["model_id"]: r for r in a_records}
        models_b = {r["model_id"]: r for r in b_records}
        shared = sorted(set(models_a) & set(models_b))
        scores_a = [models_a[m]["score"] for m in shared]
        scores_b = [models_b[m]["score"] for m in shared]
        refus_a = [int(models_a[m]["is_refusal"]) for m in shared]
        refus_b = [int(models_b[m]["is_refusal"]) for m in shared]
        nr_a = mean(scores_a) if scores_a else 0.0
        nr_b = mean(scores_b) if scores_b else 0.0
        ref_a = mean(refus_a) if refus_a else 0.0
        ref_b = mean(refus_b) if refus_b else 0.0
        delta = nr_b - nr_a
        # Paired t-stat across the M shared models
        diffs = [b - a for a, b in zip(scores_a, scores_b)]
        if len(diffs) >= 2:
            md = mean(diffs)
            sd = pstdev(diffs) * math.sqrt(len(diffs) / (len(diffs) - 1)) if len(diffs) > 1 else 0.0
            se = sd / math.sqrt(len(diffs)) if sd > 0 else 0.0
            t_stat = md / se if se > 0 else float("nan")
        else:
            t_stat = float("nan")
            se = 0.0
        mediation_rows.append({
            "creator_id": pid,
            "creator_name": pname,
            "artifact": artifact,
            "n_models": len(shared),
            "NR_A": round(nr_a, 4),
            "NR_B": round(nr_b, 4),
            "delta": round(delta, 4),
            "refusal_A": round(ref_a, 4),
            "refusal_B": round(ref_b, 4),
            "se_delta": round(se, 4),
            "t_paired": round(t_stat, 3) if not math.isnan(t_stat) else "",
        })
        all_deltas.append(delta)
        overall_a.append(nr_a)
        overall_b.append(nr_b)

        # per-(pair, model)
        for m in shared:
            per_model_rows.append({
                "creator_id": pid,
                "model_id": m,
                "score_A": round(models_a[m]["score"], 4),
                "score_B": round(models_b[m]["score"], 4),
                "delta": round(models_b[m]["score"] - models_a[m]["score"], 4),
                "is_refusal_A": int(models_a[m]["is_refusal"]),
                "is_refusal_B": int(models_b[m]["is_refusal"]),
            })

    # Write CSVs
    with open(ROOT / "mediation_results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(mediation_rows[0].keys()))
        w.writeheader()
        w.writerows(mediation_rows)
    with open(ROOT / "per_model_lift.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(per_model_rows[0].keys()))
        w.writeheader()
        w.writerows(per_model_rows)

    # ---- per-model aggregate lift ----
    # Aggregate per model across the 11 pairs
    by_model: dict[str, list[float]] = {}
    by_model_a: dict[str, list[float]] = {}
    by_model_b: dict[str, list[float]] = {}
    for row in per_model_rows:
        by_model.setdefault(row["model_id"], []).append(row["delta"])
        by_model_a.setdefault(row["model_id"], []).append(row["score_A"])
        by_model_b.setdefault(row["model_id"], []).append(row["score_B"])

    # Tier assignment (manual; matches paper's panel partition where applicable)
    FRONTIER_REASONING = {"gpt-5.5-think","claude-opus-4.6-think","claude-sonnet-4.6-think",
                          "gemini-3.1-pro","gemini-3-flash-think","gemini-2.5-pro-think",
                          "grok-4.20-think","deepseek-v4-pro-think","glm-5.1-think"}
    FRONTIER_CHAT = {"gpt-5.4","gpt-5.3","grok-4","glm-4.7-think","deepseek-v3.2-think",
                     "qwen3.5-397b-a17b-think","kimi-k2.6-think"}
    MID_WEIGHT = {"llama-4-maverick","llama-3.3-70b","mistral-large","mistral-medium-3.1",
                  "deepseek-v4-flash-think","ernie-4.5-300b-a47b","minimax-m2.7-think",
                  "qwen3-235b-a22b-think","kimi-k2","glm-4-32b"}
    SMALL = {"gpt-oss-20b-think","phi-4","llama-3.1-8b","llama-3.2-1b","gemma-4-31b",
             "gemma-3-12b","gemma-3-4b","mistral-small-24b","qwen3-32b-think","qwen3-8b-think",
             "ministral-3b"}
    def tier(mid: str) -> str:
        if mid in FRONTIER_REASONING: return "frontier_reasoning"
        if mid in FRONTIER_CHAT: return "frontier_chat"
        if mid in MID_WEIGHT: return "mid_weight"
        if mid in SMALL: return "small"
        return "other"

    model_agg = []
    for mid, deltas in by_model.items():
        model_agg.append({
            "model_id": mid,
            "tier": tier(mid),
            "mean_delta": round(mean(deltas), 4),
            "mean_NR_A": round(mean(by_model_a[mid]), 4),
            "mean_NR_B": round(mean(by_model_b[mid]), 4),
            "n_pairs": len(deltas),
        })
    model_agg.sort(key=lambda r: -r["mean_delta"])
    with open(ROOT / "per_model_summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(model_agg[0].keys()))
        w.writeheader()
        w.writerows(model_agg)

    # Aggregate by tier
    tier_groups: dict[str, list[float]] = {}
    tier_a: dict[str, list[float]] = {}
    tier_b: dict[str, list[float]] = {}
    for row in model_agg:
        tier_groups.setdefault(row["tier"], []).append(row["mean_delta"])
        tier_a.setdefault(row["tier"], []).append(row["mean_NR_A"])
        tier_b.setdefault(row["tier"], []).append(row["mean_NR_B"])
    tier_rows = []
    for t in ["frontier_reasoning","frontier_chat","mid_weight","small","other"]:
        if t in tier_groups:
            tier_rows.append({
                "tier": t,
                "n_models": len(tier_groups[t]),
                "mean_NR_A": round(mean(tier_a[t]), 4),
                "mean_NR_B": round(mean(tier_b[t]), 4),
                "mean_delta": round(mean(tier_groups[t]), 4),
            })
    with open(ROOT / "tier_summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(tier_rows[0].keys()))
        w.writeheader()
        w.writerows(tier_rows)

    # ---- summary ----
    summary = {
        "n_pairs": len(pairs),
        "n_models_panel": len(by_model),
        "mean_NR_A": round(mean(overall_a), 4),
        "mean_NR_B": round(mean(overall_b), 4),
        "mean_delta": round(mean(all_deltas), 4),
        "median_delta": round(sorted(all_deltas)[len(all_deltas) // 2], 4),
        "min_delta": round(min(all_deltas), 4),
        "max_delta": round(max(all_deltas), 4),
        "n_positive_delta": sum(1 for d in all_deltas if d > 0),
        "per_pair_delta": {p["creator_id"]: p["delta"] for p in mediation_rows},
        "observational_jiayi_lift": 0.369,  # from a4_artifact_mediation.csv
    }
    (ROOT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))

    # Print quick markdown table
    print("\n| creator | artifact | NR_A | NR_B | delta |")
    print("|---|---|---:|---:|---:|")
    for r in mediation_rows:
        print(f"| {r['creator_name']} | {r['artifact']} | {r['NR_A']:.3f} | {r['NR_B']:.3f} | {r['delta']:+.3f} |")


if __name__ == "__main__":
    main()
