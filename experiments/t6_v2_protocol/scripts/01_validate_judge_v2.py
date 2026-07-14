"""Validate judge v2 (context-aware, no echo credit) by re-judging SAVED responses.

Two strata, chosen to test both failure and preservation:
  A. t5_1 award-ladder records on boilerplate-gold anchors (IMO golds, OpenAlex
     long-tail controls): v1 credited context echo; v2 coverage should collapse
     toward zero UNLESS the response contains real beyond-context facts.
  B. t5_1 laureate records with Wikipedia-intro golds (turing_award,
     fields_medal) and t4_1 news events (dense golds, thin contexts): genuine
     recognition; v2 scores should track v1 closely.

Writes outputs/judge_v2_validation.csv with v1 and v2 scores per record.
"""
from __future__ import annotations

import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from google import genai
from google.genai import types as genai_types

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent

JUDGE_TPL = (HERE / "inputs" / "judge_prompt.txt").read_text()
JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "coverage": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "accuracy": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "rationale": {"type": "string"},
    },
    "required": ["coverage", "accuracy", "rationale"],
}
JUDGE_SYSTEM = (
    "You are an objective grader scoring a language-model response against a "
    "gold-answer reference paragraph about a named entity. You do not bring "
    "outside knowledge; you grade only what the response says against what the "
    "gold answer says, discounting anything the probe context already gave away."
)

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def judge_v2(name: str, context: str, gold: str, response: str) -> dict:
    prompt = JUDGE_TPL.format(name=name, context=context, gold_answer=gold,
                              response=response)
    for attempt in range(3):
        try:
            resp = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    system_instruction=JUDGE_SYSTEM,
                    temperature=0.0,
                    response_mime_type="application/json",
                    response_schema=JUDGE_SCHEMA,
                ),
            )
            p = json.loads(resp.text)
            return {"coverage": float(p["coverage"]), "accuracy": float(p["accuracy"]),
                    "rationale": str(p["rationale"])}
        except Exception as e:  # noqa: BLE001
            if attempt == 2:
                return {"coverage": float("nan"), "accuracy": float("nan"),
                        "rationale": f"[JUDGE-ERROR: {e}]"}
            time.sleep(2 * (attempt + 1))


def load_exp(results_path: Path, entities_path: Path, gold_path: Path):
    recs = json.loads(results_path.read_text())
    ents = {e["id"]: e for e in json.loads(entities_path.read_text())}
    gold = json.loads(gold_path.read_text())
    return recs, ents, gold


def main() -> None:
    random.seed(20260712)
    rows = []

    # --- stratum A/B from t5_1 award ladder (partial run OK) ---
    t51 = REPO / "experiments" / "t5_1_award_ladder"
    recs, ents, gold = load_exp(t51 / "outputs" / "pilot_results_awards.json",
                                t51 / "inputs" / "award_entities.json",
                                t51 / "inputs" / "award_gold.json")
    coh = {i: e.get("cohort", "?") for i, e in ents.items()}
    boiler = [r for r in recs if not r["is_refusal"] and coh.get(r["entity_id"], "") in
              ("imo_gold_anchor", "imo_gold", "openalex_control",
               "long_tail_researcher_openalex")]
    dense = [r for r in recs if not r["is_refusal"] and coh.get(r["entity_id"], "") in
             ("turing_award", "fields_medal", "nobel_physics")]
    for stratum, pool, n in (("A_boilerplate_t51", boiler, 150),
                             ("B_dense_t51", dense, 150)):
        for r in random.sample(pool, min(n, len(pool))):
            e = ents[r["entity_id"]]
            rows.append((stratum, r, e.get("context", ""), gold[r["entity_id"]]))

    # --- stratum B2 from t4_1 events (dense golds) ---
    t41 = REPO / "experiments" / "t4_1_news_events"
    recs, ents, gold = load_exp(t41 / "outputs" / "pilot_results_events.json",
                                t41 / "inputs" / "event_entities.json",
                                t41 / "inputs" / "event_gold.json")
    pool = [r for r in recs if not r["is_refusal"]]
    for r in random.sample(pool, min(150, len(pool))):
        e = ents[r["entity_id"]]
        rows.append(("B2_events_t41", r, e.get("context", ""), gold[r["entity_id"]]))

    print(f"Re-judging {len(rows)} saved records under judge v2...")
    out = []

    def work(item):
        stratum, r, ctx, g = item
        v2 = judge_v2(r["entity_name"], ctx, g, r["response"])
        return {
            "stratum": stratum, "entity_id": r["entity_id"],
            "model_id": r["model_id"],
            "v1_coverage": r["coverage"], "v1_accuracy": r["accuracy"],
            "v1_score": r["score"],
            "v2_coverage": v2["coverage"], "v2_accuracy": v2["accuracy"],
            "v2_score": (v2["coverage"] * v2["accuracy"])
            if v2["coverage"] == v2["coverage"] else float("nan"),
            "v2_rationale": v2["rationale"],
        }

    with ThreadPoolExecutor(max_workers=16) as ex:
        futs = [ex.submit(work, it) for it in rows]
        for i, f in enumerate(as_completed(futs)):
            out.append(f.result())
            if (i + 1) % 50 == 0:
                print(f"  {i+1}/{len(rows)}")

    import pandas as pd
    df = pd.DataFrame(out)
    outp = HERE / "outputs" / "judge_v2_validation.csv"
    df.to_csv(outp, index=False)
    print(f"wrote {outp}")
    print(df.groupby("stratum")[["v1_score", "v2_score"]].mean().round(3))
    for s, g in df.groupby("stratum"):
        ok = g.dropna(subset=["v2_score"])
        print(f"{s}: corr(v1,v2)={ok.v1_score.corr(ok.v2_score):.3f} "
              f"n={len(ok)} errors={g.v2_score.isna().sum()}")


if __name__ == "__main__":
    sys.exit(main())
