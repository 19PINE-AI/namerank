"""T3.1 — Training-cutoff gradient: is the NameRank "silent zone" a corpus-
TIMING effect rather than an intrinsic-obscurity effect?

Design. Two cohorts are "first-appearance" cohorts whose members became
nameable in *any* indexable corpus only on a sharp date:

  * deepseek_v3_author      emergence = 2024-12  (arXiv:2412.19437)
  * gpt5_system_card_author emergence = 2025-08  (OpenAI GPT-5 System Card)

The gold answer for each is literally "X is listed as a contributor on
[document]". A model whose training cutoff PREDATES the emergence date
cannot possibly have absorbed that document, so it must refuse or
hallucinate. A model whose cutoff POSTDATES it can at least reproduce the
contributor fact. If NameRank's silent zone is a timing effect, recognition
of these cohorts should jump at the emergence date and rise with cutoff.

Controls. Every other cohort's members were nameable long before any model
cutoff (2023-10 .. 2026-03). Their recognition should be ~flat in cutoff
apart from a smooth capability/generosity drift. The difference between the
recency-cohort slope and the control-cohort slope (difference-in-
differences) isolates corpus-timing from general model capability.

Reads only released artifacts:
  data/raw/pilot_summary_en.csv.gz
  data/inputs/pilot_entities.json
  data/analysis/model_cutoffs.json

Writes:
  outputs/per_model_cohort_means.csv   one row per (model, cohort): mean score, refusal, cutoff
  outputs/cohort_cutoff_slopes.csv     per cohort: slope of mean-score on cutoff-month, Pearson r
  outputs/natural_experiment.csv       pre/post split for the two recency cohorts + a control
  outputs/did.csv                      difference-in-differences (recency gap vs cutoff)
  outputs/summary.json
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
OUT = HERE / "outputs"

RECENCY = {
    "deepseek_v3_author": "2024-12",
    "gpt5_system_card_author": "2025-08",
}
# Stable control cohorts: established researchers/individuals nameable well
# before any cutoff. Used for the difference-in-differences baseline.
STABLE_CONTROL = [
    "cs_faculty",
    "long_tail_researcher_openalex",
    "imo_gold",
]


def ym_to_month(ym: str) -> int:
    """'2025-08' -> integer month index (months since 2000-01)."""
    y, m = ym.split("-")
    return (int(y) - 2000) * 12 + (int(m) - 1)


def pearson(xs, ys):
    n = len(xs)
    if n < 2:
        return float("nan")
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return float("nan")
    return sxy / math.sqrt(sxx * syy)


def ols_slope(xs, ys):
    """Return (slope, intercept) of y ~ x."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return float("nan"), float("nan")
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    return slope, my - slope * mx


def main() -> None:
    OUT.mkdir(exist_ok=True)

    ents = json.loads((REPO / "data" / "inputs" / "pilot_entities.json").read_text())
    cohort_of = {e["id"]: e.get("cohort", "?") for e in ents}

    cuts = json.loads((REPO / "data" / "analysis" / "model_cutoffs.json").read_text())
    cutoff_ym = {m["id"]: m["training_cutoff"] for m in cuts}
    cutoff_month = {m["id"]: ym_to_month(m["training_cutoff"]) for m in cuts}

    # --- accumulate per (model, cohort): scores + refusals ---
    raw_gz = REPO / "data" / "raw" / "pilot_summary_en.csv.gz"
    agg = defaultdict(lambda: {"scores": [], "refusals": []})
    fh = io.TextIOWrapper(gzip.open(raw_gz, "rb"), encoding="utf-8")
    with fh as f:
        for r in csv.DictReader(f):
            coh = cohort_of.get(r["entity_id"])
            if coh is None:
                continue
            mid = r["model_id"]
            if mid not in cutoff_month:
                continue
            agg[(mid, coh)]["scores"].append(float(r["score"]))
            agg[(mid, coh)]["refusals"].append(int(r["is_refusal"]))

    # --- per (model, cohort) means ---
    cohorts = sorted({c for (_, c) in agg})
    models = sorted(cutoff_month, key=lambda m: cutoff_month[m])

    with open(OUT / "per_model_cohort_means.csv", "w") as f:
        f.write("model_id,cutoff,cutoff_month,cohort,n,mean_score,refusal_rate\n")
        for mid in models:
            for coh in cohorts:
                cell = agg.get((mid, coh))
                if not cell:
                    continue
                ms = sum(cell["scores"]) / len(cell["scores"])
                rr = sum(cell["refusals"]) / len(cell["refusals"])
                f.write(f"{mid},{cutoff_ym[mid]},{cutoff_month[mid]},{coh},"
                        f"{len(cell['scores'])},{ms:.4f},{rr:.4f}\n")

    # --- per-cohort slope of model-mean-score on cutoff month ---
    cohort_slopes = {}
    with open(OUT / "cohort_cutoff_slopes.csv", "w") as f:
        f.write("cohort,n_models,slope_per_year,pearson_r,mean_score\n")
        for coh in cohorts:
            xs, ys = [], []
            for mid in models:
                cell = agg.get((mid, coh))
                if cell:
                    xs.append(cutoff_month[mid])
                    ys.append(sum(cell["scores"]) / len(cell["scores"]))
            if len(xs) < 3:
                continue
            slope, _ = ols_slope(xs, ys)
            r = pearson(xs, ys)
            cohort_slopes[coh] = {"slope_year": slope * 12, "r": r,
                                  "mean": sum(ys) / len(ys), "n_models": len(xs)}
            f.write(f"{coh},{len(xs)},{slope*12:.4f},{r:.4f},"
                    f"{sum(ys)/len(ys):.4f}\n")

    # --- natural-experiment pre/post split for the two recency cohorts ---
    def split_stats(coh, emergence_month, lo_hi_gap=0):
        """Return (pre, post) dicts. lo_hi_gap drops models within the gap
        window around emergence to create a clean pre/post separation."""
        pre_s, post_s, pre_r, post_r = [], [], [], []
        pre_models, post_models = [], []
        for mid in models:
            cell = agg.get((mid, coh))
            if not cell:
                continue
            cm = cutoff_month[mid]
            ms = sum(cell["scores"]) / len(cell["scores"])
            rr = sum(cell["refusals"]) / len(cell["refusals"])
            if cm < emergence_month - lo_hi_gap:
                pre_s.append(ms); pre_r.append(rr); pre_models.append(mid)
            elif cm >= emergence_month + lo_hi_gap:
                post_s.append(ms); post_r.append(rr); post_models.append(mid)
        return (
            {"n": len(pre_s), "mean": _m(pre_s), "refusal": _m(pre_r),
             "models": pre_models},
            {"n": len(post_s), "mean": _m(post_s), "refusal": _m(post_r),
             "models": post_models},
        )

    natexp = {}
    with open(OUT / "natural_experiment.csv", "w") as f:
        f.write("cohort,emergence,group,n_models,mean_score,refusal_rate\n")
        for coh, em in RECENCY.items():
            em_m = ym_to_month(em)
            pre, post = split_stats(coh, em_m)
            natexp[coh] = {"emergence": em, "pre": pre, "post": post,
                           "jump": post["mean"] - pre["mean"],
                           "refusal_drop": pre["refusal"] - post["refusal"]}
            f.write(f"{coh},{em},pre,{pre['n']},{pre['mean']:.4f},{pre['refusal']:.4f}\n")
            f.write(f"{coh},{em},post,{post['n']},{post['mean']:.4f},{post['refusal']:.4f}\n")
        # placebo: same split dates applied to the stable control cohorts
        for coh in STABLE_CONTROL:
            for em in sorted(set(RECENCY.values())):
                em_m = ym_to_month(em)
                pre, post = split_stats(coh, em_m)
                f.write(f"{coh}_PLACEBO@{em},{em},pre,{pre['n']},"
                        f"{pre['mean']:.4f},{pre['refusal']:.4f}\n")
                f.write(f"{coh}_PLACEBO@{em},{em},post,{post['n']},"
                        f"{post['mean']:.4f},{post['refusal']:.4f}\n")

    # --- difference-in-differences ---
    # For each model, gap(m) = R_recency(m) - R_control(m). Regress gap on
    # cutoff. The control absorbs general capability/generosity drift; a
    # positive gap-slope is recency-specific corpus absorption.
    control_mean = {}
    for mid in models:
        vals = []
        for coh in STABLE_CONTROL:
            cell = agg.get((mid, coh))
            if cell:
                vals.append(sum(cell["scores"]) / len(cell["scores"]))
        if vals:
            control_mean[mid] = sum(vals) / len(vals)

    did = {}
    with open(OUT / "did.csv", "w") as f:
        f.write("cohort,slope_recency_per_year,slope_control_per_year,"
                "did_slope_per_year,gap_slope_per_year,gap_pearson_r\n")
        # control slope (shared baseline)
        cxs = [cutoff_month[m] for m in models if m in control_mean]
        cys = [control_mean[m] for m in models if m in control_mean]
        control_slope_year = ols_slope(cxs, cys)[0] * 12
        for coh, em in RECENCY.items():
            xs, ys, gaps = [], [], []
            for mid in models:
                cell = agg.get((mid, coh))
                if cell and mid in control_mean:
                    xs.append(cutoff_month[mid])
                    rm = sum(cell["scores"]) / len(cell["scores"])
                    ys.append(rm)
                    gaps.append(rm - control_mean[mid])
            rec_slope_year = ols_slope(xs, ys)[0] * 12
            gap_slope_year = ols_slope(xs, gaps)[0] * 12
            gap_r = pearson(xs, gaps)
            did[coh] = {
                "slope_recency_year": rec_slope_year,
                "slope_control_year": control_slope_year,
                "did_slope_year": rec_slope_year - control_slope_year,
                "gap_slope_year": gap_slope_year,
                "gap_pearson_r": gap_r,
            }
            f.write(f"{coh},{rec_slope_year:.4f},{control_slope_year:.4f},"
                    f"{rec_slope_year-control_slope_year:.4f},"
                    f"{gap_slope_year:.4f},{gap_r:.4f}\n")

    # --- matched-split difference-in-differences (cleanest estimand) ---
    # (recency_post - recency_pre) - mean_over_controls(control_post - control_pre)
    # using the SAME model split as the recency cohort. This nets out the
    # capability/generosity drift that lifts ALL cohorts across cutoff.
    matched_did = {}
    for coh, em in RECENCY.items():
        em_m = ym_to_month(em)
        r_pre, r_post = split_stats(coh, em_m)
        r_jump = r_post["mean"] - r_pre["mean"]
        ctrl_jumps = []
        for cc in STABLE_CONTROL:
            c_pre, c_post = split_stats(cc, em_m)
            ctrl_jumps.append(c_post["mean"] - c_pre["mean"])
        ctrl_jump = sum(ctrl_jumps) / len(ctrl_jumps)
        matched_did[coh] = {
            "recency_jump": r_jump,
            "control_jump_mean": ctrl_jump,
            "control_jumps": dict(zip(STABLE_CONTROL, ctrl_jumps)),
            "matched_did": r_jump - ctrl_jump,
        }

    summary = {
        "recency_cohorts": RECENCY,
        "stable_control": STABLE_CONTROL,
        "natural_experiment": natexp,
        "matched_did": matched_did,
        "did": did,
        "cohort_slopes_sorted": sorted(
            ({"cohort": c, **v} for c, v in cohort_slopes.items()),
            key=lambda d: -d["slope_year"]),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))

    # --- console report ---
    print("=== Natural experiment: recognition pre/post emergence ===")
    for coh, d in natexp.items():
        print(f"\n{coh}  (emergence {d['emergence']})")
        print(f"  PRE  cutoff ({d['pre']['n']:2d} models): "
              f"mean={d['pre']['mean']:.4f}  refusal={d['pre']['refusal']:.3f}")
        print(f"  POST cutoff ({d['post']['n']:2d} models): "
              f"mean={d['post']['mean']:.4f}  refusal={d['post']['refusal']:.3f}")
        print(f"  JUMP in mean score = {d['jump']:+.4f}   "
              f"refusal drop = {d['refusal_drop']:+.3f}")

    print("\n=== Matched-split difference-in-differences (headline) ===")
    for coh, d in matched_did.items():
        print(f"{coh}: recency jump {d['recency_jump']:+.4f}  "
              f"control jump {d['control_jump_mean']:+.4f}  "
              f"==> matched DiD {d['matched_did']:+.4f}")

    print("\n=== Regression difference-in-differences (recency vs stable control) ===")
    for coh, d in did.items():
        print(f"{coh}: recency slope {d['slope_recency_year']:+.4f}/yr  "
              f"control slope {d['slope_control_year']:+.4f}/yr  "
              f"DiD {d['did_slope_year']:+.4f}/yr  (gap r={d['gap_pearson_r']:.3f})")

    print("\n=== Per-cohort cutoff slope (score per year of cutoff), sorted ===")
    for d in summary["cohort_slopes_sorted"]:
        tag = "  <-- RECENCY" if d["cohort"] in RECENCY else ""
        print(f"  {d['cohort']:32s} slope={d['slope_year']:+.4f}/yr "
              f"r={d['r']:+.3f}  mean={d['mean']:.3f}{tag}")


def _m(xs):
    return sum(xs) / len(xs) if xs else float("nan")


if __name__ == "__main__":
    main()
