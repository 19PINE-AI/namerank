"""Combine T0 (existing data) with T1/T2/T3 (this experiment) for the
200 stratified entities, then run all required analyses.

Outputs (written to t2_6_prompt_sensitivity/):
  combined_records.csv
  variance_decomposition.csv
  per_entity_template_correlation.csv
  cohort_means_per_template.csv
  within_cell_sigma.csv
  panel_mean_vs_template_variance.csv
  summary.json

NameRank per (entity, template) = mean(score) across the 37 panel models.
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
INPUTS = HERE / "inputs"

OUT_FILES = {
    "combined": HERE / "combined_records.csv",
    "var_decomp": HERE / "variance_decomposition.csv",
    "per_ent_corr": HERE / "per_entity_template_correlation.csv",
    "cohort_means": HERE / "cohort_means_per_template.csv",
    "within_cell": HERE / "within_cell_sigma.csv",
    "panel_vs_template": HERE / "panel_mean_vs_template_variance.csv",
    "summary": HERE / "summary.json",
}


def load_t0_for_subset(entity_ids: set[str]) -> list[dict]:
    """Pull T0 records for the 200 entities from the master pilot_summary.

    NOTE: always prefer the .csv.gz (immutable, released). The plain .csv may
    be overwritten by concurrent run_probe.py invocations from other
    experiments.
    """
    raw_gz = REPO / "data" / "raw" / "pilot_summary_en.csv.gz"
    raw_plain = REPO / "data" / "raw" / "pilot_summary_en.csv"
    if raw_gz.exists():
        fh = io.TextIOWrapper(gzip.open(raw_gz, "rb"), encoding="utf-8")
    else:
        fh = open(raw_plain, "r", encoding="utf-8")
    rows = []
    with fh as f:
        for r in csv.DictReader(f):
            if r["entity_id"] in entity_ids:
                rows.append({
                    "entity_id": r["entity_id"],
                    "entity_name": r["entity_name"],
                    "model_id": r["model_id"],
                    "template": "T0",
                    "is_refusal": int(r["is_refusal"]),
                    "score": float(r["score"]),
                })
    return rows


def load_template_outputs(tag: str) -> list[dict]:
    p = HERE / f"outputs_{tag}" / "pilot_summary.csv"
    rows = []
    with open(p, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                "entity_id": r["entity_id"],
                "entity_name": r["entity_name"],
                "model_id": r["model_id"],
                "template": tag,
                "is_refusal": int(r["is_refusal"]),
                "score": float(r["score"]),
            })
    return rows


def pearson(xs, ys) -> float:
    n = len(xs)
    if n < 2:
        return float("nan")
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return float("nan")
    return sxy / math.sqrt(sxx * syy)


def main() -> None:
    entities = json.loads((INPUTS / "pilot_entities.json").read_text())
    ent_meta = {e["id"]: e for e in entities}
    entity_ids = set(ent_meta)

    # --- gather ---
    t0 = load_t0_for_subset(entity_ids)
    t1 = load_template_outputs("T1")
    t2 = load_template_outputs("T2")
    t3 = load_template_outputs("T3")
    all_rows = t0 + t1 + t2 + t3
    print(f"T0={len(t0)}  T1={len(t1)}  T2={len(t2)}  T3={len(t3)}  total={len(all_rows)}")

    # --- combined_records.csv ---
    with open(OUT_FILES["combined"], "w", encoding="utf-8") as f:
        f.write("entity_id,entity_name,model_id,template,is_refusal,score,cohort\n")
        for r in all_rows:
            cohort = ent_meta.get(r["entity_id"], {}).get("cohort", "?")
            nm = r["entity_name"].replace('"', '""')
            f.write(f'{r["entity_id"]},"{nm}",{r["model_id"]},{r["template"]},'
                    f'{r["is_refusal"]},{r["score"]:.4f},{cohort}\n')

    # --- variance decomposition (Eq. 1) ---
    n = len(all_rows)
    grand = sum(r["score"] for r in all_rows) / n
    total_ss = sum((r["score"] - grand) ** 2 for r in all_rows)

    def marg(key_fn):
        bag = defaultdict(list)
        for r in all_rows:
            bag[key_fn(r)].append(r["score"])
        means = {k: sum(v)/len(v) for k, v in bag.items()}
        counts = {k: len(v) for k, v in bag.items()}
        ss = sum(counts[k] * (means[k] - grand) ** 2 for k in means)
        return ss, means, counts

    ss_entity, _, _ = marg(lambda r: r["entity_id"])
    ss_model, _, _ = marg(lambda r: r["model_id"])
    ss_template, mean_template, _ = marg(lambda r: r["template"])
    ss_cohort, _, _ = marg(lambda r: ent_meta.get(r["entity_id"], {}).get("cohort", "?"))

    # Type-III-ish: subtract main effects of all three to estimate residual
    # We'll use a simple additive model: y_ijk = mu + a_i + b_j + c_k + e
    # OLS via group means (unbalanced but here perfectly balanced: 200x37x4).
    # Residual after entity+model+template:
    ent_mean = defaultdict(list)
    mod_mean = defaultdict(list)
    tpl_mean = defaultdict(list)
    for r in all_rows:
        ent_mean[r["entity_id"]].append(r["score"])
        mod_mean[r["model_id"]].append(r["score"])
        tpl_mean[r["template"]].append(r["score"])
    ent_mean = {k: sum(v)/len(v) for k, v in ent_mean.items()}
    mod_mean = {k: sum(v)/len(v) for k, v in mod_mean.items()}
    tpl_mean = {k: sum(v)/len(v) for k, v in tpl_mean.items()}

    resid_ss = 0.0
    for r in all_rows:
        pred = (ent_mean[r["entity_id"]] - grand) + (mod_mean[r["model_id"]] - grand) \
               + (tpl_mean[r["template"]] - grand) + grand
        resid_ss += (r["score"] - pred) ** 2

    with open(OUT_FILES["var_decomp"], "w", encoding="utf-8") as f:
        f.write("factor,SS,pct_of_total\n")
        f.write(f"total,{total_ss:.4f},100.00\n")
        f.write(f"entity,{ss_entity:.4f},{100*ss_entity/total_ss:.2f}\n")
        f.write(f"model,{ss_model:.4f},{100*ss_model/total_ss:.2f}\n")
        f.write(f"template,{ss_template:.4f},{100*ss_template/total_ss:.2f}\n")
        f.write(f"cohort,{ss_cohort:.4f},{100*ss_cohort/total_ss:.2f}\n")
        f.write(f"residual_after_main_effects,{resid_ss:.4f},"
                f"{100*resid_ss/total_ss:.2f}\n")

    print(f"\nVariance decomposition (n={n}, grand={grand:.4f}):")
    print(f"  entity  SS = {ss_entity:8.2f}  ({100*ss_entity/total_ss:5.2f}%)")
    print(f"  model   SS = {ss_model:8.2f}  ({100*ss_model/total_ss:5.2f}%)")
    print(f"  template SS= {ss_template:8.2f}  ({100*ss_template/total_ss:5.2f}%)")
    print(f"  cohort  SS = {ss_cohort:8.2f}  ({100*ss_cohort/total_ss:5.2f}%)")
    print(f"  resid   SS = {resid_ss:8.2f}  ({100*resid_ss/total_ss:5.2f}%)")
    print(f"  template-mean by tag: {mean_template}")

    # --- per (entity, model) within-template sigma ---
    cell = defaultdict(list)
    for r in all_rows:
        cell[(r["entity_id"], r["model_id"])].append(r["score"])
    cell_sigmas = []
    with open(OUT_FILES["within_cell"], "w", encoding="utf-8") as f:
        f.write("entity_id,model_id,n_obs,mean,sigma\n")
        for (eid, mid), scores in cell.items():
            if len(scores) >= 2:
                mu = sum(scores) / len(scores)
                sd = statistics.pstdev(scores)
                cell_sigmas.append(sd)
                f.write(f"{eid},{mid},{len(scores)},{mu:.4f},{sd:.4f}\n")
    sigs = sorted(cell_sigmas)
    median = sigs[len(sigs)//2]
    p90 = sigs[int(0.9 * len(sigs))]
    p95 = sigs[int(0.95 * len(sigs))]
    mean_sig = sum(sigs) / len(sigs)
    print(f"\nWithin-(entity,model) sigma across templates "
          f"(n={len(sigs)} cells):")
    print(f"  mean={mean_sig:.4f}  median={median:.4f}  "
          f"p90={p90:.4f}  p95={p95:.4f}")

    # --- per-entity NameRank per template, and pairwise Pearson ---
    nr = defaultdict(lambda: defaultdict(list))  # nr[entity][template] = [scores]
    for r in all_rows:
        nr[r["entity_id"]][r["template"]].append(r["score"])
    per_entity_nr = {}  # eid -> {T0,T1,T2,T3}
    for eid, by_t in nr.items():
        per_entity_nr[eid] = {t: sum(s)/len(s) for t, s in by_t.items()}

    templates = ["T0", "T1", "T2", "T3"]
    eids_sorted = sorted(per_entity_nr.keys())
    rows_pe = []
    for eid in eids_sorted:
        row = {"entity_id": eid, "cohort": ent_meta[eid].get("cohort", "?")}
        for t in templates:
            row[t] = per_entity_nr[eid].get(t, float("nan"))
        rows_pe.append(row)

    with open(OUT_FILES["per_ent_corr"], "w", encoding="utf-8") as f:
        f.write("entity_id,cohort,NR_T0,NR_T1,NR_T2,NR_T3\n")
        for row in rows_pe:
            f.write(f'{row["entity_id"]},{row["cohort"]},'
                    f'{row["T0"]:.4f},{row["T1"]:.4f},'
                    f'{row["T2"]:.4f},{row["T3"]:.4f}\n')

    # pairwise Pearson
    pair_r = {}
    for i, ti in enumerate(templates):
        for tj in templates[i+1:]:
            xs = [per_entity_nr[e][ti] for e in eids_sorted]
            ys = [per_entity_nr[e][tj] for e in eids_sorted]
            pair_r[f"{ti}_{tj}"] = pearson(xs, ys)
    print("\nPer-entity NR pairwise Pearson (panel-mean per template):")
    for k, v in pair_r.items():
        print(f"  r({k}) = {v:.4f}")

    # --- panel-mean variance vs cross-model variance per entity ---
    # (a) Var of single-model NR scores across 37 models per entity (per template T0 only, mirror paper)
    # (b) Var of panel-mean NR across 4 templates per entity
    cross_model_var_T0 = {}
    for eid in eids_sorted:
        # gather single-model means at T0 (per cell mean across templates? No, paper uses single template)
        # Here: at T0, cell mean equals the single score (1 obs); so var across models at T0:
        scores_T0 = [r["score"] for r in all_rows if r["entity_id"] == eid and r["template"] == "T0"]
        if len(scores_T0) >= 2:
            cross_model_var_T0[eid] = statistics.pvariance(scores_T0)
    panel_mean_var = {}
    for eid in eids_sorted:
        nrs = [per_entity_nr[eid][t] for t in templates if t in per_entity_nr[eid]]
        if len(nrs) >= 2:
            panel_mean_var[eid] = statistics.pvariance(nrs)

    with open(OUT_FILES["panel_vs_template"], "w", encoding="utf-8") as f:
        f.write("entity_id,cohort,var_cross_model_T0,var_panel_mean_across_templates,ratio\n")
        for eid in eids_sorted:
            a = cross_model_var_T0.get(eid, float("nan"))
            b = panel_mean_var.get(eid, float("nan"))
            if a and a > 0 and not math.isnan(a) and not math.isnan(b):
                ratio = b / a
            else:
                ratio = float("nan")
            f.write(f"{eid},{ent_meta[eid].get('cohort','?')},"
                    f"{a:.6f},{b:.6f},{ratio:.6f}\n")

    a_vals = [v for v in cross_model_var_T0.values() if not math.isnan(v)]
    b_vals = [v for v in panel_mean_var.values() if not math.isnan(v)]
    print(f"\nVariance comparison per entity (n={len(a_vals)} entities):")
    print(f"  median cross-model var (T0)         = {statistics.median(a_vals):.5f}")
    print(f"  median panel-mean var across templates = {statistics.median(b_vals):.5f}")
    print(f"  ratio (panel-mean var / cross-model var) median = "
          f"{statistics.median([panel_mean_var[e]/cross_model_var_T0[e] for e in eids_sorted if cross_model_var_T0.get(e,0)>0]):.4f}")

    # --- cohort means per template ---
    cohort_t = defaultdict(lambda: defaultdict(list))
    for eid in eids_sorted:
        c = ent_meta[eid].get("cohort", "?")
        for t in templates:
            cohort_t[c][t].append(per_entity_nr[eid][t])
    with open(OUT_FILES["cohort_means"], "w", encoding="utf-8") as f:
        f.write("cohort,n_entities,NR_T0,NR_T1,NR_T2,NR_T3,range\n")
        cohort_rows = []
        for c, by_t in cohort_t.items():
            n_e = len(by_t["T0"])
            means_c = {t: sum(by_t[t])/len(by_t[t]) for t in templates}
            r_range = max(means_c.values()) - min(means_c.values())
            cohort_rows.append((c, n_e, means_c, r_range))
        cohort_rows.sort(key=lambda x: -x[2]["T0"])
        for c, n_e, m, rng in cohort_rows:
            f.write(f"{c},{n_e},{m['T0']:.4f},{m['T1']:.4f},"
                    f"{m['T2']:.4f},{m['T3']:.4f},{rng:.4f}\n")
    print("\nCohort means per template:")
    for c, n_e, m, rng in cohort_rows:
        print(f"  {c:35s} n={n_e:3d}  T0={m['T0']:.3f} T1={m['T1']:.3f} "
              f"T2={m['T2']:.3f} T3={m['T3']:.3f}  range={rng:.3f}")

    # cohort-ordering check: Spearman-ish by Pearson on ranks
    cohort_keys = [c for c, *_ in cohort_rows]
    cohort_order = {t: sorted(cohort_keys, key=lambda c: -(
        sum(cohort_t[c][t]) / len(cohort_t[c][t]))) for t in templates}

    # --- summary.json ---
    summary = {
        "n_records": n,
        "n_entities": len(eids_sorted),
        "n_models": len(set(r["model_id"] for r in all_rows)),
        "templates": templates,
        "grand_mean": grand,
        "total_SS": total_ss,
        "SS": {
            "entity": ss_entity, "model": ss_model,
            "template": ss_template, "cohort": ss_cohort,
            "residual_after_main_effects": resid_ss,
        },
        "pct_of_total": {
            "entity": 100 * ss_entity / total_ss,
            "model": 100 * ss_model / total_ss,
            "template": 100 * ss_template / total_ss,
            "cohort": 100 * ss_cohort / total_ss,
            "residual_after_main_effects": 100 * resid_ss / total_ss,
        },
        "template_means": tpl_mean,
        "within_cell_sigma": {
            "mean": mean_sig, "median": median, "p90": p90, "p95": p95,
            "n_cells": len(sigs),
        },
        "pairwise_pearson_panel_mean_NR": pair_r,
        "variance_ratio_panel_to_cross_model": {
            "median_b_over_a":
                statistics.median([panel_mean_var[e]/cross_model_var_T0[e]
                                   for e in eids_sorted
                                   if cross_model_var_T0.get(e, 0) > 0]),
            "median_cross_model_var_T0": statistics.median(a_vals),
            "median_panel_mean_var_across_templates": statistics.median(b_vals),
        },
        "cohort_ordering": cohort_order,
    }
    OUT_FILES["summary"].write_text(json.dumps(summary, indent=2))
    print(f"\nWrote summary -> {OUT_FILES['summary']}")


if __name__ == "__main__":
    main()
