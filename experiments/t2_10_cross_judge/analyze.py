"""
Analyze cross-judge results.

Produces:
- rejudge_results.csv : per-record gemini/claude/gpt5 scores
- cross_judge_correlation.csv : per-cohort pearson/spearman correlations
- family_bias_check.csv : per (judge_family, response_family) mean scores
- reference_pilot_under_each_judge.csv : per entity x judge NameRank
"""

import os
import json
import csv
import math
from collections import defaultdict
from statistics import mean

ROOT = "/home/ubuntu/namerank/experiments/t2_10_cross_judge"
RECS = json.load(open(os.path.join(ROOT, "sample_records.json")))
CLAUDE = json.load(open(os.path.join(ROOT, "claude_judge.json")))
GPT = json.load(open(os.path.join(ROOT, "gpt_judge.json")))

with open("/home/ubuntu/namerank/data/inputs/model_set.json") as f:
    MODELS = {m["id"]: m for m in json.load(f)}


def get(judge_out, idx, key):
    v = judge_out.get(str(idx)) or judge_out.get(idx)
    if not v:
        return None
    val = v.get(key)
    if val is None:
        return None
    try:
        return float(val)
    except Exception:
        return None


def pearson(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 3:
        return None
    xs2 = [p[0] for p in pairs]
    ys2 = [p[1] for p in pairs]
    mx = mean(xs2); my = mean(ys2)
    num = sum((x - mx) * (y - my) for x, y in pairs)
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs2))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys2))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def spearman(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 3:
        return None
    def ranks(vs):
        idx = sorted(range(len(vs)), key=lambda i: vs[i])
        r = [0.0] * len(vs)
        i = 0
        while i < len(vs):
            j = i
            while j + 1 < len(vs) and vs[idx[j + 1]] == vs[idx[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                r[idx[k]] = avg
            i = j + 1
        return r
    xs2 = [p[0] for p in pairs]; ys2 = [p[1] for p in pairs]
    rx = ranks(xs2); ry = ranks(ys2)
    return pearson(rx, ry)


# -- Build rejudge_results.csv --
rows = []
for i, rec in enumerate(RECS):
    rows.append({
        "idx": i,
        "entity_id": rec["entity_id"],
        "entity_name": rec["entity_name"],
        "cohort": rec["cohort"],
        "model_id": rec["model_id"],
        "model_family": MODELS.get(rec["model_id"], {}).get("family", ""),
        "is_refusal": int(rec["is_refusal"]),
        "gemini_cov": rec["gemini_coverage"],
        "gemini_acc": rec["gemini_accuracy"],
        "gemini_score": rec["gemini_score"],
        "claude_cov": get(CLAUDE, i, "coverage"),
        "claude_acc": get(CLAUDE, i, "accuracy"),
        "gpt5_cov": get(GPT, i, "coverage"),
        "gpt5_acc": get(GPT, i, "accuracy"),
        "response_excerpt": (rec["response"] or "")[:300].replace("\n", " "),
    })

# Derive overall score = mean(cov, acc) where both present
for r in rows:
    if r["claude_cov"] is not None and r["claude_acc"] is not None:
        r["claude_score"] = (r["claude_cov"] + r["claude_acc"]) / 2.0
    else:
        r["claude_score"] = None
    if r["gpt5_cov"] is not None and r["gpt5_acc"] is not None:
        r["gpt5_score"] = (r["gpt5_cov"] + r["gpt5_acc"]) / 2.0
    else:
        r["gpt5_score"] = None

with open(os.path.join(ROOT, "rejudge_results.csv"), "w", newline="") as f:
    cols = ["idx", "entity_id", "entity_name", "cohort", "model_id", "model_family",
            "is_refusal", "gemini_cov", "gemini_acc", "gemini_score",
            "claude_cov", "claude_acc", "claude_score",
            "gpt5_cov", "gpt5_acc", "gpt5_score", "response_excerpt"]
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for r in rows:
        w.writerow(r)
print("Wrote rejudge_results.csv with", len(rows), "rows")

# -- Cross-judge correlations: overall + per-cohort --
def correlations_for_subset(subset, label):
    out = {"subset": label, "n": len(subset)}
    # On the overall "score" (mean of cov+acc)
    gs = [r["gemini_score"] for r in subset]
    cs = [r["claude_score"] for r in subset]
    ps = [r["gpt5_score"] for r in subset]
    out["pearson_gem_claude"] = pearson(gs, cs)
    out["spearman_gem_claude"] = spearman(gs, cs)
    out["pearson_gem_gpt5"] = pearson(gs, ps)
    out["spearman_gem_gpt5"] = spearman(gs, ps)
    out["pearson_claude_gpt5"] = pearson(cs, ps)
    out["spearman_claude_gpt5"] = spearman(cs, ps)
    return out


corr_rows = [correlations_for_subset(rows, "ALL")]
cohorts = sorted(set(r["cohort"] for r in rows))
for c in cohorts:
    sub = [r for r in rows if r["cohort"] == c]
    corr_rows.append(correlations_for_subset(sub, c))

# Special: Chinese-name researcher subset (heuristic: long_tail_researcher_openalex + imo_gold)
# Within reference_pilot, also flag Chinese-name entities.
chinese_entities = {"bojie_li", "jiayi_weng", "tianshou", "tuixue_online"}
chinese_subset = [r for r in rows if (r["entity_id"] in chinese_entities)]
if chinese_subset:
    corr_rows.append(correlations_for_subset(chinese_subset, "ref_pilot_chinese_names"))

with open(os.path.join(ROOT, "cross_judge_correlation.csv"), "w", newline="") as f:
    cols = ["subset", "n", "pearson_gem_claude", "spearman_gem_claude",
            "pearson_gem_gpt5", "spearman_gem_gpt5",
            "pearson_claude_gpt5", "spearman_claude_gpt5"]
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for r in corr_rows:
        w.writerow({k: (round(r[k], 4) if isinstance(r.get(k), float) else r.get(k))
                    for k in cols})
print("Wrote cross_judge_correlation.csv")

# -- Family bias check: per (judge, response_family) mean score --
fam_rows = []
families = sorted(set(r["model_family"] for r in rows if r["model_family"]))
for judge_name, judge_family, score_field in [
    ("gemini", "gemini", "gemini_score"),
    ("claude", "claude", "claude_score"),
    ("gpt5", "gpt5", "gpt5_score"),
]:
    for fam in families:
        sub = [r for r in rows if r["model_family"] == fam and r[score_field] is not None]
        if not sub:
            continue
        m = mean(r[score_field] for r in sub)
        fam_rows.append({
            "judge": judge_name,
            "judge_family": judge_family,
            "response_family": fam,
            "is_same_family": int(judge_family == fam),
            "n": len(sub),
            "mean_score": round(m, 4),
        })

with open(os.path.join(ROOT, "family_bias_check.csv"), "w", newline="") as f:
    cols = ["judge", "judge_family", "response_family", "is_same_family", "n", "mean_score"]
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for r in fam_rows:
        w.writerow(r)
print("Wrote family_bias_check.csv")

# Also compute aggregate "in-family lift" for each judge:
# mean(score | response_family == judge_family) - mean(score | response_family != judge_family)
print("\nIn-family lift per judge:")
for judge_name, judge_family, score_field in [
    ("gemini", "gemini", "gemini_score"),
    ("claude", "claude", "claude_score"),
    ("gpt5", "gpt5", "gpt5_score"),
]:
    in_fam = [r[score_field] for r in rows if r["model_family"] == judge_family and r[score_field] is not None]
    out_fam = [r[score_field] for r in rows if r["model_family"] != judge_family and r[score_field] is not None]
    if in_fam and out_fam:
        lift = mean(in_fam) - mean(out_fam)
        print(f"  {judge_name}: in_fam_mean={mean(in_fam):.3f} (n={len(in_fam)}), "
              f"out_fam_mean={mean(out_fam):.3f} (n={len(out_fam)}), lift={lift:+.3f}")

# -- Reference pilot NameRank per entity per judge --
# NameRank per entity = mean of (score) across the 37 models in the sample.
ref = [r for r in rows if r["cohort"] == "reference_pilot"]
ent_means = defaultdict(lambda: {"gemini": [], "claude": [], "gpt5": []})
for r in ref:
    if r["gemini_score"] is not None:
        ent_means[r["entity_id"]]["gemini"].append(r["gemini_score"])
    if r["claude_score"] is not None:
        ent_means[r["entity_id"]]["claude"].append(r["claude_score"])
    if r["gpt5_score"] is not None:
        ent_means[r["entity_id"]]["gpt5"].append(r["gpt5_score"])

rp_rows = []
for eid, scores in ent_means.items():
    rp_rows.append({
        "entity_id": eid,
        "n_models": len(scores["gemini"]),
        "namerank_gemini": round(mean(scores["gemini"]), 4) if scores["gemini"] else None,
        "namerank_claude": round(mean(scores["claude"]), 4) if scores["claude"] else None,
        "namerank_gpt5": round(mean(scores["gpt5"]), 4) if scores["gpt5"] else None,
    })

# Add ranks
for key, rank_key in [("namerank_gemini", "rank_gemini"),
                      ("namerank_claude", "rank_claude"),
                      ("namerank_gpt5", "rank_gpt5")]:
    sorted_rows = sorted(rp_rows, key=lambda r: -(r[key] or -1))
    for i, r in enumerate(sorted_rows):
        r[rank_key] = i + 1

with open(os.path.join(ROOT, "reference_pilot_under_each_judge.csv"), "w", newline="") as f:
    cols = ["entity_id", "n_models",
            "namerank_gemini", "rank_gemini",
            "namerank_claude", "rank_claude",
            "namerank_gpt5", "rank_gpt5"]
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for r in sorted(rp_rows, key=lambda r: -(r["namerank_gemini"] or 0)):
        w.writerow(r)
print("Wrote reference_pilot_under_each_judge.csv")

# -- Print summary to stdout --
print("\n=== SUMMARY ===")
print("\nOverall correlations:")
for r in corr_rows:
    if r["subset"] == "ALL":
        print(f"  n={r['n']}")
        print(f"  Pearson(gemini, claude) = {r['pearson_gem_claude']}")
        print(f"  Pearson(gemini, gpt5)   = {r['pearson_gem_gpt5']}")
        print(f"  Pearson(claude, gpt5)   = {r['pearson_claude_gpt5']}")
        print(f"  Spearman(gemini, claude) = {r['spearman_gem_claude']}")
        print(f"  Spearman(gemini, gpt5)   = {r['spearman_gem_gpt5']}")
        print(f"  Spearman(claude, gpt5)   = {r['spearman_claude_gpt5']}")

print("\nReference pilot NameRank under each judge (sorted by gemini):")
sorted_rp = sorted(rp_rows, key=lambda r: -(r["namerank_gemini"] or 0))
print(f"{'entity':<22} {'gem':>8} {'cla':>8} {'gpt5':>8} {'rg':>4} {'rc':>4} {'rp':>4}")
for r in sorted_rp:
    print(f"{r['entity_id']:<22} {r['namerank_gemini']:>8} {r['namerank_claude']:>8} "
          f"{r['namerank_gpt5']:>8} {r['rank_gemini']:>4} {r['rank_claude']:>4} {r['rank_gpt5']:>4}")

print("\nPer-cohort correlations (Pearson):")
print(f"{'cohort':<32} {'n':>4} {'gem-cla':>10} {'gem-gpt5':>10} {'cla-gpt5':>10}")
for r in corr_rows:
    if r["subset"] == "ALL":
        continue
    print(f"{r['subset']:<32} {r['n']:>4} {str(r['pearson_gem_claude']):>10} "
          f"{str(r['pearson_gem_gpt5']):>10} {str(r['pearson_claude_gpt5']):>10}")
