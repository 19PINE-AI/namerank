"""NameRank probe runner.

For each (entity, model) pair on the panel, sends the open-ended probe to the
probed model via OpenRouter, then sends the (gold, response) pair to the
Gemini-3-Flash-Preview judge via the direct Google API for cov/acc scoring.
Also stores BAAI/bge-large-en-v1.5 cosine similarity as a sanity signal.

Resumable: existing results in <outputs-dir>/pilot_results.json are honored;
only missing (entity, model) pairs are re-issued.

Required env:
  OPENROUTER_API_KEY  — for probed-model calls
  GEMINI_API_KEY      — for the judge

Usage:
  python run_probe.py                          # full English run from data/inputs
  python run_probe.py --lang zh                # Chinese sub-run probe
  python run_probe.py --max-entities 10 --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from _paths import INPUTS, RAW, REPO

try:
    from openai import OpenAI
except ImportError:
    sys.exit("Install: pip install openai")
try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    sys.exit("Install: pip install google-genai")
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
except ImportError:
    sys.exit("Install: pip install sentence-transformers numpy")


REFUSAL_PATTERNS = [
    "i don't know", "i'm not sure", "i am not sure", "i don't recognize",
    "i'm not familiar", "not familiar with", "no information",
    "unknown", "未知", "我不知道", "我不认识", "不熟悉", "没有相关信息",
    "i cannot find", "cannot identify", "i have no information",
]


def is_refusal(text: str) -> bool:
    if not text or len(text.strip()) < 5:
        return True
    t = text.strip().lower()
    if t in ("unknown", "unknown.", "未知", "未知。"):
        return True
    if len(t) < 80:
        for pat in REFUSAL_PATTERNS:
            if pat in t:
                return True
    return False


def call_probed_model(client, model_id, probe, thinking=False, provider_only=None,
                      timeout=120, max_retries=5):
    extra = {}
    if thinking:
        extra["reasoning"] = {"effort": "medium"}
    if provider_only:
        extra["provider"] = {"only": provider_only}
    last_err = None
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": probe}],
                extra_body=extra,
                timeout=timeout,
            )
            content = resp.choices[0].message.content or ""
            words = content.split()
            if len(words) > 200:
                content = " ".join(words[:200])
            return content
        except Exception as e:  # noqa: BLE001
            last_err = e
            es = str(e).lower()
            transient = any(s in es for s in ("429", "rate limit", "rate-limit",
                                              "timeout", "503", "502", "504"))
            if not transient or attempt == max_retries - 1:
                return f"[ERROR: {type(e).__name__}: {e}]"
            time.sleep((2 ** (attempt + 1)) + random.uniform(0, 1))
    return f"[ERROR: {type(last_err).__name__}: {last_err}]"


JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "coverage": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "accuracy": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "rationale": {"type": "string"},
    },
    "required": ["coverage", "accuracy", "rationale"],
}
JUDGE_SYSTEM = (
    "You are an objective grader scoring a language-model response against a "
    "gold-answer reference paragraph about a named entity. You do not bring "
    "outside knowledge; you grade only what the response says against what the "
    "gold answer says."
)


def call_judge(client, judge_prompt: str) -> dict:
    try:
        resp = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=judge_prompt,
            config=genai_types.GenerateContentConfig(
                system_instruction=JUDGE_SYSTEM,
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=JUDGE_SCHEMA,
            ),
        )
        p = json.loads(resp.text)
        return {"coverage": float(p["coverage"]),
                "accuracy": float(p["accuracy"]),
                "rationale": str(p["rationale"])}
    except Exception as e:  # noqa: BLE001
        return {"coverage": 0.0, "accuracy": 0.0,
                "rationale": f"[JUDGE-ERROR: {type(e).__name__}: {e}]"}


def cosine(a, b) -> float:
    na = np.linalg.norm(a); nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def main() -> None:
    p = argparse.ArgumentParser(description="NameRank probe runner")
    p.add_argument("--lang", choices=["en", "zh"], default="en")
    p.add_argument("--inputs-dir", default=str(INPUTS))
    p.add_argument("--outputs-dir", default=str(REPO / "outputs"))
    p.add_argument("--max-entities", type=int, default=None)
    p.add_argument("--max-models", type=int, default=None)
    p.add_argument("--parallel", type=int, default=8)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    inputs = Path(args.inputs_dir)
    outputs = Path(args.outputs_dir)

    models = json.loads((inputs / "model_set.json").read_text())
    entities = json.loads((inputs / "pilot_entities.json").read_text())
    gold = json.loads((inputs / "gold_answers.json").read_text())
    probe_tpl = (inputs / f"probe_template_{args.lang}.txt").read_text()
    judge_tpl = (inputs / "judge_prompt.txt").read_text()

    if args.max_entities:
        entities = entities[: args.max_entities]
    if args.max_models:
        models = models[: args.max_models]

    n_pairs = len(entities) * len(models)
    print(f"Plan: {len(entities)} entities x {len(models)} models = {n_pairs:,} probes")
    if args.dry_run:
        return

    or_client = OpenAI(base_url="https://openrouter.ai/api/v1",
                       api_key=os.environ["OPENROUTER_API_KEY"])
    gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    encoder = SentenceTransformer("BAAI/bge-large-en-v1.5")
    print("Encoding gold answers...")
    gold_emb = {eid: encoder.encode(t, convert_to_numpy=True) for eid, t in gold.items()}

    outputs.mkdir(parents=True, exist_ok=True)
    results_path = outputs / f"pilot_results_{args.lang}.json"
    completed: set[tuple[str, str]] = set()
    results: list[dict] = []
    if results_path.exists():
        results = json.loads(results_path.read_text())
        completed = {(r["entity_id"], r["model_id"]) for r in results}
        print(f"Resuming with {len(completed):,} pairs already done")

    def process(entity, model):
        if (entity["id"], model["id"]) in completed:
            return None
        probe = probe_tpl.format(name=entity["name"], context=entity["context"])
        response = call_probed_model(or_client, model["openrouter_id"], probe,
                                     thinking=model.get("thinking", False),
                                     provider_only=model.get("provider_only"))
        refused = is_refusal(response)
        if refused:
            score = {"coverage": 0.0, "accuracy": 0.0, "rationale": "refusal"}
        else:
            judge_input = judge_tpl.format(name=entity["name"],
                                           gold_answer=gold[entity["id"]],
                                           response=response)
            score = call_judge(gemini_client, judge_input)
        sim = cosine(encoder.encode(response, convert_to_numpy=True),
                     gold_emb[entity["id"]])
        return {
            "entity_id": entity["id"], "entity_name": entity["name"],
            "model_id": model["id"], "response": response,
            "is_refusal": refused,
            "coverage": score["coverage"], "accuracy": score["accuracy"],
            "score": score["coverage"] * score["accuracy"],
            "rationale": score["rationale"],
            "embedding_sim": sim, "ts": time.time(),
        }

    pairs = [(e, m) for e in entities for m in models]
    pending = [(e, m) for e, m in pairs if (e["id"], m["id"]) not in completed]
    print(f"Dispatching {len(pending):,} pending probes with {args.parallel} workers")

    with ThreadPoolExecutor(max_workers=args.parallel) as ex:
        futs = {ex.submit(process, e, m): (e["id"], m["id"]) for e, m in pending}
        for i, fut in enumerate(as_completed(futs)):
            try:
                rec = fut.result()
            except Exception as exc:  # noqa: BLE001
                print(f"  [ERROR] {futs[fut]}: {exc}")
                continue
            if rec is None:
                continue
            results.append(rec)
            if (i + 1) % 200 == 0:
                results_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
                print(f"  checkpoint {i+1}/{len(pending)}")

    results_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))

    # Flat record CSV → data/raw/pilot_summary_<lang>.csv
    RAW.mkdir(parents=True, exist_ok=True)
    csv_path = RAW / f"pilot_summary_{args.lang}.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("entity_id,entity_name,model_id,is_refusal,coverage,accuracy,score,embedding_sim\n")
        for r in results:
            name = r["entity_name"].replace('"', '""')
            f.write(f'{r["entity_id"]},"{name}",{r["model_id"]},'
                    f'{int(r["is_refusal"])},{r["coverage"]:.3f},{r["accuracy"]:.3f},'
                    f'{r["score"]:.3f},{r["embedding_sim"]:.3f}\n')
    print(f"Done. {len(results):,} records -> {results_path}, {csv_path}")


if __name__ == "__main__":
    main()
