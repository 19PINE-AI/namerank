"""Cross-judge robustness under the recognition verdict.

Re-judge a stratified sample of the main-dataset responses with two additional
judges (Claude + GPT) under the SAME tightened recognition rubric that the
canonical Gemini judge uses, then measure inter-judge agreement on the BINARY
verdict (not a graded score). Gemini verdicts are read from the completed
recognition_final.jsonl; Claude and GPT are called here.

Outputs outputs/cross_judge.jsonl with one row per (entity, model) holding all
three verdicts, and prints the agreement + per-cohort tables used by
app:cross-judge.

Usage: python 23_cross_judge.py [--per-cohort 60] [--parallel 12]
"""
from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import anthropic
import openai

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
TPL = (HERE / "inputs" / "judge_prompt_v3_tightened.txt").read_text()
FINAL = HERE / "outputs" / "recognition_final.jsonl"
OUT = HERE / "outputs" / "cross_judge.jsonl"

SYS = ("You are an objective grader judging whether a language model genuinely "
       "recognizes a specific named entity. Use knowledge freely to refute, but "
       "credit only positively-verified non-guessable facts; for competition "
       "participants, fellowship recipients, and minor-paper authors you lack "
       "reliable per-individual memory, so credit only gold-present facts or "
       "major widely-documented achievements — never confabulated verification.")

# Stratified sample: the diagnostic reference set + the cohorts that carry the
# headline findings. Deterministic (sorted, no RNG) so the run is reproducible.
STRATA = {
    "Reference set": "reference_pilot",
    "OpenAlex long-tail researchers": "long_tail_researcher_openalex",
    "CS faculty": "cs_faculty",
    "IMO gold": "imo_gold",
    "GPT-5 system-card authors": "gpt5_system_card_author",
    "Writers": "mid_tier_writer",
    "OSS projects": "oss_project",
    "Named methods": "named_method",
    "Foundation models": "foundation_model",
}

ac = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
# The direct OpenAI key is read-only; route GPT through OpenRouter instead.
oc = openai.OpenAI(api_key=os.environ["OPENROUTER_API_KEY"],
                   base_url="https://openrouter.ai/api/v1")
CLAUDE_MODEL = "claude-opus-4-6"
GPT_MODEL = "openai/gpt-5.1"


def _prompt(name, ctx, gold, resp):
    return TPL.format(name=name, context=ctx, gold_answer=gold, response=resp)


def judge_claude(name, ctx, gold, resp):
    for a in range(4):
        try:
            m = ac.messages.create(
                model=CLAUDE_MODEL, max_tokens=600, temperature=0.0,
                system=SYS + " Respond with a JSON object with keys "
                "recognized (boolean) and rationale (string).",
                messages=[{"role": "user", "content": _prompt(name, ctx, gold, resp)}])
            txt = m.content[0].text
            s = txt[txt.find("{"): txt.rfind("}") + 1]
            return int(bool(json.loads(s)["recognized"]))
        except Exception:
            if a == 3:
                return None
            time.sleep(2 * (a + 1))


def judge_gpt(name, ctx, gold, resp):
    for a in range(4):
        try:
            r = oc.chat.completions.create(
                model=GPT_MODEL, max_tokens=800,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYS + " Respond with a JSON "
                     "object with keys recognized (boolean) and rationale (string)."},
                    {"role": "user", "content": _prompt(name, ctx, gold, resp)}])
            return int(bool(json.loads(r.choices[0].message.content)["recognized"]))
        except Exception:
            if a == 3:
                return None
            time.sleep(2 * (a + 1))


def load_records(path):
    txt = Path(path).read_text()
    recs = []
    if "\n{" in txt[:2000] or path.suffix == ".jsonl":
        for line in txt.splitlines():
            try:
                recs.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    else:
        recs = json.loads(txt)
    return recs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-cohort", type=int, default=60)
    ap.add_argument("--parallel", type=int, default=12)
    args = ap.parse_args()

    ents = {e["id"]: e for e in json.loads(
        (HERE / "inputs/pilot_entities_v2.json").read_text())}
    gold = json.loads((HERE / "inputs/gold_answers_v2.json").read_text())
    gold = {k: (v if isinstance(v, str) else v.get("gold", "")) for k, v in gold.items()}

    # Gemini verdicts from the finished uniform pass (main only).
    gem = {}
    for line in open(FINAL):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("dataset") == "main":
            gem[(r["entity_id"], r["model_id"])] = r["recognized"]
    print(f"loaded {len(gem)} gemini verdicts (main)", flush=True)

    recs = load_records(HERE / "outputs/full_v2_results.jsonl")
    by_cohort = {label: [] for label in STRATA}
    cid = {label: cohort for label, cohort in STRATA.items()}
    want = set(cid.values())
    for r in recs:
        eid, mid = r.get("entity_id"), r.get("model_id")
        e = ents.get(eid)
        if not e or e.get("cohort") not in want:
            continue
        if r.get("is_refusal") or not r.get("response"):
            # refusal -> recognized 0 by all judges; still counts toward agreement
            pass
        if (eid, mid) not in gem:
            continue
        label = next(l for l, c in cid.items() if c == e["cohort"])
        by_cohort[label].append(r)

    # Deterministic stratified subsample: sort by (entity_id, model_id), take
    # an evenly-spaced slice so models & entities are both spread.
    sample = []
    for label, rs in by_cohort.items():
        rs.sort(key=lambda r: (r["entity_id"], r["model_id"]))
        if len(rs) > args.per_cohort:
            step = len(rs) / args.per_cohort
            rs = [rs[int(i * step)] for i in range(args.per_cohort)]
        for r in rs:
            r["_cohort_label"] = label
        sample.extend(rs)
    print(f"sampled {len(sample)} records across {len(by_cohort)} cohorts", flush=True)

    done = set()
    if OUT.exists():
        for line in open(OUT):
            try:
                r = json.loads(line)
                done.add((r["entity_id"], r["model_id"]))
            except json.JSONDecodeError:
                pass
    todo = [r for r in sample if (r["entity_id"], r["model_id"]) not in done]
    print(f"resuming: {len(done)} done, {len(todo)} to judge", flush=True)

    def work(r):
        eid, mid = r["entity_id"], r["model_id"]
        e = ents[eid]
        if r.get("is_refusal") or not r.get("response"):
            c = g = 0
        else:
            c = judge_claude(e["name"], e.get("context", ""), gold[eid], r["response"])
            g = judge_gpt(e["name"], e.get("context", ""), gold[eid], r["response"])
        if c is None or g is None:
            return None
        return {"cohort": r["_cohort_label"], "entity_id": eid, "model_id": mid,
                "gemini": gem[(eid, mid)], "claude": c, "gpt": g}

    n = 0
    with open(OUT, "a") as out:
        with ThreadPoolExecutor(max_workers=args.parallel) as ex:
            for fut in as_completed([ex.submit(work, r) for r in todo]):
                v = fut.result()
                if v:
                    out.write(json.dumps(v, ensure_ascii=False) + "\n")
                    n += 1
                    if n % 100 == 0:
                        out.flush()
                        print(f"  {n}/{len(todo)} ({time.strftime('%H:%M:%S')})",
                              flush=True)
    print(f"CROSS-JUDGE DONE: {n} new verdicts", flush=True)
    (HERE / "outputs" / "CROSS_JUDGE_DONE").touch()


if __name__ == "__main__":
    main()
