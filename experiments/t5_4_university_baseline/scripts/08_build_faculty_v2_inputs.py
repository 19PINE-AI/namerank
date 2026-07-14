"""Build v2 golds/contexts for the CSRankings faculty cohorts and merge them
into the experiment's v2 inputs.

Golds follow the v2 full pass's cs_faculty route exactly (imported from
t6_v2_protocol/scripts/02f_gold_researchers_s2.py): S2 name search, the
faculty namesake guard (paperCount dominance, no reference h-index), the
CS-topical check, and mechanical composition with the institution named in
the gold. Contexts follow the cs_faculty v2 convention:
"a computer science faculty member at {university}".

Appends to inputs/univ_entities_v2.json and inputs/univ_gold_v2.json
(idempotent: existing faculty entries are replaced), so the single
06_run_probe_v2.py run covers windowed + faculty cohorts + controls.

Resumable (S2 fetches checkpoint to outputs/_s2_faculty_cache.json).
"""
from __future__ import annotations

import csv
import importlib.util
import json
import re
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
T6 = REPO / "experiments" / "t6_v2_protocol"
CACHE = HERE / "outputs" / "_s2_faculty_cache.json"

spec = importlib.util.spec_from_file_location(
    "gold02f", T6 / "scripts" / "02f_gold_researchers_s2.py")
s2mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s2mod)


def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return s or "x"


def build_s2_gold(m: dict, cache: dict) -> None:
    """cs_faculty-branch match + compose; records into cache keyed by eid."""
    eid = m["eid"]
    q = urllib.parse.quote(m["name"])
    sr = s2mod.s2_get(f"/author/search?query={q}"
                      "&fields=name,hIndex,paperCount,affiliations")
    cands = [a for a in (sr or {}).get("data", [])
             if s2mod.name_ok(m["name"], a.get("name", ""))] if sr else []
    author, reason = (s2mod.pick_author(cands, None, m["institution"])
                      if cands else (None, "no name-matched candidate"))
    if not author:
        cache[eid] = {"matched": 0, "reason": reason}
        return
    pr = s2mod.s2_get(f"/author/{author['authorId']}/papers"
                      "?fields=title,year,venue,citationCount,"
                      "fieldsOfStudy,s2FieldsOfStudy&limit=100")
    papers = (pr or {}).get("data", []) if pr else []
    if not s2mod.cs_topical(papers):
        cache[eid] = {"matched": 0,
                      "reason": "matched author not CS-topical (rejected)"}
        return
    g, thin = s2mod.build_gold(m["name"], None, m["institution"], papers)
    cache[eid] = {"matched": 1, "reason": reason, "gold": g,
                  "thin_gold": thin, "s2_author": str(author["authorId"])}


def main() -> None:
    cohorts = json.loads((HERE / "outputs" / "faculty_candidates.json").read_text())
    members = []
    for cid, lst in cohorts.items():
        for m in lst:
            m = dict(m)
            m["eid"] = f"{cid}_{slug(m['name'])}"
            members.append(m)

    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    todo = [m for m in members if m["eid"] not in cache]
    print(f"{len(members)} faculty; {len(todo)} to fetch from S2", flush=True)
    for n, m in enumerate(todo, 1):
        build_s2_gold(m, cache)
        if n % 40 == 0:
            CACHE.write_text(json.dumps(cache, ensure_ascii=False))
            k = sum(1 for v in cache.values() if v.get("matched"))
            print(f"  {n}/{len(todo)} fetched ({k} matched)", flush=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False))

    entities = json.loads((HERE / "inputs" / "univ_entities_v2.json").read_text())
    gold = json.loads((HERE / "inputs" / "univ_gold_v2.json").read_text())
    entities = [e for e in entities if not e["cohort"].startswith("univ_fac_")]

    rows = []
    for m in members:
        rec = cache.get(m["eid"], {})
        matched = bool(rec.get("matched"))
        ent = {
            "id": m["eid"], "name": m["name"],
            "context": ("a computer science faculty member at "
                        f"{m['institution']}"),
            "cohort": m["cohort"], "institution": m["institution"],
            "scholarid": m.get("scholarid", ""),
            "control": False, "gold_v2": matched,
        }
        if matched:
            ent["thin_gold"] = rec["thin_gold"]
            gold[m["eid"]] = rec["gold"]
        entities.append(ent)
        rows.append([m["eid"], m["cohort"], int(matched),
                     rec.get("s2_author", ""), rec.get("reason", "")])

    (HERE / "inputs" / "univ_entities_v2.json").write_text(
        json.dumps(entities, indent=1, ensure_ascii=False))
    (HERE / "inputs" / "univ_gold_v2.json").write_text(
        json.dumps(gold, indent=1, ensure_ascii=False))
    with open(HERE / "outputs" / "v2_faculty_match_report.csv", "w",
              newline="") as f:
        w = csv.writer(f)
        w.writerow(["entity_id", "cohort", "gold_v2", "s2_author", "reason"])
        w.writerows(rows)

    from collections import Counter
    built = Counter(e["cohort"] for e in entities
                    if e.get("gold_v2") and e["cohort"].startswith("univ_fac_"))
    print(f"\nfaculty v2 golds built: {dict(built)}")


if __name__ == "__main__":
    main()
