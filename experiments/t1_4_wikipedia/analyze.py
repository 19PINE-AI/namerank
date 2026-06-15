"""Analysis: does Wikipedia presence dominate NameRank?

Runs the four headline analyses requested:
  (1) Headline regressions on long_tail_researcher_openalex
  (2) Cross-cohort variance decomposition (has_wikipedia ± cohort FE)
  (3) Credential-cohort Wikipedia coverage
  (4) Stanford vs. Tsinghua conditional on has_wikipedia
"""
from __future__ import annotations

import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path("/home/ubuntu/namerank")
ANAL = ROOT / "data/analysis"
INP = ROOT / "data/inputs"
OUT = ROOT / "experiments/t1_4_wikipedia"


# -----------------------------------------------------------------------------
# Loaders
# -----------------------------------------------------------------------------
def load_entities() -> dict[str, dict]:
    return {e["id"]: e for e in json.loads((INP / "pilot_entities.json").read_text())}


def load_namerank() -> dict[str, float]:
    return {row["entity_id"]: float(row["namerank"])
            for row in csv.DictReader(open(ANAL / "namerank_per_entity.csv", encoding="utf-8"))}


def load_wiki(lenient: bool = False) -> dict[str, dict]:
    """Load the cache. If lenient=True, additionally flag entities whose
    rejected candidate is a "family" page that plausibly covers the entity
    (e.g. Claude 4 Opus -> "Claude (language model)").  This rescues
    foundation_model / programming_language artifacts whose specific version
    doesn't have its own article but is covered in a family article.
    """
    data = json.loads((OUT / "wikipedia_lookup.json").read_text())
    if not lenient:
        return data
    out = {}
    for eid, r in data.items():
        r2 = dict(r)
        if not r2.get("has_wikipedia") and r2.get("title_matched") and \
                r2.get("notes", "").startswith("unconfirmed:artifact_name_mismatch"):
            # Treat as family-covered (binary 1, sitelinks/pageviews still 0
            # — the strict signals only count direct pages).
            r2["has_wikipedia"] = True
            r2["notes"] = "family:" + r2["notes"]
        out[eid] = r2
    return out


# -----------------------------------------------------------------------------
# Regression helpers (OLS without scikit so we don't add a dep)
# -----------------------------------------------------------------------------
def ols(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, float, np.ndarray]:
    """Return (beta, R², residuals). X already includes intercept column."""
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    yhat = X @ beta
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return beta, r2, y - yhat


def design(*cols) -> np.ndarray:
    """Stack columns and prepend intercept."""
    n = len(cols[0])
    X = np.ones((n, len(cols) + 1))
    for i, c in enumerate(cols):
        X[:, i + 1] = c
    return X


# -----------------------------------------------------------------------------
# (1) headline regressions on long_tail_researcher_openalex
# -----------------------------------------------------------------------------
def headline_regressions(ents, nr, wiki):
    rows = []
    for eid, e in ents.items():
        if e.get("cohort") != "long_tail_researcher_openalex":
            continue
        w = wiki.get(eid)
        if not w or eid not in nr:
            continue
        h = e.get("h_index")
        cit = e.get("cited_by_count")
        if h is None or cit is None:
            continue
        rows.append({
            "id": eid,
            "namerank": nr[eid],
            "has_wiki": int(bool(w.get("has_wikipedia"))),
            "sitelinks": int(w.get("sitelinks") or 0),
            "pageviews": int(w.get("pageviews_30d") or 0),
            "h_index": int(h),
            "cited_by": int(cit),
        })
    if not rows:
        return {"error": "no_rows"}

    y = np.array([r["namerank"] for r in rows])
    has = np.array([r["has_wiki"] for r in rows], dtype=float)
    log_sl = np.array([math.log1p(r["sitelinks"]) for r in rows])
    log_pv = np.array([math.log1p(r["pageviews"]) for r in rows])
    log_h = np.array([math.log1p(r["h_index"]) for r in rows])
    log_c = np.array([math.log1p(r["cited_by"]) for r in rows])

    models = {}

    # M0: NR ~ has_wiki
    _, r2, _ = ols(design(has), y)
    models["M0_has_wiki"] = {"r2": r2}

    # M1: + log_sitelinks
    _, r2, _ = ols(design(has, log_sl), y)
    models["M1_+log_sitelinks"] = {"r2": r2}

    # M2: + log_pageviews
    _, r2, _ = ols(design(has, log_sl, log_pv), y)
    models["M2_+log_pageviews"] = {"r2": r2}

    # M3: + log h-index (the paper's headline signal)
    beta, r2, _ = ols(design(has, log_sl, log_pv, log_h), y)
    models["M3_+log_h_index"] = {
        "r2": r2,
        "beta_intercept": float(beta[0]),
        "beta_has_wiki": float(beta[1]),
        "beta_log_sitelinks": float(beta[2]),
        "beta_log_pageviews": float(beta[3]),
        "beta_log_h_index": float(beta[4]),
    }

    # M4: + log citations
    beta, r2, _ = ols(design(has, log_sl, log_pv, log_h, log_c), y)
    models["M4_+log_citations"] = {
        "r2": r2,
        "beta_intercept": float(beta[0]),
        "beta_has_wiki": float(beta[1]),
        "beta_log_sitelinks": float(beta[2]),
        "beta_log_pageviews": float(beta[3]),
        "beta_log_h_index": float(beta[4]),
        "beta_log_citations": float(beta[5]),
    }

    # Baseline comparisons:
    # - h_index ALONE
    _, r2_h, _ = ols(design(log_h), y)
    models["B_log_h_index_only"] = {"r2": r2_h}
    # - h_index + citations (paper's reported)
    _, r2_hc, _ = ols(design(log_h, log_c), y)
    models["B_h_index_+citations"] = {"r2": r2_hc}
    # - has_wiki + h_index (clean 2-var)
    _, r2_wh, _ = ols(design(has, log_h), y)
    models["B_has_wiki_+_h_index"] = {"r2": r2_wh}
    # - pageviews ALONE
    _, r2_pv, _ = ols(design(log_pv), y)
    models["B_log_pageviews_only"] = {"r2": r2_pv}
    # - sitelinks ALONE
    _, r2_sl, _ = ols(design(log_sl), y)
    models["B_log_sitelinks_only"] = {"r2": r2_sl}

    # Marginal R²: M3 - M2 = added R² from h_index given wiki controls
    marg = {
        "marginal_has_wiki_vs_intercept": round(models["M0_has_wiki"]["r2"], 4),
        "marginal_sitelinks_given_wiki": round(models["M1_+log_sitelinks"]["r2"]
                                                 - models["M0_has_wiki"]["r2"], 4),
        "marginal_pageviews_given_wiki_sl": round(models["M2_+log_pageviews"]["r2"]
                                                    - models["M1_+log_sitelinks"]["r2"], 4),
        "marginal_h_index_given_all_wiki": round(models["M3_+log_h_index"]["r2"]
                                                   - models["M2_+log_pageviews"]["r2"], 4),
        "marginal_citations_given_all": round(models["M4_+log_citations"]["r2"]
                                                - models["M3_+log_h_index"]["r2"], 4),
        "marginal_h_index_alone": round(models["B_log_h_index_only"]["r2"], 4),
        "marginal_pageviews_alone": round(models["B_log_pageviews_only"]["r2"], 4),
    }

    # Conditional: among entities WITH Wikipedia pages
    rows_w = [r for r in rows if r["has_wiki"]]
    rows_nw = [r for r in rows if not r["has_wiki"]]
    cond = {"n_with_wiki": len(rows_w), "n_without_wiki": len(rows_nw)}
    for label, sub in [("with_wiki", rows_w), ("without_wiki", rows_nw)]:
        if len(sub) >= 5:
            y_s = np.array([r["namerank"] for r in sub])
            lh_s = np.array([math.log1p(r["h_index"]) for r in sub])
            _, r2_s, _ = ols(design(lh_s), y_s)
            cond[f"{label}_R2_h_index"] = round(r2_s, 4)
            cond[f"{label}_mean_NR"] = round(float(y_s.mean()), 4)
            cond[f"{label}_mean_h"] = round(float(np.mean([r["h_index"] for r in sub])), 2)

    return {"n": len(rows), "models": models, "marginal": marg, "conditional": cond}


# -----------------------------------------------------------------------------
# (2) Cross-cohort variance decomposition
# -----------------------------------------------------------------------------
def variance_decomp(ents, nr, wiki):
    rows = []
    for eid, e in ents.items():
        if eid not in nr:
            continue
        w = wiki.get(eid)
        if not w:
            continue
        rows.append({
            "namerank": nr[eid], "cohort": e.get("cohort", "unknown"),
            "has_wiki": int(bool(w.get("has_wikipedia"))),
            "log_pv": math.log1p(int(w.get("pageviews_30d") or 0)),
            "log_sl": math.log1p(int(w.get("sitelinks") or 0)),
        })
    y = np.array([r["namerank"] for r in rows])
    has = np.array([r["has_wiki"] for r in rows], dtype=float)
    log_pv = np.array([r["log_pv"] for r in rows])
    log_sl = np.array([r["log_sl"] for r in rows])

    cohorts = sorted({r["cohort"] for r in rows})
    cohort_index = {c: i for i, c in enumerate(cohorts)}
    n = len(rows)
    C = np.zeros((n, len(cohorts) - 1))  # drop one as reference
    ref = cohorts[0]
    for i, r in enumerate(rows):
        if r["cohort"] != ref:
            C[i, cohort_index[r["cohort"]] - 1] = 1.0

    out = {"n": n, "n_cohorts": len(cohorts)}

    # has_wiki alone
    _, r2, _ = ols(design(has), y)
    out["R2_has_wiki_only"] = round(r2, 4)
    # has_wiki + log_pv
    _, r2, _ = ols(design(has, log_pv), y)
    out["R2_has_wiki_+log_pv"] = round(r2, 4)
    # has_wiki + log_pv + log_sl
    _, r2, _ = ols(design(has, log_pv, log_sl), y)
    out["R2_wiki_block_all"] = round(r2, 4)
    # cohort FE alone
    X_c = np.hstack([np.ones((n, 1)), C])
    _, r2, _ = ols(X_c, y) if False else (None, *ols(X_c, y)[1:])
    # Simpler: build columns and concat
    X_c = np.ones((n, 1))
    X_c = np.hstack([X_c, C])
    beta_c, *_ = np.linalg.lstsq(X_c, y, rcond=None)
    yhat = X_c @ beta_c
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    out["R2_cohort_FE_only"] = round(1 - ss_res / ss_tot, 4)

    # has_wiki + cohort FE
    X_full = np.column_stack([np.ones(n), has, C])
    beta, *_ = np.linalg.lstsq(X_full, y, rcond=None)
    yhat = X_full @ beta
    ss_res = float(np.sum((y - yhat) ** 2))
    out["R2_has_wiki_+_cohort_FE"] = round(1 - ss_res / ss_tot, 4)

    # full wiki block + cohort FE
    X_full2 = np.column_stack([np.ones(n), has, log_pv, log_sl, C])
    beta, *_ = np.linalg.lstsq(X_full2, y, rcond=None)
    yhat = X_full2 @ beta
    ss_res = float(np.sum((y - yhat) ** 2))
    out["R2_wiki_block_+_cohort_FE"] = round(1 - ss_res / ss_tot, 4)

    out["marginal_has_wiki_over_cohort_FE"] = round(
        out["R2_has_wiki_+_cohort_FE"] - out["R2_cohort_FE_only"], 4)
    out["marginal_cohort_FE_over_has_wiki"] = round(
        out["R2_has_wiki_+_cohort_FE"] - out["R2_has_wiki_only"], 4)

    return out


# -----------------------------------------------------------------------------
# (3) Credential cohort wiki coverage
# -----------------------------------------------------------------------------
CREDENTIAL_COHORTS = [
    "imo_gold", "cmo_china_gold", "cpho_china_first_prize", "noi_china_gold",
    "ioi_gold", "icpc_world_finals_gold", "putnam_fellow", "rhodes_scholar",
    "msra_phd_fellowship",
]
COMPARISON_COHORTS = [
    "long_tail_researcher_openalex", "cs_faculty", "reference_pilot",
    "long_tail_researcher_ikp",
]


def credential_coverage(ents, nr, wiki):
    rows = []
    for cohort in CREDENTIAL_COHORTS + COMPARISON_COHORTS:
        nrs = []
        nrs_w = []
        nrs_nw = []
        n_total = 0
        n_wiki = 0
        sitelinks = []
        pageviews = []
        for eid, e in ents.items():
            if e.get("cohort") != cohort:
                continue
            w = wiki.get(eid)
            if eid not in nr or not w:
                continue
            n_total += 1
            nrs.append(nr[eid])
            if w.get("has_wikipedia"):
                n_wiki += 1
                nrs_w.append(nr[eid])
                sitelinks.append(int(w.get("sitelinks") or 0))
                pageviews.append(int(w.get("pageviews_30d") or 0))
            else:
                nrs_nw.append(nr[eid])
        if n_total == 0:
            continue
        rows.append({
            "cohort": cohort,
            "n_total": n_total,
            "n_wiki": n_wiki,
            "wiki_pct": round(100 * n_wiki / n_total, 2),
            "mean_NR_all": round(statistics.mean(nrs), 4),
            "mean_NR_with_wiki": round(statistics.mean(nrs_w), 4) if nrs_w else None,
            "mean_NR_without_wiki": round(statistics.mean(nrs_nw), 4) if nrs_nw else None,
            "mean_sitelinks_in_wiki": round(statistics.mean(sitelinks), 2) if sitelinks else None,
            "median_pageviews_in_wiki": round(statistics.median(pageviews), 1) if pageviews else None,
        })
    return rows


# -----------------------------------------------------------------------------
# (4) Stanford vs Tsinghua conditional on has_wiki
# -----------------------------------------------------------------------------
US_INST = ["Carnegie Mellon", "Cornell", "Michigan", "Washington", "Princeton", "Stanford",
           "Georgia Institute", "Johns Hopkins", "Illinois", "MIT", "Berkeley", "UCLA", "USC",
           "NYU", "Columbia", "Yale", "Harvard", "Brown", "Duke", "UT Austin", "Texas",
           "Penn", "UCSD", "UC San Diego", "Northwestern", "Wisconsin", "Maryland",
           "Massachusetts", "California", "Virginia", "Boston University", "Rutgers",
           "Rice", "Vanderbilt", "Caltech", "Buffalo", "Stony Brook", "Pittsburgh",
           "Notre Dame", "Indiana", "Ohio", "Florida", "Arizona", "Oregon", "Utah",
           "Colorado", "Iowa", "Kansas", "Minnesota", "Tennessee", "North Carolina",
           "George Washington", "Drexel"]
CN_INST = ["Tsinghua", "Peking", "USTC", "Shanghai Jiao Tong", "Fudan", "Zhejiang",
           "Wuhan", "Harbin Institute", "Nanjing", "Xian Jiaotong", "Beihang",
           "Renmin", "Beijing Institute"]


def institution_country(inst: str) -> str:
    il = inst.lower()
    for kw in US_INST:
        if kw.lower() in il:
            return "USA"
    for kw in CN_INST:
        if kw.lower() in il:
            return "China"
    return "Other"


def institution_gap(ents, nr, wiki):
    rows = []
    for eid, e in ents.items():
        if e.get("cohort") != "cs_faculty" or eid not in nr:
            continue
        inst = e.get("institution", "") or ""
        country = institution_country(inst)
        if country not in ("USA", "China"):
            continue
        w = wiki.get(eid)
        if not w:
            continue
        rows.append({
            "id": eid, "namerank": nr[eid],
            "country": country, "institution": inst,
            "has_wiki": int(bool(w.get("has_wikipedia"))),
            "log_pv": math.log1p(int(w.get("pageviews_30d") or 0)),
            "log_sl": math.log1p(int(w.get("sitelinks") or 0)),
            "pageviews_30d": int(w.get("pageviews_30d") or 0),
            "sitelinks": int(w.get("sitelinks") or 0),
        })
    if not rows:
        return {"error": "no_rows"}

    y = np.array([r["namerank"] for r in rows])
    us = np.array([1.0 if r["country"] == "USA" else 0.0 for r in rows])
    has = np.array([r["has_wiki"] for r in rows], dtype=float)
    log_pv = np.array([r["log_pv"] for r in rows])
    log_sl = np.array([r["log_sl"] for r in rows])

    out = {}
    out["n_USA"] = int(us.sum())
    out["n_China"] = int(len(us) - us.sum())
    out["mean_NR_USA"] = round(float(y[us == 1].mean()), 4)
    out["mean_NR_China"] = round(float(y[us == 0].mean()), 4)
    out["wiki_pct_USA"] = round(100 * float(has[us == 1].mean()), 2)
    out["wiki_pct_China"] = round(100 * float(has[us == 0].mean()), 2)

    # M0: NR ~ US dummy
    beta, r2, _ = ols(design(us), y)
    out["M0_country_only"] = {"R2": round(r2, 4),
                              "beta_USA": round(float(beta[1]), 4)}
    # M1: + has_wiki
    beta, r2, _ = ols(design(us, has), y)
    out["M1_+has_wiki"] = {"R2": round(r2, 4),
                            "beta_USA": round(float(beta[1]), 4),
                            "beta_has_wiki": round(float(beta[2]), 4)}
    # M2: + log_pv + log_sl
    beta, r2, _ = ols(design(us, has, log_pv, log_sl), y)
    out["M2_+wiki_block"] = {"R2": round(r2, 4),
                              "beta_USA": round(float(beta[1]), 4),
                              "beta_has_wiki": round(float(beta[2]), 4),
                              "beta_log_pv": round(float(beta[3]), 4),
                              "beta_log_sl": round(float(beta[4]), 4)}
    # Restricted: only entities WITHOUT Wikipedia pages
    sub = [r for r in rows if not r["has_wiki"]]
    if len(sub) >= 10:
        y_s = np.array([r["namerank"] for r in sub])
        us_s = np.array([1.0 if r["country"] == "USA" else 0.0 for r in sub])
        beta, r2, _ = ols(design(us_s), y_s)
        out["restricted_no_wiki"] = {
            "n_USA": int(us_s.sum()),
            "n_China": int(len(us_s) - us_s.sum()),
            "mean_NR_USA": round(float(y_s[us_s == 1].mean()), 4),
            "mean_NR_China": round(float(y_s[us_s == 0].mean()), 4) if any(us_s == 0) else None,
            "beta_USA": round(float(beta[1]), 4),
            "R2": round(r2, 4),
        }
    # Restricted: only WITH Wikipedia
    sub = [r for r in rows if r["has_wiki"]]
    if len(sub) >= 10:
        y_s = np.array([r["namerank"] for r in sub])
        us_s = np.array([1.0 if r["country"] == "USA" else 0.0 for r in sub])
        if any(us_s == 1) and any(us_s == 0):
            beta, r2, _ = ols(design(us_s), y_s)
            out["restricted_wiki"] = {
                "n_USA": int(us_s.sum()),
                "n_China": int(len(us_s) - us_s.sum()),
                "mean_NR_USA": round(float(y_s[us_s == 1].mean()), 4),
                "mean_NR_China": round(float(y_s[us_s == 0].mean()), 4),
                "beta_USA": round(float(beta[1]), 4),
                "R2": round(r2, 4),
            }

    # Stanford-specific vs Tsinghua-specific breakout
    def is_stanford(inst):
        return "stanford" in inst.lower()
    def is_tsinghua(inst):
        return "tsinghua" in inst.lower()
    stanford = [r for r in rows if is_stanford(r["institution"])]
    tsinghua = [r for r in rows if is_tsinghua(r["institution"])]
    inst_break = {}
    for label, sub in [("Stanford", stanford), ("Tsinghua", tsinghua)]:
        if sub:
            nrs = [r["namerank"] for r in sub]
            inst_break[label] = {
                "n": len(sub),
                "mean_NR": round(float(np.mean(nrs)), 4),
                "wiki_pct": round(100*float(np.mean([r["has_wiki"] for r in sub])), 2),
                "mean_pv": round(float(np.mean([r["pageviews_30d"] for r in sub])), 1),
                "mean_sl": round(float(np.mean([r["sitelinks"] for r in sub])), 2),
            }
    out["stanford_vs_tsinghua"] = inst_break
    # Save rows for CSV
    out["_rows"] = rows
    return out


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main():
    ents = load_entities()
    nr = load_namerank()
    wiki = load_wiki(lenient=False)
    wiki_lenient = load_wiki(lenient=True)
    print(f"Loaded: {len(ents)} entities, {len(nr)} namerank, {len(wiki)} wiki")
    n_hits_s = sum(1 for v in wiki.values() if v.get("has_wikipedia"))
    n_hits_l = sum(1 for v in wiki_lenient.values() if v.get("has_wikipedia"))
    print(f"Wikipedia hits STRICT:  {n_hits_s}/{len(wiki)} ({100*n_hits_s/len(wiki):.1f}%)")
    print(f"Wikipedia hits LENIENT: {n_hits_l}/{len(wiki_lenient)} ({100*n_hits_l/len(wiki_lenient):.1f}%)")

    results = {
        "summary": {
            "n_entities": len(wiki),
            "wiki_hits_strict": n_hits_s,
            "wiki_hits_lenient": n_hits_l,
            "wiki_pct_strict": round(100 * n_hits_s / len(wiki), 2),
            "wiki_pct_lenient": round(100 * n_hits_l / len(wiki_lenient), 2),
        },
    }
    print("\n[1] Headline regressions on long_tail_researcher_openalex...")
    results["headline_regressions_long_tail"] = headline_regressions(ents, nr, wiki)
    results["headline_regressions_long_tail_lenient"] = headline_regressions(ents, nr, wiki_lenient)
    print("STRICT:")
    print(json.dumps(results["headline_regressions_long_tail"], indent=2))

    print("\n[2] Cross-cohort variance decomposition (STRICT)...")
    results["variance_decomposition"] = variance_decomp(ents, nr, wiki)
    print(json.dumps(results["variance_decomposition"], indent=2))
    print("\n[2b] Cross-cohort variance decomposition (LENIENT)...")
    results["variance_decomposition_lenient"] = variance_decomp(ents, nr, wiki_lenient)
    print(json.dumps(results["variance_decomposition_lenient"], indent=2))

    print("\n[3] Credential cohort coverage (STRICT)...")
    cov = credential_coverage(ents, nr, wiki)
    results["credential_coverage"] = cov
    for r in cov:
        print(f"  {r['cohort']:<32} n={r['n_total']:<4} wiki={r['n_wiki']:<3} "
              f"({r['wiki_pct']:5.1f}%) NR_all={r['mean_NR_all']:.3f}")
    results["credential_coverage_lenient"] = credential_coverage(ents, nr, wiki_lenient)

    print("\n[4] Stanford-vs-Tsinghua / USA-vs-China conditional on has_wiki (STRICT)...")
    inst_full = institution_gap(ents, nr, wiki)
    inst_rows = inst_full.pop("_rows", [])
    results["institution_gap"] = inst_full
    print(json.dumps(results["institution_gap"], indent=2))

    (OUT / "regression_results.json").write_text(json.dumps(results, indent=2))
    print(f"\nWrote {OUT/'regression_results.json'}")

    # CSV for credential coverage
    cred_csv = OUT / "credential_wiki_coverage.csv"
    if cov:
        with open(cred_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(cov[0].keys()))
            w.writeheader()
            w.writerows(cov)
        print(f"Wrote {cred_csv}")

    # Stanford / Tsinghua CSV: per-faculty rows used in analysis
    st_csv = OUT / "stanford_tsinghua_wiki.csv"
    if inst_rows:
        # Keep all US-vs-China cs_faculty entities so the file shows the full
        # comparison set (Stanford and Tsinghua subsets are easy to filter).
        fieldnames = ["id", "country", "institution", "namerank",
                      "has_wiki", "sitelinks", "pageviews_30d", "log_pv", "log_sl"]
        with open(st_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in inst_rows:
                w.writerow({k: r.get(k) for k in fieldnames})
        print(f"Wrote {st_csv} ({len(inst_rows)} rows)")

    # Also (re)flatten wikipedia_lookup.json -> wikipedia_lookup.csv defensively
    # in case the worker script crashed before its own flatten step.
    csv_path = OUT / "wikipedia_lookup.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["entity_id", "entity_name", "cohort", "has_wikipedia",
                    "title_matched", "qid", "sitelinks", "pageviews_30d",
                    "method", "notes"])
        for eid, r in wiki.items():
            e = ents.get(eid, {})
            w.writerow([eid, e.get("name", ""), e.get("cohort", ""),
                        int(bool(r.get("has_wikipedia"))),
                        r.get("title_matched") or "", r.get("qid") or "",
                        r.get("sitelinks") or 0, r.get("pageviews_30d") or 0,
                        r.get("method") or "", r.get("notes") or ""])
    print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
