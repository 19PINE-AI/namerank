"""Build protocol-v2 inputs for the per-university baseline cohorts.

Golds are built the same way the v2 full pass built the flagship
long_tail_researcher_openalex cohort's golds: via Semantic Scholar
(t6_v2_protocol/scripts/02f_gold_researchers_s2.py — OpenAlex is
credit-metered and exhausted), whose functions are imported directly:
name search, h-index-band + paperCount-dominance namesake guard, and
mechanical "most-cited works" composition with no bibliometric aggregates.
Following the oa_author convention, the institution appears in the v2
context, not the gold.

- context v2: "an academic researcher in {subfield} at {institution}"
  (role + field + institution; no citations, no h-index)
- in-run controls: the same 60 OpenAlex long-tail + 40 IMO control entities,
  with contexts and golds copied verbatim from the t6 v2 inputs

Resumable (S2 golds checkpoint to outputs/_s2_gold_cache.json every 40).
Writes inputs/univ_entities_v2.json, inputs/univ_gold_v2.json,
outputs/v2_match_report.csv.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
T6 = REPO / "experiments" / "t6_v2_protocol"
CACHE = HERE / "outputs" / "_s2_gold_cache.json"

spec = importlib.util.spec_from_file_location(
    "gold02f", T6 / "scripts" / "02f_gold_researchers_s2.py")
s2mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s2mod)


def build_s2_gold(e: dict, cache: dict) -> None:
    """Match entity on S2 and compose a v2 gold; records into cache."""
    eid = e["id"]
    if s2mod.is_org_name(e["name"]):
        cache[eid] = {"matched": 0, "reason": "org-name (not a person)"}
        return
    q = urllib.parse.quote(e["name"])
    sr = s2mod.s2_get(f"/author/search?query={q}"
                      "&fields=name,hIndex,paperCount,affiliations")
    cands = [a for a in (sr or {}).get("data", [])
             if s2mod.name_ok(e["name"], a.get("name", ""))] if sr else []
    author, reason = (s2mod.pick_author(cands, e["h_index"], None)
                      if cands else (None, "no name-matched candidate"))
    if not author:
        cache[eid] = {"matched": 0, "reason": reason}
        return
    pr = s2mod.s2_get(f"/author/{author['authorId']}/papers"
                      "?fields=title,year,venue,citationCount,"
                      "fieldsOfStudy,s2FieldsOfStudy&limit=100")
    papers = (pr or {}).get("data", []) if pr else []
    g, thin = s2mod.build_gold(e["name"], e["subfield"], None, papers)
    cache[eid] = {"matched": 1, "reason": reason, "gold": g,
                  "thin_gold": thin, "s2_author": str(author["authorId"])}


def main() -> None:
    v1_entities = json.loads((HERE / "inputs" / "univ_entities.json").read_text())
    univ = [e for e in v1_entities if not e.get("control")]
    control_ids = [e["id"] for e in v1_entities if e.get("control")]

    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    todo = [e for e in univ if e["id"] not in cache]
    print(f"{len(univ)} university entities; {len(todo)} to fetch from S2",
          flush=True)
    for n, e in enumerate(todo, 1):
        build_s2_gold(e, cache)
        if n % 40 == 0:
            CACHE.write_text(json.dumps(cache, ensure_ascii=False))
            m = sum(1 for v in cache.values() if v.get("matched"))
            print(f"  {n}/{len(todo)} fetched ({m} matched)", flush=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False))

    entities_v2, gold_v2, rows = [], {}, []
    for e in univ:
        rec = cache.get(e["id"], {})
        matched = bool(rec.get("matched"))
        ent = dict(e)
        ent["context"] = (f"an academic researcher in {e['subfield']} "
                          f"at {e['institution']}")
        ent["gold_v2"] = matched
        if matched:
            ent["thin_gold"] = rec["thin_gold"]
            gold_v2[e["id"]] = rec["gold"]
        entities_v2.append(ent)
        rows.append([e["id"], e["cohort"], int(matched),
                     rec.get("s2_author", ""), rec.get("reason", "")])

    # in-run controls: contexts + golds verbatim from the t6 v2 inputs
    t6_ents = {e["id"]: e for e in json.loads(
        (T6 / "inputs" / "pilot_entities_v2.json").read_text())}
    t6_gold = json.loads((T6 / "inputs" / "gold_answers_v2.json").read_text())
    n_ctrl_v2 = 0
    for cid in control_ids:
        te = t6_ents.get(cid)
        if te is None:
            rows.append([cid, "control", 0, "", "not in t6 v2 inputs"])
            continue
        ent = dict(te)
        ent["control"] = True
        entities_v2.append(ent)
        if te.get("gold_v2"):
            gold_v2[cid] = t6_gold[cid]
            n_ctrl_v2 += 1
        rows.append([cid, te["cohort"], int(bool(te.get("gold_v2"))),
                     "", "copied from t6 v2 inputs"])

    (HERE / "inputs" / "univ_entities_v2.json").write_text(
        json.dumps(entities_v2, indent=1, ensure_ascii=False))
    (HERE / "inputs" / "univ_gold_v2.json").write_text(
        json.dumps(gold_v2, indent=1, ensure_ascii=False))
    with open(HERE / "outputs" / "v2_match_report.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["entity_id", "cohort", "gold_v2", "s2_author", "reason"])
        w.writerows(rows)

    from collections import Counter
    built = Counter(e["cohort"] for e in entities_v2 if e.get("gold_v2"))
    thin = sum(1 for e in entities_v2 if e.get("thin_gold"))
    print(f"\nv2 golds built: {dict(built)}")
    print(f"controls with v2 golds: {n_ctrl_v2}/{len(control_ids)}; "
          f"thin golds: {thin}")


if __name__ == "__main__":
    main()
