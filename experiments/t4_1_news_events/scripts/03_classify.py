"""Classify candidate articles: discrete news event? date, country, region, category.

Uses Gemini 3 Flash Preview (same family as the study judge) with a strict
response schema, batched 20 articles per call. Classification uses only the
article title, short description, and first-paragraph extract.
"""
from __future__ import annotations

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from google import genai
from google.genai import types as genai_types

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "outputs"

REGIONS = ["North America", "Latin America", "Western Europe",
           "Eastern Europe & Russia", "Middle East & North Africa",
           "Sub-Saharan Africa", "South Asia", "East Asia",
           "Southeast Asia", "Central Asia & Caucasus", "Oceania", "Global"]
CATEGORIES = ["natural_disaster", "accident_disaster", "conflict_terrorism",
              "politics_elections", "civil_unrest", "crime_legal", "sports",
              "entertainment_culture", "science_space", "business_tech",
              "health", "royalty_ceremony", "other"]

SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "idx": {"type": "integer"},
            "is_discrete_event": {"type": "boolean"},
            "start_year": {"type": "integer"},
            "start_month": {"type": "integer"},
            "country": {"type": "string"},
            "region": {"type": "string", "enum": REGIONS},
            "category": {"type": "string", "enum": CATEGORIES},
            "location_phrase": {"type": "string"},
        },
        "required": ["idx", "is_discrete_event", "start_year", "start_month",
                     "country", "region", "category", "location_phrase"],
    },
}

PROMPT = """You are classifying Wikipedia articles for a research cohort of NEWS EVENTS.

A "discrete event" is a specific occurrence (or tightly bounded series, e.g. an
election, a trial, a storm, a tournament, an accident, a protest wave) that
BEGAN at an identifiable date. NOT discrete events: people, organizations,
places, products, laws, ongoing multi-year topics (e.g. "COVID-19 pandemic in
X" country overviews), lists, seasons of TV shows, annual article series.

For each article below, output one object:
- idx: the article's number as given
- is_discrete_event: per the definition above
- start_year / start_month: when the event began (the event itself, not the
  article). If not a discrete event or outside 2020-2024, put 0 for both.
- country: primary country affected/hosting ("International" if none).
- region: one of the given enums; "Global" only for genuinely worldwide events.
- category: one of the given enums.
- location_phrase: a short neutral place phrase for a disambiguation clause,
  e.g. "in Turkey and Syria", "off the coast of the Philippines", "in the
  United Kingdom", "in Kazan, Russia". No facts beyond geography.

ARTICLES:
{items}
"""


def main() -> None:
    summaries = json.loads((OUT / "summaries.json").read_text())
    arts = [s for s in summaries if s and s.get("type") == "standard"
            and s.get("extract") and len(s["extract"].split()) >= 25]
    print(f"{len(arts)} articles to classify")

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    path = OUT / "classified.json"
    done: dict[str, dict] = {}
    if path.exists():
        done = {d["target"]: d for d in json.loads(path.read_text())}
    todo = [a for a in arts if a["target"] not in done]
    print(f"{len(todo)} remaining ({len(done)} cached)")

    B = 20
    batches = [todo[bi:bi + B] for bi in range(0, len(todo), B)]
    lock = threading.Lock()

    cfg = genai_types.GenerateContentConfig(
        temperature=0.0,
        response_mime_type="application/json",
        response_schema=SCHEMA,
        thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
    )

    def classify_batch(batch):
        items = "\n\n".join(
            f"[{i}] TITLE: {a['title']}\nDESC: {a.get('description') or '-'}\n"
            f"EXTRACT: {' '.join((a['extract'] or '').split()[:120])}"
            for i, a in enumerate(batch))
        for attempt in range(4):
            try:
                resp = client.models.generate_content(
                    model="gemini-3-flash-preview",
                    contents=PROMPT.format(items=items),
                    config=cfg,
                )
                parsed = json.loads(resp.text)
                with lock:
                    for p in parsed:
                        i = p.pop("idx")
                        if 0 <= i < len(batch):
                            done[batch[i]["target"]] = {
                                "target": batch[i]["target"], **p}
                return True
            except Exception as e:  # noqa: BLE001
                print(f"  [retry {attempt}] {e}", flush=True)
                time.sleep(5 * (attempt + 1))
        return False

    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(classify_batch, b) for b in batches]
        for i, fut in enumerate(as_completed(futs)):
            fut.result()
            if (i + 1) % 10 == 0:
                with lock:
                    path.write_text(json.dumps(list(done.values()),
                                               ensure_ascii=False))
                print(f"  {i+1}/{len(batches)} batches, {len(done)} classified",
                      flush=True)

    path.write_text(json.dumps(list(done.values()), indent=0, ensure_ascii=False))
    n_ev = sum(1 for d in done.values()
               if d.get("is_discrete_event") and d.get("start_year") in (2021, 2022, 2023))
    print(f"Done: {len(done)} classified, {n_ev} discrete 2021-2023 events")


if __name__ == "__main__":
    main()
