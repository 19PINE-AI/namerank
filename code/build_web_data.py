"""Bundle data slices for the static companion website.

The static site (in web/) is served from a flat directory of small JSON files
under web/assets/data/. We build those slices here from the canonical CSVs in
data/analysis/ so the site stays in sync with the released numbers.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from _paths import ANALYSIS, REPO

OUT = REPO / "web" / "assets" / "data"


def read_csv(path: Path) -> list[dict]:
    return list(csv.DictReader(open(path, encoding="utf-8")))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # 1. Per-entity for the lookup page. Slim down to fields the page uses.
    per_entity = []
    for r in read_csv(ANALYSIS / "namerank_per_entity.csv"):
        per_entity.append({
            "id": r["entity_id"],
            "name": r["entity_name"],
            "cohort": r["cohort"],
            "nr": float(r["namerank"]),
            "sd": float(r["namerank_sd"]),
            "refusal": float(r["refusal_rate"]),
        })
    (OUT / "per_entity.json").write_text(json.dumps(per_entity, ensure_ascii=False))
    print(f"per_entity.json  {len(per_entity):>5} entities")

    # 2. Cohort summary.
    cohorts = []
    for r in read_csv(ANALYSIS / "cohort_summary.csv"):
        cohorts.append({
            "cohort": r["cohort"], "n": int(r["n"]),
            "mean": float(r["mean"]), "median": float(r["median"]),
            "sd": float(r["sd"]),
            "p10": float(r["p10"]), "p25": float(r["p25"]),
            "p75": float(r["p75"]), "p90": float(r["p90"]),
            "frac_recognized": float(r["frac_recognized"]),
            "frac_silent": float(r["frac_silent"]),
        })
    (OUT / "cohort_summary.json").write_text(json.dumps(cohorts))
    print(f"cohort_summary.json  {len(cohorts):>5} cohorts")

    # 3. Inversion pairs — paper uses 11 verified pairs.
    pairs = []
    nr_lookup = {r["name"]: r["nr"] for r in per_entity}
    for r in read_csv(ANALYSIS / "attribution_pairs_v2.csv"):
        pairs.append({
            "creator": r["creator"], "artifact": r["artifact"],
            "c_to_a": float(r["c_to_a"]), "a_to_c": float(r["a_to_c"]),
            "asymmetry": float(r["asym"]),
            "nr_creator": nr_lookup.get(r["creator"]),
            "nr_artifact": nr_lookup.get(r["artifact"]),
        })
    (OUT / "inversion_pairs.json").write_text(json.dumps(pairs, ensure_ascii=False))
    print(f"inversion_pairs.json  {len(pairs):>4} pairs")

    # 4. Cross-language deltas.
    crosslang = []
    for r in read_csv(ANALYSIS / "cross_language_per_entity.csv"):
        crosslang.append({
            "id": r["entity_id"], "name": r["entity_name"], "cohort": r["cohort"],
            "en": float(r["en_all"]), "zh": float(r["zh_all"]),
            "delta": float(r["delta_zh_minus_en"]),
            "en_w": float(r["en_western"]), "en_c": float(r["en_chinese"]),
            "zh_w": float(r["zh_western"]), "zh_c": float(r["zh_chinese"]),
        })
    (OUT / "cross_language.json").write_text(json.dumps(crosslang, ensure_ascii=False))
    print(f"cross_language.json  {len(crosslang):>5} entities")

    # 5. Credential ladder.
    creds = read_csv(ANALYSIS / "credential_ladder.csv")
    creds_norm = [{
        "credential": r["credential"], "rung": r["rung"], "prestige": r["prestige"],
        "n": int(r["n"]), "mean": float(r["mean"]),
        "median": float(r["median"]), "sd": float(r["sd"]),
        "min_year": r["min_year"] or None, "max_year": r["max_year"] or None,
    } for r in creds]
    (OUT / "credential_ladder.json").write_text(json.dumps(creds_norm))
    print(f"credential_ladder.json  {len(creds_norm):>3} credentials")

    # 6. Country gradient.
    rows = read_csv(ANALYSIS / "cs_faculty_by_country.csv")
    countries = [{
        "country": r["country"], "n": int(r["n"]),
        "mean": float(r["mean"]), "median": float(r["median"]),
        "sd": float(r["sd"]),
        "frac_above_0_5": float(r["frac_above_0_5"]),
    } for r in rows]
    (OUT / "cs_faculty_by_country.json").write_text(json.dumps(countries))
    print(f"cs_faculty_by_country.json  {len(countries):>3} countries")

    # 7. Per-model summary (Appendix C of the paper). Optional — only if the
    # CSV exists; it is rebuilt by code/per_model_summary.py.
    pm_csv = ANALYSIS / "per_model_summary.csv"
    if pm_csv.exists():
        per_model = [{
            "model_id": r["model_id"],
            "vendor": r["vendor"],
            "family": r["family"],
            "thinking": r["thinking"] == "1",
            "n_records": int(r["n_records"]),
            "mean_score": float(r["mean_score"]),
            "refusal_rate": float(r["refusal_rate"]),
            "mean_score_non_refusal": float(r["mean_score_non_refusal"]),
        } for r in read_csv(pm_csv)]
        (OUT / "per_model.json").write_text(json.dumps(per_model))
        print(f"per_model.json  {len(per_model):>5} models")

    # 8. Panel-size sensitivity curve (Appendix A2).
    ps_csv = ANALYSIS / "a2_panel_size_curve.csv"
    if ps_csv.exists():
        panel = [{
            "k": int(r["k"]),
            "pearson_mean": float(r["pearson_mean"]),
            "pearson_sd": float(r["pearson_sd"]),
            "pearson_min": float(r["pearson_min"]),
            "pearson_max": float(r["pearson_max"]),
            "spearman_mean": float(r["spearman_mean"]),
            "spearman_sd": float(r["spearman_sd"]),
        } for r in read_csv(ps_csv)]
        (OUT / "panel_size_curve.json").write_text(json.dumps(panel))
        print(f"panel_size_curve.json  {len(panel):>5} rows")

    # 9. Conditional NameRank (Appendix A3 - per-cohort recognition rate).
    cond_csv = ANALYSIS / "a3_conditional_namerank.csv"
    if cond_csv.exists():
        cond = [{
            "cohort": r["cohort"], "n": int(r["n"]),
            "unconditional": float(r["unconditional_nr"]),
            "conditional": float(r["conditional_nr"]),
            "recognition_rate": float(r["recognition_rate"]),
            "delta": float(r["delta_cond_uncond"]),
            "factor": float(r["factor_cond_uncond"]),
        } for r in read_csv(cond_csv)]
        (OUT / "conditional_namerank.json").write_text(json.dumps(cond))
        print(f"conditional_namerank.json  {len(cond):>3} cohorts")


if __name__ == "__main__":
    main()
