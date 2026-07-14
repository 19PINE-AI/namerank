"""v2 probe run for the per-university baseline cohorts.

Adapted from t6_v2_protocol/scripts/04_run_probe_v2.py (same panel,
probe template, judge v2, refusal detector, JSONL resume); reads this
experiment's v2 inputs and writes only under its outputs/.

Same probe template, refusal detector, judge model, and embedding diagnostic
as the main run; differences from code/run_probe.py:
- panel = main model_set.json minus 2026-07 dead models + IKP-v2 replacements
  (the t4_1 events panel, 36 models);
- judge prompt is experiments/t6_v2_protocol/inputs/judge_prompt.txt and
  receives the probe context, giving no credit for context restatement;
- results are appended to a JSONL (raw responses retained; resumable);
- entity list is cohort-interleaved so partial results cover all cohorts.

Usage:
  python 04_run_probe_v2.py --pilot            # stratified pilot subset
  python 04_run_probe_v2.py [--parallel 24]    # full run
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "code"))

from run_probe import call_probed_model, cosine, is_refusal  # noqa: E402

from openai import OpenAI  # noqa: E402
from google import genai  # noqa: E402
from google.genai import types as genai_types  # noqa: E402

DEAD_MODELS = {
    "ernie-4.5-300b-a47b", "mistral-large", "mistral-medium-3.1",
    "ministral-3b", "kimi-k2", "grok-4", "glm-4-32b", "llama-3.2-1b",
    "grok-4.20-think",
}

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
    "outside knowledge; you grade only what the response says against what "
    "the gold answer says, discounting anything the probe context already "
    "gave away.")

# pilot: stratified real subset + all synthetics, mixed model tiers
PILOT_COHORTS = {
    "reference_pilot": 8, "long_tail_researcher_openalex": 8, "cs_faculty": 6,
    "imo_gold": 6, "noi_china_gold": 3, "msra_phd_fellowship": 4,
    "cmo_china_gold": 3, "putnam_fellow": 2, "rhodes_scholar": 2,
    "mid_tier_writer": 3, "mid_tier_actor": 3, "mid_tier_founder": 2,
    "mid_tier_athlete": 2, "long_tail_paper": 4, "research_paper": 2,
    "oss_project": 4, "named_method": 2, "benchmark": 2,
    "ai_startup_or_company": 2, "foundation_model": 2,
    "gpt5_system_card_author": 2, "deepseek_v3_author": 2,
}
PILOT_MODELS = [
    "gpt-5.5-think", "claude-opus-4.6-think", "gemini-3.1-pro",
    "deepseek-v4-pro-think", "qwen3-235b-a22b-think", "kimi-k2.6-think",
    "llama-3.3-70b", "gemma-3-4b", "phi-4", "qwen3-8b-think",
    "claude-fable-5-think", "nemotron-3-nano-30b-think",
]


def judge_v2(client, tpl, name, context, gold, response):
    prompt = tpl.format(name=name, context=context, gold_answer=gold,
                        response=response)
    for attempt in range(3):
        try:
            resp = client.models.generate_content(
                model="gemini-3-flash-preview", contents=prompt,
                config=genai_types.GenerateContentConfig(
                    system_instruction=JUDGE_SYSTEM, temperature=0.0,
                    response_mime_type="application/json",
                    response_schema=JUDGE_SCHEMA))
            p = json.loads(resp.text)
            return {"coverage": float(p["coverage"]),
                    "accuracy": float(p["accuracy"]),
                    "rationale": str(p["rationale"])}
        except Exception as e:  # noqa: BLE001
            if attempt == 2:
                return {"coverage": 0.0, "accuracy": 0.0,
                        "rationale": f"[JUDGE-ERROR: {type(e).__name__}: {e}]"}
            time.sleep(2 * (attempt + 1))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--parallel", type=int, default=24)
    p.add_argument("--pilot", action="store_true")
    p.add_argument("--max-entities", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    inputs = HERE / "inputs"
    main_inputs = REPO / "data" / "inputs"

    models = [m for m in json.loads((main_inputs / "model_set.json").read_text())
              if m["id"] not in DEAD_MODELS]
    models += json.loads((REPO / "experiments/t4_1_news_events/inputs/"
                          "model_set_replacements.json").read_text())
    entities = json.loads((inputs / "univ_entities_v2.json").read_text())
    gold = json.loads((inputs / "univ_gold_v2.json").read_text())
    probe_tpl = (main_inputs / "probe_template_en.txt").read_text()
    judge_tpl = (REPO / "experiments/t6_v2_protocol/inputs/"
                 "judge_prompt.txt").read_text()

    if False and args.pilot:
        rng = random.Random(20260712)
        picked = []
        by_coh: dict[str, list] = {}
        for e in entities:
            by_coh.setdefault(e["cohort"], []).append(e)
        for coh, n in PILOT_COHORTS.items():
            pool = [e for e in by_coh.get(coh, []) if e.get("gold_v2")]
            picked += rng.sample(pool, min(n, len(pool)))
        picked += [e for e in entities if e.get("synthetic")]
        entities = picked
        models = [m for m in models if m["id"] in PILOT_MODELS]
        out_path = HERE / "outputs" / "pilot_v2_results.jsonl"
    else:
        out_path = HERE / "outputs" / "univ_v2_results.jsonl"

    n_all = len(entities)
    entities = [e for e in entities if e.get("gold_v2")]
    if n_all - len(entities):
        print(f"[INFO] skipping {n_all - len(entities)} entities whose v2 gold "
              f"is not built yet (v1_fallback); re-run after their builders "
              f"finish — completed pairs resume for free")

    rng = random.Random(42)
    rng.shuffle(entities)  # interleave cohorts for early-coverage checkpoints
    if args.max_entities:
        entities = entities[: args.max_entities]

    print(f"Plan: {len(entities)} entities x {len(models)} models = "
          f"{len(entities) * len(models):,} probes -> {out_path.name}")
    if args.dry_run:
        for e in entities[:5]:
            print("  PROBE:", probe_tpl.format(name=e["name"],
                                               context=e["context"])[:160])
        return

    or_client = OpenAI(base_url="https://openrouter.ai/api/v1",
                       api_key=os.environ["OPENROUTER_API_KEY"])
    gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    encoder, gold_emb = None, {}
    try:
        from sentence_transformers import SentenceTransformer
        encoder = SentenceTransformer("BAAI/bge-large-en-v1.5")
        print("Encoding gold answers...")
        gold_emb = {e["id"]: encoder.encode(gold[e["id"]], convert_to_numpy=True)
                    for e in entities}
    except Exception as e:  # noqa: BLE001
        print(f"[WARN] embeddings unavailable ({e}); sim=-1")

    completed: set[tuple[str, str]] = set()
    if out_path.exists():
        with open(out_path) as f:
            for line in f:
                try:
                    r = json.loads(line)
                    completed.add((r["entity_id"], r["model_id"]))
                except json.JSONDecodeError:
                    pass
        print(f"Resuming: {len(completed):,} pairs already done")

    ctx_of = {e["id"]: e["context"] for e in entities}

    def process(entity, model):
        probe = probe_tpl.format(name=entity["name"], context=entity["context"])
        response = call_probed_model(or_client, model["openrouter_id"], probe,
                                     thinking=model.get("thinking", False),
                                     provider_only=model.get("provider_only"))
        refused = is_refusal(response)
        if refused:
            score = {"coverage": 0.0, "accuracy": 0.0, "rationale": "refusal"}
        else:
            score = judge_v2(gemini_client, judge_tpl, entity["name"],
                             ctx_of[entity["id"]], gold[entity["id"]], response)
        sim = -1.0
        if encoder is not None:
            sim = cosine(encoder.encode(response, convert_to_numpy=True),
                         gold_emb[entity["id"]])
        return {
            "entity_id": entity["id"], "entity_name": entity["name"],
            "model_id": model["id"], "response": response,
            "is_refusal": refused,
            "coverage": score["coverage"], "accuracy": score["accuracy"],
            "score": score["coverage"] * score["accuracy"],
            "rationale": score["rationale"],
            "embedding_sim": sim, "ts": time.time(),
        }

    pending = [(e, m) for e in entities for m in models
               if (e["id"], m["id"]) not in completed]
    rng.shuffle(pending)
    print(f"Dispatching {len(pending):,} probes with {args.parallel} workers")

    n_err = 0
    with open(out_path, "a", encoding="utf-8") as fout:
        with ThreadPoolExecutor(max_workers=args.parallel) as ex:
            futs = {ex.submit(process, e, m): (e["id"], m["id"])
                    for e, m in pending}
            for i, fut in enumerate(as_completed(futs)):
                try:
                    rec = fut.result()
                except Exception as exc:  # noqa: BLE001
                    n_err += 1
                    if n_err <= 20 or n_err % 100 == 0:
                        print(f"  [ERROR {n_err}] {futs[fut]}: {exc}")
                    continue
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                if (i + 1) % 200 == 0:
                    fout.flush()
                    print(f"  {i+1}/{len(pending)} "
                          f"({time.strftime('%H:%M:%S')}, errors={n_err})",
                          flush=True)
    print(f"Done. errors={n_err}. Output: {out_path}")


if __name__ == "__main__":
    main()
