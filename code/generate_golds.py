"""Generate canonical, web-grounded gold answers with Gemini + Google Search.

For each entity we give Gemini the probe NAME and the disambiguation CONTEXT
(identity pin only) and have it search the web and write ONE factual profile
of who the entity really is -- going beyond the context to the entity's actual
notable identity, or honestly thin when little is verifiable. A hardened
namesake guard (validated on obscure common-name medalists) forces the model
to include beyond-context facts only when a source ties them to THIS
individual via a matching identifier (school, competition record, year), so
common-name namesakes are not merged in.

This replaces the boilerplate/context-echo golds that credited context echo.
Responses do not depend on the gold, so downstream studies re-judge stored
responses against these golds without re-probing.

Usage:
  python generate_golds.py --entities <entities.json> --out <golds.json> \
      [--parallel 8] [--model gemini-3-flash-preview]

`entities.json` is a list of {id, name, context}. Output is
{entity_id: {"gold": text, "n_sources": int, "n_words": int}} plus a sidecar
`<out>.meta.json` with per-entity provenance. Resumable.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from google import genai
from google.genai import types

INSTR = """You write reference profiles for a recognition benchmark. You are given an entity NAME and a DISAMBIGUATION (a short description that identifies WHICH entity is meant -- its purpose is to pin identity against namesakes).

Search the web, then write ONE factual profile of this specific entity.

NAMESAKE GUARD (most important rule): Chinese and other common names are shared by many people. Include a fact about the entity's education, career, or later life ONLY IF a source explicitly ties that fact to THIS SAME individual through a matching identifier -- the same school, the same competition/olympiad record, a consistent graduation year, or an explicit statement. A person who merely shares the name but has no sourced connection to the DISAMBIGUATION is a DIFFERENT person; exclude them entirely.

LENGTH DISCIPLINE (important for fair measurement): Write AT MOST {maxwords} words, and select the entity's MOST DISTINCTIVE, IDENTIFYING facts to fill that budget -- the specific named achievements, works, roles, or affiliations a knowledgeable person would name first. Do NOT try to be exhaustive: a famous person is summarized to their top few facts, not given a longer profile than an obscure one. Prefer specific named facts over generic description. Do NOT restate the disambiguation to fill space.

RULES:
1. State only facts verifiable from search results tied to THIS individual. Never invent, guess, or speculate.
2. Prioritize source-linked facts that go BEYOND the disambiguation (named works, roles, companies, achievements, affiliations) -- these are what the benchmark scores.
3. If you cannot verify any beyond-disambiguation facts with explicit source-linkage, write ONLY the facts the disambiguation itself guarantees. A one-sentence profile is the CORRECT, honest answer for a genuinely low-profile entity -- do not pad, do not generalize about their cohort, do not invent a plausible career.
4. If you cannot confidently distinguish this entity from namesakes, restrict to what the disambiguation guarantees.
5. Neutral third person, no hedging ("appears to be", "likely").

Output only the profile text."""


def make_gold(client, model, name, context, maxwords):
    resp = client.models.generate_content(
        model=model,
        contents=f"NAME: {name}\nDISAMBIGUATION: {context}\n\nWrite the profile.",
        config=types.GenerateContentConfig(
            system_instruction=INSTR.format(maxwords=maxwords),
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.0,
        ),
    )
    text = (resp.text or "").strip()
    gm = resp.candidates[0].grounding_metadata
    n_src = len(gm.grounding_chunks) if gm and gm.grounding_chunks else 0
    n_q = len(gm.web_search_queries) if gm and gm.web_search_queries else 0
    return text, n_src, n_q


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--entities", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--parallel", type=int, default=8)
    p.add_argument("--model", default="gemini-3-flash-preview")
    p.add_argument("--maxwords", type=int, default=55,
                   help="length-normalization cap; golds target a common band "
                        "so fame is not penalized by coverage-denominator size")
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args()

    entities = json.loads(Path(args.entities).read_text())
    if args.limit:
        entities = entities[: args.limit]
    out_path = Path(args.out)
    meta_path = out_path.with_suffix(".meta.json")

    golds = json.loads(out_path.read_text()) if out_path.exists() else {}
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    done = set(golds)
    todo = [e for e in entities if e["id"] not in done]
    print(f"{len(entities)} entities, {len(done)} done, {len(todo)} to generate")

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def work(e):
        for attempt in range(4):
            try:
                text, n_src, n_q = make_gold(client, args.model, e["name"],
                                             e["context"], args.maxwords)
                if not text:
                    raise ValueError("empty gold")
                return e["id"], {"gold": text, "n_sources": n_src,
                                 "n_words": len(text.split())}, \
                    {"name": e["name"], "context": e["context"],
                     "n_sources": n_src, "n_queries": n_q}
            except Exception as exc:  # noqa: BLE001
                if attempt == 3:
                    return e["id"], None, {"error": f"{type(exc).__name__}: {exc}"}
                time.sleep(2 * (attempt + 1))

    n = 0
    with ThreadPoolExecutor(max_workers=args.parallel) as ex:
        futs = {ex.submit(work, e): e["id"] for e in todo}
        for fut in as_completed(futs):
            eid, g, m = fut.result()
            if g:
                golds[eid] = g
            meta[eid] = m
            n += 1
            if n % 20 == 0:
                out_path.write_text(json.dumps(golds, indent=1, ensure_ascii=False))
                meta_path.write_text(json.dumps(meta, indent=1, ensure_ascii=False))
                print(f"  {n}/{len(todo)} ({time.strftime('%H:%M:%S')})", flush=True)

    out_path.write_text(json.dumps(golds, indent=1, ensure_ascii=False))
    meta_path.write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    thin = sum(1 for g in golds.values() if g["n_words"] < 45)
    zero = sum(1 for m in meta.values() if m.get("n_sources") == 0)
    print(f"done: {len(golds)} golds ({thin} thin <45w; {zero} with 0 sources), "
          f"-> {out_path}")


if __name__ == "__main__":
    main()
