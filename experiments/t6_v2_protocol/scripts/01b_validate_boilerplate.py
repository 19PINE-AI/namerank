"""Stratum A of the judge-v2 validation: boilerplate-gold records from the
in-flight t5_3 NOI-tier run (NOI medalists, boilerplate credential golds whose
only entity-specific facts are in the probe context). Expectation: v2 coverage
collapses toward zero unless the response contains real beyond-context facts.
Appends to outputs/judge_v2_validation.csv with stratum A_boilerplate_t53.
"""
from __future__ import annotations

import importlib.util
import json
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent

spec = importlib.util.spec_from_file_location(
    "vj", HERE / "scripts" / "01_validate_judge_v2.py")
vj = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vj)

random.seed(20260712)
recs = json.loads((REPO / "experiments/t5_3_noi_medal_tiers/outputs/pilot_results_tiers.json").read_text())
ents = {e["id"]: e for e in json.loads((REPO / "experiments/t5_3_noi_medal_tiers/inputs/tier_entities.json").read_text())}
gold = json.loads((REPO / "experiments/t5_3_noi_medal_tiers/inputs/tier_gold.json").read_text())

pool = [r for r in recs if not r["is_refusal"]]
sample = random.sample(pool, min(150, len(pool)))
print(f"Re-judging {len(sample)} boilerplate records under judge v2...")


def work(r):
    e = ents[r["entity_id"]]
    v2 = vj.judge_v2(r["entity_name"], e.get("context", ""), gold[r["entity_id"]],
                     r["response"])
    return {
        "stratum": "A_boilerplate_t53", "entity_id": r["entity_id"],
        "model_id": r["model_id"],
        "v1_coverage": r["coverage"], "v1_accuracy": r["accuracy"],
        "v1_score": r["score"],
        "v2_coverage": v2["coverage"], "v2_accuracy": v2["accuracy"],
        "v2_score": (v2["coverage"] * v2["accuracy"])
        if v2["coverage"] == v2["coverage"] else float("nan"),
        "v2_rationale": v2["rationale"],
    }


out = []
with ThreadPoolExecutor(max_workers=16) as ex:
    for f in as_completed([ex.submit(work, r) for r in sample]):
        out.append(f.result())

df = pd.DataFrame(out)
outp = HERE / "outputs" / "judge_v2_validation.csv"
old = pd.read_csv(outp)
pd.concat([old[old.stratum != "A_boilerplate_t53"], df]).to_csv(outp, index=False)
print(df[["v1_score", "v2_score"]].mean().round(3))
print("v2_score==0 share:", (df.v2_score == 0).mean().round(3),
      "| v1_score==0 share:", (df.v1_score == 0).mean().round(3))
print("\nlargest v1->v2 drops (echo cases):")
df["drop"] = df.v1_score - df.v2_score
print(df.nlargest(5, "drop")[["entity_id", "model_id", "v1_score", "v2_score", "v2_rationale"]].to_string(index=False))
print("\nrecords keeping v2>0.3 (genuine beyond-context knowledge):")
print(df[df.v2_score > 0.3][["entity_id", "model_id", "v1_score", "v2_score", "v2_rationale"]].head(8).to_string(index=False))
