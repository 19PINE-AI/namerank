"""Aggregate arm-B probe results and compute Δ vs. arm-A.

Outputs (under experiments/t1_2_context_ab/):
  delta_per_entity.csv          per-entity (id, name, cohort, NR_A, NR_B, delta, refusal_A, refusal_B)
  delta_per_cohort.csv          cohort-level summary
  stanford_tsinghua_test.csv    focused test on the 60-ish CS-faculty entities
"""
from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path("/home/ubuntu/namerank")
EXP = ROOT / "experiments" / "t1_2_context_ab"
INPUTS_A = ROOT / "data" / "inputs"
OUTPUTS_B = EXP / "outputs_B"
NR_A_CSV = ROOT / "data" / "analysis" / "namerank_per_entity.csv"


def aggregate_b() -> tuple[dict, dict]:
    """Return (per_entity_namerank_b, per_entity_refusal_rate_b)."""
    records = json.loads((OUTPUTS_B / "pilot_results_en.json").read_text())
    scores: dict[str, list[float]] = defaultdict(list)
    refusals: dict[str, list[int]] = defaultdict(list)
    for r in records:
        eid = r["entity_id"]
        scores[eid].append(float(r.get("score") or 0.0))
        refusals[eid].append(1 if r.get("is_refusal") else 0)
    nr_b = {eid: sum(v) / len(v) for eid, v in scores.items()}
    ref_b = {eid: sum(v) / len(v) for eid, v in refusals.items()}
    return nr_b, ref_b


def load_a() -> tuple[dict, dict]:
    """Return (NR_A, refusal_A) keyed by entity id."""
    nr_a, ref_a = {}, {}
    with open(NR_A_CSV) as f:
        for r in csv.DictReader(f):
            nr_a[r["entity_id"]] = float(r["namerank"])
            ref_a[r["entity_id"]] = float(r["refusal_rate"])
    return nr_a, ref_a


def main() -> None:
    entities = json.loads((EXP / "inputs_B" / "pilot_entities.json").read_text())
    by_id = {e["id"]: e for e in entities}
    # Also load arm-A entities for institutional info
    a_entities = {e["id"]: e for e in json.loads(
        (INPUTS_A / "pilot_entities.json").read_text())}

    nr_b, ref_b = aggregate_b()
    nr_a, ref_a = load_a()

    rows = []
    for e in entities:
        eid = e["id"]
        if eid not in nr_b:
            print(f"WARN: no B-arm score for {eid}")
            continue
        if eid not in nr_a:
            print(f"WARN: no A-arm score for {eid}")
            continue
        rows.append({
            "entity_id": eid,
            "entity_name": e["name"],
            "cohort": e["cohort"],
            "institution": a_entities.get(eid, {}).get("institution", ""),
            "NR_A": round(nr_a[eid], 4),
            "NR_B": round(nr_b[eid], 4),
            "delta": round(nr_b[eid] - nr_a[eid], 4),
            "refusal_A": round(ref_a[eid], 3),
            "refusal_B": round(ref_b[eid], 3),
        })

    # delta_per_entity.csv (sorted by most negative delta first)
    rows.sort(key=lambda r: r["delta"])
    with open(EXP / "delta_per_entity.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows -> delta_per_entity.csv")

    # delta_per_cohort.csv
    by_cohort: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_cohort[r["cohort"]].append(r)
    cohort_rows = []
    for cohort, rs in sorted(by_cohort.items()):
        nrA = [r["NR_A"] for r in rs]
        nrB = [r["NR_B"] for r in rs]
        deltas = [r["delta"] for r in rs]
        rA = [r["refusal_A"] for r in rs]
        rB = [r["refusal_B"] for r in rs]
        cohort_rows.append({
            "cohort": cohort,
            "n": len(rs),
            "NR_A_mean": round(statistics.mean(nrA), 4),
            "NR_B_mean": round(statistics.mean(nrB), 4),
            "delta_mean": round(statistics.mean(deltas), 4),
            "delta_sd": round(statistics.stdev(deltas) if len(deltas) > 1 else 0.0, 4),
            "delta_median": round(statistics.median(deltas), 4),
            "refusal_A_mean": round(statistics.mean(rA), 4),
            "refusal_B_mean": round(statistics.mean(rB), 4),
            "refusal_delta": round(statistics.mean(rB) - statistics.mean(rA), 4),
        })
    cohort_rows.sort(key=lambda r: r["delta_mean"])
    with open(EXP / "delta_per_cohort.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(cohort_rows[0].keys()))
        w.writeheader()
        w.writerows(cohort_rows)
    print("Wrote delta_per_cohort.csv")

    # stanford_tsinghua_test.csv: per-institution under A and B
    inst_target = {"Stanford University", "Carnegie Mellon University",
                   "Tsinghua University", "Peking University"}
    inst_rows: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r["cohort"] != "cs_faculty":
            continue
        inst = r["institution"]
        if inst in inst_target:
            inst_rows[inst].append(r)
    inst_csv_rows = []
    for inst, rs in inst_rows.items():
        nrA = [r["NR_A"] for r in rs]
        nrB = [r["NR_B"] for r in rs]
        deltas = [r["delta"] for r in rs]
        inst_csv_rows.append({
            "institution": inst,
            "n": len(rs),
            "NR_A_mean": round(statistics.mean(nrA), 4),
            "NR_A_sd": round(statistics.stdev(nrA) if len(nrA) > 1 else 0.0, 4),
            "NR_B_mean": round(statistics.mean(nrB), 4),
            "NR_B_sd": round(statistics.stdev(nrB) if len(nrB) > 1 else 0.0, 4),
            "delta_mean": round(statistics.mean(deltas), 4),
        })
    # Order: Stanford, CMU, Tsinghua, Peking
    order = ["Stanford University", "Carnegie Mellon University",
             "Tsinghua University", "Peking University"]
    inst_csv_rows.sort(key=lambda r: order.index(r["institution"])
                       if r["institution"] in order else 99)

    # Gap rows
    def gap(inst1: str, inst2: str) -> dict | None:
        a = next((r for r in inst_csv_rows if r["institution"] == inst1), None)
        b = next((r for r in inst_csv_rows if r["institution"] == inst2), None)
        if not a or not b:
            return None
        return {
            "comparison": f"{inst1} vs. {inst2}",
            "gap_A": round(a["NR_A_mean"] - b["NR_A_mean"], 4),
            "gap_B": round(a["NR_B_mean"] - b["NR_B_mean"], 4),
            "absolute_shrinkage": round((a["NR_A_mean"] - b["NR_A_mean"]) -
                                        (a["NR_B_mean"] - b["NR_B_mean"]), 4),
            "relative_shrinkage_pct": round(
                100 * (1.0 - (a["NR_B_mean"] - b["NR_B_mean"]) /
                       (a["NR_A_mean"] - b["NR_A_mean"]))
                if (a["NR_A_mean"] - b["NR_A_mean"]) != 0 else 0.0, 2),
        }

    gaps = [g for g in [
        gap("Stanford University", "Tsinghua University"),
        gap("Stanford University", "Peking University"),
        gap("Carnegie Mellon University", "Tsinghua University"),
        gap("Stanford University", "Carnegie Mellon University"),
    ] if g]

    with open(EXP / "stanford_tsinghua_test.csv", "w", newline="", encoding="utf-8") as f:
        # First block: per-institution stats
        w = csv.DictWriter(f, fieldnames=["institution", "n",
                                          "NR_A_mean", "NR_A_sd",
                                          "NR_B_mean", "NR_B_sd",
                                          "delta_mean"])
        w.writeheader()
        for r in inst_csv_rows:
            w.writerow(r)
        if gaps:
            f.write("\n# Institutional gaps (NR_A_mean[i] - NR_A_mean[j])\n")
            gw = csv.DictWriter(f, fieldnames=list(gaps[0].keys()))
            gw.writeheader()
            for g in gaps:
                gw.writerow(g)
        else:
            f.write("\n# (No institutional gap rows: required institutions absent from arm-B output)\n")
    print("Wrote stanford_tsinghua_test.csv")

    # Print headline summary
    print("\n=== HEADLINE ===")
    for r in cohort_rows:
        print(f"  {r['cohort']:<35s} n={r['n']:>3d}  "
              f"NR_A={r['NR_A_mean']:.3f}  NR_B={r['NR_B_mean']:.3f}  "
              f"Δ={r['delta_mean']:+.3f}  refΔ={r['refusal_delta']:+.3f}")

    print("\n=== INSTITUTIONAL GAPS ===")
    for r in inst_csv_rows:
        print(f"  {r['institution']:<35s} n={r['n']:>3d}  "
              f"A={r['NR_A_mean']:.3f}  B={r['NR_B_mean']:.3f}  "
              f"Δ={r['delta_mean']:+.3f}")
    print()
    for g in gaps:
        print(f"  {g['comparison']:<60s} gap_A={g['gap_A']:+.3f} "
              f"gap_B={g['gap_B']:+.3f}  shrink_abs={g['absolute_shrinkage']:+.3f} "
              f"({g['relative_shrinkage_pct']:.1f}%)")

    # Reference pilot stability
    print("\n=== REFERENCE PILOT (10 anchors) ===")
    ref_rows = [r for r in rows if r["cohort"] == "reference_pilot"]
    ref_rows.sort(key=lambda r: r["delta"])
    for r in ref_rows:
        print(f"  {r['entity_name']:<25s}  A={r['NR_A']:.3f}  "
              f"B={r['NR_B']:.3f}  Δ={r['delta']:+.3f}")


if __name__ == "__main__":
    main()
