#!/usr/bin/env python3
"""Build compact JSON data assets for the NameRank explainer site.

Reads from the repo's data/ and experiments/ directories and writes:
  site/src/data/*.json      -- small assets imported at build time
  site/public/data/*.json   -- larger assets fetched lazily at runtime

Run from the repo root:  python3 site/scripts/build_data.py
"""

import csv
import gzip
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC_DATA = ROOT / "site" / "src" / "data"
PUB_DATA = ROOT / "site" / "public" / "data"

sys.path.insert(0, str(ROOT / "paper" / "figures"))
from _style import COHORT_NAMES, CREDENTIAL_COHORTS  # noqa: E402


def jdump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  wrote {path.relative_to(ROOT)}  ({path.stat().st_size/1024:.0f} KB)")


def rd(x, nd=3):
    return round(float(x), nd)


# ---------------------------------------------------------------- cohorts
ARTIFACT_COHORTS = {
    "programming_language", "database_or_data_system", "benchmark", "ai_hardware",
    "dataset", "research_paper", "conference", "mid_tier_product", "industry_product",
    "named_method", "oss_project", "foundation_model", "website_or_service",
    "mid_tier_online_course", "mid_tier_podcast", "long_tail_paper", "mid_tier_book",
    "award", "ai_startup_or_company", "mid_tier_yc_company",
}


def cohort_category(slug: str) -> str:
    if slug in CREDENTIAL_COHORTS or slug in {"deepseek_v3_author", "gpt5_system_card_author"}:
        return "credential"
    if slug in ARTIFACT_COHORTS:
        return "artifact"
    return "person"


def build_cohorts():
    rows = list(csv.DictReader(open(ROOT / "data/analysis/cohort_summary.csv")))
    out = []
    for r in rows:
        slug = r["cohort"]
        out.append({
            "slug": slug,
            "name": COHORT_NAMES.get(slug, slug.replace("_", " ")),
            "category": cohort_category(slug),
            "n": int(r["n"]),
            "mean": rd(r["mean"]),
            "median": rd(r["median"]),
            "sd": rd(r["sd"]),
            "p10": rd(r["p10"]),
            "p90": rd(r["p90"]),
            "recognized": rd(r["frac_recognized"]),
            "refusal": rd(r["refusal_rate"]),
        })
    out.sort(key=lambda c: -c["mean"])
    jdump(SRC_DATA / "cohorts.json", out)
    return {c["slug"]: c for c in out}


# ---------------------------------------------------------------- models
def build_models():
    meta = {m["id"]: m for m in json.load(open(ROOT / "data/inputs/model_set.json"))}
    cutoffs = {m["id"]: m for m in json.load(open(ROOT / "data/analysis/model_cutoffs.json"))}
    rows = list(csv.DictReader(open(ROOT / "data/analysis/per_model_summary.csv")))
    out = []
    for r in rows:
        mid = r["model_id"]
        out.append({
            "id": mid,
            "vendor": r["vendor"],
            "family": r["family"],
            "lab": meta.get(mid, {}).get("lab", r["vendor"].title()),
            "thinking": r["thinking"] in ("1", "True", "true"),
            "mean": rd(r["mean_score"], 4),
            "refusal": rd(r["refusal_rate"], 4),
            "meanNonRefusal": rd(r["mean_score_non_refusal"], 4),
            "cutoff": cutoffs.get(mid, {}).get("training_cutoff"),
        })
    out.sort(key=lambda m: -m["mean"])
    jdump(SRC_DATA / "models.json", out)
    return [m["id"] for m in out]


# ---------------------------------------------------------------- entities
def build_entities():
    inputs = {e["id"]: e for e in json.load(open(ROOT / "data/inputs/pilot_entities.json"))}
    rows = list(csv.DictReader(open(ROOT / "data/analysis/namerank_per_entity.csv")))
    cols = ["id", "name", "cohort", "country", "year", "nr", "sd", "refusal"]
    data = []
    for r in rows:
        e = inputs.get(r["entity_id"], {})
        data.append([
            r["entity_id"],
            r["entity_name"],
            r["cohort"],
            e.get("credential_country") or None,
            e.get("credential_year") or None,
            rd(r["namerank"]),
            rd(r["namerank_sd"]),
            rd(r["refusal_rate"]),
        ])
    data.sort(key=lambda x: -x[5])
    jdump(PUB_DATA / "entities.json", {"cols": cols, "rows": data})
    return inputs


# ------------------------------------------------------- per-entity matrix
def build_matrix(model_order):
    m = json.load(open(ROOT / "data/analysis/namerank_matrix.json"))
    scores = {}
    for eid, per_model in m.items():
        scores[eid] = [
            (rd(per_model[mid]) if per_model.get(mid) is not None else None)
            for mid in model_order
        ]
    jdump(PUB_DATA / "matrix.json", {"models": model_order, "scores": scores})


# ---------------------------------------------------------------- gold shards
def build_gold(inputs):
    gold = json.load(open(ROOT / "data/inputs/gold_answers.json"))
    by_cohort = defaultdict(dict)
    for eid, text in gold.items():
        cohort = inputs.get(eid, {}).get("cohort", "unknown")
        by_cohort[cohort][eid] = text
    for cohort, d in by_cohort.items():
        jdump(PUB_DATA / "gold" / f"{cohort}.json", d)
    return gold


# ---------------------------------------------------------------- judged cases
def build_cases(inputs, gold):
    recs = json.load(open(ROOT / "experiments/t2_10_cross_judge/sample_records.json"))
    claude = json.load(open(ROOT / "experiments/t2_10_cross_judge/claude_judge.json"))
    gpt = json.load(open(ROOT / "experiments/t2_10_cross_judge/gpt_judge.json"))
    nr = {r["entity_id"]: rd(r["namerank"]) for r in
          csv.DictReader(open(ROOT / "data/analysis/namerank_per_entity.csv"))}
    out = []
    for i, r in enumerate(recs):
        eid = r["entity_id"]
        case = {
            "i": i,
            "entity": eid,
            "name": r["entity_name"],
            "model": r["model_id"],
            "cohort": r["cohort"],
            "context": inputs.get(eid, {}).get("context", ""),
            "nr": nr.get(eid),
            "refusal": bool(r["is_refusal"]),
            "response": r["response"],
            "gold": gold.get(eid, ""),
            "judges": {
                "gemini": {
                    "cov": rd(r["gemini_coverage"], 2),
                    "acc": rd(r["gemini_accuracy"], 2),
                    "score": rd(r["gemini_score"], 3),
                    "rationale": r.get("gemini_rationale", ""),
                },
            },
        }
        for jname, jdata in (("claude", claude), ("gpt", gpt)):
            j = jdata.get(str(i))
            if j:
                case["judges"][jname] = {
                    "cov": rd(j["coverage"], 2),
                    "acc": rd(j["accuracy"], 2),
                    "score": rd(j["coverage"] * j["accuracy"], 3),
                    "rationale": j.get("rationale", ""),
                }
        out.append(case)
    jdump(PUB_DATA / "cases.json", out)
    return out


# ------------------------------------------------- curated explainer cases
def build_explainer_cases(cases):
    """Pick four archetypes: full recognition, partial, hallucination, refusal."""
    def key(c):
        return c["judges"]["gemini"]

    chosen = {}
    # full recognition: famous entity, high cov & acc
    full = [c for c in cases if key(c)["score"] >= 0.85 and not c["refusal"]
            and c["cohort"] == "reference_pilot" and len(c["response"]) < 1400]
    if full:
        chosen["full"] = max(full, key=lambda c: key(c)["score"])
    # partial: middling coverage, perfect accuracy
    part = [c for c in cases if 0.3 <= key(c)["cov"] <= 0.55 and key(c)["acc"] >= 0.9
            and not c["refusal"] and len(c["response"]) < 1200]
    if part:
        chosen["partial"] = part[0]
    # hallucination: fluent but wrong -- coverage credited, accuracy tanked
    hall = [c for c in cases if key(c)["cov"] >= 0.3 and key(c)["acc"] <= 0.45
            and not c["refusal"] and len(c["response"]) < 1400]
    if hall:
        chosen["hallucination"] = max(hall, key=lambda c: key(c)["cov"] - key(c)["acc"])
    # refusal: prefer a literal "unknown" from a frontier model about a
    # real-but-unpropagated researcher (the "silent, not misleading" story)
    ref = [c for c in cases if c["refusal"] and 0 < len(c["response"]) < 400]
    ref.sort(key=lambda c: (c["name"] != "Jiayi Weng", c["model"] != "gpt-5.4"))
    if ref:
        chosen["refusal"] = ref[0]
    jdump(SRC_DATA / "explainer_cases.json", chosen)
    for k, v in chosen.items():
        print(f"    explainer[{k}] = {v['name']} x {v['model']} "
              f"(cov {key(v)['cov']}, acc {key(v)['acc']})")


# ---------------------------------------------------------------- findings
def build_ladder(cohorts):
    rows = list(csv.DictReader(open(ROOT / "data/analysis/credential_ladder.csv")))
    ladder = [{
        "credential": r["credential"],
        "rung": r["rung"],
        "prestige": r["prestige"],
        "n": int(r["n"]),
        "mean": rd(r["mean"]),
        "sd": rd(r["sd"]),
        "years": f"{r['min_year']}-{r['max_year']}",
    } for r in rows]
    baselines = {
        "longTail": {"label": "Long-tail working researchers (OpenAlex)",
                     "mean": cohorts["long_tail_researcher_openalex"]["mean"],
                     "n": cohorts["long_tail_researcher_openalex"]["n"]},
        "csFaculty": {"label": "CS faculty",
                      "mean": cohorts["cs_faculty"]["mean"],
                      "n": cohorts["cs_faculty"]["n"]},
    }
    jdump(SRC_DATA / "ladder.json", {"rows": ladder, "baselines": baselines})


# Canonical inversion table from the paper (Table: tab:inversion).
INVERSION = [
    ["Simon Willison", 0.594, "Datasette", 0.899, 0.54, 0.89],
    ["Dario Amodei", 0.584, "Anthropic", 0.811, 1.00, 0.41],
    ["Andrej Karpathy", 0.614, "nanoGPT", 0.707, 0.05, 0.76],
    ["Jiayi Weng", 0.331, "Tianshou", 0.420, 0.25, 0.00],
    ["Tri Dao", 0.532, "FlashAttention", 0.607, 0.74, 0.54],
    ["Lilian Weng", 0.590, "lilianweng.github.io", 0.614, 0.97, 0.97],
    ["Harrison Chase", 0.479, "LangChain", 0.502, 1.00, 0.22],
    ["Aman Sanger", 0.289, "Cursor", 0.305, 1.00, 0.00],
    ["Demis Hassabis", 0.664, "Google DeepMind", 0.490, 1.00, 0.62],
    ["Mira Murati", 0.442, "Thinking Machines Lab", 0.222, 0.97, 1.00],
    ["Aravind Srinivas", 0.663, "Perplexity", 0.193, 1.00, 0.33],
]


def build_inversion():
    out = [{
        "creator": c, "nrCreator": nc, "artifact": a, "nrArtifact": na,
        "delta": rd(na - nc), "cToA": ca, "aToC": ac,
    } for c, nc, a, na, ca, ac in INVERSION]
    jdump(SRC_DATA / "inversion.json", out)


def build_country():
    rows = list(csv.DictReader(open(ROOT / "data/analysis/cs_faculty_by_country.csv")))
    out = []
    for r in rows:
        n = int(r["n"])
        mean, sd = float(r["mean"]), float(r["sd"])
        ci = 1.96 * sd / math.sqrt(n) if n > 1 else 0.0
        out.append({
            "country": r["country"], "n": n, "mean": rd(mean), "sd": rd(sd),
            "lo": rd(mean - ci), "hi": rd(mean + ci), "firm": n >= 10,
        })
    out.sort(key=lambda x: -x["mean"])
    jdump(SRC_DATA / "country.json", out)


def build_crosslang():
    rows = list(csv.DictReader(open(ROOT / "data/analysis/cross_language_per_entity.csv")))
    en = [float(r["en_all"]) for r in rows]
    zh = [float(r["zh_all"]) for r in rows]
    deltas = sorted(float(r["delta_zh_minus_en"]) for r in rows)
    n = len(rows)
    hist_edges = [i / 20 - 0.5 for i in range(0, 21)]  # -0.5 .. 0.5
    hist = [0] * (len(hist_edges) - 1)
    for d in deltas:
        idx = min(max(int((d + 0.5) * 20), 0), len(hist) - 1)
        hist[idx] += 1
    out = {
        "n": n,
        "enMean": rd(sum(en) / n),
        "zhMean": rd(sum(zh) / n),
        "deltaMean": rd(sum(deltas) / n),
        "deltaMedian": rd(deltas[n // 2]),
        "fracZhLower": rd(sum(1 for d in deltas if d < 0) / n),
        "hist": {"edges": hist_edges, "counts": hist},
    }
    jdump(SRC_DATA / "crosslang.json", out)


def build_heatmap(model_order, cohorts):
    """Cohort x model mean score from the raw records."""
    sums = defaultdict(float)
    counts = defaultdict(int)
    inputs = {e["id"]: e["cohort"] for e in json.load(open(ROOT / "data/inputs/pilot_entities.json"))}
    with gzip.open(ROOT / "data/raw/pilot_summary_en.csv.gz", "rt") as f:
        for r in csv.DictReader(f):
            cohort = inputs.get(r["entity_id"])
            if cohort is None:
                continue
            k = (cohort, r["model_id"])
            sums[k] += float(r["score"])
            counts[k] += 1
    cohort_order = [c for c in cohorts]  # already sorted by mean desc
    grid = [
        [rd(sums[(c, m)] / counts[(c, m)]) if counts[(c, m)] else None
         for m in model_order]
        for c in cohort_order
    ]
    jdump(SRC_DATA / "heatmap.json",
          {"cohorts": cohort_order, "models": model_order, "grid": grid})


HERO_IDS = ["sam_altman", "andrej_karpathy", "tianshou", "jiayi_weng",
            "bojie_li", "imo_dongyi_wei"]


def build_hero(model_order):
    m = json.load(open(ROOT / "data/analysis/namerank_matrix.json"))
    nr = {r["entity_id"]: (r["entity_name"], rd(r["namerank"]), r["cohort"])
          for r in csv.DictReader(open(ROOT / "data/analysis/namerank_per_entity.csv"))}
    inputs = {e["id"]: e for e in json.load(open(ROOT / "data/inputs/pilot_entities.json"))}
    out = []
    for eid in HERO_IDS:
        if eid not in m or eid not in nr:
            print(f"    WARNING: hero entity {eid} missing, skipped")
            continue
        name, nrv, cohort = nr[eid]
        out.append({
            "id": eid, "name": name, "nr": nrv, "cohort": cohort,
            "context": inputs.get(eid, {}).get("context", ""),
            "scores": [(rd(m[eid][mid]) if m[eid].get(mid) is not None else None)
                       for mid in model_order],
        })
    jdump(SRC_DATA / "hero_entities.json", out)


def build_stats(cohorts):
    stats = {
        "entities": 5719,
        "models": 37,
        "cohorts": 54,
        "records": 211603,
        "zhRecords": 8880,
        "zhEntities": 240,
        "inversionPairs": 11,
        "inversionCount": 8,
        "treadmillAtOrBelow": 7,
        "treadmillTotal": 9,
        "cvR2H": 0.38, "cvR2HSd": 0.09,
        "cvR2Cites": 0.12, "cvR2CitesSd": 0.07,
        "stanford": {"mean": 0.537, "n": 19},
        "tsinghua": {"mean": 0.258, "n": 4},
        "contextLiftMean": 0.058,
        "contextLiftJiayi": 0.288,
        "longTailBaseline": cohorts["long_tail_researcher_openalex"]["mean"],
        "probeTemplate": open(ROOT / "data/inputs/probe_template_en.txt").read().strip(),
    }
    jdump(SRC_DATA / "stats.json", stats)


def main():
    print("Building site data assets...")
    cohorts = build_cohorts()
    model_order = build_models()
    inputs = build_entities()
    build_matrix(model_order)
    gold = build_gold(inputs)
    cases = build_cases(inputs, gold)
    build_explainer_cases(cases)
    build_ladder(cohorts)
    build_inversion()
    build_country()
    build_crosslang()
    build_heatmap(model_order, cohorts)
    build_hero(model_order)
    build_stats(cohorts)
    print("Done.")


if __name__ == "__main__":
    main()
