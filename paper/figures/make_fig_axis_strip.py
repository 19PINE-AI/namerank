"""F7 — Cross-domain entities on one recognition axis (replaces the old
headline table). Selected named entities from the diagnostic reference set +
key artifacts, placed on 0-1 with leader labels, person/artifact colored.
Output: fig_axis_strip.pdf
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

PICKS = [  # (entity_id, display, is_artifact, dataset)
    ("yann_lecun", "Yann LeCun", False, "main"),
    ("geoffrey_hinton", "Geoffrey Hinton", False, "main"),
    ("sam_altman", "Sam Altman", False, "main"),
    ("langchain", "LangChain", True, "main"),
    ("andrej_karpathy", "Andrej Karpathy", False, "main"),
    ("mira_murati", "Mira Murati", False, "main"),
    ("dario_amodei", "Dario Amodei", False, "main"),
    ("aravind_srinivas", "Aravind Srinivas", False, "main"),
    ("nanogpt", "nanoGPT", True, "main"),
    ("artifact_tianshou", "Tianshou", True, "main"),
    ("aman_sanger", "Aman Sanger", False, "main"),
    ("suresh_kumar", "Suresh Kumar (Walmart CTO)", False, "main"),
    # Competition alumni turned notable operators/researchers, spread across the
    # discriminative band (the career-arc thesis, one name at a time).
    ("ioi_scott_wu", "Scott Wu", False, "main"),
    ("noi_wu_jiajun_2009", "Jiajun Wu", False, "main"),
    ("ioi_haoqiang_fan", "Haoqiang Fan", False, "main"),
    ("jiayi_weng", "Jiayi Weng", False, "main"),
    # Two named systems from the boundary-condition study (App. asymmetry),
    # measured under the same final judge in the awards dataset.
    ("artifact_ustc_hackergame", "USTC Hackergame", True, "awards"),
    ("tuixue_online", "tuixue.online", True, "main"),
    ("artifact_icourse_club", "iCourse.club", True, "awards"),
    # Diagnostic probe under the same panel + final judge, stored outside the
    # released cohort dataset (experiments/t6_v2_protocol/inputs/systems_diagnostic.json).
    ("artifact_pine_ai", "Pine AI", True, "diag"),
    ("alex_wei", "Alex Wei", False, "main"),
    ("andrea_vallone", "Andrea Vallone", False, "main"),
]

# Diagnostic named entities measured on the same panel but kept out of the
# released cohort dataset (so paper totals are unchanged).
import json
from collections import defaultdict
DIAG_FILE = (Path(_data.__file__).resolve().parent.parent.parent
             / "experiments/t6_v2_protocol/outputs/systems_diagnostic_results.jsonl")
_diag_votes = defaultdict(list)
if DIAG_FILE.exists():
    for line in open(DIAG_FILE):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        _diag_votes[r["entity_id"]].append(r["recognized"])
diag = {k: sum(v) / len(v) for k, v in _diag_votes.items()}

dfs = {ds: _data.per_entity(ds).set_index("entity_id")
       for ds in {p[3] for p in PICKS} - {"diag"}}
fl = _data.floors("main")
print("data sources:", _data.source_report())

rows = []
for eid, disp, is_art, ds in PICKS:
    val = None
    if ds == "diag":
        val = diag.get(eid)
    else:
        df = dfs[ds]
        if eid in df.index:
            val = float(df.loc[eid].recognition)
        else:  # fall back to name match
            m = df[df.name.str.lower() == disp.split(" (")[0].lower()]
            if len(m):
                val = float(m.iloc[0].recognition)
    if val is not None:
        rows.append((disp, val, is_art))
rows.sort(key=lambda r: r[1])

fig, ax = plt.subplots(figsize=(6.9, 3.6))
_style.floor_band(ax, max(0.02, fl["_people"]), axis="x")
ax.set_ylim(-1.85, 1.75)
ax.get_yaxis().set_visible(False)
for s in ("left", "right", "top"):
    ax.spines[s].set_visible(False)
_style.recog_xaxis(ax)

# stagger labels above/below with per-side x-spacing enforcement
MIN_GAP = 0.075
side_x = {True: -10.0, False: -10.0}   # last label x per side (up/down)
levels = {True: 0, False: 0}
for i, (disp, v, is_art) in enumerate(rows):
    color = RECOG["artifact"] if is_art else RECOG["person"]
    ax.scatter([v], [0], s=42, color=color, zorder=4,
               edgecolor="white", linewidth=0.7)
    up = i % 2 == 0
    xt = max(v, side_x[up] + MIN_GAP)
    xt = min(xt, 1.02)
    if xt - v > 0.10:              # too far — drop to a deeper level instead
        levels[up] = (levels[up] + 1) % 3
        xt = max(v, (side_x[up] + MIN_GAP) if levels[up] == 0 else v)
    side_x[up] = xt
    depth = 0.52 + 0.40 * levels[up]
    ytext = depth if up else -depth
    ax.annotate(disp, xy=(v, 0), xytext=(xt, ytext), ha="center",
                va="bottom" if up else "top", fontsize=7.3, color=color,
                arrowprops=dict(arrowstyle="-", color="#bbbbbb", lw=0.6,
                                relpos=(0.5, 0.0 if up else 1.0)))
    levels[up] = (levels[up] + 1) % 3
ax.axhline(0, color="#888888", linewidth=1.0, zorder=2)
ax.set_xlim(-0.01, 1.06)

from matplotlib.lines import Line2D
ax.legend(handles=[
    Line2D([0], [0], marker="o", color="none", markerfacecolor=RECOG["person"],
           markersize=6, label="people"),
    Line2D([0], [0], marker="o", color="none",
           markerfacecolor=RECOG["artifact"], markersize=6, label="artifacts"),
], loc="upper left", frameon=False, fontsize=8)

fig.tight_layout()
fig.savefig(HERE / "fig_axis_strip.pdf")
fig.savefig(HERE / "fig_axis_strip.png", dpi=150)
print(f"wrote fig_axis_strip.pdf ({len(rows)} entities)")
