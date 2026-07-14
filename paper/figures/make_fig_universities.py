"""F19 — The corpus-density gradient at the institution level, two designs.
(a) Faculty design (CSRankings rosters, rankable): per-university recognition.
(b) Citation-matched design (500-30K window): at FIXED citations the top-
    corpus-density schools still lead — corpus density, not productivity.
Data: t5_4 verdicts via _data (dataset 'univ').
Output: fig_universities.pdf
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import matplotlib.pyplot as plt
import numpy as np
import _data
import _style
from _style import RECOG

_style.apply_style()

FAC = {"univ_fac_mit": "MIT", "univ_fac_uc_berkeley": "UC Berkeley",
       "univ_fac_ucsd": "UC San Diego", "univ_fac_uc_irvine": "UC Irvine"}
WIN = {"univ_mit": "MIT", "univ_uc_berkeley": "UC Berkeley",
       "univ_ucsd": "UC San Diego", "univ_uc_irvine": "UC Irvine"}

tab = _data.cohort_table("univ", min_n=8).set_index("cohort")
print("data sources:", _data.source_report())
base = None
if "long_tail_researcher_openalex" in tab.index:
    base = float(tab.loc["long_tail_researcher_openalex", "recognition"])

fig, axes = plt.subplots(1, 2, figsize=(6.9, 2.7), sharex=True)
for ax, mapping, title in [
        (axes[0], FAC, "(a) Faculty rosters (no bibliometric conditioning)"),
        (axes[1], WIN, "(b) Citation-matched (500–30K window)")]:
    rows = [(nm, tab.loc[c]) for c, nm in mapping.items() if c in tab.index]
    rows.sort(key=lambda kv: kv[1].recognition)
    for i, (nm, r) in enumerate(rows):
        _style.ci_dot(ax, i, r.recognition, r.ci95, RECOG["person"], size=34)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([nm for nm, _ in rows], fontsize=8.5)
    ax.set_ylim(-0.7, len(rows) - 0.3)
    if base:
        _style.baseline_line(ax, base, "baseline")
    ax.set_xlim(0.3, 0.9)
    ax.set_xlabel("recognition rate")
    ax.set_title(title, fontsize=8.6, loc="left")
    ax.grid(axis="x", color="#ececec", linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
if base:
    axes[0].annotate("working-researcher\nbaseline", xy=(base, 2.8),
                     fontsize=6.8, color=RECOG["baseline"], ha="center")

fig.tight_layout()
fig.savefig(HERE / "fig_universities.pdf")
fig.savefig(HERE / "fig_universities.png", dpi=150)
print("wrote fig_universities.pdf")
