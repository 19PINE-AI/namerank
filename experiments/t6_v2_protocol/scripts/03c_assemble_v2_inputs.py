"""Assemble the final v2 inputs.

- pilot_entities_v2.json: all 5,719 v1 entities with v2 contexts + gold
  provenance fields, plus the 45 synthetic nulls.
- gold_answers_v2.json: priority merge credentials > people > artifacts >
  wikipedia; entities with no v2 gold keep the v1 gold and carry
  gold_v2=false (excluded from v2 headline analyses, still probed).

Run after 02a/02b/02c/02d and 03/03b have written their outputs.
"""
from __future__ import annotations

import csv
import html
import json
import re
from collections import Counter
from pathlib import Path


def clean(text: str) -> str:
    """Unescape HTML entities (Crossref/Wikipedia) and collapse whitespace."""
    return re.sub(r"\s+", " ", html.unescape(text or "")).strip()

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
INP = HERE / "inputs"

pe = json.loads((REPO / "data/inputs/pilot_entities.json").read_text())
v1_gold = json.loads((REPO / "data/inputs/gold_answers.json").read_text())
ctx = json.loads((INP / "contexts_v2.json").read_text())

sources = []
for fname, label in [("gold_v2_credentials.json", "credentials"),
                     ("gold_v2_researchers_s2_rich.json", "researchers_s2_rich"),
                     ("gold_v2_people.json", "people"),
                     ("gold_v2_researchers_s2.json", "researchers_s2"),
                     ("gold_v2_papers.json", "papers"),
                     ("gold_v2_artifacts.json", "artifacts"),
                     ("gold_v2_wikipedia.json", "wikipedia")]:
    p = INP / fname
    if p.exists():
        sources.append((label, json.loads(p.read_text())))
        print(f"{label}: {len(sources[-1][1])} golds")
    else:
        print(f"[WARN] {fname} missing — run its builder first")

entities_out, gold_out, rows = [], {}, []
for e in pe:
    eid = e["id"]
    rec = None
    src = None
    for label, g in sources:
        if eid in g and not g[eid].get("thin_gold") and g[eid].get("gold"):
            rec, src = g[eid], label
            break
    if rec is None:  # accept thin golds as second pass
        for label, g in sources:
            if eid in g and g[eid].get("gold"):
                rec, src = g[eid], label
                break
    e2 = dict(e)
    e2["context"] = ctx[eid]
    e2["context_v1"] = e["context"]
    # the 37 reference golds are hand-curated dense bios (the one gold set
    # that passed the construct audit) — they ARE valid v2 golds
    if rec is None and e["cohort"] == "reference_pilot":
        rec, src = {"gold": v1_gold[eid], "confidence": "high",
                    "thin_gold": False}, "v1_curated"
    # NOTE (2026-07-12 audit fix, issue 3): the old membership-minimal gold for
    # unmatched author-list contributors ("listed as a contributor on the
    # DeepSeek-V3 / GPT-5 report") merely restates the probe context, so capable
    # models echo it (gemini-3-flash 0.87, gemma-3-4b 0.21 — the v1 echo
    # signature). It is REMOVED. Unmatched contributors get no v2 gold
    # (gold_v2=False → excluded from the v2 NameRank headline); the cohort's
    # silence is reported separately via full-cohort refusal rate. Only
    # contributors matched to a real independent bio (02a/OpenAlex) carry a v2
    # gold and enter the v2 cohort mean.
    if rec:
        gold_out[eid] = clean(rec["gold"])
        e2["gold_v2"] = True
        e2["gold_source"] = src
        e2["gold_confidence"] = rec.get("confidence", "medium")
        e2["thin_gold"] = bool(rec.get("thin_gold"))
        if rec.get("not_a_person"):
            e2["not_a_person"] = True
    else:
        gold_out[eid] = v1_gold[eid]
        e2["gold_v2"] = False
        e2["gold_source"] = "v1_fallback"
        e2["gold_confidence"] = "v1"
        e2["thin_gold"] = True
    entities_out.append(e2)
    rows.append({"entity_id": eid, "cohort": e["cohort"],
                 "gold_source": e2["gold_source"],
                 "confidence": e2["gold_confidence"],
                 "thin_gold": int(e2["thin_gold"]),
                 "gold_words": len(gold_out[eid].split())})

syn_e = json.loads((INP / "synthetic_v2_entities.json").read_text())
syn_g = json.loads((INP / "synthetic_v2_gold.json").read_text())
for e in syn_e:
    e2 = dict(e)
    e2["gold_v2"] = True
    e2["gold_source"] = "synthetic"
    e2["gold_confidence"] = "high"
    e2["thin_gold"] = False
    entities_out.append(e2)
    gold_out[e["id"]] = syn_g[e["id"]]

(INP / "pilot_entities_v2.json").write_text(
    json.dumps(entities_out, ensure_ascii=False, indent=1))
(INP / "gold_answers_v2.json").write_text(
    json.dumps(gold_out, ensure_ascii=False, indent=1))
with open(HERE / "outputs" / "assembly_report.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

print(f"\n{len(entities_out)} entities ({len(syn_e)} synthetic)")
print("gold source:", dict(Counter(r["gold_source"] for r in rows)))
print("v1_fallback by cohort (top 15):")
fb = Counter(r["cohort"] for r in rows if r["gold_source"] == "v1_fallback")
for c, n in fb.most_common(15):
    tot = sum(1 for r in rows if r["cohort"] == c)
    print(f"  {c}: {n}/{tot}")
print("thin golds:", sum(r["thin_gold"] for r in rows))
