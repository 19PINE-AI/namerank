"""Credential-treadmill thesis: NameRank by once-prestigious credential.

Writes data/analysis/credential_ladder.csv.
"""
from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict

from _paths import ANALYSIS, INPUTS


CRED = {
    "imo_gold": ("HS-math", "International Math Olympiad gold (2005-2015)", "high"),
    "ioi_gold": ("HS-CS", "International Olympiad in Informatics gold", "high"),
    "icpc_world_finals_gold": ("UG-CS", "ICPC World Finalist gold", "high"),
    "putnam_fellow": ("UG-math", "Putnam top-25 fellow", "high"),
    "cmo_china_gold": ("HS-math-CN", "China Math Olympiad gold", "high"),
    "noi_china_gold": ("HS-CS-CN", "National Olympiad in Informatics China gold", "high"),
    "cpho_china_first_prize": ("HS-physics-CN", "China Physics Olympiad first prize", "med"),
    "rhodes_scholar": ("UG-general", "Rhodes Scholarship recipient", "high"),
    "msra_phd_fellowship": ("PhD", "MSRA PhD Fellowship", "med"),
    "deepseek_v3_author": ("paper-author", "DeepSeek-V3 paper author", "ind"),
    "gpt5_system_card_author": ("paper-author", "GPT-5 system card author", "ind"),
}


def pearson(x, y):
    n = len(x)
    if n < 3:
        return 0.0
    mx, my = statistics.mean(x), statistics.mean(y)
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    sx = sum((xi - mx) ** 2 for xi in x) ** 0.5
    sy = sum((yi - my) ** 2 for yi in y) ** 0.5
    return num / (sx * sy) if sx * sy > 0 else 0.0


def main() -> None:
    ents = {e["id"]: e for e in json.loads((INPUTS / "pilot_entities.json").read_text())}
    nr = {row["entity_id"]: float(row["namerank"])
          for row in csv.DictReader(open(ANALYSIS / "namerank_per_entity.csv", encoding="utf-8"))}

    cred_rows = []
    for cohort_id, (rung, descr, prestige) in CRED.items():
        subset = [e for e in ents.values() if e.get("cohort") == cohort_id]
        nrs = [nr[e["id"]] for e in subset if e["id"] in nr]
        years = [int(e["credential_year"]) for e in subset if e.get("credential_year")]
        if not nrs:
            continue
        cred_rows.append({
            "credential": descr, "rung": rung, "prestige": prestige,
            "n": len(nrs),
            "mean": round(statistics.mean(nrs), 3),
            "median": round(statistics.median(nrs), 3),
            "sd": round(statistics.stdev(nrs) if len(nrs) > 1 else 0.0, 3),
            "min_year": min(years) if years else None,
            "max_year": max(years) if years else None,
        })

    lt_nr = [nr[eid] for eid, e in ents.items()
             if e.get("cohort") == "long_tail_researcher_openalex" and eid in nr]
    lt_baseline = statistics.mean(lt_nr) if lt_nr else 0.0
    print(f"long_tail_researcher_openalex baseline (n={len(lt_nr)}): mean={lt_baseline:.3f}")
    print("\n{:<45} {:<5} {:<7} {:<13}".format("Credential", "n", "mean", "vs baseline"))
    for row in sorted(cred_rows, key=lambda r: -r["mean"]):
        print(f"{row['credential']:<45} {row['n']:<5} {row['mean']:<7.3f} {row['mean']-lt_baseline:+.3f}")

    # Within-IMO year trend
    imo = [e for e in ents.values()
           if e.get("cohort") == "imo_gold" and e.get("credential_year") and e["id"] in nr]
    if len(imo) > 10:
        years_imo = [int(e["credential_year"]) for e in imo]
        nrs_imo = [nr[e["id"]] for e in imo]
        print(f"\nIMO gold Pearson(year, NameRank) = {pearson(years_imo, nrs_imo):.3f}")

    out = ANALYSIS / "credential_ladder.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(cred_rows[0].keys()))
        w.writeheader()
        w.writerows(cred_rows)
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
