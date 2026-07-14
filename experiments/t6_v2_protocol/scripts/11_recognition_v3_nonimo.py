"""Roll out the v3 recognition-verdict scoring to the NON-IMO cohorts.

Coordination: a concurrent session owns IMO-family v3 scoring. This script
SKIPS every IMO-family cohort (imo_gold, synthetic_imo_gold_v2) and writes ONLY
non-IMO verdicts to outputs/recognition_v3_nonimo.jsonl (append-only, keyed by
(entity_id, model_id), resumable). Final v3 scores = merge of that file with
the IMO session's output. Uses the shared inputs/judge_prompt_v3.txt rubric.

Reads retained responses from full_v2_results.jsonl; refusals get recognized=0
with no judge call. Re-runnable to pick up records probed after an earlier run.

Usage:
  python 11_recognition_v3_nonimo.py --sample 400   # validation subset
  python 11_recognition_v3_nonimo.py                # full non-IMO rollout
"""
from __future__ import annotations

import argparse
import json
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from google import genai
from google.genai import types as genai_types

HERE = Path(__file__).resolve().parent.parent
TPL = (HERE / "inputs" / "judge_prompt_v3.txt").read_text()
OUT = HERE / "outputs" / "recognition_v3_nonimo.jsonl"

IMO_FAMILY = {"imo_gold", "synthetic_imo_gold_v2"}

SCHEMA = {"type": "object", "properties": {
    "recognized": {"type": "boolean"},
    "coverage": {"type": "number"}, "accuracy": {"type": "number"},
    "rationale": {"type": "string"}},
    "required": ["recognized", "coverage", "accuracy", "rationale"]}
SYS = ("You are an objective grader judging whether a language model genuinely "
       "recognizes a named entity. You grade only the response against the gold "
       "answer, giving no credit for restating the probe context or for "
       "guessable generic facts.")
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def judge(name, context, gold, response):
    for a in range(3):
        try:
            r = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=TPL.format(name=name, context=context,
                                    gold_answer=gold, response=response),
                config=genai_types.GenerateContentConfig(
                    system_instruction=SYS, temperature=0.0,
                    response_mime_type="application/json",
                    response_schema=SCHEMA))
            p = json.loads(r.text)
            return (bool(p["recognized"]), float(p["coverage"]),
                    float(p["accuracy"]), str(p["rationale"]))
        except Exception:  # noqa: BLE001
            if a == 2:
                return None
            time.sleep(2 * (a + 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--parallel", type=int, default=6)
    args = ap.parse_args()

    ents = {e["id"]: e for e in json.loads(
        (HERE / "inputs" / "pilot_entities_v2.json").read_text())}
    gold = json.loads((HERE / "inputs" / "gold_answers_v2.json").read_text())

    done = set()
    if OUT.exists():
        with open(OUT) as f:
            for line in f:
                try:
                    r = json.loads(line)
                    done.add((r["entity_id"], r["model_id"]))
                except json.JSONDecodeError:
                    pass
    print(f"resuming: {len(done)} non-IMO v3 verdicts already written")

    todo = []
    with open(HERE / "outputs" / "full_v2_results.jsonl") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            e = ents.get(r["entity_id"])
            if not e or e["cohort"] in IMO_FAMILY:
                continue
            if (r["entity_id"], r["model_id"]) in done:
                continue
            todo.append(r)

    if args.sample:
        random.seed(11)
        # stratified: all synthetic answered + spread of real + some refusals
        syn = [r for r in todo if ents[r["entity_id"]].get("synthetic")
               and not r["is_refusal"]]
        rest = [r for r in todo if r not in syn]
        random.shuffle(rest)
        todo = syn + rest[:max(0, args.sample - len(syn))]
        print(f"SAMPLE mode: {len(todo)} records ({len(syn)} synthetic answered)")
    else:
        print(f"FULL non-IMO rollout: {len(todo)} records to judge")

    def work(r):
        e = ents[r["entity_id"]]
        base = {"entity_id": r["entity_id"], "model_id": r["model_id"],
                "cohort": e["cohort"], "synthetic": bool(e.get("synthetic"))}
        if r["is_refusal"]:
            return {**base, "recognized": 0, "coverage": 0.0, "accuracy": 0.0,
                    "rationale": "refusal", "is_refusal": 1}
        res = judge(r["entity_name"], e["context"], gold[r["entity_id"]],
                    r["response"])
        if res is None:
            return None
        rec, cov, acc, rat = res
        return {**base, "recognized": int(rec), "coverage": cov,
                "accuracy": acc, "rationale": rat, "is_refusal": 0}

    n = 0
    with open(OUT, "a") as out:
        with ThreadPoolExecutor(max_workers=args.parallel) as ex:
            for fut in as_completed([ex.submit(work, r) for r in todo]):
                v = fut.result()
                if v:
                    out.write(json.dumps(v, ensure_ascii=False) + "\n")
                    n += 1
                    if n % 500 == 0:
                        out.flush()
                        print(f"  {n}/{len(todo)} ({time.strftime('%H:%M:%S')})",
                              flush=True)
    print(f"done: wrote {n} verdicts -> {OUT.name}")


if __name__ == "__main__":
    main()
