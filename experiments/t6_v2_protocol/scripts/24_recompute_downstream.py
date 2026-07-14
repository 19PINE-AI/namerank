"""Post-uniform-pass recompute of the downstream appendix numbers on the
recognition verdict. Run after FINAL_JUDGE_DONE (main+events+llm+univ) and the
zh sub-run finish. Emits paper_numbers_downstream.json and, for events, rebuilds
event_summary.csv (score := recognized) then invokes the existing analyze.py so
the attention regressions recompute on recognition.

Sections covered:
  events     rebuild event_summary.csv from recognition_final(events) -> analyze.py
  crosslang  NR_en (main verdicts) vs NR_zh (zh_results verdicts), per cohort/entity/model
  gender     man-minus-woman recognition gap per person cohort (gender-guesser)
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
FINAL = HERE / "outputs" / "recognition_final.jsonl"
OUT = {}


def load_final():
    """(dataset, entity_id, model_id) -> recognized, plus per-dataset views."""
    rec = {}
    for line in open(FINAL):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        rec[(r.get("dataset"), r["entity_id"], r["model_id"])] = r["recognized"]
    return rec


# ---------------------------------------------------------------- events
def recompute_events(final):
    t4 = REPO / "experiments/t4_1_news_events"
    src = {(r["entity_id"], r["model_id"]): r
           for r in json.load(open(t4 / "outputs/pilot_results_events.json"))}
    # rebuild event_summary.csv with score := recognition verdict
    n = 0
    with open(t4 / "outputs/event_summary.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["entity_id", "entity_name", "model_id", "is_refusal",
                    "coverage", "accuracy", "score", "embedding_sim"])
        for (ds, eid, mid), verdict in final.items():
            if ds != "events":
                continue
            s = src.get((eid, mid), {})
            w.writerow([eid, s.get("entity_name", ""), mid,
                        int(s.get("is_refusal", 0)), 0.0, 0.0, int(verdict),
                        s.get("embedding_sim", 0.0) or 0.0])
            n += 1
    print(f"[events] wrote {n} rows to event_summary.csv (score=recognition)")
    r = subprocess.run([sys.executable, "analyze.py"], cwd=t4,
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("[events] analyze.py FAILED:\n", r.stderr[-2000:])
        return
    aj = json.loads((t4 / "outputs/analysis.json").read_text())
    OUT["events"] = aj
    print(f"[events] analyze.py ok: n={aj['n']}, "
          f"r2_peak={aj['r2_peak_views']:.3f}, r2_total={aj['r2_total_views']:.3f}")


# ---------------------------------------------------------------- cross-language
def recompute_crosslang(final):
    zh = {}
    zpath = HERE / "outputs/zh_results.jsonl"
    ents_zh = {}
    for line in open(zpath):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        zh[(r["entity_id"], r["model_id"])] = r["recognized"]
        ents_zh[r["entity_id"]] = {"name": r["entity_name"], "cohort": r["cohort"]}
    # English verdicts for the same entities come from the main uniform pass
    en = {(eid, mid): v for (ds, eid, mid), v in final.items() if ds == "main"}

    # west/east model split for per-model deltas, derived from vendor.
    CHINA = {"deepseek", "alibaba", "moonshot", "zhipu", "baidu", "minimax"}
    mset = json.loads((REPO / "data/inputs/model_set.json").read_text())
    west = {m["id"] for m in mset if m["vendor"] not in CHINA}

    ent_en, ent_zh = defaultdict(list), defaultdict(list)
    coh_en, coh_zh = defaultdict(list), defaultdict(list)
    mdl_en, mdl_zh = defaultdict(list), defaultdict(list)
    for (eid, mid), vz in zh.items():
        ve = en.get((eid, mid))
        if ve is None:
            continue
        c = ents_zh[eid]["cohort"]
        ent_en[eid].append(ve); ent_zh[eid].append(vz)
        coh_en[c].append(ve); coh_zh[c].append(vz)
        mdl_en[mid].append(ve); mdl_zh[mid].append(vz)

    cohorts = {}
    for c in coh_en:
        ne, nz = np.mean(coh_en[c]), np.mean(coh_zh[c])
        cohorts[c] = {"n": len(set()), "n_rec": len(coh_en[c]),
                      "nr_en": round(float(ne), 3), "nr_zh": round(float(nz), 3),
                      "delta": round(float(nz - ne), 3)}
    ent_delta = {eid: {"name": ents_zh[eid]["name"], "cohort": ents_zh[eid]["cohort"],
                       "nr_en": round(float(np.mean(ent_en[eid])), 3),
                       "nr_zh": round(float(np.mean(ent_zh[eid])), 3),
                       "delta": round(float(np.mean(ent_zh[eid]) - np.mean(ent_en[eid])), 3)}
                 for eid in ent_en}
    mdl_delta = {mid: round(float(np.mean(mdl_zh[mid]) - np.mean(mdl_en[mid])), 3)
                 for mid in mdl_en}
    w = [d for m, d in mdl_delta.items() if m in west]
    e = [d for m, d in mdl_delta.items() if m not in west]
    OUT["crosslang"] = {"cohorts": cohorts,
                        "entities_sorted": sorted(ent_delta.values(),
                                                  key=lambda d: -d["delta"]),
                        "model_deltas": mdl_delta,
                        "class_avg_west": round(float(np.mean(w)), 3) if w else None,
                        "class_avg_china": round(float(np.mean(e)), 3) if e else None}
    print(f"[crosslang] {len(cohorts)} cohorts, {len(ent_delta)} entities, "
          f"{len(mdl_delta)} models")


# ---------------------------------------------------------------- gender
def recompute_gender(final):
    try:
        import gender_guesser.detector as gg
    except ImportError:
        print("[gender] gender-guesser not installed; skipping")
        return
    d = gg.Detector(case_sensitive=False)
    ents = {e["id"]: e for e in json.loads(
        (HERE / "inputs/pilot_entities_v2.json").read_text())}
    per = defaultdict(list)
    for (ds, eid, mid), v in final.items():
        if ds != "main" or eid not in ents:
            continue
        per[eid].append(v)
    ent_rec = {e: float(np.mean(vs)) for e, vs in per.items()}

    def gender(name):
        first = name.strip().split()[0] if name.strip() else ""
        g = d.get_gender(first)
        if g in ("male", "mostly_male"):
            return "m"
        if g in ("female", "mostly_female"):
            return "f"
        return None

    cohorts = ["cs_faculty", "long_tail_researcher_openalex",
               "long_tail_researcher_ikp", "mid_tier_actor", "mid_tier_athlete",
               "mid_tier_writer", "mid_tier_comedian"]
    res = {}
    from scipy import stats
    for c in cohorts:
        m, f = [], []
        for eid, e in ents.items():
            if e.get("cohort") != c or eid not in ent_rec:
                continue
            g = gender(e["name"])
            if g == "m":
                m.append(ent_rec[eid])
            elif g == "f":
                f.append(ent_rec[eid])
        if len(m) >= 5 and len(f) >= 5:
            p = stats.mannwhitneyu(m, f, alternative="two-sided").pvalue
            res[c] = {"n_m": len(m), "n_f": len(f),
                      "delta": round(float(np.mean(m) - np.mean(f)), 3),
                      "p": round(float(p), 3)}
    OUT["gender"] = res
    print(f"[gender] {len(res)} cohorts computed")


def main():
    final = load_final()
    print(f"loaded {len(final)} final verdicts")
    recompute_events(final)
    recompute_crosslang(final)
    recompute_gender(final)
    (HERE / "outputs" / "paper_numbers_downstream.json").write_text(
        json.dumps(OUT, indent=1))
    print("wrote paper_numbers_downstream.json")


if __name__ == "__main__":
    main()
