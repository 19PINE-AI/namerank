"""Wrapper around code/run_probe.py that:
  - reads templates by --template label (T1/T2/T3) from a single inputs/ dir
  - writes pilot_results.json and pilot_summary.csv into --outputs-dir
  - does NOT touch the repo's global data/raw/ directory

We import the helpers from code.run_probe so logic stays in one place.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "code"))

from run_probe import (  # noqa: E402
    call_judge,
    call_probed_model,
    cosine,
    is_refusal,
)
import os as _os
_os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")  # hide GPU before torch loads

from openai import OpenAI  # noqa: E402
from google import genai  # noqa: E402
import torch  # noqa: E402
torch.set_num_threads(2)  # keep CPU encoder from saturating
from sentence_transformers import SentenceTransformer  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs-dir", required=True)
    ap.add_argument("--outputs-dir", required=True)
    ap.add_argument("--template", required=True,
                    help="label, e.g. T1; reads probe_template_en_<label>.txt")
    ap.add_argument("--parallel", type=int, default=16)
    ap.add_argument("--max-entities", type=int, default=None)
    ap.add_argument("--max-models", type=int, default=None)
    args = ap.parse_args()

    inputs = Path(args.inputs_dir)
    outputs = Path(args.outputs_dir)
    outputs.mkdir(parents=True, exist_ok=True)

    models = json.loads((inputs / "model_set.json").read_text())
    entities = json.loads((inputs / "pilot_entities.json").read_text())
    gold = json.loads((inputs / "gold_answers.json").read_text())
    probe_tpl = (inputs / f"probe_template_en_{args.template}.txt").read_text()
    judge_tpl = (inputs / "judge_prompt.txt").read_text()

    if args.max_entities:
        entities = entities[: args.max_entities]
    if args.max_models:
        models = models[: args.max_models]

    print(f"[{args.template}] {len(entities)} entities x {len(models)} models "
          f"= {len(entities)*len(models):,} probes")

    or_client = OpenAI(base_url="https://openrouter.ai/api/v1",
                       api_key=os.environ["OPENROUTER_API_KEY"])
    gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    # Force CPU to avoid GPU OOM contention from other workloads on this box.
    encoder = SentenceTransformer("BAAI/bge-large-en-v1.5", device="cpu")
    print("Encoding gold answers...")
    gold_emb = {eid: encoder.encode(t, convert_to_numpy=True) for eid, t in gold.items()}

    results_path = outputs / "pilot_results.json"
    completed: set[tuple[str, str]] = set()
    results: list[dict] = []
    if results_path.exists():
        results = json.loads(results_path.read_text())
        completed = {(r["entity_id"], r["model_id"]) for r in results}
        print(f"Resuming with {len(completed):,} pairs already done")

    def process(entity, model):
        if (entity["id"], model["id"]) in completed:
            return None
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

    pairs = [(e, m) for e in entities for m in models]
    pending = [(e, m) for e, m in pairs if (e["id"], m["id"]) not in completed]
    print(f"Dispatching {len(pending):,} pending probes with {args.parallel} workers")

    with ThreadPoolExecutor(max_workers=args.parallel) as ex:
        futs = {ex.submit(process, e, m): (e["id"], m["id"]) for e, m in pending}
        for i, fut in enumerate(as_completed(futs)):
            try:
                rec = fut.result()
            except Exception as exc:  # noqa: BLE001
                print(f"  [ERROR] {futs[fut]}: {exc}")
                continue
            if rec is None:
                continue
            results.append(rec)
            if (i + 1) % 500 == 0:
                results_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
                print(f"  checkpoint {i+1}/{len(pending)}")

    results_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))

    csv_path = outputs / "pilot_summary.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("entity_id,entity_name,model_id,is_refusal,coverage,accuracy,score,embedding_sim\n")
        for r in results:
            name = r["entity_name"].replace('"', '""')
            f.write(f'{r["entity_id"]},"{name}",{r["model_id"]},'
                    f'{int(r["is_refusal"])},{r["coverage"]:.3f},{r["accuracy"]:.3f},'
                    f'{r["score"]:.3f},{r["embedding_sim"]:.3f}\n')
    print(f"[{args.template}] done. {len(results):,} records -> {results_path}, {csv_path}")


if __name__ == "__main__":
    main()
