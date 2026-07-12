"""T5.4 pairwise self-report runner.

Presents each pair from inputs/pairs.json to the three self-report models
(same OpenRouter ids and reasoning settings as the main run) and records the
parsed verdict: A / B / EQUAL / NEITHER / PARSE_ERROR / ERROR.

Resumable on (pair_id, model_id); checkpoints every 200 completions.

Required env: OPENROUTER_API_KEY
Usage: python run_pairwise.py [--parallel 12] [--max-pairs N] [--models m1,m2]
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

from openai import OpenAI

HERE = Path(__file__).parent
REPO = HERE.parent.parent

VERDICTS = ("A", "B", "EQUAL", "NEITHER")


def load_models() -> list[dict]:
    wanted = {"gpt-5.5-think", "claude-opus-4.6-think", "gemini-3.1-pro"}
    ms = json.loads((REPO / "data/inputs/model_set.json").read_text())
    out = [m for m in ms if m["id"] in wanted]
    assert len(out) == len(wanted), [m["id"] for m in out]
    return out


def parse_verdict(text: str) -> str:
    if not text:
        return "PARSE_ERROR"
    t = text.strip()
    # strip markdown emphasis and trailing punctuation from the first line
    first = re.sub(r"[*_`#]", "", t.splitlines()[0]).strip().rstrip(".:,;!").upper()
    if first in VERDICTS:
        return first
    m = re.match(r"^(A|B|EQUAL|NEITHER)\b", first)
    if m:
        return m.group(1)
    # answer marker anywhere in the text
    m = re.search(r"(?:ANSWER|VERDICT)\s*[:\-]?\s*(A|B|EQUAL|NEITHER)\b",
                  t.upper())
    if m:
        return m.group(1)
    # unambiguous keyword fallback (EQUAL/NEITHER are safe; bare A/B are not)
    words = set(re.findall(r"\b(EQUAL|NEITHER)\b", t.upper()))
    if len(words) == 1:
        return words.pop()
    return "PARSE_ERROR"


def call_model(client: OpenAI, model: dict, prompt: str,
               timeout: int = 180, max_retries: int = 5) -> str:
    extra = {}
    if model.get("thinking"):
        extra["reasoning"] = {"effort": "medium"}
    if model.get("provider_only"):
        extra["provider"] = {"only": model["provider_only"]}
    last_err = None
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=model["openrouter_id"],
                messages=[{"role": "user", "content": prompt}],
                extra_body=extra,
                timeout=timeout,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:  # noqa: BLE001
            last_err = e
            es = str(e).lower()
            transient = any(s in es for s in ("429", "rate limit", "rate-limit",
                                              "timeout", "503", "502", "504",
                                              "overloaded"))
            if not transient or attempt == max_retries - 1:
                return f"[ERROR: {type(e).__name__}: {e}]"
            time.sleep((2 ** (attempt + 1)) + random.uniform(0, 1))
    return f"[ERROR: {type(last_err).__name__}: {last_err}]"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parallel", type=int, default=12)
    ap.add_argument("--max-pairs", type=int, default=None)
    ap.add_argument("--models", default=None,
                    help="comma-separated model ids (default: all three)")
    args = ap.parse_args()

    models = load_models()
    if args.models:
        keep = set(args.models.split(","))
        models = [m for m in models if m["id"] in keep]
    entities = {e["id"]: e for e in json.loads(
        (HERE / "inputs/entities.json").read_text())}
    pairs = json.loads((HERE / "inputs/pairs.json").read_text())
    if args.max_pairs:
        pairs = pairs[: args.max_pairs]
    tpl = (HERE / "inputs/pairwise_prompt.txt").read_text()

    results_path = HERE / "outputs/pairwise_results.json"
    results: list[dict] = []
    if results_path.exists():
        results = json.loads(results_path.read_text())
    done = {(r["pair_id"], r["model_id"]) for r in results
            if r["verdict"] != "ERROR"}
    results = [r for r in results if (r["pair_id"], r["model_id"]) in done]

    todo = [(p, m) for m in models for p in pairs
            if (p["pair_id"], m["id"]) not in done]
    print(f"{len(pairs)} pairs x {len(models)} models; "
          f"{len(done)} done, {len(todo)} pending")
    if not todo:
        return

    client = OpenAI(base_url="https://openrouter.ai/api/v1",
                    api_key=os.environ["OPENROUTER_API_KEY"])
    lock = Lock()

    def process(pair: dict, model: dict) -> dict:
        ea, eb = entities[pair["a"]], entities[pair["b"]]
        prompt = tpl.format(name_a=ea["name"], context_a=ea["context"],
                            name_b=eb["name"], context_b=eb["context"])
        raw = call_model(client, model, prompt)
        verdict = "ERROR" if raw.startswith("[ERROR") else parse_verdict(raw)
        return {"pair_id": pair["pair_id"], "model_id": model["id"],
                "a": pair["a"], "b": pair["b"], "stratum": pair["stratum"],
                "rev_of": pair["rev_of"], "verdict": verdict,
                "raw": raw[:400], "ts": time.time()}

    with ThreadPoolExecutor(max_workers=args.parallel) as ex:
        futs = [ex.submit(process, p, m) for p, m in todo]
        for i, fut in enumerate(as_completed(futs)):
            rec = fut.result()
            with lock:
                results.append(rec)
                if (i + 1) % 200 == 0:
                    results_path.write_text(
                        json.dumps(results, ensure_ascii=False))
                    n_err = sum(r["verdict"] in ("ERROR", "PARSE_ERROR")
                                for r in results)
                    print(f"  {i+1}/{len(todo)} (errors so far: {n_err})",
                          flush=True)

    results_path.write_text(json.dumps(results, ensure_ascii=False))
    from collections import Counter
    print("verdicts:", Counter(r["verdict"] for r in results))
    print(f"done -> {results_path}")


if __name__ == "__main__":
    main()
