"""Credential ladder (Section 4.1): the nine olympiad/fellowship credentials on
the recognition axis, all below the working-researcher baseline, with the two
large-team author-list cohorts shown for context.

Horizontal dot-plot with 95% CI whiskers, a baseline reference line, and the
synthetic-null floor band. Consistent with the atlas/country figures.
Output: fig_credential_ladder.pdf
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import matplotlib.pyplot as plt
import _data
import _style
from _style import RECOG

_style.apply_style()

t = _data.cohort_table("main", min_n=1).set_index("cohort")
print("data sources:", _data.source_report())

# (cohort key, display label, kind) — kind: 'baseline' | 'credential' | 'authorlist'
ROWS = [
    ("long_tail_researcher_openalex", "OpenAlex working researcher", "baseline"),
    ("putnam_fellow",                 "Putnam top-25 fellow",        "credential"),
    ("icpc_world_finals_gold",        "ICPC World Finalist gold",    "credential"),
    ("msra_phd_fellowship",           "MSRA PhD Fellowship",         "credential"),
    ("ioi_gold",                      "IOI gold",                    "credential"),
    ("rhodes_scholar",                "Rhodes Scholarship",          "credential"),
    ("imo_gold",                      "IMO gold",                    "credential"),
    ("deepseek_v3_author",            "DeepSeek-V3 report author",   "authorlist"),
    ("gpt5_system_card_author",       "GPT-5 system-card author",    "authorlist"),
    ("noi_china_gold",                "NOI China gold",              "credential"),
    ("cmo_china_gold",                "CMO China gold",              "credential"),
    ("cpho_china_first_prize",        "CPhO China first prize",      "credential"),
]

baseline = float(t.loc["long_tail_researcher_openalex", "recognition"])
floor = 0.02

fig, ax = plt.subplots(figsize=(6.9, 4.5))
_style.floor_band(ax, floor)
_style.baseline_line(ax, baseline, "baseline")

COL = {"baseline": RECOG["baseline"], "credential": RECOG["person"],
       "authorlist": RECOG["muted"]}
n = len(ROWS)
yticklabels = []
for i, (key, label, kind) in enumerate(ROWS):
    y = n - 1 - i            # top row first
    r = t.loc[key]
    rec, ci = float(r.recognition), float(r.ci95)
    col = COL[kind]
    if kind == "authorlist":
        # hollow marker: large-team author list, shown for context (not a credential)
        ax.errorbar(rec, y, xerr=ci, fmt="none", ecolor="#9a9a9a", elinewidth=1.3,
                    capsize=2.0, capthick=1.3, zorder=3)
        ax.scatter([rec], [y], s=34, facecolor="white", edgecolor="#8a8a8a",
                   linewidth=1.2, zorder=4)
        rowlabel = f"{label}$^\\dagger$"          # no n: probed cohort > scored subset
    else:
        _style.ci_dot(ax, y, rec, ci, col, size=44 if kind == "baseline" else 32)
        rowlabel = f"{label}  ($n{{=}}{int(r.n_ent)}$)"
    ax.annotate(f"{rec:.2f}", xy=(rec + ci + 0.012, y), va="center", ha="left",
                fontsize=7.8, color="#333")
    yticklabels.append((y, rowlabel, "bold" if kind == "baseline" else "normal"))

ax.set_yticks([y for y, _, _ in yticklabels])
labs = ax.set_yticklabels([s for _, s, _ in yticklabels], fontsize=8.4)
for lab, (_, _, w) in zip(labs, yticklabels):
    lab.set_fontweight(w)

_style.recog_xaxis(ax, 0, 0.52)
ax.set_xticks([0, 0.1, 0.2, 0.3, 0.4, 0.5])
ax.set_ylim(-0.7, n - 0.3)
ax.grid(axis="x", color="#ececec", linewidth=0.6, zorder=0)
ax.set_axisbelow(True)

# the message lives in the empty region to the right of the baseline, where
# nothing lands because no credential clears it.
ax.annotate("no credential\nclears the baseline", xy=(0.455, n - 4.5),
            fontsize=8.6, style="italic", color=RECOG["baseline"],
            ha="center", va="center")
ax.annotate("", xy=(baseline + 0.004, n - 6.2), xytext=(0.455, n - 5.4),
            arrowprops=dict(arrowstyle="->", color=RECOG["baseline"], lw=0.8))

fig.tight_layout()
fig.savefig(HERE / "fig_credential_ladder.pdf")
fig.savefig(HERE / "fig_credential_ladder.png", dpi=150)
print("wrote fig_credential_ladder.pdf")
