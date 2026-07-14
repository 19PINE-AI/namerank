"""Probe + open-book judge the LLM-area cohorts on the 36-model panel.

Reuses the main run's panel (t6 model_set minus dead models + IKP-v2
replacements), the shared probe template, and the canonical open-book
recognition judge (t6 judge_prompt_v3.txt). Writes JSONL with retained
responses and the recognition verdict per record. Resumable.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
T6 = REPO / "experiments" / "t6_v2_protocol"
sys.path.insert(0, str(REPO / "code"))

from run_probe import call_probed_model, is_refusal  # noqa: E402
from openai import OpenAI  # noqa: E402
from google import genai  # noqa: E402
from google.genai import types as genai_types  # noqa: E402

DEAD = {"ernie-4.5-300b-a47b", "mistral-large", "mistral-medium-3.1",
        "ministral-3b", "kimi-k2", "grok-4", "glm-4-32b", "llama-3.2-1b",
        "grok-4.20-think"}
TPL = (T6 / "inputs" / "judge_prompt_v3.txt").read_text()
SCHEMA = {"type": "object", "properties": {
    "recognized": {"type": "boolean"}, "coverage": {"type": "number"},
    "accuracy": {"type": "number"}, "rationale": {"type": "string"}},
    "required": ["recognized", "coverage", "accuracy", "rationale"]}
SYS = ("You are an objective grader judging whether a language model genuinely "
       "recognizes a specific named entity, using the gold answer to "
       "disambiguate which entity and your own reliable knowledge to verify "
       "facts. Use knowledge freely to refute, but credit only positively-"
       "verified facts; never credit fabrication or a same-name different entity.")


def judge(client, name, ctx, gold, resp):
    for a in range(4):
        try:
            r = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=TPL.format(name=name, context=ctx, gold_answer=gold,
                                    response=resp),
                config=genai_types.GenerateContentConfig(
                    system_instruction=SYS, temperature=0.0,
                    response_mime_type="application/json", response_schema=SCHEMA))
            p = json.loads(r.text)
            return int(bool(p["recognized"])), p.get("rationale", "")
        except Exception:
            if a == 3:
                return None, "ERR"
            time.sleep(2 * (a + 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parallel", type=int, default=12)
    args = ap.parse_args()

    models = [m for m in json.loads(
        (REPO / "data/inputs/model_set.json").read_text()) if m["id"] not in DEAD]
    models += json.loads((REPO / "experiments/t4_1_news_events/inputs/"
                          "model_set_replacements.json").read_text())
    ents = json.loads((HERE / "inputs" / "probe_entities.json").read_text())
    gold = json.loads((HERE / "inputs" / "probe_gold.json").read_text())
    probe_tpl = (REPO / "data/inputs/probe_template_en.txt").read_text()

    out_path = HERE / "outputs" / "llm_area_results.jsonl"
    done = set()
    if out_path.exists():
        for line in open(out_path):
            try:
                r = json.loads(line)
                done.add((r["entity_id"], r["model_id"]))
            except json.JSONDecodeError:
                pass
    pending = [(e, m) for e in ents for m in models
               if (e["id"], m["id"]) not in done]
    print(f"{len(ents)} entities x {len(models)} models; "
          f"{len(done)} done, {len(pending)} pending", flush=True)

    or_client = OpenAI(base_url="https://openrouter.ai/api/v1",
                       api_key=os.environ["OPENROUTER_API_KEY"])
    gclient = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def process(e, m):
        probe = probe_tpl.format(name=e["name"], context=e["context"])
        resp = call_probed_model(or_client, m["openrouter_id"], probe,
                                 thinking=m.get("thinking", False),
                                 provider_only=m.get("provider_only"))
        refused = is_refusal(resp)
        if refused:
            rec, rat = 0, "refusal"
        else:
            rec, rat = judge(gclient, e["name"], e["context"], gold[e["id"]], resp)
            if rec is None:
                rec, rat = 0, "[JUDGE-ERROR]"
        return {"entity_id": e["id"], "entity_name": e["name"],
                "cohort": e["cohort"], "model_id": m["id"],
                "is_refusal": int(refused), "recognized": rec,
                "response": resp, "rationale": rat, "ts": time.time()}

    n = 0
    with open(out_path, "a") as fout:
        with ThreadPoolExecutor(max_workers=args.parallel) as ex:
            futs = {ex.submit(process, e, m): (e["id"], m["id"])
                    for e, m in pending}
            for fut in as_completed(futs):
                try:
                    rec = fut.result()
                except Exception as exc:  # noqa: BLE001
                    print(f"  [ERR] {futs[fut]}: {exc}"); continue
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                n += 1
                if n % 200 == 0:
                    fout.flush()
                    print(f"  {n}/{len(pending)} ({time.strftime('%H:%M:%S')})",
                          flush=True)
    print(f"done: {n} records -> {out_path}")


if __name__ == "__main__":
    main()
