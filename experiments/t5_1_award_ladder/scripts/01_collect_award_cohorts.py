"""Collect mid/late-career award laureate cohorts from Wikidata.

Award cohorts (P166 award-received statements, P585 year qualifier):
  Late-career : Turing Award (all), Fields Medal (all),
                Nobel Prize in Physics (2000-2023 only).
  Mid-career  : Goedel Prize (all), ACM Prize in Computing (all),
                MacArthur Fellows (sample 60 of 2000-2023),
                ACM Fellows (sample 60 of 2000-2023).
  Early-career: Sloan Research Fellows (sample 60 of 2000-2023).

Completeness note (recorded per cohort in the output): the prize cohorts
(Turing/Fields/Nobel/Goedel/ACM Prize) are complete rosters by construction
-- every laureate has a Wikidata item.  The fellowship/honor cohorts
(MacArthur/ACM Fellow/Sloan) are sampled from Wikidata's coverage, which may
omit low-profile recipients; their cohort means are upper bounds and are
flagged as such downstream.

Writes outputs/award_candidates.json.
"""
from __future__ import annotations

import json
import random
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "outputs"
UA = {"User-Agent": "NameRankResearch/1.0 (bojieli@gmail.com) requests"}
SPARQL = "https://query.wikidata.org/sparql"

AWARDS = [
    # cohort_id, QID, career stage, year filter, sample size (None = all), complete roster?
    ("turing_award",       "Q185667",   "late",  None,         None, True),
    ("fields_medal",       "Q28835",    "late",  None,         None, True),
    ("nobel_physics",      "Q38104",    "late",  (2000, 2023), None, True),
    ("godel_prize",        "Q1417143",  "mid",   None,         None, True),
    ("acm_prize_computing","Q29836618", "mid",   None,         None, True),
    ("macarthur_fellow",   "Q1543268",  "mid",   (2000, 2023), 60,   False),
    ("acm_fellow",         "Q18748039", "mid",   (2000, 2023), 60,   False),
    ("sloan_fellow",       "Q7541057",  "early", (2000, 2023), 60,   False),
]

QUERY = """
SELECT ?person ?personLabel ?personDescription ?year ?article WHERE {{
  ?person p:P166 ?st . ?st ps:P166 wd:{qid} .
  ?person wdt:P31 wd:Q5 .
  OPTIONAL {{ ?st pq:P585 ?date . BIND(YEAR(?date) AS ?year) }}
  OPTIONAL {{ ?article schema:about ?person ;
              schema:isPartOf <https://en.wikipedia.org/> }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
"""


def fetch_award(qid: str) -> list[dict]:
    for attempt in range(4):
        try:
            r = requests.get(SPARQL, params={"query": QUERY.format(qid=qid),
                                             "format": "json"},
                             headers=UA, timeout=120)
            r.raise_for_status()
            rows = r.json()["results"]["bindings"]
            break
        except Exception as e:  # noqa: BLE001
            print(f"  retry {attempt}: {e}")
            time.sleep(5 * (attempt + 1))
    else:
        raise RuntimeError(f"SPARQL failed for {qid}")
    people: dict[str, dict] = {}
    for b in rows:
        pid = b["person"]["value"].rsplit("/", 1)[-1]
        year = b.get("year", {}).get("value")
        year = int(year) if year else None
        rec = people.setdefault(pid, {
            "wikidata": pid,
            "name": b["personLabel"]["value"],
            "description": b.get("personDescription", {}).get("value"),
            "enwiki": None, "years": [],
        })
        if year and year not in rec["years"]:
            rec["years"].append(year)
        if "article" in b and not rec["enwiki"]:
            rec["enwiki"] = b["article"]["value"]
    out = list(people.values())
    for rec in out:
        rec["years"].sort()
        rec["award_year"] = rec["years"][0] if rec["years"] else None
    return out


def main() -> None:
    rng = random.Random(42)
    cohorts = {}
    for cid, qid, stage, yr_filter, sample, complete in AWARDS:
        print(f"== {cid} ({qid})")
        recs = fetch_award(qid)
        n_raw = len(recs)
        if yr_filter:
            lo, hi = yr_filter
            recs = [r for r in recs if r["award_year"] and lo <= r["award_year"] <= hi]
        # drop QID-labelled items (no English label)
        recs = [r for r in recs if not r["name"].startswith("Q")]
        n_filtered = len(recs)
        if sample and len(recs) > sample:
            recs = rng.sample(sorted(recs, key=lambda r: r["wikidata"]), sample)
        for r in recs:
            r["cohort"] = cid
            r["career_stage"] = stage
        cohorts[cid] = {
            "qid": qid, "career_stage": stage, "complete_roster": complete,
            "n_wikidata": n_raw, "n_after_filter": n_filtered,
            "n_selected": len(recs), "members": recs,
        }
        print(f"   wikidata {n_raw} -> filtered {n_filtered} -> selected {len(recs)}")
        time.sleep(2)
    OUT.mkdir(exist_ok=True)
    (OUT / "award_candidates.json").write_text(json.dumps(cohorts, indent=1, ensure_ascii=False))
    total = sum(c["n_selected"] for c in cohorts.values())
    print(f"TOTAL selected: {total}")


if __name__ == "__main__":
    main()
