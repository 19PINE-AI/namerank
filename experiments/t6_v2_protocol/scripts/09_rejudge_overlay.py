"""Re-judge already-probed records against corrected golds, WITHOUT touching
the running results JSONL. Reads retained responses from full_v2_results.jsonl,
re-scores with judge v2 against the current (corrected) gold_answers_v2.json,
and writes rejudge_overlay.jsonl keyed by (entity_id, model_id). Analysis
prefers overlay scores where present.

Usage: python 09_rejudge_overlay.py <cohort1> <cohort2> ...
Safe to run alongside the probe run (append-only to a different file).
"""
from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from google import genai
from google.genai import types as genai_types

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent

JUDGE_TPL = (HERE / "inputs" / "judge_prompt.txt").read_text()
SCHEMA = {"type": "object", "properties": {
    "coverage": {"type": "number"}, "accuracy": {"type": "number"},
    "rationale": {"type": "string"}},
    "required": ["coverage", "accuracy", "rationale"]}
SYS = ("You are an objective grader scoring a language-model response against a "
       "gold-answer reference paragraph about a named entity. You do not bring "
       "outside knowledge; you grade only what the response says against what "
       "the gold answer says, discounting anything the probe context already "
       "gave away.")
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def judge(name, context, gold, response):
    prompt = JUDGE_TPL.format(name=name, context=context, gold_answer=gold,
                              response=response)
    for a in range(3):
        try:
            r = client.models.generate_content(
                model="gemini-3-flash-preview", contents=prompt,
                config=genai_types.GenerateContentConfig(
                    system_instruction=SYS, temperature=0.0,
                    response_mime_type="application/json",
                    response_schema=SCHEMA))
            p = json.loads(r.text)
            return float(p["coverage"]), float(p["accuracy"])
        except Exception:  # noqa: BLE001
            if a == 2:
                return None, None
            time.sleep(2 * (a + 1))


def main():
    cohorts = set(sys.argv[1:])
    ents = {e["id"]: e for e in json.loads(
        (HERE / "inputs" / "pilot_entities_v2.json").read_text())}
    gold = json.loads((HERE / "inputs" / "gold_answers_v2.json").read_text())
    overlay_path = HERE / "outputs" / "rejudge_overlay.jsonl"
    done = set()
    if overlay_path.exists():
        with open(overlay_path) as f:
            for line in f:
                try:
                    r = json.loads(line)
                    done.add((r["entity_id"], r["model_id"]))
                except json.JSONDecodeError:
                    pass

    # collect answered records for the target cohorts from the run JSONL
    todo = []
    with open(HERE / "outputs" / "full_v2_results.jsonl") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r["is_refusal"]:
                continue
            e = ents.get(r["entity_id"])
            if not e or e["cohort"] not in cohorts:
                continue
            if (r["entity_id"], r["model_id"]) in done:
                continue
            todo.append(r)
    print(f"re-judging {len(todo)} answered records in {cohorts}")

    def work(r):
        e = ents[r["entity_id"]]
        cov, acc = judge(r["entity_name"], e["context"],
                         gold[r["entity_id"]], r["response"])
        if cov is None:
            return None
        return {"entity_id": r["entity_id"], "model_id": r["model_id"],
                "coverage": cov, "accuracy": acc, "score": cov * acc}

    n = 0
    with open(overlay_path, "a") as out:
        with ThreadPoolExecutor(max_workers=8) as ex:
            for fut in as_completed([ex.submit(work, r) for r in todo]):
                rec = fut.result()
                if rec:
                    out.write(json.dumps(rec) + "\n")
                    n += 1
                    if n % 200 == 0:
                        out.flush()
                        print(f"  {n}/{len(todo)}", flush=True)
    print(f"done: {n} overlay records -> {overlay_path}")


if __name__ == "__main__":
    main()
