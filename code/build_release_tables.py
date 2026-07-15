#!/usr/bin/env python3
"""Regenerate the released aggregate tables in data/analysis/ from the recognition
run — the single, authoritative NameRank metric used throughout the paper.

Record-level source of truth:
    experiments/t6_v2_protocol/outputs/recognition_final.jsonl[.gz]
        one binary `recognized` verdict per (dataset, entity_id, model_id),
        produced by the open-book anti-confabulation judge. The repo ships the
        gzipped form (~12MB); this script reads the plain .jsonl if present and
        falls back to the .gz otherwise, so no manual decompression is needed.

Everything here is a deterministic aggregation of that file plus the per-dataset
entity metadata. Numbers are cross-checked at the end against the paper's own
figure source (paper/figures/computed_numbers.json) so a drift is loud.

Outputs (all under data/analysis/):
    namerank_matrix.json        entity -> {model: recognized 0/1}   (main run)
    per_model_summary.csv       per-model recognition + refusal rates
    cohort_summary.csv          per-cohort recognition distribution
    credential_ladder.csv       the credential-treadmill table
    cs_faculty_by_country.csv   country gradient (CS-faculty cohort)
    cross_language_per_entity.csv  EN vs ZH recognition on the 240-entity sub-run
    attribution_pairs_v2.csv    creator vs artifact recognition (inversion pairs)

Run:  python3 code/build_release_tables.py
"""
from __future__ import annotations

import csv
import gzip
import json
import statistics as st
from collections import defaultdict
from pathlib import Path


def open_jsonl(path: Path):
    """Open a .jsonl, transparently falling back to its shipped .gz sibling."""
    if path.exists():
        return open(path)
    gz = path.with_suffix(path.suffix + ".gz")
    if gz.exists():
        return gzip.open(gz, "rt")
    raise FileNotFoundError(f"{path} (and {gz.name}) not found")

REPO = Path(__file__).resolve().parent.parent
T6 = REPO / "experiments" / "t6_v2_protocol"
FINAL = T6 / "outputs" / "recognition_final.jsonl"
ZH = T6 / "outputs" / "zh_results.jsonl"
OUT = REPO / "data" / "analysis"
COMPUTED = REPO / "paper" / "figures" / "computed_numbers.json"

ENTITY_FILES = {
    "main": T6 / "inputs" / "pilot_entities_v2.json",
    "awards": REPO / "experiments/t5_1_award_ladder/inputs/award_entities.json",
    "llm": REPO / "experiments/t5_5_llm_area/inputs/probe_entities.json",
    "univ": REPO / "experiments/t5_4_university_baseline/inputs/univ_entities_v2.json",
}

# 36-model recognition panel, partitioned by vendor country of origin (matches
# the Western/Chinese split the paper uses only for the cross-language check).
CHINESE_PREFIXES = ("deepseek", "glm", "kimi", "minimax", "qwen", "step")

# CS-faculty institution -> country (verbatim from the retired
# code/country_affiliation.py, which is how the paper's country gradient is cut).
COUNTRY_KEYWORDS = {
    "USA": ["Carnegie Mellon", "Cornell", "Michigan", "Washington", "Princeton", "Stanford",
            "Georgia Institute", "Johns Hopkins", "Illinois", "MIT", "Berkeley", "UCLA", "USC",
            "NYU", "Columbia", "Yale", "Harvard", "Brown", "Duke", "UT Austin", "Texas",
            "Penn", "UCSD", "UC San Diego", "Northwestern", "Wisconsin", "Maryland",
            "Massachusetts", "California", "Virginia", "Boston University", "Rutgers",
            "Rice", "Vanderbilt", "Caltech", "Buffalo", "Stony Brook", "Pittsburgh",
            "Notre Dame", "Indiana", "Ohio", "Florida", "Arizona", "Oregon", "Utah",
            "Colorado", "Iowa", "Kansas", "Minnesota", "Tennessee", "North Carolina",
            "George Washington", "Drexel"],
    "UK": ["Cambridge", "Oxford", "Imperial College", "UCL", "Edinburgh", "Manchester",
           "Glasgow", "Bristol", "Sussex", "Warwick", "Sheffield", "Leeds", "Lancaster",
           "Surrey", "Southampton", "Birmingham"],
    "Canada": ["Toronto", "Waterloo", "McGill", "British Columbia", "UBC", "Alberta",
               "Montreal", "Simon Fraser", "Western Ontario", "York University"],
    "China": ["Tsinghua", "Peking", "USTC", "Shanghai Jiao Tong", "Fudan", "Zhejiang",
              "Wuhan", "Harbin Institute", "Nanjing", "Xian Jiaotong", "Beihang",
              "Renmin", "Beijing Institute"],
    "Hong Kong": ["HKUST", "Chinese University of Hong Kong", "City University of Hong Kong",
                  "Hong Kong Polytechnic"],
    "Singapore": ["NTU", "Nanyang Technological", "NUS", "National University of Singapore"],
    "Australia": ["Monash", "Melbourne", "Sydney", "ANU", "Queensland", "New South Wales"],
    "Germany": ["TUM", "Max Planck", "Heidelberg", "Munich", "Berlin", "Stuttgart",
                "Karlsruhe", "RWTH", "Saarland", "Darmstadt", "Bonn"],
    "Netherlands": ["TU Delft", "Eindhoven", "Amsterdam", "Leiden", "Utrecht", "Groningen"],
    "Switzerland": ["ETH", "EPFL", "Lausanne", "Zurich"],
    "France": ["INRIA", "Paris", "Sorbonne", "Lyon", "Grenoble"],
    "Italy": ["Roma", "Milano", "Politecnico", "Bologna"],
    "Spain": ["A Coruna", "A Coruña", "Madrid", "Barcelona", "Polytechnic"],
    "Portugal": ["Lisboa", "Porto"],
    "Israel": ["Technion", "Hebrew University", "Tel Aviv", "Weizmann"],
    "Japan": ["Tokyo", "Kyoto", "Osaka"],
    "South Korea": ["KAIST", "Seoul", "POSTECH"],
    "India": ["IIT", "IIIT"],
    "Brazil": ["UFRGS", "USP", "UNICAMP"],
    "Sweden": ["KTH", "Chalmers", "Lund", "Stockholm"],
    "Russia": ["Moscow", "Saint Petersburg"],
    "Greece": ["Athens", "Thessaloniki", "Crete"],
}


def lookup_country(inst: str):
    il = (inst or "").lower()
    for country, kws in COUNTRY_KEYWORDS.items():
        if any(kw.lower() in il for kw in kws):
            return country
    return None


def vendor_of(mid: str) -> str:
    m = mid.lower()
    table = {
        "claude": "anthropic", "gpt-oss": "openai", "gpt": "openai",
        "gemini": "google", "gemma": "google", "llama": "meta",
        "mistral": "mistral", "phi": "microsoft", "nemotron": "nvidia",
        "deepseek": "deepseek", "glm": "zhipu", "kimi": "moonshot",
        "minimax": "minimax", "qwen": "alibaba", "step": "stepfun",
    }
    for pref, v in table.items():
        if m.startswith(pref):
            return v
    return "other"


def model_class(mid: str) -> str:
    return "chinese" if mid.lower().startswith(CHINESE_PREFIXES) else "western"


def load_final():
    """dataset -> {(eid, mid): recognized};  dataset -> {(eid, mid): rationale}"""
    rec = defaultdict(dict)
    rat = defaultdict(dict)
    with open_jsonl(FINAL) as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            ds, eid, mid = r["dataset"], r["entity_id"], r["model_id"]
            rec[ds][(eid, mid)] = int(r["recognized"])
            rat[ds][(eid, mid)] = r.get("rationale", "")
    return rec, rat


def entities(dataset):
    return {e["id"]: e for e in json.loads(ENTITY_FILES[dataset].read_text())}


def per_entity(rec, dataset):
    """eid -> dict(name, cohort, recognition, n_models, refusal_rate, votes{mid:0/1})"""
    ents = entities(dataset)
    votes = defaultdict(dict)
    for (eid, mid), v in rec[dataset].items():
        votes[eid][mid] = v
    out = {}
    for eid, mv in votes.items():
        e = ents.get(eid)
        if not e:
            continue
        vals = list(mv.values())
        out[eid] = {
            "name": e.get("name", eid),
            "cohort": e.get("cohort", "?"),
            "synthetic": bool(e.get("synthetic")),
            "gold_v2": bool(e.get("gold_v2", True)),
            "recognition": sum(vals) / len(vals),
            "n_models": len(vals),
            "votes": mv,
            "meta": e,
        }
    return out


def eligible(d):
    """The paper's cohort-mean population: real entities with a v2 gold, judged
    by the full panel (matches paper/figures/_data.cohort_table)."""
    return (not d["synthetic"]) and d["gold_v2"] and d["n_models"] >= 30


def q(sorted_vals, p):
    if not sorted_vals:
        return 0.0
    i = p * (len(sorted_vals) - 1)
    lo = int(i)
    if lo == len(sorted_vals) - 1:
        return sorted_vals[lo]
    frac = i - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[lo + 1] * frac


def r3(x):
    return round(float(x), 3)


# --------------------------------------------------------------------------- #
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rec, rat = load_final()
    main_pe = per_entity(rec, "main")
    awards_pe = per_entity(rec, "awards")
    computed = json.loads(COMPUTED.read_text())
    checks = []  # (label, ours, paper)

    # ---- namerank_matrix.json : entity -> {model: recognized} -------------- #
    matrix = {eid: dict(sorted(d["votes"].items())) for eid, d in main_pe.items()}
    (OUT / "namerank_matrix.json").write_text(json.dumps(matrix, indent=0))
    print(f"namerank_matrix.json         {len(matrix)} entities x "
          f"{len(next(iter(matrix.values())))} models")

    # ---- per_model_summary.csv -------------------------------------------- #
    by_model_rec = defaultdict(list)
    by_model_refuse = defaultdict(list)
    for (eid, mid), v in rec["main"].items():
        by_model_rec[mid].append(v)
        by_model_refuse[mid].append(1 if rat["main"][(eid, mid)] == "refusal" else 0)
    with open(OUT / "per_model_summary.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["model_id", "vendor", "class", "n_records",
                    "recognition_rate", "refusal_rate"])
        for mid in sorted(by_model_rec):
            recs = by_model_rec[mid]
            w.writerow([mid, vendor_of(mid), model_class(mid), len(recs),
                        r3(sum(recs) / len(recs)),
                        r3(sum(by_model_refuse[mid]) / len(recs))])
    print(f"per_model_summary.csv        {len(by_model_rec)} models")

    # ---- cohort_summary.csv ----------------------------------------------- #
    coh = defaultdict(list)
    coh_ref = defaultdict(list)
    for eid, d in main_pe.items():
        if not eligible(d):
            continue
        coh[d["cohort"]].append(d["recognition"])
        # entity refusal rate = fraction of its models that hard-refused
        refs = [1 if rat["main"][(eid, mid)] == "refusal" else 0
                for mid in d["votes"]]
        coh_ref[d["cohort"]].append(sum(refs) / len(refs))
    with open(OUT / "cohort_summary.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cohort", "n", "mean", "median", "sd",
                    "p10", "p25", "p75", "p90",
                    "frac_recognized", "frac_silent", "refusal_rate"])
        for c in sorted(coh):
            vals = sorted(coh[c])
            n = len(vals)
            w.writerow([c, n, r3(st.mean(vals)), r3(st.median(vals)),
                        r3(st.pstdev(vals) if n > 1 else 0.0),
                        r3(q(vals, .10)), r3(q(vals, .25)),
                        r3(q(vals, .75)), r3(q(vals, .90)),
                        r3(sum(v >= 0.5 for v in vals) / n),
                        r3(sum(v == 0.0 for v in vals) / n),
                        r3(st.mean(coh_ref[c]))])
    print(f"cohort_summary.csv           {len(coh)} cohorts")
    for slug, key in [("long_tail_researcher_openalex", "main.baseline"),
                      ("cs_faculty", "main.faculty")]:
        if coh.get(slug):
            checks.append((f"cohort {slug}", round(st.mean(coh[slug]), 3),
                           computed.get(key)))

    # ---- credential_ladder.csv -------------------------------------------- #
    # static descriptors (cohort -> label/rung/prestige); values recomputed.
    CRED = [
        ("imo_gold", "International Math Olympiad gold", "HS-math", "high", "main"),
        ("ioi_gold", "International Olympiad in Informatics gold", "HS-CS", "high", "main"),
        ("icpc_world_finals_gold", "ICPC World Finalist gold", "UG-CS", "high", "main"),
        ("putnam_fellow", "Putnam top-25 fellow", "UG-math", "high", "main"),
        ("cmo_china_gold", "China Math Olympiad gold", "HS-math-CN", "high", "main"),
        ("noi_china_gold", "National Olympiad in Informatics China gold", "HS-CS-CN", "high", "main"),
        ("cpho_china_first_prize", "China Physics Olympiad first prize", "HS-physics-CN", "med", "main"),
        ("rhodes_scholar", "Rhodes Scholarship recipient", "UG-general", "high", "main"),
        ("msra_phd_fellowship", "MSRA PhD Fellowship", "PhD", "med", "main"),
        ("deepseek_v3_author", "DeepSeek-V3 paper author", "paper-author", "ind", "main"),
        ("gpt5_system_card_author", "GPT-5 system card author", "paper-author", "ind", "main"),
    ]
    key_map = {"imo_gold": "main.imo", "ioi_gold": "main.ioi",
               "icpc_world_finals_gold": "main.icpc", "putnam_fellow": "main.putnam",
               "cmo_china_gold": "main.cmo", "noi_china_gold": "main.noi",
               "cpho_china_first_prize": "main.cpho", "rhodes_scholar": "main.rhodes",
               "msra_phd_fellowship": "main.msra", "deepseek_v3_author": "main.deepseek",
               "gpt5_system_card_author": "main.gpt5"}
    with open(OUT / "credential_ladder.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["credential", "rung", "prestige", "n", "mean", "median", "sd"])
        for slug, label, rung, prestige, ds in CRED:
            src = main_pe if ds == "main" else awards_pe
            vals = sorted(d["recognition"] for d in src.values()
                          if d["cohort"] == slug and eligible(d))
            mean = st.mean(vals)
            w.writerow([label, rung, prestige, len(vals), r3(mean),
                        r3(st.median(vals)),
                        r3(st.pstdev(vals) if len(vals) > 1 else 0.0)])
            checks.append((f"credential {slug}", round(mean, 3),
                           computed.get(key_map[slug])))
    print(f"credential_ladder.csv        {len(CRED)} rungs")

    # ---- cs_faculty_by_country.csv ---------------------------------------- #
    by_country = defaultdict(list)
    for d in main_pe.values():
        if d["cohort"] != "cs_faculty" or not eligible(d):
            continue
        country = lookup_country(d["meta"].get("institution", ""))
        if country:
            by_country[country].append(d["recognition"])
    with open(OUT / "cs_faculty_by_country.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["country", "n", "mean", "median", "sd", "frac_above_0_5"])
        rows = [(c, sorted(v)) for c, v in by_country.items() if len(v) >= 5]
        for c, vals in sorted(rows, key=lambda x: -st.mean(x[1])):
            n = len(vals)
            w.writerow([c, n, r3(st.mean(vals)), r3(st.median(vals)),
                        r3(st.pstdev(vals) if n > 1 else 0.0),
                        r3(sum(v >= 0.5 for v in vals) / n)])
    print(f"cs_faculty_by_country.csv    {len(rows)} countries (n>=5)")
    for lab, key in [("USA", "country.usa"), ("China", "country.china"),
                     ("India", "country.india")]:
        v = by_country.get(lab)
        if v:
            checks.append((f"country {lab}", round(st.mean(v), 3), computed.get(key)))

    # ---- cross_language_per_entity.csv ------------------------------------ #
    zh = defaultdict(dict)
    zh_meta = {}
    with open_jsonl(ZH) as f:
        for line in f:
            r = json.loads(line)
            zh[r["entity_id"]][r["model_id"]] = int(r["recognized"])
            zh_meta[r["entity_id"]] = (r.get("entity_name"), r.get("cohort"))

    def split_mean(votes):
        w_ = [v for m, v in votes.items() if model_class(m) == "western"]
        c_ = [v for m, v in votes.items() if model_class(m) == "chinese"]
        allv = list(votes.values())
        return (sum(allv) / len(allv) if allv else None,
                sum(w_) / len(w_) if w_ else None,
                sum(c_) / len(c_) if c_ else None)

    rows = []
    for eid, zv in zh.items():
        d = main_pe.get(eid)
        if not d:
            continue
        en_all, en_w, en_c = split_mean(d["votes"])
        zh_all, zh_w, zh_c = split_mean(zv)
        name, cohort = zh_meta[eid]
        rows.append([eid, name or d["name"], cohort or d["cohort"],
                     r3(en_all), r3(zh_all), r3(zh_all - en_all),
                     r3(en_w), r3(en_c), r3(zh_w), r3(zh_c),
                     r3(zh_w - en_w), r3(zh_c - en_c)])
    rows.sort(key=lambda r: r[0])
    with open(OUT / "cross_language_per_entity.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["entity_id", "entity_name", "cohort",
                    "en_all", "zh_all", "delta_zh_minus_en",
                    "en_western", "en_chinese", "zh_western", "zh_chinese",
                    "western_lang_lift", "chinese_lang_lift"])
        w.writerows(rows)
    print(f"cross_language_per_entity.csv {len(rows)} entities")

    # ---- attribution_pairs_v2.csv ----------------------------------------- #
    name2rec = {}
    for d in main_pe.values():
        name2rec.setdefault(d["name"].lower(), d["recognition"])
    PAIRS = [
        ("Jiayi Weng", "Tianshou"), ("Andrej Karpathy", "nanoGPT"),
        ("Harrison Chase", "LangChain"), ("Tri Dao", "FlashAttention"),
        ("Lilian Weng", "lilianweng.github.io"), ("Simon Willison", "Datasette"),
        ("Aman Sanger", "Cursor"), ("Dario Amodei", "Anthropic"),
        ("Demis Hassabis", "Google DeepMind"), ("Mira Murati", "Thinking Machines Lab"),
        ("Aravind Srinivas", "Perplexity"),
    ]
    with open(OUT / "attribution_pairs_v2.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["creator", "artifact", "creator_recognition",
                    "artifact_recognition", "artifact_minus_creator"])
        n_written = 0
        for creator, artifact in PAIRS:
            cv, av = name2rec.get(creator.lower()), name2rec.get(artifact.lower())
            if cv is None or av is None:
                print(f"  ! pair skipped (missing recognition): {creator} / {artifact}")
                continue
            w.writerow([creator, artifact, r3(cv), r3(av), r3(av - cv)])
            n_written += 1
    print(f"attribution_pairs_v2.csv     {n_written} pairs")

    # ---- verification ----------------------------------------------------- #
    print("\nverification vs paper/figures/computed_numbers.json:")
    ok = True
    for label, ours, paper in checks:
        if paper is None:
            print(f"  ?  {label:28} ours={ours}  (no paper value)")
            continue
        match = abs(ours - paper) <= 0.002
        ok = ok and match
        print(f"  {'OK' if match else 'XX'} {label:28} ours={ours}  paper={paper}")
    print("\nALL CHECKS PASS" if ok else "\n*** MISMATCH — investigate ***")


if __name__ == "__main__":
    main()
