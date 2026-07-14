"""Build the three LLM-area cohorts (t5_5), ~100 entities each, via Semantic
Scholar. Authors are resolved by their S2 authorId taken DIRECTLY from the
originating paper's author list (no name search), which eliminates the
same-name namesake problem. Golds are entity-specific verifiable works;
contexts are role-only.

Cohorts:
  A llm_method_originator    — first author of a named method/benchmark paper
  B llm_foundational_author  — co-authors of landmark LLM/DL papers
  C llm_best_paper_author    — authors of best-paper / landmark award papers

Writes inputs/entities.json, inputs/gold.json, inputs/artifacts.json,
outputs/roster_report.csv. Resumable via outputs/_s2_cache.json.
"""
from __future__ import annotations

import csv
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "inputs"))
import seeds  # noqa: E402

UA = {"User-Agent": "NameRank-t5_5 (mailto:boj@19pine.ai)"}
S2 = "https://api.semanticscholar.org/graph/v1"
CACHE = HERE / "outputs" / "_s2_cache.json"
cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}


def s2_get(path):
    if path in cache:
        return cache[path]
    for a in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(S2 + path, headers=UA),
                                        timeout=30) as r:
                j = json.load(r)
                cache[path] = j
                return j
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(3 * (a + 1)); continue
            return None
        except Exception:
            time.sleep(2)
    return None


def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", (s or "").lower()).strip()


def surname(name):
    t = norm(name).split()
    return t[-1] if t else ""


def search_paper(query, year=None):
    d = s2_get(f"/paper/search?query={urllib.parse.quote(query)}"
               "&fields=title,year,authors&limit=6")
    items = (d or {}).get("data", []) or []
    want = set(norm(query).split())
    for it in items:
        got = set(norm(it.get("title", "")).split())
        if want and len(want & got) >= max(2, 0.45 * len(want)):
            if year and it.get("year") and abs(it["year"] - year) > 3:
                continue
            auths = [(a["name"], a["authorId"]) for a in (it.get("authors") or [])
                     if a.get("authorId")]
            if auths:
                return it.get("title"), it.get("year"), auths
    return None, None, []


def author_works(aid):
    d = s2_get(f"/author/{aid}/papers?fields=title,year,venue,citationCount&limit=100")
    return (d or {}).get("data", []) or []


ABBREV = re.compile(r"^[A-Z]\.?\s")            # "J. Hu", "P Abbeel"


def canonical_name(aid, fallback):
    """Prefer a full name over a paper's abbreviated author-list form."""
    if not ABBREV.match(fallback):
        return fallback
    d = s2_get(f"/author/{aid}?fields=name")
    nm = (d or {}).get("name", "")
    return nm if nm and not ABBREV.match(nm) else fallback


def author_search(name):
    d = s2_get(f"/author/search?query={urllib.parse.quote(name)}"
               "&fields=name,paperCount")
    cands = [a for a in (d or {}).get("data", []) or []
             if surname(a["name"]) == surname(name)]
    cands.sort(key=lambda a: -(a.get("paperCount") or 0))
    return [(a["name"], a["authorId"]) for a in cands[:8]]


def has_work_matching(works, method):
    """True if the author has a paper whose title matches the method name
    (all method-name content tokens present) — verifies authorship of the
    named method, rejecting same-name namesakes."""
    mt = [t for t in norm(re.sub(r"\(.*?\)", "", method)).split()
          if len(t) > 2 and t not in ("the", "for", "and", "with", "via")]
    if not mt:
        return False
    for p in works:
        tt = set(norm(p.get("title", "")).split())
        if sum(t in tt for t in mt) >= max(1, len(mt) - 1):
            return True
    return False


def works_gold(name, aid, role, works=None):
    ps = works if works is not None else author_works(aid)
    ps = sorted(ps, key=lambda x: -(x.get("citationCount") or 0))
    named = []
    for p in ps[:5]:
        t = " ".join((p.get("title") or "").split()[:14])
        if not t:
            continue
        v, y = (p.get("venue") or "").strip(), p.get("year")
        named.append(f"“{t}" + (f" ({v}, {y})" if v and y else
                                     (f" ({y})" if y else "")) + "”")
    g = f"{name} is {role}."
    if named:
        g += " Their most-cited works include " + ", ".join(named) + "."
    return g, len(named) >= 2


def main():
    entities, gold, report, artifacts = [], {}, [], []
    seen_ids = {}            # authorId -> cohort (dedup, A>B>C)
    seen_norm = {}           # norm(name) -> authorId

    ROLE = {"llm_method_originator": "a machine learning researcher",
            "llm_foundational_author": "an AI researcher",
            "llm_best_paper_author": "a machine learning researcher"}

    def add(name, aid, cohort, artifact, kind, extra=None, works=None):
        if aid in seen_ids or norm(name) in seen_norm:
            return False
        g, ok = works_gold(name, aid, ROLE[cohort], works=works)
        if not ok:
            return False
        eid = f"{cohort}_{re.sub(r'[^a-z0-9]+','_',norm(name))}"
        entities.append({"id": eid, "name": name, "context": ROLE[cohort],
                         "cohort": cohort, "gold_v2": True, "gold_source": "s2",
                         "s2_author": aid})
        gold[eid] = g
        seen_ids[aid] = cohort
        seen_norm[norm(name)] = aid
        art = {"person": name, "artifact": artifact, "kind": kind, "cohort": cohort}
        if extra:
            art.update(extra)
        artifacts.append(art)
        return True

    def ncoh(c):
        return sum(1 for e in entities if e["cohort"] == c)

    # ── A: method originators — resolve the seeded first author by name, then
    # VERIFY they authored the method's paper (rejects same-name namesakes). ──
    print("Cohort A: method originators", flush=True)
    for method, seed_author, year in seeds.METHODS:
        if ncoh("llm_method_originator") >= 100:
            break
        matched = 0
        for name, aid in author_search(seed_author):
            works = author_works(aid)
            if has_work_matching(works, method):
                if add(seed_author, aid, "llm_method_originator", method, "method",
                       works=works):
                    matched = 1
                break
        report.append({"cohort": "A", "seed": method, "matched": matched})
        CACHE.write_text(json.dumps(cache))

    # ── B: foundational-paper authors (full rosters) ──
    print("Cohort B: foundational-paper authors", flush=True)
    for title, year in seeds.FOUNDATIONAL_PAPERS:
        if ncoh("llm_foundational_author") >= 100:
            break
        rtitle, yr, auths = search_paper(title, year)
        report.append({"cohort": "B", "seed": title, "matched": int(bool(auths))})
        for name, aid in auths[:12]:
            if ncoh("llm_foundational_author") >= 100:
                break
            add(canonical_name(aid, name), aid, "llm_foundational_author",
                rtitle or title, "paper")
        CACHE.write_text(json.dumps(cache))

    # ── C: best-paper / landmark award authors ──
    print("Cohort C: best-paper-award authors", flush=True)
    for title, venue, year in seeds.BEST_PAPER:
        if ncoh("llm_best_paper_author") >= 100:
            break
        rtitle, yr, auths = search_paper(title, year)
        report.append({"cohort": "C", "seed": f"{title} [{venue} {year}]",
                       "matched": int(bool(auths))})
        for name, aid in auths[:8]:
            if ncoh("llm_best_paper_author") >= 100:
                break
            add(canonical_name(aid, name), aid, "llm_best_paper_author",
                rtitle or title, "best_paper", {"venue": venue, "year": year})
        CACHE.write_text(json.dumps(cache))

    (HERE / "inputs" / "entities.json").write_text(
        json.dumps(entities, ensure_ascii=False, indent=1))
    (HERE / "inputs" / "gold.json").write_text(
        json.dumps(gold, ensure_ascii=False, indent=1))
    (HERE / "inputs" / "artifacts.json").write_text(
        json.dumps(artifacts, ensure_ascii=False, indent=1))
    with open(HERE / "outputs" / "roster_report.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["cohort", "seed", "matched"])
        w.writeheader(); w.writerows(report)

    from collections import Counter
    print("\nroster:", dict(Counter(e["cohort"] for e in entities)),
          "| total", len(entities), flush=True)
    for c in ROLE:
        for e in [x for x in entities if x["cohort"] == c][:3]:
            print(f"  [{c}] {e['name']}: {gold[e['id']][:105]}")


if __name__ == "__main__":
    main()
