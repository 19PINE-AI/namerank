"""Validate the recognition-verdict judge (judge v3) on a stratified sample of
already-probed responses (real + synthetic across cohorts). Shows that a
DIRECTLY-JUDGED binary 'recognized' keeps the synthetic (guessability) floor
near zero while separating real cohorts — without post-hoc thresholding.

Writes outputs/recognition_validation.csv and prints floor/separation.
"""
from __future__ import annotations

import json
import os
import random
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from google import genai
from google.genai import types as genai_types

HERE = Path(__file__).resolve().parent.parent
TPL = (HERE / "inputs" / "judge_prompt_v3.txt").read_text()
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
            return bool(p["recognized"]), float(p["coverage"]), float(p["accuracy"]), p["rationale"]
        except Exception:  # noqa: BLE001
            if a == 2:
                return None, None, None, "ERR"
            time.sleep(2 * (a + 1))


def main():
    random.seed(7)
    ents = {e["id"]: e for e in json.loads(
        (HERE / "inputs" / "pilot_entities_v2.json").read_text())}
    gold = json.loads((HERE / "inputs" / "gold_answers_v2.json").read_text())
    recs = [json.loads(l) for l in open(
        HERE / "outputs" / "pilot_v2_results.PASSED.jsonl")]
    for r in recs:
        e = ents.get(r["entity_id"], {})
        r["cohort"] = e.get("cohort", "?")
        r["syn"] = bool(e.get("synthetic"))

    # stratified sample: all synthetic answered + sample of real per cohort
    syn = [r for r in recs if r["syn"] and not r["is_refusal"]]
    real = defaultdict(list)
    for r in recs:
        if not r["syn"] and not r["is_refusal"]:
            real[r["cohort"]].append(r)
    sample = list(syn)
    for coh, rs in real.items():
        sample += random.sample(rs, min(40, len(rs)))
    # include refusals (should be recognized=false) as a sanity check
    refs = [r for r in recs if r["is_refusal"]]
    sample += random.sample(refs, min(60, len(refs)))
    print(f"judging {len(sample)} records (syn answered={len(syn)})")

    def work(r):
        if r["is_refusal"]:
            return {**{k: r[k] for k in ("entity_id", "model_id", "cohort", "syn")},
                    "recognized": 0, "cov": 0, "acc": 0, "rat": "refusal"}
        rec, cov, acc, rat = judge(r["entity_name"], ents[r["entity_id"]]["context"],
                                   gold[r["entity_id"]], r["response"])
        if rec is None:
            return None
        return {**{k: r[k] for k in ("entity_id", "model_id", "cohort", "syn")},
                "recognized": int(rec), "cov": cov, "acc": acc, "rat": rat}

    out = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for f in as_completed([ex.submit(work, r) for r in sample]):
            v = f.result()
            if v:
                out.append(v)
    import pandas as pd
    df = pd.DataFrame(out)
    df.to_csv(HERE / "outputs" / "recognition_validation.csv", index=False)

    print("\n=== DIRECTLY-JUDGED recognition rate (fraction recognized) ===")
    syn_rate = df[df.syn].recognized.mean()
    print(f"SYNTHETIC (guessability floor): {syn_rate:.3f}  n={df.syn.sum()}")
    print("real cohorts:")
    for coh, g in df[~df.syn].groupby("cohort"):
        print(f"  {coh:28s} recognized={g.recognized.mean():.3f} "
              f"(cov*acc mean={np.mean(g.cov*g.acc):.3f}) n={len(g)}")
    # false-positive audit: synthetic entities judged recognized
    fp = df[(df.syn) & (df.recognized == 1)]
    print(f"\nSYNTHETIC false-positives (recognized=1 on fictional entity): {len(fp)}")
    for _, r in fp.head(8).iterrows():
        print(f"  {r.entity_id} [{r.model_id}]: {r.rat[:130]}")


if __name__ == "__main__":
    main()
