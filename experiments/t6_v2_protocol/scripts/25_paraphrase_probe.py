"""Prompt-paraphrase sensitivity experiment.

Re-probe a cohort-stratified subset on the full 36-model panel under three
paraphrased probe templates (T1--T3). T0 is the main-run template, whose
verdicts are read from recognition_final.jsonl, so only T1--T3 are probed here.
Each fresh response is judged by the canonical tightened recognition judge.

Output: outputs/paraphrase_results.jsonl (one row per entity,model,template with
the recognition verdict). Resumable. Touches PARAPHRASE_DONE at the end.

Usage: python 25_paraphrase_probe.py [--per-cohort 12] [--parallel 40]
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
sys.path.insert(0, str(REPO / "code"))

from run_probe import call_probed_model, is_refusal  # noqa: E402
from openai import OpenAI  # noqa: E402
from google import genai  # noqa: E402
from google.genai import types as genai_types  # noqa: E402

OUT = HERE / "outputs" / "paraphrase_results.jsonl"
JUDGE_TPL = (HERE / "inputs" / "judge_prompt_v3_tightened.txt").read_text()
JUDGE_SYS = ("You are an objective grader judging whether a language model genuinely "
             "recognizes a specific named entity. Use knowledge freely to refute, but "
             "credit only positively-verified non-guessable facts; for competition "
             "participants, fellowship recipients, and minor-paper authors you lack "
             "reliable per-individual memory, so credit only gold-present facts or "
             "major widely-documented achievements — never confabulated verification.")
SCHEMA = {"type": "object", "properties": {
    "recognized": {"type": "boolean"}, "rationale": {"type": "string"}},
    "required": ["recognized", "rationale"]}

# Paraphrased probe templates. T0 is the main-run template (verdicts reused).
TEMPLATES = {
    "T1": ('What can you tell me about {name}? They are {context}. Reply with only '
           '"unknown" if you are not familiar with this entity. Aim for about 150 words.'),
    "T2": ('Please share what you know about {name}, {context}. If unknown to you, '
           'answer with just "unknown". Keep it under ~150 words.'),
    "T3": ('Briefly describe {name}, who is {context}. Respond "unknown" if you have '
           'no information. Around 150 words please.'),
}

# Cohorts spanning silent -> universal, so the decomposition covers the ladder.
STRATA = {
    "reference_pilot": 12, "long_tail_researcher_openalex": 12, "cs_faculty": 12,
    "imo_gold": 12, "gpt5_system_card_author": 10, "mid_tier_writer": 12,
    "oss_project": 12, "named_method": 12, "foundation_model": 12,
    "long_tail_paper": 10, "rhodes_scholar": 10, "ai_startup_or_company": 10,
}

DEAD_MODELS = {
    "ernie-4.5-300b-a47b", "mistral-large", "mistral-medium-3.1",
    "ministral-3b", "kimi-k2", "grok-4", "glm-4-32b", "llama-3.2-1b",
    "grok-4.20-think",
}

gemini = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def judge(name, ctx, gold, resp):
    prompt = JUDGE_TPL.format(name=name, context=ctx, gold_answer=gold, response=resp)
    for a in range(4):
        try:
            r = gemini.models.generate_content(
                model="gemini-3-flash-preview", contents=prompt,
                config=genai_types.GenerateContentConfig(
                    system_instruction=JUDGE_SYS, temperature=0.0,
                    response_mime_type="application/json", response_schema=SCHEMA))
            return int(bool(json.loads(r.text)["recognized"]))
        except Exception:
            if a == 3:
                return None
            time.sleep(2 * (a + 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-cohort", type=int, default=12)
    ap.add_argument("--parallel", type=int, default=40)
    args = ap.parse_args()

    ents = {e["id"]: e for e in json.loads(
        (HERE / "inputs/pilot_entities_v2.json").read_text())}
    gold = json.loads((HERE / "inputs/gold_answers_v2.json").read_text())
    gold = {k: (v if isinstance(v, str) else v.get("gold", "")) for k, v in gold.items()}

    models = [m for m in json.loads((REPO / "data/inputs/model_set.json").read_text())
              if m["id"] not in DEAD_MODELS]
    models += json.loads((REPO / "experiments/t4_1_news_events/inputs/"
                          "model_set_replacements.json").read_text())
    print(f"panel: {len(models)} models", flush=True)

    # deterministic stratified subset
    by_coh = {}
    for e in ents.values():
        if e.get("synthetic") or not e.get("gold_v2"):
            continue
        by_coh.setdefault(e.get("cohort"), []).append(e)
    subset = []
    for coh, n in STRATA.items():
        pool = sorted(by_coh.get(coh, []), key=lambda e: e["id"])
        subset += pool[:min(n, args.per_cohort if args.per_cohort else n)]
    print(f"subset: {len(subset)} entities across {len(STRATA)} cohorts", flush=True)

    done = set()
    if OUT.exists():
        for line in open(OUT):
            try:
                r = json.loads(line)
                done.add((r["entity_id"], r["model_id"], r["template"]))
            except json.JSONDecodeError:
                pass
    print(f"resuming: {len(done)} verdicts on disk", flush=True)

    jobs = []
    for e in subset:
        for m in models:
            for tkey, tpl in TEMPLATES.items():
                if (e["id"], m["id"], tkey) in done:
                    continue
                jobs.append((e, m, tkey, tpl))
    print(f"{len(jobs)} (entity,model,template) probes to run", flush=True)

    or_client = OpenAI(base_url="https://openrouter.ai/api/v1",
                       api_key=os.environ["OPENROUTER_API_KEY"])

    def work(job):
        e, m, tkey, tpl = job
        probe = tpl.format(name=e["name"], context=e.get("context", ""))
        try:
            resp = call_probed_model(or_client, m["openrouter_id"], probe,
                                     thinking=m.get("thinking", False))
        except Exception:
            return None
        refused = is_refusal(resp)
        rec = 0 if refused else judge(e["name"], e.get("context", ""),
                                      gold[e["id"]], resp)
        if rec is None:
            return None
        return {"entity_id": e["id"], "cohort": e.get("cohort"),
                "model_id": m["id"], "template": tkey,
                "is_refusal": int(refused), "recognized": rec}

    n = 0
    with open(OUT, "a") as out:
        with ThreadPoolExecutor(max_workers=args.parallel) as ex:
            for fut in as_completed([ex.submit(work, j) for j in jobs]):
                v = fut.result()
                if v:
                    out.write(json.dumps(v, ensure_ascii=False) + "\n")
                    n += 1
                    if n % 200 == 0:
                        out.flush()
                        print(f"  {n}/{len(jobs)} ({time.strftime('%H:%M:%S')})",
                              flush=True)
    print(f"PARAPHRASE PROBE DONE: {n} new verdicts", flush=True)
    (HERE / "outputs" / "PARAPHRASE_DONE").touch()


if __name__ == "__main__":
    main()
