#!/usr/bin/env python3
"""Build compact JSON data assets for the NameRank explainer site.

Every output reflects the paper's RECOGNITION-VERDICT metric (binary
recognized/not, 36-model panel), read through the paper's own figure data
provider (paper/figures/_data.py) and anchored to the authoritative scalar
table (paper/figures/computed_numbers.json). Table-only numbers are lifted
verbatim from the recognition-vintage LaTeX tables in paper/appendix.tex.

Writes:
  site/src/data/*.json      -- small assets imported at build time
  site/public/data/*.json   -- larger assets fetched lazily at runtime

Run from the repo root:  python3 site/scripts/build_data.py
"""

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC_DATA = ROOT / "site" / "src" / "data"
PUB_DATA = ROOT / "site" / "public" / "data"

sys.path.insert(0, str(ROOT / "paper" / "figures"))
import _data  # noqa: E402  (recognition data provider)
from _style import COHORT_NAMES, CREDENTIAL_COHORTS  # noqa: E402

CN = json.load(open(ROOT / "paper" / "figures" / "computed_numbers.json"))


def jdump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  wrote {path.relative_to(ROOT)}  ({path.stat().st_size/1024:.0f} KB)")


def rd(x, nd=3):
    if x is None:
        return None
    return round(float(x), nd)


# ---------------------------------------------------------------- cohort helper
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


# ---------------------------------------------------------------- shared recognition state
def load_state():
    """Recognition verdicts + refusal flags for the main dataset."""
    ents = _data.entities("main")
    ent_cohort = {eid: e.get("cohort", "?") for eid, e in ents.items()}

    V = _data._verdicts("main")  # {(entity_id, model_id): 0/1 recognized}
    print(f"    recognition source: {_data.source_report()}")

    # refusal flags come from the raw records (rationale == 'refusal')
    ref_model = defaultdict(list)
    ref_entity = defaultdict(list)
    ref_cohort = defaultdict(list)
    with open(_data.FINAL) as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("dataset") != "main":
                continue
            isref = 1 if r.get("rationale") == "refusal" else 0
            m, e = r["model_id"], r["entity_id"]
            ref_model[m].append(isref)
            ref_entity[e].append(isref)
            ref_cohort[ent_cohort.get(e, "?")].append(isref)

    # model order: recognition mean desc
    recog_by_model = defaultdict(list)
    for (_e, m), rec in V.items():
        recog_by_model[m].append(rec)
    model_order = sorted(recog_by_model, key=lambda m: -sum(recog_by_model[m]) / len(recog_by_model[m]))

    def mean(xs):
        return sum(xs) / len(xs) if xs else None

    return {
        "ents": ents,
        "V": V,
        "model_order": model_order,
        "recog_by_model": recog_by_model,
        "ref_model": {m: mean(v) for m, v in ref_model.items()},
        "ref_entity": {e: mean(v) for e, v in ref_entity.items()},
        "ref_cohort": {c: mean(v) for c, v in ref_cohort.items()},
        "per_entity": _data.per_entity("main"),
    }


# ================================================================ BUNDLED
def build_stats(st):
    self_report = json.load(open(ROOT / "experiments/t5_4_self_report/outputs/summary.json"))
    stats = {
        "entities": 4685,
        "models": 36,
        "cohorts": 54,
        "baseline": rd(CN["main.baseline"], 4),
        "faculty": rd(CN["main.faculty"], 4),
        "floors": {"people": rd(CN["floor.people"], 4), "papers": rd(CN["floor.papers"], 4)},
        "var": {"entity": CN["var.entity"], "cohort": CN["var.cohort"], "model": CN["var.model"]},
        "hindex": {
            "r2H": CN["hindex.r2_h"], "r2Cites": CN["hindex.r2_cites"],
            "r2Joint": CN["hindex.r2_joint"], "n": CN["hindex.n"],
        },
        "injectionLift": CN["injection.mean_lift"],  # -0.013 (recognition; near-zero)
        "selfreport": {
            "rhoAggregate": CN["selfreport.rho_aggregate"],   # 0.83
            "rhoInterModel": CN["selfreport.rho_inter_model"],  # 0.9
            "rhoPanelFame": CN["selfreport.rho_panel_fame"],   # 0.57
            # "borrowed, not introspective": self-rank ~ own scores among known
            "rhoOwnKnown": rd(self_report["gpt-5.5-think"]["bt"]["rho_own_known"], 4),  # 0.043
            "rhoOwnAll": CN["selfreport.rho_own_behavior"],    # 0.3 (all entities)
        },
        "probeTemplate": open(ROOT / "data/inputs/probe_template_en.txt").read().strip(),
    }
    jdump(SRC_DATA / "stats.json", stats)


def build_cohorts(st):
    ct = _data.cohort_table("main", min_n=10)  # cohort, recognition, ci95, n_ent
    pe = st["per_entity"]
    real = pe[~pe.synthetic & pe.gold_v2 & (pe.n_models >= 30)].copy()
    real["any"] = real.recognition > 0
    recog_any = real.groupby("cohort")["any"].mean().to_dict()
    out = []
    for r in ct.to_dict("records"):
        slug = r["cohort"]
        out.append({
            "slug": slug,
            "name": COHORT_NAMES.get(slug, slug.replace("_", " ")),
            "category": cohort_category(slug),
            "n": int(r["n_ent"]),
            "mean": rd(r["recognition"]),
            "ci95": rd(r["ci95"]),
            "recognized": rd(recog_any.get(slug, 0.0)),
            "refusal": rd(st["ref_cohort"].get(slug)),
        })
    out.sort(key=lambda c: -c["mean"])
    jdump(SRC_DATA / "cohorts.json", out)


VENDOR_PREFIX = [
    ("gpt-oss", "openai"), ("gpt", "openai"), ("claude", "anthropic"),
    ("gemini", "google"), ("gemma", "google"), ("grok", "xai"),
    ("deepseek", "deepseek"), ("glm", "zhipu"), ("qwen", "alibaba"),
    ("kimi", "moonshot"), ("minimax", "minimax"), ("step", "stepfun"),
    ("nemotron", "nvidia"), ("llama", "meta"), ("phi", "microsoft"),
    ("mistral", "mistral"),
]


def derive_vendor(mid: str) -> str:
    for pre, vend in VENDOR_PREFIX:
        if mid.startswith(pre):
            return vend
    return mid.split("-")[0]


def build_models(st):
    meta = {}
    for f in ("data/inputs/model_set.json",
              "experiments/t4_1_news_events/inputs/model_set_replacements.json"):
        for m in json.load(open(ROOT / f)):
            meta[m["id"]] = m
    cutoffs = {m["id"]: m.get("training_cutoff")
               for m in json.load(open(ROOT / "data/analysis/model_cutoffs.json"))}
    out = []
    for mid in st["model_order"]:
        recs = st["recog_by_model"][mid]
        m = meta.get(mid, {})
        vendor = m.get("vendor") or derive_vendor(mid)
        out.append({
            "id": mid,
            "mean": rd(sum(recs) / len(recs), 4),
            "refusal": rd(st["ref_model"].get(mid), 4),
            "vendor": vendor,
            "lab": m.get("lab") or vendor.title(),
            "thinking": bool(m.get("thinking", "think" in mid)),
            "cutoff": cutoffs.get(mid),
        })
    out.sort(key=lambda m: -m["mean"])
    n = len(out)
    if n != 36:
        print(f"    WARNING: panel has {n} models, expected 36")
    jdump(SRC_DATA / "models.json", out)


HERO_IDS = ["sam_altman", "andrej_karpathy", "tianshou", "jiayi_weng",
            "bojie_li", "imo_dongyi_wei"]


def build_hero(st):
    ents, V, model_order = st["ents"], st["V"], st["model_order"]
    pe = st["per_entity"].set_index("entity_id")
    out = []
    for eid in HERO_IDS:
        if eid not in pe.index or not any(e == eid for (e, _m) in V):
            print(f"    WARNING: hero entity {eid} missing, skipped")
            continue
        row = pe.loc[eid]
        e = ents.get(eid, {})
        out.append({
            "id": eid,
            "name": e.get("name", eid),
            "nr": rd(row.recognition),
            "cohort": e.get("cohort", "?"),
            "context": e.get("context", ""),
            "scores": [V.get((eid, m)) for m in model_order],
        })
    jdump(SRC_DATA / "hero.json", out)


def build_ladder(st):
    ct = _data.cohort_table("main", min_n=10).set_index("cohort")
    rows = []
    for slug in CREDENTIAL_COHORTS:
        if slug not in ct.index:
            print(f"    WARNING: credential cohort {slug} below min_n, skipped")
            continue
        r = ct.loc[slug]
        rows.append({
            "credential": COHORT_NAMES.get(slug, slug.replace("_", " ")),
            "slug": slug,
            "mean": rd(r.recognition),
            "n": int(r.n_ent),
        })
    rows.sort(key=lambda x: -x["mean"])
    out = {
        "rows": rows,
        "baseline": {"label": "Working researchers (OpenAlex long tail)",
                     "mean": rd(CN["main.baseline"], 4)},
        "floor": rd(CN["floor.people"], 4),
    }
    jdump(SRC_DATA / "ladder.json", out)


AWARD_GROUPS = {
    "early": [("imo", "main.imo", "IMO gold"), ("ioi", "main.ioi", "IOI gold"),
              ("noi", "main.noi", "NOI China gold"), ("cmo", "main.cmo", "CMO China gold"),
              ("cpho", "main.cpho", "CPhO first prize"), ("rhodes", "main.rhodes", "Rhodes Scholar"),
              ("msra", "main.msra", "MSRA PhD Fellowship"), ("putnam", "main.putnam", "Putnam top-25"),
              ("icpc", "main.icpc", "ICPC World Finals gold")],
    "llm": [("llm_foundational", "llm.llm_foundational", "Foundational-paper authors"),
            ("llm_bestpaper", "llm.llm_bestpaper", "Best-paper authors"),
            ("llm_method", "llm.llm_method", "Named-method originators")],
    "mid": [("godel", "awards.godel", "Gödel Prize"), ("acmfellow", "awards.acmfellow", "ACM Fellow"),
            ("macarthur", "awards.macarthur", "MacArthur Fellow"), ("sloan", "awards.sloan", "Sloan Fellow"),
            ("acmprize", "awards.acmprize", "ACM Prize in Computing")],
    "marquee": [("fields", "awards.fields", "Fields Medal"), ("turing", "awards.turing", "Turing Award"),
                ("nobel", "awards.nobel", "Nobel Prize (Physics)")],
}


def build_awards():
    baseline = CN["main.baseline"]  # 0.396
    out = []
    for group, entries in AWARD_GROUPS.items():
        for key, cnkey, label in entries:
            mean = CN[cnkey]
            out.append({
                "key": key, "label": label, "group": group,
                "mean": rd(mean), "vsBaseline": rd(mean - baseline),
            })
    jdump(SRC_DATA / "awards.json",
          {"baseline": rd(baseline, 4), "floor": rd(CN["floor.people"], 4), "entries": out})


# tab:inversion (recognition vintage) + tab:injection (recognition delta B-A)
# creator, NRc, artifact, NRa, delta(a-c), C->A, A->C
INVERSION = [
    ("Jiayi Weng", 0.22, "Tianshou", 0.78, 0.56, 0.25, 0.00),
    ("Aman Sanger", 0.58, "Cursor", 0.81, 0.23, 1.00, 0.00),
    ("Tri Dao", 0.72, "FlashAttention", 0.94, 0.22, 0.74, 0.54),
    ("Harrison Chase", 0.75, "LangChain", 0.94, 0.19, 1.00, 0.22),
    ("Simon Willison", 0.83, "Datasette", 1.00, 0.17, 0.54, 0.89),
    ("Aravind Srinivas", 0.75, "Perplexity", 0.89, 0.14, 1.00, 0.33),
    ("Dario Amodei", 0.92, "Anthropic", 1.00, 0.08, 1.00, 0.41),
    ("Demis Hassabis", 1.00, "Google DeepMind", 1.00, 0.00, 1.00, 0.62),
    ("Andrej Karpathy", 0.86, "nanoGPT", 0.78, -0.08, 0.05, 0.76),
    ("Mira Murati", 0.78, "Thinking Machines Lab", 0.17, -0.61, 0.97, 1.00),
]
INJECTION = {
    "Jiayi Weng": 0.11, "Simon Willison": 0.08, "Tri Dao": 0.06, "Aman Sanger": 0.03,
    "Harrison Chase": 0.00, "Demis Hassabis": 0.00, "Andrej Karpathy": -0.03,
    "Mira Murati": -0.08, "Aravind Srinivas": -0.08, "Dario Amodei": -0.11,
}


def build_inversion():
    out = [{
        "creator": c, "nrCreator": nc, "artifact": a, "nrArtifact": na,
        "delta": d, "cToA": ca, "aToC": ac, "injectionDelta": INJECTION.get(c),
    } for c, nc, a, na, d, ca, ac in INVERSION]
    jdump(SRC_DATA / "inversion.json", out)


def build_noi():
    s = json.load(open(ROOT / "experiments/t5_3_noi_medal_tiers/outputs/tier_openbook_summary.json"))
    tiers = {}
    for t, d in s["tiers"].items():
        tiers[t] = {
            "n": d["n"], "mean": rd(d["mean"]), "median": rd(d["median"]),
            "silentZero": d["silent_zero"], "recognizedAny": d["recognized_any"],
        }
    scatter = []
    csv_path = ROOT / "experiments/t5_3_noi_medal_tiers/outputs/tier_openbook_per_entity.csv"
    if csv_path.exists():
        for r in csv.DictReader(open(csv_path)):
            scatter.append({"name": r["name"], "tier": r["tier"],
                            "nr": rd(float(r["recognition"]))})
    out = {
        "floor": rd(s["floor_synthetic_noi"], 4),
        "tiers": tiers,
        "kruskalP": s["kruskal_p"],
        "cliffGoldSilver": rd(s["cliff_gold_silver"]),
        "cliffSilverBronze": rd(s["cliff_silver_bronze"]),
        "mwuSilverBronzeP": rd(s["mwu_silver_bronze_p"]),
        "scatter": scatter,
    }
    jdump(SRC_DATA / "noi.json", out)


def build_bibliometrics():
    out = {
        "r2": {"h": CN["hindex.r2_h"], "cites": CN["hindex.r2_cites"], "joint": CN["hindex.r2_joint"]},
        "n": CN["hindex.n"],
        # tab:h-index-decile (recognition vintage)
        "deciles": [
            {"decile": 1, "h": 4, "mean": 0.18},
            {"decile": 4, "h": 18, "mean": 0.38},
            {"decile": 7, "h": 31, "mean": 0.46},
            {"decile": 10, "h": 61, "mean": 0.60},
        ],
    }
    jdump(SRC_DATA / "bibliometrics.json", out)


def build_geography():
    inst = {
        "mit": {"raw": CN["univ.fac_mit"], "matched": CN["univ.win_mit"]},
        "berkeley": {"raw": CN["univ.fac_berkeley"], "matched": CN["univ.win_berkeley"]},
        "ucsd": {"raw": CN["univ.fac_ucsd"], "matched": CN["univ.win_ucsd"]},
        "irvine": {"raw": CN["univ.fac_irvine"], "matched": CN["univ.win_irvine"]},
    }
    countries = [
        {"country": "USA", "n": CN["country.usa_n"], "mean": CN["country.usa"]},
        {"country": "UK", "n": 10, "mean": 0.64},          # tab:cs-country
        {"country": "Hong Kong", "n": 8, "mean": 0.59},    # tab:cs-country
        {"country": "Canada", "n": 8, "mean": 0.58},       # tab:cs-country
        {"country": "China", "n": CN["country.china_n"], "mean": CN["country.china"]},
        {"country": "India", "n": CN["country.india_n"], "mean": CN["country.india"]},
    ]
    countries.sort(key=lambda c: -c["mean"])
    jdump(SRC_DATA / "geography.json", {"institutions": inst, "countries": countries})


def build_events():
    a = json.load(open(ROOT / "experiments/t4_1_news_events/outputs/analysis.json"))
    deciles = [{
        "decile": d["decile"], "n": d["n"], "geomeanViews": d["geomean_views"],
        "meanNr": rd(d["mean_nr"]), "refusal": rd(d["refusal"]),
    } for d in a["deciles"]]
    out = {
        "n": a["n"],
        "deciles": deciles,
        "r2": {"total": rd(a["r2_total_views"]), "peak": rd(a["r2_peak_views"]),
               "duration": rd(a["r2_eff_duration"])},
        "stdCoef": {"peak": rd(a["peak_vs_duration"]["beta_peak"]),
                    "duration": rd(a["peak_vs_duration"]["beta_dur"])},
        "recurringAdjDelta": rd(a["recurring"]["adj_delta"]),
    }
    jdump(SRC_DATA / "events.json", out)


def build_selfreport():
    s = json.load(open(ROOT / "experiments/t5_4_self_report/outputs/summary.json"))
    per = []
    for mid, d in s.items():
        if mid.startswith("_"):
            continue
        bt, binr, trap = d["bt"], d["binary"], d["trap"]
        per.append({
            "model": mid,
            "rhoPanel": rd(bt["rho_panel_known"]),
            "rhoOwnKnown": rd(bt["rho_own_known"], 4),
            "pickedKnown": rd(binr["picked_known"]),
            "pickedUnknown": rd(binr["picked_unknown"]),
            "neither": rd(binr["neither"]),
            "trapFalse": rd(trap["false_recognition"], 4),
            "reversal": rd(d["position_consistency"]),
        })
    out = {
        "models": per,
        "aggregate": {"rhoAggregate": CN["selfreport.rho_aggregate"],
                      "rhoInterModel": CN["selfreport.rho_inter_model"]},
    }
    jdump(SRC_DATA / "selfreport.json", out)


# tab:cross-lang (recognition vintage): cohort, n, en, zh, delta
CROSSLANG = [
    ("MSRA PhD Fellowship", 30, 0.166, 0.183, 0.018),
    ("DeepSeek-V3 authors", 69, 0.069, 0.075, 0.006),
    ("CMO China gold", 30, 0.029, 0.028, -0.001),
    ("NOI China gold", 29, 0.086, 0.084, -0.002),
    ("CPhO China first prize", 30, 0.034, 0.029, -0.006),
    ("Diagnostic reference set", 37, 0.627, 0.615, -0.012),
    ("Writers (control)", 5, 0.906, 0.872, -0.033),
    ("Filmmakers (control)", 5, 0.994, 0.961, -0.033),
    ("Politicians (control)", 5, 0.900, 0.861, -0.039),
]


def build_crosslang():
    rows = [{"cohort": c, "n": n, "en": en, "zh": zh, "delta": d}
            for c, n, en, zh, d in CROSSLANG]
    out = {"rows": rows, "summary": {"maxAbsDelta": 0.04}}
    jdump(SRC_DATA / "crosslang.json", out)


def build_robustness():
    out = {
        "variance": {"entity": CN["var.entity"], "cohort": CN["var.cohort"], "model": CN["var.model"]},
        # tab:cross-judge-bias overall row + kappa (Gemini/Claude)
        "crossJudge": {"gemini": 0.57, "claude": 0.58, "gpt": 0.42, "kappaGeminiClaude": 0.89},
        "paraphrase": {"templateVarPct": 0, "rhoLadder": 0.997},
        "floors": {"people": rd(CN["floor.people"], 4), "papers": rd(CN["floor.papers"], 4)},
        "confounds": {"wikipediaR2": 0.10, "hindexR2": CN["hindex.r2_h"]},
    }
    jdump(SRC_DATA / "robustness.json", out)


# ================================================================ FETCHED
def build_entities(st):
    ents = st["ents"]
    pe = st["per_entity"]
    real = pe[~pe.synthetic]
    cols = ["id", "name", "cohort", "country", "year", "nr", "refusal"]
    rows = []
    for r in real.to_dict("records"):
        eid = r["entity_id"]
        e = ents.get(eid, {})
        rows.append([
            eid, r["name"], r["cohort"],
            e.get("credential_country") or None,
            e.get("credential_year") or None,
            rd(r["recognition"]),
            rd(st["ref_entity"].get(eid)),
        ])
    rows.sort(key=lambda x: -(x[5] or 0))
    jdump(PUB_DATA / "entities.json", {"cols": cols, "rows": rows})
    return len(rows)


def build_matrix(st):
    V, model_order = st["V"], st["model_order"]
    ents = set(e for (e, _m) in V)
    scores = {eid: [V.get((eid, m)) for m in model_order] for eid in ents}
    jdump(PUB_DATA / "matrix.json", {"models": model_order, "scores": scores})


def build_gold(st):
    gold = json.load(open(ROOT / "data/inputs/gold_answers.json"))
    ents = st["ents"]
    by_cohort = defaultdict(dict)
    for eid, text in gold.items():
        cohort = ents.get(eid, {}).get("cohort", "unknown")
        by_cohort[cohort][eid] = text
    for cohort, d in by_cohort.items():
        jdump(PUB_DATA / "gold" / f"{cohort}.json", d)
    return gold


def build_cases(st, gold):
    recs = json.load(open(ROOT / "experiments/t2_10_cross_judge/sample_records.json"))
    claude = json.load(open(ROOT / "experiments/t2_10_cross_judge/claude_judge.json"))
    gpt = json.load(open(ROOT / "experiments/t2_10_cross_judge/gpt_judge.json"))
    ents = st["ents"]
    nr = dict(zip(st["per_entity"].entity_id, st["per_entity"].recognition))
    out = []
    for i, r in enumerate(recs):
        eid = r["entity_id"]
        case = {
            "i": i,
            "entity": eid,
            "name": r["entity_name"],
            "model": r["model_id"],
            "cohort": r["cohort"],
            "context": ents.get(eid, {}).get("context", ""),
            "nr": rd(nr.get(eid)),
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


def build_explainer_cases(cases):
    """Pick four archetypes: full recognition, partial, hallucination, refusal."""
    def key(c):
        return c["judges"]["gemini"]

    chosen = {}
    full = [c for c in cases if key(c)["score"] >= 0.85 and not c["refusal"]
            and c["cohort"] == "reference_pilot" and len(c["response"]) < 1400]
    if full:
        chosen["full"] = max(full, key=lambda c: key(c)["score"])
    part = [c for c in cases if 0.3 <= key(c)["cov"] <= 0.55 and key(c)["acc"] >= 0.9
            and not c["refusal"] and len(c["response"]) < 1200]
    if part:
        chosen["partial"] = part[0]
    hall = [c for c in cases if key(c)["cov"] >= 0.3 and key(c)["acc"] <= 0.45
            and not c["refusal"] and len(c["response"]) < 1400]
    if hall:
        chosen["hallucination"] = max(hall, key=lambda c: key(c)["cov"] - key(c)["acc"])
    ref = [c for c in cases if c["refusal"] and 0 < len(c["response"]) < 400]
    ref.sort(key=lambda c: (c["name"] != "Jiayi Weng", c["model"] != "gpt-5.4"))
    if ref:
        chosen["refusal"] = ref[0]
    jdump(SRC_DATA / "explainer_cases.json", chosen)
    for k, v in chosen.items():
        print(f"    explainer[{k}] = {v['name']} x {v['model']} "
              f"(cov {key(v)['cov']}, acc {key(v)['acc']})")


def build_answers():
    """Shard every verbatim model answer into per-entity JSON files.

    Reads the MAIN dataset (full_v2_results.jsonl) grouped by entity, joins the
    authoritative recognition verdict from recognition_final.jsonl, and writes
    site/public/data/answers/<entity_id>.json plus a compact answers_index.json.
    """
    RESULTS = ROOT / "experiments/t6_v2_protocol/outputs/full_v2_results.jsonl"
    RECOG = ROOT / "experiments/t6_v2_protocol/outputs/recognition_final.jsonl"
    ENTS = ROOT / "experiments/t6_v2_protocol/inputs/pilot_entities_v2.json"

    # 1. recognition verdicts (main only): (entity_id, model_id) -> (recognized, rationale)
    verdict = {}
    with open(RECOG) as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("dataset") != "main":
                continue
            verdict[(r["entity_id"], r["model_id"])] = (
                int(r.get("recognized", 0)), r.get("rationale", "") or "")

    # entity metadata; skip synthetic entities
    ent_meta = {}
    for e in json.load(open(ENTS)):
        if e.get("synthetic"):
            continue
        ent_meta[e["id"]] = e

    # 2. stream results once, grouping records by entity_id (non-synthetic only)
    by_entity = defaultdict(list)
    with open(RESULTS) as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            eid = r.get("entity_id")
            if eid not in ent_meta:
                continue
            by_entity[eid].append(r)

    # 3. write one shard per entity + 4. build compact index
    answers_dir = PUB_DATA / "answers"
    index = {}
    n_files = 0
    for eid, recs in by_entity.items():
        e = ent_meta[eid]
        answers = []
        n_rec = n_ref = 0
        for r in recs:
            mid = r["model_id"]
            rec, rat = verdict.get((eid, mid), (0, ""))
            refusal = bool(r.get("is_refusal"))
            n_rec += 1 if rec else 0
            n_ref += 1 if refusal else 0
            text = (r.get("response") or "").strip()
            if len(text) > 1600:
                text = text[:1600]
            answers.append({
                "model": mid,
                "recognized": rec,
                "refusal": refusal,
                "response": text,
                "rationale": rat,
            })
        # recognized first (1 before 0), non-refusal before refusal, then model_id
        answers.sort(key=lambda a: (-a["recognized"], a["refusal"], a["model"]))
        nr = round(n_rec / len(answers), 3) if answers else 0.0
        jdump(answers_dir / f"{eid}.json", {
            "id": eid,
            "name": e.get("name", eid),
            "cohort": e.get("cohort", "?"),
            "context": e.get("context", ""),
            "nr": nr,
            "answers": answers,
        })
        index[eid] = {"n": len(answers), "rec": n_rec, "ref": n_ref}
        n_files += 1

    jdump(PUB_DATA / "answers_index.json", index)
    print(f"    answer shards written: {n_files}")
    return n_files


def main():
    print("Building site data assets (recognition metric)...")
    st = load_state()
    # bundled
    build_stats(st)
    build_cohorts(st)
    build_models(st)
    build_hero(st)
    build_ladder(st)
    build_awards()
    build_inversion()
    build_noi()
    build_bibliometrics()
    build_geography()
    build_events()
    build_selfreport()
    build_crosslang()
    build_robustness()
    # fetched
    n_ent = build_entities(st)
    build_matrix(st)
    gold = build_gold(st)
    cases = build_cases(st, gold)
    build_explainer_cases(cases)
    build_answers()
    print(f"Done. panel models = {len(st['model_order'])}, real entities = {n_ent}")


if __name__ == "__main__":
    main()
