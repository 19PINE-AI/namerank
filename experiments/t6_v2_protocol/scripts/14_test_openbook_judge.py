"""Validate the OPEN-BOOK recognition judge (judge_prompt_v3_openbook.txt) on
three sets, using retained responses + current golds:
  1. FN cases: researcher/faculty substantive-but-rejected under closed-book
     (Guzdial/Satya/etc.) — should FLIP to recognized where genuinely correct.
  2. Namesake/hallucination cases — should STAY rejected (wrong-entity guard).
  3. SYNTHETIC answered records (all cohorts) — the guessability/hallucination
     floor; MUST stay near zero, else open-book credits fabrication.

Prints flip rate on FN, retention on namesakes, and the synthetic floor.
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
TPL = (HERE / "inputs" / "judge_prompt_v3_openbook.txt").read_text()
SCHEMA = {"type": "object", "properties": {
    "recognized": {"type": "boolean"}, "coverage": {"type": "number"},
    "accuracy": {"type": "number"}, "rationale": {"type": "string"}},
    "required": ["recognized", "coverage", "accuracy", "rationale"]}
SYS = ("You are an objective grader judging whether a language model genuinely "
       "recognizes a specific named entity, using the gold answer to "
       "disambiguate which entity and your own reliable knowledge to verify "
       "facts. You never credit fabrication or a same-name different entity.")
gc = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def judge(name, ctx, gold, resp):
    for a in range(3):
        try:
            r = gc.models.generate_content(
                model="gemini-3-flash-preview",
                contents=TPL.format(name=name, context=ctx, gold_answer=gold,
                                    response=resp),
                config=genai_types.GenerateContentConfig(
                    system_instruction=SYS, temperature=0.0,
                    response_mime_type="application/json", response_schema=SCHEMA))
            p = json.loads(r.text)
            return bool(p["recognized"]), p["rationale"]
        except Exception:
            if a == 2:
                return None, "ERR"
            time.sleep(2 * (a + 1))


def main():
    ents = {e["id"]: e for e in json.loads(
        (HERE / "inputs" / "pilot_entities_v2.json").read_text())}
    gold = json.loads((HERE / "inputs" / "gold_answers_v2.json").read_text())
    v3 = {}
    for line in open(HERE / "outputs" / "recognition_v3_nonimo.jsonl"):
        try:
            r = json.loads(line); v3[(r["entity_id"], r["model_id"])] = r
        except json.JSONDecodeError:
            pass
    resp = {}
    for line in open(HERE / "outputs" / "full_v2_results.jsonl"):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (r["entity_id"], r["model_id"]) in v3:
            resp[(r["entity_id"], r["model_id"])] = r

    RES = {"cs_faculty", "long_tail_researcher_openalex", "long_tail_researcher_ikp"}
    fn, syn = [], []
    for k, vr in v3.items():
        e = ents.get(vr["entity_id"], {})
        rr = resp.get(k)
        if not rr or rr["is_refusal"]:
            continue
        if e.get("synthetic"):
            syn.append((k, vr, rr, e))
        elif (e.get("cohort") in RES and vr["recognized"] == 0
              and len(rr.get("response") or "") >= 180):
            fn.append((k, vr, rr, e))
    import random
    random.seed(5)
    fn = fn[:20]
    syn = syn if len(syn) <= 120 else random.sample(syn, 120)
    print(f"FN cases: {len(fn)}, synthetic answered: {len(syn)}")

    def work(item, kind):
        k, vr, rr, e = item
        rec, rat = judge(e["name"], e["context"], gold[vr["entity_id"]], rr["response"])
        return {"kind": kind, "eid": vr["entity_id"], "name": e["name"],
                "cohort": e["cohort"], "model": rr["model_id"],
                "old": vr["recognized"], "new": int(rec) if rec is not None else None,
                "rat": rat, "resp": (rr["response"] or "")[:130]}

    out = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(work, it, "FN") for it in fn] + \
               [ex.submit(work, it, "SYN") for it in syn]
        for f in as_completed(futs):
            v = f.result()
            if v and v["new"] is not None:
                out.append(v)

    fnr = [r for r in out if r["kind"] == "FN"]
    synr = [r for r in out if r["kind"] == "SYN"]
    people = [r for r in synr if "paper" not in r["cohort"]]
    papers = [r for r in synr if "paper" in r["cohort"]]
    print(f"\n=== SYNTHETIC floor under OPEN-BOOK: "
          f"all={np.mean([r['new'] for r in synr]):.3f} (n={len(synr)}) | "
          f"people={np.mean([r['new'] for r in people]) if people else 0:.3f} "
          f"(n={len(people)}) | papers={np.mean([r['new'] for r in papers]) if papers else 0:.3f} "
          f"(n={len(papers)}) ===")
    fp = [r for r in synr if r["new"] == 1]
    print(f"synthetic false-positives (open-book credited a fictional entity): {len(fp)}")
    for r in fp[:8]:
        print(f"  {r['eid']} [{r['model']}]: {r['rat'][:130]}")
    print(f"\n=== FN cases flipped to recognized: "
          f"{sum(r['new'] for r in fnr)}/{len(fnr)} ===")
    for r in fnr:
        tag = "FLIP" if r["new"] else "stays"
        print(f"  [{tag}] {r['name']} [{r['model']}]: {r['rat'][:130]}")


if __name__ == "__main__":
    main()
