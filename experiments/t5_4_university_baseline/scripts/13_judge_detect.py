"""Judge-v3 pass over the stored v2 responses (detection headline scoring).

Uses the CANONICAL judge v3 from the concurrent full-pass session —
t6_v2_protocol/inputs/judge_prompt_v3.txt — verbatim, so this experiment's
scores are rubric-identical to the full pass. One call per answered record
returns: recognized (boolean, the headline), coverage and accuracy (retained
as the depth diagnostic, cov*acc among recognized models).

NameRank-detect(entity) = fraction of panel models with recognized=true
(refusals = false). Verification pool = the v3 web-grounded golds
(inputs/univ_gold_v3.json), which cover every entity including the 190 the
S2 matcher dropped.

This supersedes 11_rejudge_v3.py (a separate graded re-judge is no longer
needed — judge v3 returns both signals in one pass).

Reads  outputs/univ_v2_results.jsonl  (stored responses)
Writes outputs/univ_v3judge_results.jsonl

Resumable. Usage: python 13_judge_detect.py [--parallel 8]
"""
from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
T6 = REPO / "experiments" / "t6_v2_protocol"

from google import genai  # noqa: E402
from google.genai import types as genai_types  # noqa: E402

JUDGE_TPL = (T6 / "inputs" / "judge_prompt_v3.txt").read_text()
SCHEMA = {"type": "object", "properties": {
    "recognized": {"type": "boolean"},
    "coverage": {"type": "number"}, "accuracy": {"type": "number"},
    "rationale": {"type": "string"}},
    "required": ["recognized", "coverage", "accuracy", "rationale"]}
# open-book system prompt (matches t6 canonical judge_prompt_v3.txt, adopted
# 2026-07-12 as the standard v3 rubric): use knowledge freely to refute, but
# credit only positively-verified facts; the gold disambiguates which entity.
SYS = ("You are an objective grader judging whether a language model genuinely "
       "recognizes a specific named entity, using the gold answer to "
       "disambiguate which entity and your own reliable knowledge to verify "
       "facts. Use knowledge freely to refute, but credit only positively-"
       "verified facts; never credit fabrication or a same-name different entity.")


def judge_v3(client, name, context, gold, response):
    prompt = JUDGE_TPL.format(name=name, context=context, gold_answer=gold,
                              response=response)
    for attempt in range(3):
        try:
            r = client.models.generate_content(
                model="gemini-3-flash-preview", contents=prompt,
                config=genai_types.GenerateContentConfig(
                    system_instruction=SYS, temperature=0.0,
                    response_mime_type="application/json",
                    response_schema=SCHEMA))
            p = json.loads(r.text)
            return {"recognized": bool(p["recognized"]),
                    "coverage": float(p["coverage"]),
                    "accuracy": float(p["accuracy"]),
                    "rationale": str(p["rationale"])}
        except Exception as e:  # noqa: BLE001
            if attempt == 2:
                return {"recognized": False, "coverage": 0.0, "accuracy": 0.0,
                        "rationale": f"[JUDGE-ERROR: {type(e).__name__}]"}
            time.sleep(2 * (attempt + 1))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--parallel", type=int, default=8)
    args = p.parse_args()

    gold = {eid: g["gold"] for eid, g in json.loads(
        (HERE / "inputs" / "univ_gold_v3.json").read_text()).items()}
    entities = {e["id"]: e for e in json.loads(
        (HERE / "inputs" / "univ_entities_v2.json").read_text())}

    src = []
    with open(HERE / "outputs" / "univ_v2_results.jsonl") as f:
        for line in f:
            try:
                src.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    out_path = HERE / "outputs" / "univ_v3judge_results.jsonl"
    done = set()
    if out_path.exists():
        with open(out_path) as f:
            for line in f:
                try:
                    r = json.loads(line)
                    done.add((r["entity_id"], r["model_id"]))
                except json.JSONDecodeError:
                    pass

    todo = [r for r in src
            if (r["entity_id"], r["model_id"]) not in done
            and r["entity_id"] in gold]
    n_nogold = len({r["entity_id"] for r in src if r["entity_id"] not in gold})
    print(f"{len(src):,} stored records; {len(done):,} done; "
          f"{len(todo):,} to judge; {n_nogold} entities lack a v3 gold")

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def process(r):
        base = {"entity_id": r["entity_id"], "model_id": r["model_id"],
                "is_refusal": r["is_refusal"], "ts": time.time()}
        if r["is_refusal"]:
            base.update(recognized=False, coverage=0.0, accuracy=0.0,
                        score=0.0, rationale="refusal")
        else:
            e = entities[r["entity_id"]]
            s = judge_v3(client, e["name"], e["context"],
                         gold[r["entity_id"]], r["response"])
            base.update(recognized=s["recognized"], coverage=s["coverage"],
                        accuracy=s["accuracy"],
                        score=s["coverage"] * s["accuracy"],
                        rationale=s["rationale"])
        return base

    with open(out_path, "a", encoding="utf-8") as fout:
        with ThreadPoolExecutor(max_workers=args.parallel) as ex:
            futs = {ex.submit(process, r): (r["entity_id"], r["model_id"])
                    for r in todo}
            for i, fut in enumerate(as_completed(futs)):
                try:
                    rec = fut.result()
                except Exception as exc:  # noqa: BLE001
                    print(f"  [ERROR] {futs[fut]}: {exc}")
                    continue
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                if (i + 1) % 500 == 0:
                    fout.flush()
                    print(f"  {i+1}/{len(todo)} "
                          f"({time.strftime('%H:%M:%S')})", flush=True)
    print(f"Done -> {out_path}")


if __name__ == "__main__":
    main()
