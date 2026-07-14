"""F9 — The Career Arc (signature figure).

Every credential/award cohort placed on the recognition axis, grouped by
career stage (early olympiad/fellowship -> LLM-era best-paper -> mid-career
honors -> marquee late-career prizes), against the working-researcher baseline
and the synthetic-null floor. The unified thesis in one exhibit: a credential
propagates a name in proportion to the named artifacts it attaches to.

Output: fig9_career_arc.pdf (+ .png)
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import matplotlib.pyplot as plt
import pandas as pd
import _data
import _style
from _style import RECOG

_style.apply_style()

GROUPS = [
    ("Early: olympiads & fellowships", "main", [
        "cpho_china_first_prize", "cmo_china_gold", "noi_china_gold",
        "rhodes_scholar", "imo_gold", "msra_phd_fellowship", "ioi_gold",
        "putnam_fellow", "icpc_world_finals_gold"]),
    ("LLM-era: awarded & foundational papers", "llm", [
        "llm_foundational_author", "llm_best_paper_author",
        "llm_method_originator"]),
    ("Mid-career honors", "awards", [
        "macarthur_fellow", "acm_fellow", "godel_prize", "sloan_fellow",
        "acm_prize_computing"]),
    ("Late-career marquee prizes", "awards", [
        "fields_medal", "turing_award", "nobel_physics"]),
]

frames = {}
for _, ds, _c in GROUPS:
    if ds not in frames:
        frames[ds] = _data.cohort_table(ds, min_n=8)
print("data sources:", _data.source_report())

main_tab = frames["main"]
BASELINE = float(main_tab.loc[main_tab.cohort == "long_tail_researcher_openalex",
                              "recognition"].iloc[0])
fl = _data.floors("main")

rows, group_bounds = [], []
y = 0
for gname, ds, cohorts in GROUPS:
    tab = frames[ds].set_index("cohort")
    start = y
    got = [(c, tab.loc[c]) for c in cohorts if c in tab.index]
    got.sort(key=lambda kv: kv[1].recognition)
    for c, r in got:
        rows.append((y, c, r.recognition, r.ci95))
        y += 1
    if got:
        group_bounds.append((gname, start, y - 1))
        y += 1.2  # gap between groups

if not rows:
    sys.exit("no data yet — run after the awards/llm datasets are judged")

fig, ax = plt.subplots(figsize=(6.9, 0.34 * y + 1.4))
_style.floor_band(ax, max(0.02, fl["_people"]), axis="x")
_style.baseline_line(ax, BASELINE, "baseline")

for yy, c, m, ci in rows:
    _style.ci_dot(ax, yy, m, ci, RECOG["person"])

ax.set_yticks([r[0] for r in rows])
ax.set_yticklabels([_style.COHORT_NAMES.get(r[1], r[1].replace("_", " "))
                    for r in rows], fontsize=8)
for gname, y0, y1 in group_bounds:
    ax.annotate(gname, xy=(1.005, (y0 + y1) / 2), xycoords=("axes fraction", "data"),
                rotation=270, ha="left", va="center", fontsize=7.6,
                color="#555555", annotation_clip=False)
    if y1 < rows[-1][0]:
        ax.axhline(y1 + 1.1, color="#e0e0e0", linewidth=0.8)

ax.set_ylim(-1, y - 0.2)
ax.invert_yaxis()
_style.recog_xaxis(ax)
ax.annotate("working-researcher baseline", xy=(BASELINE, -0.6),
            fontsize=7.5, color=RECOG["baseline"], ha="center", va="bottom")
ax.grid(axis="x", color="#e8e8e8", linewidth=0.6, zorder=0)
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(HERE / "fig9_career_arc.pdf")
fig.savefig(HERE / "fig9_career_arc.png", dpi=150)
print(f"wrote fig9_career_arc.pdf ({len(rows)} cohorts)")
