"""Generic probe+judge runner for the paper's remaining small runs.
Probes entities on the 36-model panel with a given template, judges inline
with the FINAL rubric (judge_prompt_v3_tightened.txt). Resumable JSONL.

Jobs (--job):
  zh         240-entity cross-language sub-run: entities from the original
             zh record file, contexts/golds from the unified inputs, Chinese
             probe template. -> outputs/zh_results.jsonl
  injection  context-injection A/B: 11 creators x 2 arms (role-only context vs
             +artifact clause), golds from unified gold set (matched by name),
             English template. Judge sees the ARM's context, so echoing the
             injected artifact earns nothing (clean causal test).
             -> outputs/injection_results.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "code"))

from run_probe import call_probed_model, is_refusal  # noqa: E402
from openai import OpenAI  # noqa: E402
from google import genai  # noqa: E402
from google.genai import types as genai_types  # noqa: E402

DEAD = {"ernie-4.5-300b-a47b", "mistral-large", "mistral-medium-3.1",
        "ministral-3b", "kimi-k2", "grok-4", "glm-4-32b", "llama-3.2-1b",
        "grok-4.20-think"}
TPL_JUDGE = (HERE / "inputs" / "judge_prompt_v3_tightened.txt").read_text()
SCHEMA = {"type": "object", "properties": {
    "recognized": {"type": "boolean"}, "coverage": {"type": "number"},
    "accuracy": {"type": "number"}, "rationale": {"type": "string"}},
    "required": ["recognized", "coverage", "accuracy", "rationale"]}
SYS = ("You are an objective grader judging whether a language model genuinely "
       "recognizes a specific named entity. Use knowledge freely to refute, but "
       "credit only positively-verified non-guessable facts; for competition "
       "participants, fellowship recipients, and minor-paper authors you lack "
       "reliable per-individual memory, so credit only gold-present facts or "
       "major widely-documented achievements — never confabulated verification.")


def build_zh():
    import pandas as pd
    ids = list(pd.read_csv(REPO / "data/raw/pilot_summary_zh.csv.gz")
               .entity_id.unique())
    pe = {e["id"]: e for e in json.loads(
        (HERE / "inputs/pilot_entities_v2.json").read_text())}
    gold = json.loads((HERE / "inputs/gold_answers_v2.json").read_text())
    ents = [{"id": i, "name": pe[i]["name"], "context": pe[i]["context"],
             "cohort": pe[i]["cohort"], "gold_v2": pe[i].get("gold_v2", False)}
            for i in ids if i in pe]
    tpl = (REPO / "data/inputs/probe_template_zh.txt").read_text()
    return ents, gold, tpl, HERE / "outputs/zh_results.jsonl"


def build_injection():
    a = json.loads((REPO / "experiments/t2_7_artifact_mediation/inputs_A/"
                    "pilot_entities.json").read_text())
    b = json.loads((REPO / "experiments/t2_7_artifact_mediation/inputs_B/"
                    "pilot_entities.json").read_text())
    pe = {e["name"]: e for e in json.loads(
        (HERE / "inputs/pilot_entities_v2.json").read_text())}
    gold_all = json.loads((HERE / "inputs/gold_answers_v2.json").read_text())
    g27 = json.loads((REPO / "experiments/t2_7_artifact_mediation/inputs_A/"
                      "gold_answers.json").read_text())
    ents, gold = [], {}
    for arm, lst in (("A", a), ("B", b)):
        for e in lst:
            eid = f"inj_{arm}_{re.sub(r'[^a-z0-9]+','_',e['name'].lower())}"
            main = pe.get(e["name"])
            g = gold_all.get(main["id"]) if main else None
            if not g:
                g = g27.get(e["id"], "")
            if not g:
                continue
            ents.append({"id": eid, "name": e["name"], "context": e["context"],
                         "cohort": f"injection_arm_{arm}", "gold_v2": True})
            gold[eid] = g
    tpl = (REPO / "data/inputs/probe_template_en.txt").read_text()
    return ents, gold, tpl, HERE / "outputs/injection_results.jsonl"


def judge(client, name, ctx, gold, resp):
    for a in range(4):
        try:
            r = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=TPL_JUDGE.format(name=name, context=ctx,
                                          gold_answer=gold, response=resp),
                config=genai_types.GenerateContentConfig(
                    system_instruction=SYS, temperature=0.0,
                    response_mime_type="application/json", response_schema=SCHEMA))
            p = json.loads(r.text)
            return int(bool(p["recognized"])), str(p.get("rationale", ""))[:300]
        except Exception:
            if a == 3:
                return None, "ERR"
            time.sleep(2 * (a + 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True, choices=["zh", "injection"])
    ap.add_argument("--parallel", type=int, default=10)
    args = ap.parse_args()

    ents, gold, probe_tpl, out_path = (build_zh() if args.job == "zh"
                                       else build_injection())
    models = [m for m in json.loads(
        (REPO / "data/inputs/model_set.json").read_text()) if m["id"] not in DEAD]
    models += json.loads((REPO / "experiments/t4_1_news_events/inputs/"
                          "model_set_replacements.json").read_text())

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
    print(f"[{args.job}] {len(ents)} entities x {len(models)} models; "
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
            rec, rat = judge(gclient, e["name"], e["context"],
                             gold[e["id"]], resp)
            if rec is None:
                rec, rat = 0, "[JUDGE-ERROR]"
        return {"entity_id": e["id"], "entity_name": e["name"],
                "cohort": e["cohort"], "model_id": m["id"],
                "is_refusal": int(refused), "recognized": rec,
                "response": resp, "rationale": rat, "ts": time.time()}

    n = 0
    with open(out_path, "a") as fout:
        with ThreadPoolExecutor(max_workers=args.parallel) as ex:
            futs = {ex.submit(process, e, m): 1 for e, m in pending}
            for fut in as_completed(futs):
                try:
                    rec = fut.result()
                except Exception as exc:  # noqa: BLE001
                    print(f"  [ERR] {exc}", flush=True)
                    continue
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                n += 1
                if n % 200 == 0:
                    fout.flush()
                    print(f"  [{args.job}] {n}/{len(pending)}", flush=True)
    print(f"[{args.job}] done: {n}", flush=True)


if __name__ == "__main__":
    main()
