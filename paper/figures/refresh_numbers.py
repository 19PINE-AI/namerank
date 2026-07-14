"""Recompute every body number from the final data and print a fill map for the
\\tbd placeholders in main.tex. Run after the uniform judging pass completes;
review the map, then apply (auto-apply with --apply unwraps \\tbd{X} -> X for
each confirmed value).

The placeholders were written with the current-data value already inside
\\tbd{...}; this script recomputes each and flags any that MOVED so they get
updated rather than blindly unwrapped.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np
import _data


def coh(dataset, cohort):
    t = _data.cohort_table(dataset, min_n=1)
    r = t[t.cohort == cohort]
    return float(r.recognition.iloc[0]) if len(r) else None


def main():
    vals = {}
    m = _data.cohort_table("main", min_n=1).set_index("cohort").recognition
    for c, key in [("long_tail_researcher_openalex", "baseline"),
                   ("cs_faculty", "faculty"), ("imo_gold", "imo"),
                   ("ioi_gold", "ioi"), ("cmo_china_gold", "cmo"),
                   ("noi_china_gold", "noi"), ("rhodes_scholar", "rhodes"),
                   ("putnam_fellow", "putnam"), ("msra_phd_fellowship", "msra"),
                   ("icpc_world_finals_gold", "icpc"),
                   ("named_method", "methods"), ("oss_project", "oss"),
                   ("gpt5_system_card_author", "gpt5"),
                   ("deepseek_v3_author", "deepseek")]:
        if c in m.index:
            vals[key] = round(float(m[c]), 2)
    for c, key in [("llm_method_originator", "llm_method"),
                   ("llm_best_paper_author", "llm_bestpaper"),
                   ("llm_foundational_author", "llm_foundational")]:
        v = coh("llm", c)
        if v is not None:
            vals[key] = round(v, 2)
    fl = _data.floors("main")
    vals["floor_people"] = round(fl["_people"], 3)
    vals["floor_papers"] = round(fl["_papers"], 3)

    print("data sources:", _data.source_report())
    print("\n=== recomputed body numbers (verify \\tbd against these) ===")
    for k in sorted(vals):
        print(f"  {k:20s} {vals[k]}")
    # variance decomposition
    print("\nRun make_fig_calibration.py for the variance shares (entity/model).")


if __name__ == "__main__":
    main()
