"""Canonical v3 recognition scoring — OPEN-BOOK judge, ALL cohorts.

Consolidated owner of the whole v3 rollout (IMO + non-IMO). Reads retained
responses from full_v2_results.jsonl, judges each with the canonical open-book
rubric (inputs/judge_prompt_v3.txt), writes recognition_v3.jsonl (append-only,
keyed by (entity_id, model_id), resumable). Refusals -> recognized=0 with no
judge call. Re-run to pick up records probed after an earlier pass.

NameRank_v3(entity) = fraction of the panel that recognizes the entity.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from google import genai
from google.genai import types as genai_types

HERE = Path(__file__).resolve().parent.parent
TPL = (HERE / "inputs" / "judge_prompt_v3.txt").read_text()   # canonical open-book
OUT = HERE / "outputs" / "recognition_v3.jsonl"

SCHEMA = {"type": "object", "properties": {
    "recognized": {"type": "boolean"},
    "coverage": {"type": "number"}, "accuracy": {"type": "number"},
    "rationale": {"type": "string"}},
    "required": ["recognized", "coverage", "accuracy", "rationale"]}
SYS = ("You are an objective grader judging whether a language model genuinely "
       "recognizes a specific named entity, using the gold answer to "
       "disambiguate which entity and your own reliable knowledge to verify "
       "facts. Use knowledge freely to refute, but credit only positively-"
       "verified facts; never credit fabrication or a same-name different entity.")
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def judge(name, context, gold, response):
    for a in range(4):
        try:
            r = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=TPL.format(name=name, context=context,
                                    gold_answer=gold, response=response),
                config=genai_types.GenerateContentConfig(
                    system_instruction=SYS, temperature=0.0,
                    response_mime_type="application/json", response_schema=SCHEMA))
            p = json.loads(r.text)
            return (bool(p["recognized"]), float(p["coverage"]),
                    float(p["accuracy"]), str(p["rationale"]))
        except Exception:  # noqa: BLE001
            if a == 3:
                return None
            time.sleep(2 * (a + 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parallel", type=int, default=8)
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
    print(f"resuming: {len(done)} v3 verdicts already written")

    todo = []
    with open(HERE / "outputs" / "full_v2_results.jsonl") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r["entity_id"] not in ents:
                continue
            if (r["entity_id"], r["model_id"]) in done:
                continue
            todo.append(r)
    print(f"to judge: {len(todo)} records (all cohorts, open-book)")

    def work(r):
        e = ents[r["entity_id"]]
        base = {"entity_id": r["entity_id"], "model_id": r["model_id"],
                "cohort": e["cohort"], "synthetic": bool(e.get("synthetic")),
                "is_refusal": int(bool(r["is_refusal"]))}
        if r["is_refusal"]:
            return {**base, "recognized": 0, "coverage": 0.0, "accuracy": 0.0,
                    "rationale": "refusal"}
        res = judge(r["entity_name"], e["context"], gold[r["entity_id"]],
                    r["response"])
        if res is None:
            return None
        rec, cov, acc, rat = res
        return {**base, "recognized": int(rec), "coverage": cov,
                "accuracy": acc, "rationale": rat}

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
