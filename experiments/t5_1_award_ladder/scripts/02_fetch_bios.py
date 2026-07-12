"""Fetch gold-answer source material and bibliometrics for award laureates.

For each candidate: (a) en-Wikipedia REST summary (intro extract) as the gold
source, and (b) a best-effort OpenAlex author match (h-index, citations) for
the marginal-predictor regression.  Match confidence is recorded; downstream
regressions filter on it.

Writes outputs/bios.json.
"""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import quote, unquote

import requests

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "outputs"
UA = {"User-Agent": "NameRankResearch/1.0 (bojieli@gmail.com) requests"}


def wiki_summary(title: str) -> dict | None:
    # Full lead section (all intro paragraphs), not the REST one-paragraph
    # summary: matches the main run's 100-200-word Wikipedia-intro recipe.
    for attempt in range(3):
        try:
            r = requests.get("https://en.wikipedia.org/w/api.php",
                             params={"action": "query", "prop": "extracts",
                                     "exintro": 1, "explaintext": 1,
                                     "redirects": 1, "format": "json",
                                     "titles": title},
                             headers=UA, timeout=20)
            r.raise_for_status()
            pages = r.json()["query"]["pages"]
            page = next(iter(pages.values()))
            if "missing" in page or not page.get("extract"):
                return None
            return {"title": page.get("title"),
                    "description": None,
                    "extract": page["extract"].strip()}
        except Exception:  # noqa: BLE001
            time.sleep(1 + attempt)
    return None


def openalex_author(name: str) -> dict | None:
    for attempt in range(3):
        try:
            r = requests.get("https://api.openalex.org/authors",
                             params={"search": name, "per-page": 1,
                                     "mailto": "bojieli@gmail.com"},
                             headers=UA, timeout=30)
            r.raise_for_status()
            hits = r.json().get("results", [])
            if not hits:
                return None
            a = hits[0]
            stats = a.get("summary_stats") or {}
            inst = ((a.get("last_known_institutions") or [{}]) or [{}])[0]
            sim = SequenceMatcher(None, name.lower(),
                                  (a.get("display_name") or "").lower()).ratio()
            return {"openalex_id": a.get("id"),
                    "display_name": a.get("display_name"),
                    "name_similarity": round(sim, 3),
                    "h_index": stats.get("h_index"),
                    "cited_by_count": a.get("cited_by_count"),
                    "works_count": a.get("works_count"),
                    "institution": inst.get("display_name")}
        except Exception:  # noqa: BLE001
            time.sleep(2 + attempt)
    return None


CACHE = {}


def process(rec: dict) -> dict:
    name = rec["name"]
    title = unquote(rec["enwiki"].rsplit("/", 1)[-1]).replace("_", " ") if rec.get("enwiki") else name
    wiki = wiki_summary(title)
    cached = CACHE.get(rec["wikidata"]) or {}
    oa = cached.get("openalex") or openalex_author(name)
    return {"wikidata": rec["wikidata"], "cohort": rec["cohort"],
            "name": name, "wiki": wiki, "openalex": oa}


def main() -> None:
    cohorts = json.loads((OUT / "award_candidates.json").read_text())
    members = [m for c in cohorts.values() for m in c["members"]]
    print(f"{len(members)} laureates")
    if (OUT / "bios.json").exists():
        CACHE.update(json.loads((OUT / "bios.json").read_text()))
        print(f"reusing {len(CACHE)} cached OpenAlex matches")
    results = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(process, m): m for m in members}
        for i, f in enumerate(as_completed(futs)):
            r = f.result()
            results[r["wikidata"]] = r
            if (i + 1) % 50 == 0:
                print(f"  {i + 1}/{len(members)}")
    n_wiki = sum(1 for r in results.values() if r["wiki"] and r["wiki"].get("extract"))
    n_oa = sum(1 for r in results.values()
               if r["openalex"] and r["openalex"]["name_similarity"] >= 0.85
               and r["openalex"].get("h_index"))
    print(f"wiki extracts: {n_wiki}/{len(results)}; confident OpenAlex: {n_oa}")
    (OUT / "bios.json").write_text(json.dumps(results, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
