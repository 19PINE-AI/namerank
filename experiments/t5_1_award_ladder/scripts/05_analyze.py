"""Analyze the award-ladder run.

Outputs:
  outputs/award_namerank.csv  — per-entity NameRank, refusal rate, metadata
  outputs/cohort_summary.csv  — per-cohort ladder vs the in-run baseline
  outputs/analysis.json       — regressions, career-stage contrast, websites
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
INP, OUT = HERE / "inputs", HERE / "outputs"

STAGE_ORDER = {"early": 0, "mid": 1, "late": 2}


def ols_r2(X: np.ndarray, y: np.ndarray) -> tuple[float, np.ndarray]:
    X1 = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(X1, y, rcond=None)
    resid = y - X1 @ beta
    ss_res = float(resid @ resid)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return 1 - ss_res / ss_tot, beta


def main() -> None:
    entities = {e["id"]: e for e in json.loads((INP / "award_entities.json").read_text())}
    records = json.loads((OUT / "pilot_results_awards.json").read_text())

    per_ent = defaultdict(list)
    per_ent_refusal = defaultdict(list)
    for r in records:
        per_ent[r["entity_id"]].append(r["score"])
        per_ent_refusal[r["entity_id"]].append(int(r["is_refusal"]))

    rows = []
    for eid, scores in per_ent.items():
        e = entities[eid]
        rows.append({
            "id": eid, "name": e["name"], "cohort": e["cohort"],
            "career_stage": e.get("career_stage"),
            "award_year": e.get("award_year"),
            "control": e.get("control", False),
            "gold_source": e.get("gold_source"),
            "h_index": e.get("h_index"),
            "namerank": float(np.mean(scores)),
            "n_models": len(scores),
            "refusal_rate": float(np.mean(per_ent_refusal[eid])),
        })
    rows.sort(key=lambda r: (-r["namerank"]))
    with open(OUT / "award_namerank.csv", "w", encoding="utf-8") as f:
        f.write("id,name,cohort,career_stage,award_year,control,gold_source,"
                "h_index,namerank,n_models,refusal_rate\n")
        for r in rows:
            f.write(f'{r["id"]},"{r["name"]}",{r["cohort"]},{r["career_stage"]},'
                    f'{r["award_year"]},{int(r["control"])},{r["gold_source"]},'
                    f'{r["h_index"]},{r["namerank"]:.4f},{r["n_models"]},'
                    f'{r["refusal_rate"]:.3f}\n')

    by_cohort = defaultdict(list)
    for r in rows:
        by_cohort[r["cohort"]].append(r)
    baseline = float(np.mean([r["namerank"] for r in by_cohort["long_tail_researcher_openalex"]]))

    cohort_rows = []
    for cid, rs in sorted(by_cohort.items(), key=lambda kv: -np.mean([r["namerank"] for r in kv[1]])):
        vals = np.array([r["namerank"] for r in rs])
        yrs = [r["award_year"] for r in rs if r["award_year"]]
        yr_corr = None
        if len(yrs) >= 10 and len(set(yrs)) > 3:
            sub = np.array([(r["award_year"], r["namerank"]) for r in rs if r["award_year"]], dtype=float)
            yr_corr = float(np.corrcoef(sub[:, 0], sub[:, 1])[0, 1])
        cohort_rows.append({
            "cohort": cid, "n": len(rs),
            "career_stage": rs[0]["career_stage"],
            "mean": float(vals.mean()),
            "sem": float(vals.std(ddof=1) / math.sqrt(len(vals))) if len(vals) > 1 else None,
            "median": float(np.median(vals)),
            "vs_baseline": float(vals.mean() - baseline),
            "refusal": float(np.mean([r["refusal_rate"] for r in rs])),
            "year_namerank_corr": yr_corr,
        })
    with open(OUT / "cohort_summary.csv", "w", encoding="utf-8") as f:
        f.write("cohort,n,career_stage,mean,sem,median,vs_baseline,refusal,year_corr\n")
        for c in cohort_rows:
            sem = "" if c["sem"] is None else f'{c["sem"]:.4f}'
            ycorr = "" if c["year_namerank_corr"] is None else f'{c["year_namerank_corr"]:.3f}'
            f.write(f'{c["cohort"]},{c["n"]},{c["career_stage"]},{c["mean"]:.4f},'
                    f'{sem},{c["median"]:.4f},{c["vs_baseline"]:+.4f},'
                    f'{c["refusal"]:.3f},{ycorr}\n')

    # Marginal-predictor regression on the pooled researcher set with h-index
    pool = [r for r in rows if r["h_index"]
            and r["cohort"] != "imo_gold"
            and not (r["cohort"] == "long_tail_researcher_openalex" and r["h_index"] is None)]
    # OpenAlex controls carry h_index in entity metadata too
    reg = {}
    if len(pool) > 50:
        y = np.array([r["namerank"] for r in pool])
        logh = np.log10(np.array([r["h_index"] for r in pool], dtype=float))
        award_flag = np.array([0.0 if r["control"] else 1.0 for r in pool])
        late_flag = np.array([1.0 if r["career_stage"] == "late" else 0.0 for r in pool])
        r2_h, _ = ols_r2(logh.reshape(-1, 1), y)
        r2_award, _ = ols_r2(award_flag.reshape(-1, 1), y)
        r2_joint, beta_joint = ols_r2(np.column_stack([logh, award_flag]), y)
        r2_full, beta_full = ols_r2(np.column_stack([logh, award_flag, late_flag]), y)
        reg = {"n": len(pool), "r2_logh": r2_h, "r2_award_flag": r2_award,
               "r2_joint": r2_joint, "award_marginal_r2": r2_joint - r2_h,
               "beta_joint_[const,logh,award]": [float(b) for b in beta_joint],
               "r2_full_with_late": r2_full,
               "beta_full_[const,logh,award,late]": [float(b) for b in beta_full]}

    websites = {r["name"]: round(r["namerank"], 3) for r in rows
                if r["cohort"] in ("website_or_service", "reference_pilot")
                or r["id"] in ("tuixue_online", "nanogpt")}

    stage_means = {}
    for stage in ("early", "mid", "late"):
        vals = [r["namerank"] for r in rows if r["career_stage"] == stage]
        if vals:
            stage_means[stage] = {"n": len(vals), "mean": float(np.mean(vals))}

    analysis = {
        "baseline_openalex_inrun": baseline,
        "imo_gold_inrun": float(np.mean([r["namerank"] for r in by_cohort["imo_gold"]])),
        "cohorts": cohort_rows,
        "career_stage_means": stage_means,
        "hindex_regression": reg,
        "websites": websites,
    }
    (OUT / "analysis.json").write_text(json.dumps(analysis, indent=1))
    print(json.dumps({k: v for k, v in analysis.items() if k != "cohorts"}, indent=1))
    print("\nLadder:")
    for c in cohort_rows:
        print(f'  {c["cohort"]:32s} n={c["n"]:3d} mean={c["mean"]:.3f} '
              f'vs_baseline={c["vs_baseline"]:+.3f}')


if __name__ == "__main__":
    main()
