"""Probe the NOI 2009 medal-tier cohort on the 36-model event panel.

Identical machinery to the t4_1 event run and t5_1 award run (same probe
template, judge, refusal detector, embedding diagnostic, same 36-model panel:
28 main-run survivors + 8 IKP-v2 replacements).  Reads this experiment's
inputs and writes only under its outputs/.

Usage: python 02_run_probe.py [--parallel 12] [--max-entities N]
       [--max-models N] [--dry-run] [--no-embedding]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent          # experiment dir
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "code"))

from run_probe import (call_judge, call_probed_model, cosine,  # noqa: E402
                       is_refusal)

from openai import OpenAI  # noqa: E402
from google import genai  # noqa: E402

# Same dead-model set as the t4_1 event run (2026-07 provider churn).
DEAD_MODELS = {
    "ernie-4.5-300b-a47b", "mistral-large", "mistral-medium-3.1",
    "ministral-3b", "kimi-k2", "grok-4", "glm-4-32b", "llama-3.2-1b",
    "grok-4.20-think",
}
T4_INPUTS = REPO / "experiments" / "t4_1_news_events" / "inputs"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--parallel", type=int, default=12)
    p.add_argument("--max-entities", type=int, default=None)
    p.add_argument("--max-models", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-embedding", action="store_true")
    args = p.parse_args()

    inputs = HERE / "inputs"
    outputs = HERE / "outputs"
    main_inputs = REPO / "data" / "inputs"

    models = json.loads((main_inputs / "model_set.json").read_text())
    models = [m for m in models if m["id"] not in DEAD_MODELS]
    models += json.loads((T4_INPUTS / "model_set_replacements.json").read_text())
    entities = json.loads((inputs / "rd_entities.json").read_text())
    gold = json.loads((inputs / "rd_gold.json").read_text())
    probe_tpl = (main_inputs / "probe_template_en.txt").read_text()
    judge_tpl = (main_inputs / "judge_prompt.txt").read_text()

    if args.max_entities:
        entities = entities[: args.max_entities]
    if args.max_models:
        models = models[: args.max_models]
    print(f"Plan: {len(entities)} entities x {len(models)} models = "
          f"{len(entities) * len(models):,} probes")
    if args.dry_run:
        for e in entities[:5]:
            print("  PROBE:", probe_tpl.format(name=e["name"], context=e["context"]))
        return

    or_client = OpenAI(base_url="https://openrouter.ai/api/v1",
                       api_key=os.environ["OPENROUTER_API_KEY"])
    gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    encoder = None
    gold_emb = {}
    if not args.no_embedding:
        try:
            from sentence_transformers import SentenceTransformer
            encoder = SentenceTransformer("BAAI/bge-large-en-v1.5")
            print("Encoding gold answers...")
            gold_emb = {eid: encoder.encode(t, convert_to_numpy=True)
                        for eid, t in gold.items()}
        except Exception as e:  # noqa: BLE001
            print(f"[WARN] embedding model unavailable ({e}); sim=-1")
            encoder = None

    results_path = outputs / "pilot_results_rd.json"
    results: list[dict] = []
    completed: set[tuple[str, str]] = set()
    if results_path.exists():
        results = json.loads(results_path.read_text())
        completed = {(r["entity_id"], r["model_id"]) for r in results}
        print(f"Resuming with {len(completed):,} pairs already done")

    def process(entity, model):
        probe = probe_tpl.format(name=entity["name"], context=entity["context"])
        response = call_probed_model(or_client, model["openrouter_id"], probe,
                                     thinking=model.get("thinking", False),
                                     provider_only=model.get("provider_only"))
        refused = is_refusal(response)
        if refused:
            score = {"coverage": 0.0, "accuracy": 0.0, "rationale": "refusal"}
        else:
            judge_input = judge_tpl.format(name=entity["name"],
                                           gold_answer=gold[entity["id"]],
                                           response=response)
            score = call_judge(gemini_client, judge_input)
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
    print(f"Dispatching {len(pending):,} probes with {args.parallel} workers")

    with ThreadPoolExecutor(max_workers=args.parallel) as ex:
        futs = {ex.submit(process, e, m): (e["id"], m["id"]) for e, m in pending}
        for i, fut in enumerate(as_completed(futs)):
            try:
                rec = fut.result()
            except Exception as exc:  # noqa: BLE001
                print(f"  [ERROR] {futs[fut]}: {exc}")
                continue
            if rec:
                results.append(rec)
            if (i + 1) % 200 == 0:
                results_path.write_text(
                    json.dumps(results, indent=1, ensure_ascii=False))
                print(f"  checkpoint {i+1}/{len(pending)} "
                      f"({time.strftime('%H:%M:%S')})", flush=True)

    results_path.write_text(json.dumps(results, indent=1, ensure_ascii=False))

    csv_path = outputs / "rd_summary.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("entity_id,entity_name,model_id,is_refusal,coverage,accuracy,"
                "score,embedding_sim\n")
        for r in results:
            name = r["entity_name"].replace('"', '""')
            f.write(f'{r["entity_id"]},"{name}",{r["model_id"]},'
                    f'{int(r["is_refusal"])},{r["coverage"]:.3f},'
                    f'{r["accuracy"]:.3f},{r["score"]:.3f},'
                    f'{r["embedding_sim"]:.3f}\n')
    print(f"Done. {len(results):,} records -> {results_path}, {csv_path}")


if __name__ == "__main__":
    main()
