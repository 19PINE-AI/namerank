"""Re-judge the t5_3 responses against canonical web-researched golds.

The probe responses do not depend on the gold answer (the gold is read only
by the judge), so switching from the boilerplate medalist gold to a canonical
person-level gold requires NO re-probing: we reuse the 5,256 stored responses
in pilot_results_tiers.json and re-score each with the same Gemini judge
against the new gold.

Canonical golds come from scripts-driven web-search agents
(outputs/canonical_golds.json, keyed by hanzi). Only the 103 NOI-2009
medalists are re-judged; in-run controls keep their main-run golds and scores
(they exist to anchor to the released run). Refusals stay 0/0 by definition.

As a validation of the "one gold per person" principle, the three Bojie Li
entities (medalist / MSRA-fellowship / diagnostic-reference contexts) are all
re-judged against the SINGLE canonical Bojie gold and written to
outputs/bojie_convergence.json.

Writes outputs/pilot_results_tiers_canonical.json and
outputs/tier_per_entity_canonical.csv.

Usage: python 04_rejudge_canonical.py [--parallel 10]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import statistics as st
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "code"))
from run_probe import call_judge  # noqa: E402
from google import genai  # noqa: E402


def hanzi_of(name: str) -> str | None:
    return name.split("(")[1].rstrip(")") if "(" in name else None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--parallel", type=int, default=10)
    args = p.parse_args()

    out = HERE / "outputs"
    entities = {e["id"]: e for e in json.loads(
        (HERE / "inputs" / "tier_entities.json").read_text())}
    canon = json.loads((out / "canonical_golds_raw.json").read_text())
    judge_tpl = (REPO / "data" / "inputs" / "judge_prompt.txt").read_text()
    records = json.loads((out / "pilot_results_tiers.json").read_text())

    # entity_id -> canonical gold text, for the 103 medalists
    gold_by_eid = {eid: v["gold"] for eid, v in canon.items()
                   if entities.get(eid, {}).get("tier")}
    # Bojie convergence: all three contexts vs the SINGLE canonical Bojie gold
    bojie_gold = canon.get("noi_b_li_bojie_2009", {}).get("gold")
    bojie_eids = {"noi_b_li_bojie_2009", "msra_bojie_li_2017", "bojie_li"}

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def rejudge(rec, gold_text):
        if rec["is_refusal"]:
            return dict(rec, coverage=0.0, accuracy=0.0, score=0.0,
                        rationale="refusal")
        ji = judge_tpl.format(name=rec["entity_name"],
                              gold_answer=gold_text, response=rec["response"])
        s = call_judge(client, ji)
        return dict(rec, coverage=s["coverage"], accuracy=s["accuracy"],
                    score=s["coverage"] * s["accuracy"], rationale=s["rationale"])

    # ---- main re-judge over the 103 medalists (resumable) ----
    ckpt = out / "_rejudge_ckpt.json"
    done_pairs = {}
    if ckpt.exists():
        for r in json.loads(ckpt.read_text()):
            done_pairs[(r["entity_id"], r["model_id"])] = r
    kept = [r for r in records if r["entity_id"] not in gold_by_eid]
    todo = [(r, gold_by_eid[r["entity_id"]]) for r in records
            if r["entity_id"] in gold_by_eid
            and (r["entity_id"], r["model_id"]) not in done_pairs]
    print(f"re-judging {len(todo):,} medalist records "
          f"({len(done_pairs):,} from checkpoint); "
          f"{len(kept):,} control records kept as-is")

    rejudged = list(done_pairs.values())
    with ThreadPoolExecutor(max_workers=args.parallel) as ex:
        futs = {ex.submit(rejudge, r, g): r["entity_id"] for r, g in todo}
        for i, fut in enumerate(as_completed(futs)):
            try:
                rejudged.append(fut.result())
            except Exception as exc:  # noqa: BLE001
                print(f"  [ERROR] {futs[fut]}: {exc}")
            if (i + 1) % 300 == 0:
                ckpt.write_text(json.dumps(rejudged, ensure_ascii=False))
                print(f"  {i+1}/{len(todo)} ({time.strftime('%H:%M:%S')})",
                      flush=True)
    ckpt.write_text(json.dumps(rejudged, ensure_ascii=False))

    allrecs = kept + rejudged
    (out / "pilot_results_tiers_canonical.json").write_text(
        json.dumps(allrecs, indent=1, ensure_ascii=False))

    # per-entity aggregate (medalists only need it, but write all)
    by_ent = defaultdict(list)
    refus = defaultdict(list)
    for r in allrecs:
        by_ent[r["entity_id"]].append(r["score"])
        refus[r["entity_id"]].append(r["is_refusal"])
    rows = []
    for eid, scores in by_ent.items():
        e = entities.get(eid, {})
        rows.append({
            "entity_id": eid, "entity_name": e.get("entity_name", e.get("name")),
            "cohort": e.get("cohort"), "tier": e.get("tier"),
            "control": e.get("control"), "noi_score": e.get("noi_score"),
            "noi_rank": e.get("noi_rank"),
            "gold_words": canon.get(eid, {}).get("n_words"),
            "gold_sources": canon.get(eid, {}).get("n_sources"),
            "n_models": len(scores), "namerank": st.mean(scores),
            "namerank_sd": st.pstdev(scores), "refusal_rate": st.mean(refus[eid]),
        })
    rows.sort(key=lambda r: -r["namerank"])
    with open(out / "tier_per_entity_canonical.csv", "w", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # ---- Bojie convergence demo ----
    if bojie_gold:
        conv = {}
        for eid in bojie_eids:
            recs = [r for r in records if r["entity_id"] == eid]
            rj = []
            with ThreadPoolExecutor(max_workers=args.parallel) as ex:
                for r in ex.map(lambda x: rejudge(x, bojie_gold), recs):
                    rj.append(r)
            conv[eid] = {
                "context": entities[eid]["context"],
                "namerank_vs_canonical": st.mean(x["score"] for x in rj),
                "n": len(rj),
            }
        (out / "bojie_convergence.json").write_text(json.dumps(conv, indent=1,
                                                    ensure_ascii=False))
        print("\nBojie convergence vs single canonical gold:")
        for eid, d in conv.items():
            print(f"  {eid:24s} {d['namerank_vs_canonical']:.3f}  "
                  f"({d['context'][:50]})")

    print(f"\nwrote {out/'pilot_results_tiers_canonical.json'} and "
          f"{out/'tier_per_entity_canonical.csv'}")


if __name__ == "__main__":
    main()
