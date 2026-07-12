#!/usr/bin/env python3
"""T5.2 — fetch 24-month en-Wikipedia pageviews for the 1,681 entities whose
articles were resolved (with disambiguation checks) in T1.4.

Window: 2023-07-01 .. 2025-06-30, monthly granularity, user traffic only.
Output: outputs/pageviews_24m.csv (entity_id, title, months_returned, views_24m).
"""
import csv
import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).parent
LOOKUP = HERE.parent / "t1_4_wikipedia" / "wikipedia_lookup.csv"
OUT = HERE / "outputs" / "pageviews_24m.csv"

API = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
       "en.wikipedia/all-access/user/{title}/monthly/20230701/20250630")
HEADERS = {"User-Agent": "NameRank-research/1.0 (boj@19pine.ai) urllib"}


def fetch_one(row):
    # NB: RFC-3986 sub-delims must stay raw — the REST endpoint 404s on
    # percent-encoded apostrophes (Evan_O%27Dorney vs Evan_O'Dorney).
    title = row["title_matched"].replace(" ", "_")
    url = API.format(title=urllib.parse.quote(title, safe="'()!*,;:@&=+$"))
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                items = json.load(r).get("items", [])
            return {"entity_id": row["entity_id"], "title": row["title_matched"],
                    "months_returned": len(items),
                    "views_24m": sum(i["views"] for i in items)}
        except urllib.error.HTTPError as e:
            if e.code == 404:  # article exists but no pageview data in window
                return {"entity_id": row["entity_id"], "title": row["title_matched"],
                        "months_returned": 0, "views_24m": 0}
            if e.code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            time.sleep(2)
        except Exception:
            time.sleep(2)
    return {"entity_id": row["entity_id"], "title": row["title_matched"],
            "months_returned": -1, "views_24m": -1}  # -1 = fetch failed


def main():
    rows = [r for r in csv.DictReader(open(LOOKUP))
            if r["has_wikipedia"] == "1" and r["title_matched"]]
    print(f"fetching {len(rows)} articles")
    results = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for i, res in enumerate(ex.map(fetch_one, rows)):
            results.append(res)
            if (i + 1) % 200 == 0:
                print(f"  {i + 1}/{len(rows)}")
    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["entity_id", "title",
                                          "months_returned", "views_24m"])
        w.writeheader()
        w.writerows(results)
    failed = sum(1 for r in results if r["months_returned"] == -1)
    print(f"done: {len(results)} rows, {failed} failed")


if __name__ == "__main__":
    main()
