"""Full-coverage TIGHTENED judge on imo_gold + noi_china_gold (and their
synthetic floors) to answer: (1) IMO vs NOI separability, (2) per-entity
distribution (is the cohort carried by a tail or is most mass at the floor).

Panel recognition = recognized/36 with refusals counting as 0. Reuses verdicts
already in confab_sensitivity.jsonl; only judges the not-yet-done answered
records. Appends to confab_sensitivity.jsonl (same schema), then prints
per-entity distribution + cohort separability.
"""
from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from google import genai
from google.genai import types as genai_types

HERE = Path(__file__).resolve().parent.parent
TPL = (HERE / "inputs" / "judge_prompt_v3_tightened.txt").read_text()
OUT = HERE / "outputs" / "confab_sensitivity.jsonl"
COHORTS = ["imo_gold", "noi_china_gold",
           "synthetic_imo_gold_v2", "synthetic_noi_v2"]

SCHEMA = {"type": "object", "properties": {
    "recognized": {"type": "boolean"}, "coverage": {"type": "number"},
    "accuracy": {"type": "number"}, "rationale": {"type": "string"}},
    "required": ["recognized", "coverage", "accuracy", "rationale"]}
SYS = ("You are an objective grader judging whether a language model genuinely "
       "recognizes a specific named entity. Use knowledge freely to refute, but "
       "credit only positively-verified non-guessable facts; for competition "
       "participants and fellowship recipients you lack reliable per-individual "
       "memory, so credit only gold-present facts or major widely-documented "
       "achievements — never confabulated verification.")
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def judge(name, ctx, gold, resp):
    for a in range(4):
        try:
            r = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=TPL.format(name=name, context=ctx, gold_answer=gold,
                                    response=resp),
                config=genai_types.GenerateContentConfig(
                    system_instruction=SYS, temperature=0.0,
                    response_mime_type="application/json", response_schema=SCHEMA))
            return bool(json.loads(r.text)["recognized"])
        except Exception:
            if a == 3:
                return None
            time.sleep(2 * (a + 1))


def main():
    ents = {e["id"]: e for e in json.loads(
        (HERE / "inputs" / "pilot_entities_v2.json").read_text())}
    gold = json.loads((HERE / "inputs" / "gold_answers_v2.json").read_text())

    done = {}
    if OUT.exists():
        for line in open(OUT):
            try:
                r = json.loads(line)
                done[(r["entity_id"], r["model_id"])] = r["recognized_tight"]
            except json.JSONDecodeError:
                pass

    # all responses for target cohorts; refusal -> recognized 0 (no call)
    recs = []
    refusal = {}
    with open(HERE / "outputs" / "full_v2_results.jsonl") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            e = ents.get(r["entity_id"])
            if not e or e["cohort"] not in COHORTS:
                continue
            refusal[(r["entity_id"], r["model_id"])] = bool(r["is_refusal"])
            if not r["is_refusal"] and (r["entity_id"], r["model_id"]) not in done:
                recs.append(r)
    print(f"answered records still to judge: {len(recs)}")

    def work(r):
        e = ents[r["entity_id"]]
        rec = judge(e["name"], e["context"], gold[r["entity_id"]], r["response"])
        if rec is None:
            return None
        return {"entity_id": r["entity_id"], "model_id": r["model_id"],
                "cohort": e["cohort"], "synthetic": bool(e.get("synthetic")),
                "recognized_tight": int(rec), "rationale": "full-imo-noi"}

    n = 0
    with open(OUT, "a") as out:
        with ThreadPoolExecutor(max_workers=6) as ex:
            for fut in as_completed([ex.submit(work, r) for r in recs]):
                v = fut.result()
                if v:
                    out.write(json.dumps(v, ensure_ascii=False) + "\n")
                    done[(v["entity_id"], v["model_id"])] = v["recognized_tight"]
                    n += 1
                    if n % 300 == 0:
                        out.flush()
                        print(f"  {n}/{len(recs)}", flush=True)
    print(f"judged {n} more")

    # panel recognition per entity (refusal/unjudged -> 0)
    print("\n=== per-entity panel recognition under TIGHTENED ===")
    for cohort in ["imo_gold", "noi_china_gold"]:
        ids = [e for e in ents if ents[e]["cohort"] == cohort]
        per = []
        for eid in ids:
            mods = [m for (i, m) in refusal if i == eid]
            if len(mods) < 30:
                continue
            rec = [0 if refusal[(eid, m)] else done.get((eid, m), 0) for m in mods]
            per.append((eid, np.mean(rec)))
        per.sort(key=lambda x: x[1])
        vals = np.array([p[1] for p in per])
        se = vals.std() / np.sqrt(len(vals))
        print(f"\n{cohort}: n={len(per)}  mean {vals.mean():.3f} ±{1.96*se:.3f}  "
              f"median {np.median(vals):.3f}")
        print(f"  at floor (<=0.05): {(vals<=0.05).mean():.2f}  <=0.10: "
              f"{(vals<=0.10).mean():.2f}  >=0.30: {(vals>=0.30).mean():.2f}")
        print("  top-5: " + ", ".join(
            f"{ents[e]['name'].split('(')[0].strip()} {m:.2f}"
            for e, m in per[-5:][::-1]))
    # synthetic floors
    for c in ["synthetic_imo_gold_v2", "synthetic_noi_v2"]:
        v = [done[k] for k in done if ents.get(k[0], {}).get("cohort") == c]
        if v:
            print(f"\n{c} floor (answered): {np.mean(v):.3f} (n={len(v)})")


if __name__ == "__main__":
    main()
