"""Probe the entities the v2 run skipped (no S2 gold match), judged with
the canonical judge v3 against the v3 web-grounded golds.

The S2 namesake guard excluded 190 entities (ambiguous names — a selection
bias that correlates with exactly the East-Asian-name attenuation the paper
documents). The v3 golds cover everyone, so these entities are probed here
and scored with the same judge-v3 rubric as 13_judge_detect.py. Responses
are retained. Writes its own file (single-writer): may run alongside 13.

Writes outputs/univ_v3judge_topup.jsonl
Usage: python 12_topup_probe_v3.py [--parallel 12]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "code"))

from run_probe import call_probed_model, is_refusal  # noqa: E402
from google import genai  # noqa: E402
from openai import OpenAI  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "detect13", HERE / "scripts" / "13_judge_detect.py")
d13 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d13)

DEAD_MODELS = {
    "ernie-4.5-300b-a47b", "mistral-large", "mistral-medium-3.1",
    "ministral-3b", "kimi-k2", "grok-4", "glm-4-32b", "llama-3.2-1b",
    "grok-4.20-think",
}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--parallel", type=int, default=12)
    args = p.parse_args()

    main_inputs = REPO / "data" / "inputs"
    models = [m for m in json.loads((main_inputs / "model_set.json").read_text())
              if m["id"] not in DEAD_MODELS]
    models += json.loads((REPO / "experiments/t4_1_news_events/inputs/"
                          "model_set_replacements.json").read_text())
    gold = {eid: g["gold"] for eid, g in json.loads(
        (HERE / "inputs" / "univ_gold_v3.json").read_text()).items()}
    entities = [e for e in json.loads(
        (HERE / "inputs" / "univ_entities_v2.json").read_text())
        if not e.get("gold_v2") and e["id"] in gold]
    probe_tpl = (main_inputs / "probe_template_en.txt").read_text()

    out_path = HERE / "outputs" / "univ_v3judge_topup.jsonl"
    done = set()
    if out_path.exists():
        with open(out_path) as f:
            for line in f:
                try:
                    r = json.loads(line)
                    done.add((r["entity_id"], r["model_id"]))
                except json.JSONDecodeError:
                    pass

    pending = [(e, m) for e in entities for m in models
               if (e["id"], m["id"]) not in done]
    print(f"top-up: {len(entities)} skipped entities; "
          f"{len(pending):,} probes to run")

    or_client = OpenAI(base_url="https://openrouter.ai/api/v1",
                       api_key=os.environ["OPENROUTER_API_KEY"])
    gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def process(entity, model):
        probe = probe_tpl.format(name=entity["name"], context=entity["context"])
        response = call_probed_model(or_client, model["openrouter_id"], probe,
                                     thinking=model.get("thinking", False),
                                     provider_only=model.get("provider_only"))
        refused = is_refusal(response)
        base = {"entity_id": entity["id"], "entity_name": entity["name"],
                "model_id": model["id"], "response": response,
                "is_refusal": refused, "ts": time.time()}
        if refused:
            base.update(recognized=False, coverage=0.0, accuracy=0.0,
                        score=0.0, rationale="refusal")
        else:
            s = d13.judge_v3(gemini_client, entity["name"], entity["context"],
                             gold[entity["id"]], response)
            base.update(recognized=s["recognized"], coverage=s["coverage"],
                        accuracy=s["accuracy"],
                        score=s["coverage"] * s["accuracy"],
                        rationale=s["rationale"])
        return base

    with open(out_path, "a", encoding="utf-8") as fout:
        with ThreadPoolExecutor(max_workers=args.parallel) as ex:
            futs = {ex.submit(process, e, m): (e["id"], m["id"])
                    for e, m in pending}
            for i, fut in enumerate(as_completed(futs)):
                try:
                    rec = fut.result()
                except Exception as exc:  # noqa: BLE001
                    print(f"  [ERROR] {futs[fut]}: {exc}")
                    continue
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                if (i + 1) % 200 == 0:
                    fout.flush()
                    print(f"  {i+1}/{len(pending)} "
                          f"({time.strftime('%H:%M:%S')})", flush=True)
    print(f"Done -> {out_path}")


if __name__ == "__main__":
    main()
