#!/usr/bin/env python3
"""Repair pass: rows with months_returned<=0 are canonical-title mismatches
(case, redirects, unicode normalization), not zero-traffic articles.
Resolve the canonical title via the MediaWiki query API (redirects=1),
re-fetch pageviews, and rewrite pageviews_24m.csv in place.
"""
import csv
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "outputs" / "pageviews_24m.csv"
HEADERS = {"User-Agent": "NameRank-research/1.0 (boj@19pine.ai) urllib"}
PV_API = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
          "en.wikipedia/all-access/user/{title}/monthly/20230701/20250630")
MW_API = ("https://en.wikipedia.org/w/api.php?action=query&format=json"
          "&redirects=1&titles={title}")


def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def canonical_title(title):
    try:
        data = get(MW_API.format(title=urllib.parse.quote(title)))
        pages = data["query"]["pages"]
        page = next(iter(pages.values()))
        if "missing" in page:
            return None
        return page["title"]
    except Exception:
        return None


def fetch_views(title):
    # The REST endpoint 404s when RFC-3986 sub-delims are percent-encoded
    # (Evan_O%27Dorney -> 404, Evan_O'Dorney -> 200), so keep them raw.
    url = PV_API.format(
        title=urllib.parse.quote(title.replace(" ", "_"), safe="'()!*,;:@&=+$"))
    for attempt in range(3):
        try:
            items = get(url).get("items", [])
            return len(items), sum(i["views"] for i in items)
        except urllib.error.HTTPError as e:
            if e.code == 404 and attempt == 2:
                return 0, 0
            time.sleep(3 * (attempt + 1))
        except Exception:
            time.sleep(2)
    return -1, -1


rows = list(csv.DictReader(open(OUT)))
bad = [r for r in rows if int(r["months_returned"]) <= 0]
print(f"repairing {len(bad)} rows")
fixed = still_missing = 0
for r in bad:
    canon = canonical_title(r["title"])
    if canon is None:
        r["months_returned"], r["views_24m"] = "-2", "-2"  # -2 = no such page
        still_missing += 1
        continue
    m, v = fetch_views(canon)
    r["title"], r["months_returned"], r["views_24m"] = canon, str(m), str(v)
    if m > 0:
        fixed += 1
    time.sleep(0.05)

with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["entity_id", "title", "months_returned", "views_24m"])
    w.writeheader()
    w.writerows(rows)
print(f"fixed {fixed}, no-such-page {still_missing}, "
      f"remaining zero/failed {len(bad) - fixed - still_missing}")
