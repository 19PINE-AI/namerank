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

PICKS = [  # (entity_id, display, is_artifact)
    ("yann_lecun", "Yann LeCun", False),
    ("geoffrey_hinton", "Geoffrey Hinton", False),
    ("sam_altman", "Sam Altman", False),
    ("langchain", "LangChain", True),
    ("andrej_karpathy", "Andrej Karpathy", False),
    ("mira_murati", "Mira Murati", False),
    ("dario_amodei", "Dario Amodei", False),
    ("aravind_srinivas", "Aravind Srinivas", False),
    ("nanogpt", "nanoGPT", True),
    ("artifact_tianshou", "Tianshou", True),
    ("suresh_kumar", "Suresh Kumar (Walmart CTO)", False),
    ("tuixue_online", "tuixue.online", True),
    ("jiayi_weng", "Jiayi Weng", False),
    ("alex_wei", "Alex Wei", False),
    ("bojie_li", "Bojie Li", False),
    ("andrea_vallone", "Andrea Vallone", False),
]

df = _data.per_entity("main").set_index("entity_id")
fl = _data.floors("main")
print("data sources:", _data.source_report())

rows = []
for eid, disp, is_art in PICKS:
    hit = None
    if eid in df.index:
        hit = df.loc[eid]
    else:  # fall back to name match
        m = df[df.name.str.lower() == disp.split(" (")[0].lower()]
        if len(m):
            hit = m.iloc[0]
    if hit is not None:
        rows.append((disp, float(hit.recognition), is_art))
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
