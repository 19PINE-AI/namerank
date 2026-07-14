"""Confabulation sensitivity: re-judge credential + paper cohorts (real AND
their synthetic floors) with the anti-confabulation TIGHTENED judge, and
compare recognition rates against the canonical open-book judge on the SAME
(entity, model) records.

Runs on retained responses (probing is complete). To bound cost on the large
paper/msra cohorts, real records are sampled; ALL synthetic answered records
are judged (the floor is what matters). Writes a paired file so the comparison
is on identical records.

Output: outputs/confab_sensitivity.jsonl  (tightened verdicts)
        prints paired canonical-vs-tightened recognition per cohort.
"""
from __future__ import annotations

import json
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from google import genai
from google.genai import types as genai_types

HERE = Path(__file__).resolve().parent.parent
TPL = (HERE / "inputs" / "judge_prompt_v3_tightened.txt").read_text()
OUT = HERE / "outputs" / "confab_sensitivity.jsonl"

REAL = ["imo_gold", "noi_china_gold", "cmo_china_gold", "cpho_china_first_prize",
        "ioi_gold", "rhodes_scholar", "putnam_fellow", "msra_phd_fellowship",
        "long_tail_paper", "research_paper"]
SYN = ["synthetic_imo_gold_v2", "synthetic_noi_v2", "synthetic_paper_v2",
       "synthetic_msra_v2"]
REAL_SAMPLE = 350   # per cohort cap on real answered records

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
            p = json.loads(r.text)
            return bool(p["recognized"]), str(p["rationale"])
        except Exception:
            if a == 3:
                return None, "ERR"
            time.sleep(2 * (a + 1))


def main():
    random.seed(13)
    ents = {e["id"]: e for e in json.loads(
        (HERE / "inputs" / "pilot_entities_v2.json").read_text())}
    gold = json.loads((HERE / "inputs" / "gold_answers_v2.json").read_text())

    # canonical open-book verdicts already computed (partial ok)
    canon = {}
    vp = HERE / "outputs" / "recognition_v3.jsonl"
    if vp.exists():
        for line in open(vp):
            try:
                r = json.loads(line)
                canon[(r["entity_id"], r["model_id"])] = r["recognized"]
            except json.JSONDecodeError:
                pass

    # gather answered records for target cohorts from retained responses
    by_cohort = {c: [] for c in REAL + SYN}
    with open(HERE / "outputs" / "full_v2_results.jsonl") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            e = ents.get(r["entity_id"])
            if not e or r["is_refusal"]:
                continue
            c = e["cohort"]
            if c in by_cohort:
                by_cohort[c].append(r)

    todo = []
    for c in SYN:
        todo += by_cohort[c]                      # all synthetic
    for c in REAL:
        pool = by_cohort[c]
        todo += (pool if len(pool) <= REAL_SAMPLE
                 else random.sample(pool, REAL_SAMPLE))

    done = set()
    if OUT.exists():
        for line in open(OUT):
            try:
                r = json.loads(line)
                done.add((r["entity_id"], r["model_id"]))
            except json.JSONDecodeError:
                pass
    todo = [r for r in todo if (r["entity_id"], r["model_id"]) not in done]
    print(f"judging {len(todo)} records with tightened judge "
          f"({sum(len(by_cohort[c]) for c in SYN)} synthetic answered)")

    def work(r):
        e = ents[r["entity_id"]]
        rec, rat = judge(e["name"], e["context"], gold[r["entity_id"]],
                         r["response"])
        if rec is None:
            return None
        return {"entity_id": r["entity_id"], "model_id": r["model_id"],
                "cohort": e["cohort"], "synthetic": bool(e.get("synthetic")),
                "recognized_tight": int(rec), "rationale": rat}

    n = 0
    with open(OUT, "a") as out:
        with ThreadPoolExecutor(max_workers=6) as ex:
            for fut in as_completed([ex.submit(work, r) for r in todo]):
                v = fut.result()
                if v:
                    out.write(json.dumps(v, ensure_ascii=False) + "\n")
                    n += 1
                    if n % 300 == 0:
                        out.flush()
                        print(f"  {n}/{len(todo)}", flush=True)

    # paired comparison
    rows = []
    for line in open(OUT):
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    from collections import defaultdict
    ct = defaultdict(list)
    cc = defaultdict(list)
    for r in rows:
        k = (r["entity_id"], r["model_id"])
        ct[r["cohort"]].append(r["recognized_tight"])
        if k in canon:
            cc[r["cohort"]].append(canon[k])
    print("\n=== canonical open-book vs TIGHTENED (paired where canonical exists) ===")
    print(f"{'cohort':32s} {'canon':>7s} {'tight':>7s} {'n':>6s}")
    for c in SYN + REAL:
        t = ct.get(c, [])
        if not t:
            continue
        canon_rate = np.mean(cc[c]) if cc.get(c) else float("nan")
        print(f"{c:32s} {canon_rate:7.3f} {np.mean(t):7.3f} {len(t):6d}")


if __name__ == "__main__":
    main()
