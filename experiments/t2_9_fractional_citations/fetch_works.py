"""Fetch per-work metadata for each long_tail_researcher_openalex cohort author.

For each author we call the OpenAlex /works endpoint with a filter on author.id
and pull cited_by_count + authorships (need author_position to identify first /
last-author papers). We aggregate to per-author metrics:

  fractional_citations  = sum_w cited_by_count(w) / n_authors(w)
  n_works               = number of works returned
  mean_authors          = mean authors per work
  first_last_citations  = sum_w cited_by_count(w) restricted to first/last author
  n_first_or_last       = number of first/last author works

Output: author_works_metrics.csv

We are polite (mailto=, low concurrency, retry/backoff). Resume support: skips
authors already in the output CSV.
"""
from __future__ import annotations

import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

EXP_DIR = Path("/home/ubuntu/namerank/experiments/t2_9_fractional_citations")
ENTITIES_PATH = Path("/home/ubuntu/namerank/data/inputs/pilot_entities.json")
OUT_CSV = EXP_DIR / "author_works_metrics.csv"

MAILTO = "boj@19pine.ai"
CONCURRENCY = 8
RETRIES = 4
PER_PAGE = 200
TIMEOUT = 60


def fetch_json(url: str, retries: int = RETRIES) -> dict | None:
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": f"namerank-experiment/1.0 (mailto:{MAILTO})"},
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return json.load(resp)
        except Exception as e:  # noqa: BLE001
            last_err = e
            # backoff: 1s, 2s, 4s, 8s
            time.sleep(2 ** attempt)
    print(f"  ! failed after {retries} retries: {url[:120]}  ({last_err})", flush=True)
    return None


def author_short_id(oa_url: str) -> str:
    return oa_url.rsplit("/", 1)[-1]


def fetch_author_works(short_id: str) -> list[dict]:
    """Paginate all works for an author. Return list of {cited_by_count,
    n_authors, position (first/middle/last)}.
    """
    works: list[dict] = []
    cursor = "*"
    select = "id,cited_by_count,authorships,publication_year"
    while True:
        url = (
            "https://api.openalex.org/works?"
            + urllib.parse.urlencode(
                {
                    "filter": f"author.id:{short_id}",
                    "per-page": PER_PAGE,
                    "select": select,
                    "cursor": cursor,
                    "mailto": MAILTO,
                }
            )
        )
        data = fetch_json(url)
        if data is None:
            break
        for w in data.get("results", []):
            auths = w.get("authorships") or []
            n_auth = len(auths)
            pos = None
            for au in auths:
                a = (au.get("author") or {}).get("id") or ""
                if a.rsplit("/", 1)[-1] == short_id:
                    pos = au.get("author_position")
                    break
            works.append(
                {
                    "cited_by_count": w.get("cited_by_count") or 0,
                    "n_authors": n_auth,
                    "position": pos,  # 'first', 'middle', 'last', or None
                    "year": w.get("publication_year"),
                }
            )
        cursor = (data.get("meta") or {}).get("next_cursor")
        if not cursor:
            break
    return works


def aggregate(works: list[dict]) -> dict:
    n = len(works)
    if n == 0:
        return dict(
            n_works=0,
            fractional_citations=0.0,
            mean_authors=0.0,
            first_last_citations=0,
            n_first_or_last=0,
            total_citations_from_works=0,
            n_solo_works=0,
        )
    frac = 0.0
    total = 0
    sum_authors = 0
    fl_cites = 0
    fl_n = 0
    n_solo = 0
    for w in works:
        cbc = w["cited_by_count"]
        na = max(1, w["n_authors"] or 1)
        sum_authors += na
        total += cbc
        frac += cbc / na
        if na == 1:
            n_solo += 1
        if w["position"] in ("first", "last"):
            fl_cites += cbc
            fl_n += 1
    return dict(
        n_works=n,
        fractional_citations=frac,
        mean_authors=sum_authors / n,
        first_last_citations=fl_cites,
        n_first_or_last=fl_n,
        total_citations_from_works=total,
        n_solo_works=n_solo,
    )


def process_entity(ent: dict) -> dict | None:
    short = author_short_id(ent["openalex_id"])
    works = fetch_author_works(short)
    if not works:
        # still record with zeros so we can resume cleanly
        agg = aggregate([])
    else:
        agg = aggregate(works)
    return {
        "entity_id": ent["id"],
        "name": ent["name"],
        "openalex_id": ent["openalex_id"],
        "h_index": ent.get("h_index") or 0,
        "cited_by_count": ent.get("cited_by_count") or 0,
        **agg,
    }


def main() -> None:
    EXP_DIR.mkdir(parents=True, exist_ok=True)
    ents_all = json.loads(ENTITIES_PATH.read_text())
    cohort = [
        e for e in ents_all if e.get("cohort") == "long_tail_researcher_openalex"
    ]
    print(f"cohort size: {len(cohort)}", flush=True)

    done_ids: set[str] = set()
    if OUT_CSV.exists():
        with OUT_CSV.open() as f:
            for row in csv.DictReader(f):
                done_ids.add(row["entity_id"])
        print(f"already done: {len(done_ids)}", flush=True)
    todo = [e for e in cohort if e["id"] not in done_ids]
    print(f"todo: {len(todo)}", flush=True)
    if not todo:
        print("nothing to do", flush=True)
        return

    fieldnames = [
        "entity_id",
        "name",
        "openalex_id",
        "h_index",
        "cited_by_count",
        "n_works",
        "fractional_citations",
        "mean_authors",
        "first_last_citations",
        "n_first_or_last",
        "total_citations_from_works",
        "n_solo_works",
    ]
    file_existed = OUT_CSV.exists()
    f = OUT_CSV.open("a", newline="")
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    if not file_existed:
        writer.writeheader()
        f.flush()

    t0 = time.time()
    done = 0
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        futs = {ex.submit(process_entity, e): e for e in todo}
        for fut in as_completed(futs):
            ent = futs[fut]
            try:
                row = fut.result()
            except Exception as exc:  # noqa: BLE001
                print(f"  ! error on {ent['id']}: {exc}", flush=True)
                continue
            if row is None:
                continue
            writer.writerow(row)
            f.flush()
            done += 1
            if done % 25 == 0:
                rate = done / max(1.0, time.time() - t0)
                eta = (len(todo) - done) / max(rate, 0.01)
                print(
                    f"  {done}/{len(todo)}  rate={rate:.1f}/s  eta={eta:.0f}s",
                    flush=True,
                )
    f.close()
    print(f"finished in {time.time()-t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
