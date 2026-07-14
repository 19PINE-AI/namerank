"""Analyze the per-university baseline run.

Per-cohort NameRank means with 95% CIs, computed on (a) the full 36-model
event panel and (b) the 28 main-run survivor models only — the survivor
subset is the apples-to-apples comparison against released main-run values
(t4_1 measured survivor-panel equivalence at r=0.993, +0.011 level shift).

In-run controls (60 OpenAlex long-tail + 40 IMO golds probed with verbatim
main-run golds/contexts) anchor the comparison: their survivor-panel means
are compared against their released main-run scores to report the run shift.

Writes outputs/summary.json.
"""
from __future__ import annotations

import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent

DEAD_MODELS = {
    "ernie-4.5-300b-a47b", "mistral-large", "mistral-medium-3.1",
    "ministral-3b", "kimi-k2", "grok-4", "glm-4-32b", "llama-3.2-1b",
    "grok-4.20-think",
}


def mean_ci(xs: list[float]) -> tuple[float, float]:
    m = statistics.mean(xs)
    if len(xs) < 2:
        return m, 0.0
    half = 1.96 * statistics.stdev(xs) / math.sqrt(len(xs))
    return m, half


def main() -> None:
    results = json.loads((HERE / "outputs" / "pilot_results_univ.json").read_text())
    entities = {e["id"]: e for e in json.loads(
        (HERE / "inputs" / "univ_entities.json").read_text())}
    main_models = {m["id"] for m in json.loads(
        (REPO / "data" / "inputs" / "model_set.json").read_text())}
    survivors = main_models - DEAD_MODELS

    per_entity_full = defaultdict(list)
    per_entity_surv = defaultdict(list)
    per_entity_refusal = defaultdict(list)
    for r in results:
        per_entity_full[r["entity_id"]].append(r["score"])
        per_entity_refusal[r["entity_id"]].append(r["is_refusal"])
        if r["model_id"] in survivors:
            per_entity_surv[r["entity_id"]].append(r["score"])

    nr_full = {eid: statistics.mean(v) for eid, v in per_entity_full.items()}
    nr_surv = {eid: statistics.mean(v) for eid, v in per_entity_surv.items()}

    # control anchoring: in-run survivor-panel score vs released main-run score
    released = {r["entity_id"]: float(r["namerank"]) for r in csv.DictReader(
        open(REPO / "data" / "analysis" / "namerank_per_entity.csv"))}
    anchor = {}
    for grp, coh in (("control_openalex", "long_tail_researcher_openalex"),
                     ("control_imo", "imo_gold")):
        ids = [eid for eid, e in entities.items()
               if e.get("control") and e["cohort"] == coh and eid in nr_surv]
        inrun = [nr_surv[eid] for eid in ids]
        rel = [released[eid] for eid in ids]
        anchor[grp] = {
            "n": len(ids),
            "inrun_survivor_mean": round(statistics.mean(inrun), 4),
            "released_mean": round(statistics.mean(rel), 4),
            "shift": round(statistics.mean(inrun) - statistics.mean(rel), 4),
        }

    cohorts = defaultdict(list)
    for eid, e in entities.items():
        if eid in nr_surv:
            cohorts[e["cohort"]].append(eid)

    table = {}
    for coh, ids in sorted(cohorts.items()):
        surv = [nr_surv[i] for i in ids]
        full = [nr_full[i] for i in ids]
        ref = [statistics.mean(per_entity_refusal[i]) for i in ids]
        ms, hs = mean_ci(surv)
        mf, hf = mean_ci(full)
        table[coh] = {
            "n": len(ids),
            "survivor28_mean": round(ms, 4), "survivor28_ci95": round(hs, 4),
            "full36_mean": round(mf, 4), "full36_ci95": round(hf, 4),
            "refusal_rate": round(statistics.mean(ref), 3),
        }

    out = {"anchor": anchor, "cohorts": table,
           "n_records": len(results),
           "n_models_full": len({r["model_id"] for r in results}),
           "n_models_survivor": len(survivors)}
    (HERE / "outputs" / "summary.json").write_text(json.dumps(out, indent=1))

    print(f"records: {len(results):,}")
    print("\nAnchoring (in-run survivor panel vs released main run):")
    for g, a in anchor.items():
        print(f"  {g}: n={a['n']}  in-run {a['inrun_survivor_mean']:.3f} "
              f"vs released {a['released_mean']:.3f}  (shift {a['shift']:+.3f})")
    print(f"\n{'cohort':28s} {'n':>4s} {'surv28':>7s} {'±CI':>6s} "
          f"{'full36':>7s} {'refusal':>8s}")
    for coh, t in sorted(table.items(), key=lambda kv: -kv[1]["survivor28_mean"]):
        print(f"{coh:28s} {t['n']:4d} {t['survivor28_mean']:7.3f} "
              f"{t['survivor28_ci95']:6.3f} {t['full36_mean']:7.3f} "
              f"{t['refusal_rate']:8.1%}")


if __name__ == "__main__":
    main()
