#!/usr/bin/env python3
"""T5.2 — Is NameRank just Wikipedia-pageview rank?

Compares NameRank against 24-month en-Wikipedia pageviews (the strongest
freely available cross-domain attention metric) on the full 5,719-entity
pilot. Three questions:
  (1) Coverage: for how many entities is the attention metric defined at all?
  (2) Among entities where it IS defined, how much NameRank variance does
      log-pageviews explain, overall and within cohort?
  (3) On the long-tail researcher cohort, does log-pageviews compete with
      log h-index as a predictor?
Outputs: outputs/results.json, printed summary.
"""
import csv
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
ROOT = HERE.parent.parent

def read_csv(p):
    return list(csv.DictReader(open(p)))

nr = {r["entity_id"]: float(r["namerank"])
      for r in read_csv(ROOT / "data/analysis/namerank_per_entity.csv")}
cohort = {r["entity_id"]: r["cohort"]
          for r in read_csv(ROOT / "data/analysis/namerank_per_entity.csv")}
lookup = read_csv(HERE.parent / "t1_4_wikipedia" / "wikipedia_lookup.csv")
names = {r["entity_id"]: r["entity_name"]
         for r in read_csv(ROOT / "data/analysis/namerank_per_entity.csv")}

def title_plausible(entity_id, title):
    """Drop T1.4 disambiguation false positives (e.g. 'DSPy (Stanford)'
    matched to 'Stanford University'): the article title must share a
    token with the entity's base name (parenthetical qualifier stripped)."""
    import re
    base = re.sub(r"\s*\(.*\)", "", names.get(entity_id, "")).lower()
    toks = set(re.findall(r"[a-z0-9]+", base))
    ttl = set(re.findall(r"[a-z0-9]+", title.lower()))
    return bool(toks & ttl)

# months_returned == 0 marks articles created after the pageview window
# (e.g. Ollama, vLLM: article created 2026-04) — attention metric undefined.
pv_rows = read_csv(HERE / "outputs" / "pageviews_24m.csv")
pv = {r["entity_id"]: int(r["views_24m"])
      for r in pv_rows if int(r["months_returned"]) > 0
      and title_plausible(r["entity_id"], r["title"])}
n_post_window = sum(1 for r in pv_rows if int(r["months_returned"]) == 0)
n_title_mismatch = sum(1 for r in pv_rows if int(r["months_returned"]) > 0
                       and not title_plausible(r["entity_id"], r["title"]))
hidx = {r["entity_id"]: float(r["h_index"])
        for r in read_csv(ROOT / "experiments/t2_9_fractional_citations/author_works_metrics.csv")}

def r2(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 3 or x.std() == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1] ** 2)

def pearson(x, y):
    return float(np.corrcoef(np.asarray(x, float), np.asarray(y, float))[0, 1])

results = {}

# ── (1) coverage ─────────────────────────────────────────────────────────
matched = [r["entity_id"] for r in lookup
           if r["has_wikipedia"] == "1" and r["entity_id"] in pv and r["entity_id"] in nr]
unmatched = [r["entity_id"] for r in lookup
             if r["has_wikipedia"] == "0" and r["entity_id"] in nr]
un_nr = np.array([nr[e] for e in unmatched])
results["coverage"] = {
    "n_total": len(lookup),
    "n_matched": len(matched),
    "n_article_post_window": n_post_window,
    "n_title_mismatch_dropped": n_title_mismatch,
    "pct_matched": round(100 * len(matched) / len(lookup), 1),
    "unmatched_namerank_mean": round(float(un_nr.mean()), 3),
    "unmatched_namerank_p10": round(float(np.percentile(un_nr, 10)), 3),
    "unmatched_namerank_p90": round(float(np.percentile(un_nr, 90)), 3),
    "unmatched_pct_above_0.3": round(100 * float((un_nr > 0.3).mean()), 1),
}

# ── (2) pageviews vs NameRank among matched ──────────────────────────────
x = np.array([math.log10(pv[e] + 1) for e in matched])
y = np.array([nr[e] for e in matched])
results["matched_overall"] = {
    "n": len(matched),
    "pearson_r": round(pearson(x, y), 3),
    "r2": round(r2(x, y), 3),
}

# within-cohort: demean both variables by cohort, pool
groups = {}
for e, xi, yi in zip(matched, x, y):
    groups.setdefault(cohort[e], []).append((xi, yi))
xd, yd, per_cohort = [], [], {}
for c, pts in groups.items():
    if len(pts) < 15:
        continue
    cx, cy = np.array([p[0] for p in pts]), np.array([p[1] for p in pts])
    xd.extend(cx - cx.mean()); yd.extend(cy - cy.mean())
    per_cohort[c] = {"n": len(pts), "r": round(pearson(cx, cy), 3),
                     "r2": round(r2(cx, cy), 3)}
results["within_cohort"] = {
    "pooled_partial_r": round(pearson(xd, yd), 3),
    "pooled_partial_r2": round(r2(xd, yd), 3),
    "per_cohort": dict(sorted(per_cohort.items(), key=lambda kv: -kv[1]["n"])),
}

# ── (3) long-tail researchers: pageviews vs h-index ──────────────────────
lt_all = [e for e in nr if cohort[e] == "long_tail_researcher_openalex" and e in hidx]
wiki_flags = {r["entity_id"]: r["has_wikipedia"] for r in lookup}
lt_wiki = [e for e in lt_all if e in pv and wiki_flags.get(e) == "1"]
lt_y = [nr[e] for e in lt_all]
lt_h = [math.log10(hidx[e] + 1) for e in lt_all]
# pageviews defined as 0 for no-article researchers (most charitable coding)
lt_pv0 = [math.log10(pv.get(e, 0) + 1) if wiki_flags.get(e) == "1" and e in pv
          else 0.0 for e in lt_all]
sub_y = [nr[e] for e in lt_wiki]
sub_h = [math.log10(hidx[e] + 1) for e in lt_wiki]
sub_p = [math.log10(pv[e] + 1) for e in lt_wiki]
results["long_tail"] = {
    "n_all": len(lt_all),
    "r2_hindex_all": round(r2(lt_h, lt_y), 3),
    "r2_pageviews_zero_coded_all": round(r2(lt_pv0, lt_y), 3),
    "n_with_article": len(lt_wiki),
    "r2_hindex_subset": round(r2(sub_h, sub_y), 3),
    "r2_pageviews_subset": round(r2(sub_p, sub_y), 3),
}

out = HERE / "outputs" / "results.json"
out.write_text(json.dumps(results, indent=2))
print(json.dumps(results, indent=2))
