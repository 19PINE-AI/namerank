"""Uniform FINAL judging pass: one judge prompt (the anti-confabulation
open-book rubric, judge_prompt_v3_tightened.txt) applied to every retained
response across all experiments, so the released paper rests on a single
judge. Refusals get recognized=0 without a call. Resumable; appends to
outputs/recognition_final.jsonl with a `dataset` tag.

Datasets (responses all retained on disk):
  main     t6 full_v2_results.jsonl        (~170K records)
  events   t4_1 pilot_results_events.json  (~9.3K)
  awards   t5_1 pilot_results_awards.json  (~20K)
  llm      t5_5 llm_area_results.jsonl     (~8.9K)
  univ     t5_4 univ_v2_results.jsonl      (~25K)

Usage: python 19_uniform_final_judge.py [--parallel 10] [--only main,events]
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
REPO = HERE.parent.parent
TPL = (HERE / "inputs" / "judge_prompt_v3_tightened.txt").read_text()
OUT = HERE / "outputs" / "recognition_final.jsonl"

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
            return int(bool(p["recognized"])), str(p.get("rationale", ""))[:400]
        except Exception:
            if a == 3:
                return None, "ERR"
            time.sleep(2 * (a + 1))


def load_records(path):
    path = Path(path)
    if not path.exists():
        return []
    txt = path.read_text()
    if path.suffix == ".jsonl" or "\n{" in txt[:2000]:
        recs = []
        for line in txt.splitlines():
            try:
                recs.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return recs
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        return []


def load_gold(path):
    g = json.loads(Path(path).read_text())
    return {k: (v if isinstance(v, str) else v.get("gold", "")) for k, v in g.items()}


DATASETS = {
    "main": dict(
        records=HERE / "outputs/full_v2_results.jsonl",
        entities=HERE / "inputs/pilot_entities_v2.json",
        gold=HERE / "inputs/gold_answers_v2.json"),
    "events": dict(
        records=REPO / "experiments/t4_1_news_events/outputs/pilot_results_events.json",
        entities=REPO / "experiments/t4_1_news_events/inputs/event_entities.json",
        gold=REPO / "experiments/t4_1_news_events/inputs/event_gold.json"),
    "awards": dict(
        records=REPO / "experiments/t5_1_award_ladder/outputs/pilot_results_awards.json",
        entities=REPO / "experiments/t5_1_award_ladder/inputs/award_entities.json",
        gold=REPO / "experiments/t5_1_award_ladder/inputs/award_gold.json"),
    "llm": dict(
        records=REPO / "experiments/t5_5_llm_area/outputs/llm_area_results.jsonl",
        entities=REPO / "experiments/t5_5_llm_area/inputs/probe_entities.json",
        gold=REPO / "experiments/t5_5_llm_area/inputs/probe_gold.json"),
    "univ": dict(
        records=REPO / "experiments/t5_4_university_baseline/outputs/univ_v2_results.jsonl",
        entities=REPO / "experiments/t5_4_university_baseline/inputs/univ_entities_v2.json",
        gold=REPO / "experiments/t5_4_university_baseline/inputs/univ_gold_v3.json"),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parallel", type=int, default=10)
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    names = [n for n in args.only.split(",") if n] or list(DATASETS)

    done = set()
    if OUT.exists():
        for line in open(OUT):
            try:
                r = json.loads(line)
                done.add((r["dataset"], r["entity_id"], r["model_id"]))
            except json.JSONDecodeError:
                pass
    print(f"resuming: {len(done)} final verdicts on disk", flush=True)

    for ds in names:
        cfg = DATASETS[ds]
        ents = {e["id"]: e for e in json.loads(Path(cfg["entities"]).read_text())}
        gold = load_gold(cfg["gold"])
        recs = load_records(cfg["records"])
        todo, nrefus = [], 0
        with open(OUT, "a") as out:
            for r in recs:
                eid, mid = r.get("entity_id"), r.get("model_id")
                if not eid or eid not in ents or eid not in gold:
                    continue
                if (ds, eid, mid) in done:
                    continue
                if r.get("is_refusal"):
                    out.write(json.dumps({"dataset": ds, "entity_id": eid,
                                          "model_id": mid, "recognized": 0,
                                          "rationale": "refusal"}) + "\n")
                    done.add((ds, eid, mid))
                    nrefus += 1
                elif r.get("response"):
                    todo.append(r)
        print(f"[{ds}] {len(recs)} records: {nrefus} refusals written, "
              f"{len(todo)} to judge", flush=True)

        def work(r):
            e = ents[r["entity_id"]]
            rec, rat = judge(e["name"], e.get("context", ""),
                             gold[r["entity_id"]], r["response"])
            if rec is None:
                return None
            return {"dataset": ds, "entity_id": r["entity_id"],
                    "model_id": r["model_id"], "recognized": rec,
                    "rationale": rat}

        n = 0
        with open(OUT, "a") as out:
            with ThreadPoolExecutor(max_workers=args.parallel) as ex:
                for fut in as_completed([ex.submit(work, r) for r in todo]):
                    v = fut.result()
                    if v:
                        out.write(json.dumps(v, ensure_ascii=False) + "\n")
                        n += 1
                        if n % 1000 == 0:
                            out.flush()
                            print(f"  [{ds}] {n}/{len(todo)} "
                                  f"({time.strftime('%H:%M:%S')})", flush=True)
        print(f"[{ds}] judged {n}", flush=True)
    print("UNIFORM PASS COMPLETE", flush=True)
    (HERE / "outputs" / "FINAL_JUDGE_DONE").touch()


if __name__ == "__main__":
    main()
