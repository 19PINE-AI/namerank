"""Sample per-university working-researcher cohorts from OpenAlex.

Replicates the main run's long_tail_researcher_openalex construction, adding
one institutional stratum per university:

  - last_known_institutions.id = the university
  - total citations in [500, 30000]  (the main run's citation window)
  - at least one first-author work with >= 500 citations (the main run's
    implicit inclusion rule: every released gold asserts a first-author
    "well-cited paper", minimum observed 500 citations)

Sampling is OpenAlex server-side random sampling (sample=..&seed=42), then
candidates are screened in sample order until TARGET qualify per university.
The qualifying first-author work's primary topic supplies the subfield, as in
the main run's golds ("well-cited paper ... in this area").

Writes outputs/candidates.json.
"""
from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "outputs"
API_KEY = os.environ["OPENALEX_API_KEY"]
UA = {"User-Agent": "NameRankResearch/1.0 (bojieli@gmail.com) requests"}

UNIVERSITIES = {
    "univ_mit": ("I63966007", "Massachusetts Institute of Technology"),
    "univ_uc_berkeley": ("I95457486", "University of California, Berkeley"),
    "univ_ucsd": ("I36258959", "University of California San Diego"),
    "univ_uc_irvine": ("I204250578", "University of California, Irvine"),
}
TARGET = 100          # qualifying researchers per university
SAMPLE_N = 2400       # random candidates drawn per university (screened in order)
FA_MIN_CITES = 500    # first-author work citation floor (main-run implicit rule)
CIT_LO, CIT_HI = 500, 30000


def api_get(url: str, params: dict, tries: int = 4) -> dict | None:
    params = dict(params, api_key=API_KEY)
    for attempt in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=30)
            if r.status_code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json()
        except Exception:  # noqa: BLE001
            time.sleep(2 + 2 * attempt)
    return None


def sample_authors(inst_id: str) -> list[dict]:
    """Server-side random sample of authors at inst within the citation window."""
    out, per_page = [], 200
    pages = (SAMPLE_N + per_page - 1) // per_page
    for page in range(1, pages + 1):
        d = api_get("https://api.openalex.org/authors", {
            "filter": (f"last_known_institutions.id:{inst_id},"
                       f"cited_by_count:>{CIT_LO - 1},cited_by_count:<{CIT_HI + 1}"),
            "sample": SAMPLE_N, "seed": 42,
            "per-page": per_page, "page": page,
        })
        if not d:
            break
        out.extend(d.get("results", []))
    return out


def first_author_work(author_id: str) -> dict | None:
    """The author's most-cited first-author work with >= FA_MIN_CITES citations."""
    aid = author_id.rsplit("/", 1)[-1]
    d = api_get("https://api.openalex.org/works", {
        "filter": f"authorships.author.id:{aid},cited_by_count:>{FA_MIN_CITES - 1}",
        "sort": "cited_by_count:desc", "per-page": 50,
    })
    if not d:
        return None
    for w in d.get("results", []):
        for auth in w.get("authorships", []):
            if (auth.get("author") or {}).get("id") == author_id:
                if auth.get("author_position") == "first":
                    topic = (w.get("primary_topic") or {}).get("display_name")
                    return {"work_id": w["id"],
                            "title": w.get("display_name"),
                            "fa_citations": w["cited_by_count"],
                            "topic": topic}
                break
    return None


def screen(cohort: str, inst_name: str, candidates: list[dict]) -> list[dict]:
    """Screen candidates in sample order, in batches, until TARGET qualify."""
    accepted, checked = [], 0
    BATCH = 200
    for start in range(0, len(candidates), BATCH):
        if len(accepted) >= TARGET:
            break
        batch = candidates[start:start + BATCH]
        with ThreadPoolExecutor(max_workers=8) as ex:
            fa_results = list(ex.map(lambda a: first_author_work(a["id"]), batch))
        for a, fa in zip(batch, fa_results):
            checked += 1
            if len(accepted) >= TARGET:
                break
            if not fa or not fa["topic"]:
                continue
            stats = a.get("summary_stats") or {}
            h = stats.get("h_index")
            if not h:
                continue
            accepted.append({
                "openalex_id": a["id"],
                "name": a["display_name"],
                "cohort": cohort,
                "institution": inst_name,
                "h_index": h,
                "cited_by_count": a["cited_by_count"],
                "works_count": a.get("works_count"),
                "subfield": fa["topic"],
                "fa_citations": fa["fa_citations"],
                "fa_work": fa["title"],
            })
        print(f"  {cohort}: screened {checked}, accepted {len(accepted)}", flush=True)
    return accepted


def main() -> None:
    OUT.mkdir(exist_ok=True)
    all_accepted = {}
    for cohort, (inst_id, inst_name) in UNIVERSITIES.items():
        print(f"{cohort} ({inst_name})")
        cands = sample_authors(inst_id)
        print(f"  sampled {len(cands)} candidates")
        all_accepted[cohort] = screen(cohort, inst_name, cands)
    (OUT / "candidates.json").write_text(
        json.dumps(all_accepted, indent=1, ensure_ascii=False))
    for c, lst in all_accepted.items():
        print(c, len(lst))


if __name__ == "__main__":
    main()
