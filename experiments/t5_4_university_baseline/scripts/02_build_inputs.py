"""Build probe inputs for the per-university baseline run.

Entities = 4 university cohorts (from 01) + in-run controls resampled from
the main run with the same seed as t5_1 (60 OpenAlex long-tail researchers,
40 IMO golds — golds and contexts copied verbatim), so within-run comparisons
are immune to panel-vintage drift.

Contexts and golds follow the main run's long_tail_researcher_openalex
templates verbatim (institution, subfield, first-author well-cited paper,
total citations, h-index — all from OpenAlex).

Writes inputs/univ_entities.json and inputs/univ_gold.json.
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
OUT = HERE / "outputs"
INP = HERE / "inputs"

CONTEXT_TPL = ("an academic researcher in {subfield} at {institution}, "
               "with approximately {cited} total citations and h-index {h}")

GOLD_TPL = ("{name} is an academic researcher at {institution}, with research "
            "focus in {subfield}. They are credited as first author on at "
            "least one well-cited paper ({fa} citations) in this area, and "
            "have approximately {cited} total citations across their "
            "publications, with an h-index of {h}. As a mid-career researcher "
            "with a substantive but not famous citation profile (IKP T3-T5 "
            "equivalent), {name} represents the established "
            "academic-researcher category. LLM recognition of this individual "
            "reflects how widely their name has propagated through citing "
            "papers, course materials, and online discussions — some such "
            "researchers cross the elite-recognition threshold while many do "
            "not.")


def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return s or "x"


def main() -> None:
    cohorts = json.loads((OUT / "candidates.json").read_text())
    entities, gold = [], {}
    seen_names = set()

    for cid, members in cohorts.items():
        for m in members:
            if m["name"].lower() in seen_names:
                continue
            seen_names.add(m["name"].lower())
            eid = f"{cid}_{slug(m['name'])}"
            ctx = CONTEXT_TPL.format(subfield=m["subfield"],
                                     institution=m["institution"],
                                     cited=m["cited_by_count"], h=m["h_index"])
            entities.append({
                "id": eid, "name": m["name"], "context": ctx, "cohort": cid,
                "institution": m["institution"], "subfield": m["subfield"],
                "h_index": m["h_index"], "cited_by_count": m["cited_by_count"],
                "openalex_id": m["openalex_id"],
                "fa_citations": m["fa_citations"],
                "control": False,
            })
            gold[eid] = GOLD_TPL.format(name=m["name"],
                                        institution=m["institution"],
                                        subfield=m["subfield"],
                                        fa=m["fa_citations"],
                                        cited=m["cited_by_count"],
                                        h=m["h_index"])

    # in-run controls from the main run, golds/contexts verbatim (same seed
    # as t5_1, so the control sets match across the t5 experiments)
    main_ents = json.loads((REPO / "data" / "inputs" / "pilot_entities.json").read_text())
    main_gold = json.loads((REPO / "data" / "inputs" / "gold_answers.json").read_text())
    rng = random.Random(42)
    oa_pool = [e for e in main_ents if e["cohort"] == "long_tail_researcher_openalex"]
    imo_pool = [e for e in main_ents if e["cohort"] == "imo_gold"]
    for e in rng.sample(oa_pool, 60) + rng.sample(imo_pool, 40):
        e = dict(e)
        e["control"] = True
        entities.append(e)
        gold[e["id"]] = main_gold[e["id"]]

    INP.mkdir(exist_ok=True)
    (INP / "univ_entities.json").write_text(
        json.dumps(entities, indent=1, ensure_ascii=False))
    (INP / "univ_gold.json").write_text(
        json.dumps(gold, indent=1, ensure_ascii=False))
    from collections import Counter
    print(Counter(e["cohort"] for e in entities))
    print(f"total {len(entities)} entities")


if __name__ == "__main__":
    main()
