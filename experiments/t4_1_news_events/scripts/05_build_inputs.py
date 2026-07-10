"""Build the probe inputs: stratified event cohort + contexts + gold answers.

Stratification: log10(total_views) salience band x region group, so the cohort
spans ~4 orders of magnitude of measured attention and is not dominated by
US/UK events. Contexts are generated deterministically from (category, month,
year, location) — never from event content — mirroring the main run's
role/affiliation/field rule.

Outputs (inputs/):
  event_entities.json   probe entities: id, name, context, cohort, metadata
  event_gold.json       id -> gold answer (Wikipedia intro, 100-200 words)
  event_metadata.csv    per-event salience + classification, for analysis
"""
from __future__ import annotations

import csv
import json
import math
import random
import re
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "outputs"
INP = HERE / "inputs"
INP.mkdir(exist_ok=True)
UA = {"User-Agent": "NameRankResearch/1.0 (bojieli@gmail.com) requests"}
API = "https://en.wikipedia.org/w/api.php"

MONTH_NAMES = ["", "January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]

CATEGORY_PHRASE = {
    "natural_disaster": "a natural disaster that occurred",
    "accident_disaster": "an accident or disaster that occurred",
    "conflict_terrorism": "an armed conflict, attack, or military event that occurred",
    "politics_elections": "a political event that took place",
    "civil_unrest": "an episode of protests or civil unrest that began",
    "crime_legal": "a criminal case or legal proceeding that came to public attention",
    "sports": "a sporting event that took place",
    "entertainment_culture": "a cultural or entertainment event that took place",
    "science_space": "a science or spaceflight event that occurred",
    "business_tech": "a business or technology event that occurred",
    "health": "a public-health event that began",
    "royalty_ceremony": "a ceremonial or royal event that took place",
    "other": "a news event that occurred",
}

REGION_GROUP = {
    "North America": "Anglo-America & Oceania",
    "Oceania": "Anglo-America & Oceania",
    "Western Europe": "Western Europe",
    "Eastern Europe & Russia": "Eastern Europe & Russia",
    "Latin America": "Latin America",
    "Middle East & North Africa": "Middle East & Africa",
    "Sub-Saharan Africa": "Middle East & Africa",
    "South Asia": "South & Southeast Asia",
    "Southeast Asia": "South & Southeast Asia",
    "Central Asia & Caucasus": "South & Southeast Asia",
    "East Asia": "East Asia",
    "Global": "Global",
}

TARGET_N = 260
# per (band, group) cap keeps NA/WE from dominating; bands: log10 total views
BAND_EDGES = [0, 4.0, 5.0, 6.0, 7.0, 99]
CAP_PER_CELL = 14


def salience_band(total: int) -> int:
    lt = math.log10(max(total, 1))
    for b in range(len(BAND_EDGES) - 1):
        if BAND_EDGES[b] <= lt < BAND_EDGES[b + 1]:
            return b
    return 0


def slugify(t: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", t.lower()).strip("_")
    return s[:60]


def fetch_intro(title: str) -> str | None:
    for attempt in range(3):
        try:
            r = requests.get(API, params={
                "action": "query", "prop": "extracts", "exintro": "1",
                "explaintext": "1", "titles": title, "format": "json",
                "formatversion": "2", "redirects": "1"}, headers=UA, timeout=30)
            r.raise_for_status()
            pages = r.json()["query"]["pages"]
            return pages[0].get("extract")
        except Exception:  # noqa: BLE001
            time.sleep(1 + attempt)
    return None


def truncate_words(text: str, lo=100, hi=200) -> str:
    text = " ".join(text.split())
    words = text.split()
    if len(words) <= hi:
        return text
    # cut at last sentence end before `hi` words
    cut = " ".join(words[:hi])
    m = list(re.finditer(r"[.!?](?=\s|$)", cut))
    if m and len(cut[:m[-1].end()].split()) >= lo:
        return cut[:m[-1].end()]
    return cut + "..."


def main() -> None:
    classified = {c["target"]: c for c in json.loads((OUT / "classified.json").read_text())}
    summaries = {s["target"]: s for s in json.loads((OUT / "summaries.json").read_text()) if s}
    salience = {s["target"]: s for s in json.loads((OUT / "salience.json").read_text())}

    pool = []
    for t, c in classified.items():
        if not (c.get("is_discrete_event") and c.get("start_year") in (2021, 2022, 2023)
                and 1 <= c.get("start_month", 0) <= 12):
            continue
        s, v = summaries.get(t), salience.get(t)
        if not s or not v or s.get("type") != "standard":
            continue
        if v["total_views"] < 1000 or v["n_days"] < 200:
            continue  # too obscure to have a meaningful attention record
        extract = s.get("extract") or ""
        if len(extract.split()) < 40:
            continue
        pool.append({**c, **{k: v[k] for k in
                             ("peak_views", "total_views", "eff_duration",
                              "days_above_10", "tail_daily", "peak_date", "article")},
                     "title": s["title"], "extract": extract})

    print(f"Pool after filters: {len(pool)}")

    # stratified sample: cap each (salience band x region group) cell
    random.seed(42)
    random.shuffle(pool)
    cells: dict[tuple, list] = {}
    for e in pool:
        key = (salience_band(e["total_views"]),
               REGION_GROUP.get(e["region"], "Global"))
        cells.setdefault(key, []).append(e)

    sample = []
    for key, members in sorted(cells.items()):
        # prefer category diversity inside a cell
        members.sort(key=lambda e: e["category"])
        take = members[:CAP_PER_CELL]
        # interleave categories: simple round-robin by category
        bycat: dict[str, list] = {}
        for m in members:
            bycat.setdefault(m["category"], []).append(m)
        rr, order = [], sorted(bycat)
        while len(rr) < min(CAP_PER_CELL, len(members)):
            for cat in order:
                if bycat[cat]:
                    rr.append(bycat[cat].pop(0))
                if len(rr) >= min(CAP_PER_CELL, len(members)):
                    break
        sample.extend(rr)
        print(f"  band{key[0]} {key[1]:28s}: {len(members):4d} -> {len(rr)}")

    if len(sample) > TARGET_N:
        random.shuffle(sample)
        sample = sample[:TARGET_N]
    print(f"Sampled cohort: {len(sample)}")

    entities, gold, meta_rows = [], {}, []
    seen_ids = set()
    for e in sorted(sample, key=lambda x: -x["total_views"]):
        eid = "event_" + slugify(e["title"])
        if eid in seen_ids:
            continue
        seen_ids.add(eid)
        month = MONTH_NAMES[e["start_month"]]
        loc = e["location_phrase"].strip()
        if loc and not loc[0].islower():
            loc = loc[0].lower() + loc[1:]
        phrase = CATEGORY_PHRASE.get(e["category"], CATEGORY_PHRASE["other"])
        context = f"{phrase} {loc} in {month} {e['start_year']}"
        context = re.sub(r"\s+", " ", context).strip()

        intro = fetch_intro(e["title"]) or e["extract"]
        g = truncate_words(intro)
        if len(g.split()) < 40:
            continue
        gold[eid] = g
        entities.append({
            "id": eid, "name": e["title"], "context": context,
            "cohort": f"news_{e['category']}",
            "credential_year": e["start_year"], "credential_country": e["country"],
        })
        meta_rows.append({
            "id": eid, "title": e["title"], "article": e["article"],
            "start_year": e["start_year"], "start_month": e["start_month"],
            "country": e["country"], "region": e["region"],
            "region_group": REGION_GROUP.get(e["region"], "Global"),
            "category": e["category"],
            "peak_views": e["peak_views"], "total_views": e["total_views"],
            "eff_duration": e["eff_duration"], "days_above_10": e["days_above_10"],
            "tail_daily": e["tail_daily"], "peak_date": e["peak_date"],
            "gold_words": len(gold[eid].split()),
        })
        time.sleep(0.05)

    (INP / "event_entities.json").write_text(
        json.dumps(entities, indent=1, ensure_ascii=False))
    (INP / "event_gold.json").write_text(
        json.dumps(gold, indent=1, ensure_ascii=False))
    with open(INP / "event_metadata.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(meta_rows[0].keys()))
        w.writeheader()
        w.writerows(meta_rows)
    print(f"Wrote {len(entities)} entities -> {INP}")


if __name__ == "__main__":
    main()
