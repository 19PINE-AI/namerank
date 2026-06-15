"""
Re-judge stratified sample with Claude Opus 4.6 and GPT-5.5.

Reads sample_records.json. Skips records where is_refusal=True (scored 0/0 by convention).
Writes rejudge_results.csv.
"""

import os
import sys
import json
import time
import re
import csv
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from anthropic import Anthropic
from openai import OpenAI

ROOT = "/home/ubuntu/namerank/experiments/t2_10_cross_judge"
PROMPT_TMPL = open("/home/ubuntu/namerank/data/inputs/judge_prompt.txt").read()
GOLD = json.load(open("/home/ubuntu/namerank/data/inputs/gold_answers.json"))
RECS = json.load(open(os.path.join(ROOT, "sample_records.json")))

CLAUDE_MODEL = "claude-opus-4-5"   # Anthropic API canonical ID for Claude Opus 4.6
GPT_MODEL = "openai/gpt-5.5"       # OpenRouter

MAX_RESPONSE_CHARS = 8000
MAX_WORKERS_PER_PROVIDER = 8

anthropic_client = Anthropic()
openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)


def build_prompt(rec):
    gold = GOLD[rec["entity_id"]]
    return PROMPT_TMPL.format(
        name=rec["entity_name"],
        gold_answer=gold,
        response=(rec["response"] or "")[:MAX_RESPONSE_CHARS],
    )


JSON_RE = re.compile(r"\{[^{}]*\"coverage\"[^{}]*\}", re.DOTALL)


def parse_judge_json(text):
    if not text:
        return None
    s = text.strip()
    # strip fences
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    try:
        obj = json.loads(s)
    except Exception:
        m = re.search(r"\{.*\}", s, re.DOTALL)
        if not m:
            return None
        try:
            obj = json.loads(m.group(0))
        except Exception:
            return None
    try:
        cov = float(obj.get("coverage", 0.0))
        acc = float(obj.get("accuracy", 0.0))
        rat = str(obj.get("rationale", ""))[:500]
    except Exception:
        return None
    return {"coverage": max(0.0, min(1.0, cov)),
            "accuracy": max(0.0, min(1.0, acc)),
            "rationale": rat}


def call_claude(prompt, retries=4):
    backoff = 2.0
    for attempt in range(retries):
        try:
            msg = anthropic_client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=400,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text
        except Exception as e:
            msg_s = str(e)
            if attempt == retries - 1:
                raise
            # backoff on rate / overload
            sleep = backoff * (2 ** attempt) + random.uniform(0, 1.0)
            time.sleep(sleep)
    return None


def call_gpt(prompt, retries=4):
    backoff = 2.0
    for attempt in range(retries):
        try:
            resp = openrouter_client.chat.completions.create(
                model=GPT_MODEL,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": prompt + "\n\nReturn ONLY the JSON object."}],
            )
            return resp.choices[0].message.content
        except Exception:
            if attempt == retries - 1:
                raise
            sleep = backoff * (2 ** attempt) + random.uniform(0, 1.0)
            time.sleep(sleep)
    return None


def judge_one(rec, judge):
    if rec["is_refusal"]:
        return {"coverage": 0.0, "accuracy": 0.0, "rationale": "refusal"}
    prompt = build_prompt(rec)
    try:
        if judge == "claude":
            text = call_claude(prompt)
        else:
            text = call_gpt(prompt)
    except Exception as e:
        return {"coverage": None, "accuracy": None, "rationale": f"ERROR: {e}"[:300]}
    parsed = parse_judge_json(text)
    if not parsed:
        return {"coverage": None, "accuracy": None, "rationale": f"PARSE_FAIL: {(text or '')[:200]}"}
    return parsed


def run_judge(judge):
    out = {}
    progress_lock = threading.Lock()
    done = [0]
    t0 = time.time()

    def task(idx, rec):
        return idx, judge_one(rec, judge)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS_PER_PROVIDER) as ex:
        futures = [ex.submit(task, i, r) for i, r in enumerate(RECS)]
        for fut in as_completed(futures):
            idx, result = fut.result()
            out[idx] = result
            with progress_lock:
                done[0] += 1
                if done[0] % 25 == 0 or done[0] == len(RECS):
                    elapsed = time.time() - t0
                    rate = done[0] / elapsed if elapsed else 0
                    print(f"[{judge}] {done[0]}/{len(RECS)} done, {rate:.2f}/s", flush=True)
    return out


def main():
    judge = sys.argv[1] if len(sys.argv) > 1 else "both"
    if judge in ("claude", "both"):
        print("Running Claude judge…", flush=True)
        claude_out = run_judge("claude")
        with open(os.path.join(ROOT, "claude_judge.json"), "w") as f:
            json.dump(claude_out, f)
        print("Claude saved.", flush=True)
    if judge in ("gpt", "both"):
        print("Running GPT-5 judge…", flush=True)
        gpt_out = run_judge("gpt")
        with open(os.path.join(ROOT, "gpt_judge.json"), "w") as f:
            json.dump(gpt_out, f)
        print("GPT saved.", flush=True)


if __name__ == "__main__":
    main()
