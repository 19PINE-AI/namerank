"""F13/F15 — Named-artifact amplification, two panels.
(a) Dumbbells: creator vs artifact recognition for the verified pairs, sorted
    by artifact-creator delta. Artifact out-ranks creator for independent
    creators; exceptions are senior leaders.
(b) Method originators at scale: creator recognition vs the method's own
    recognition (t5_5 pairs matched into the main run), diagonal reference.
Output: fig_inversion.pdf
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import matplotlib.pyplot as plt
import numpy as np
import _data
import _style
from _style import RECOG

_style.apply_style()

df = _data.per_entity("main").set_index("entity_id")
name2rec = {}
for i, r in df.iterrows():
    name2rec.setdefault(r["name"].lower(), r["recognition"])


def rec_of(name):
    return name2rec.get(name.lower())


pairs = list(csv.DictReader(open(REPO / "data/analysis/attribution_pairs_v2.csv")))
rows = []
for p in pairs:
    cv, av = rec_of(p["creator"]), rec_of(p["artifact"])
    if cv is not None and av is not None:
        rows.append((p["creator"], cv, p["artifact"], av))
rows.sort(key=lambda r: r[3] - r[1])
print("data sources:", _data.source_report())

fig, (axa, axb) = plt.subplots(1, 2, figsize=(6.9, 4.0),
                               gridspec_kw={"width_ratios": [1.15, 1.0]})

for i, (cr, cv, ar, av) in enumerate(rows):
    axa.plot([cv, av], [i, i], color="#cfcfcf", linewidth=2.0, zorder=1)
    axa.scatter([cv], [i], s=34, color=RECOG["person"], zorder=3,
                edgecolor="white", linewidth=0.6)
    axa.scatter([av], [i], s=34, color=RECOG["artifact"], zorder=3,
                edgecolor="white", linewidth=0.6)
axa.set_yticks(range(len(rows)))
axa.set_yticklabels([f"{cr} / {ar}" for cr, cv, ar, av in rows], fontsize=7.0)
axa.set_ylim(-0.7, len(rows) - 0.3)
_style.recog_xaxis(axa)
axa.set_xlabel("recognition rate")
axa.set_title("(a) Creator vs. artifact", fontsize=9, loc="left")
axa.grid(axis="x", color="#ececec", linewidth=0.6, zorder=0)
axa.set_axisbelow(True)
from matplotlib.lines import Line2D
axa.legend(handles=[
    Line2D([0], [0], marker="o", color="none", markerfacecolor=RECOG["person"],
           markersize=6, label="creator"),
    Line2D([0], [0], marker="o", color="none", markerfacecolor=RECOG["artifact"],
           markersize=6, label="artifact")],
    loc="lower right", frameon=False, fontsize=7.5)

art = json.loads((REPO / "experiments/t5_5_llm_area/inputs/artifacts.json").read_text())
llm = _data.per_entity("llm").set_index("entity_id")
llm_name = {}
for i, r in llm.iterrows():
    llm_name.setdefault(r["name"].lower(), r["recognition"])
sc = []
for a in art:
    if a["kind"] != "method":
        continue
    cv = llm_name.get(a["person"].lower())
    av = rec_of(a["artifact"])
    if cv is not None and av is not None:
        sc.append((cv, av))
if sc:
    cvs, avs = zip(*sc)
    axb.scatter(cvs, avs, s=18, alpha=0.5, color=RECOG["artifact"],
                edgecolor="none")
    axb.plot([0, 1], [0, 1], color="#999999", linewidth=1.0, linestyle=(0, (4, 3)))
    above = sum(a > c for c, a in sc)
    axb.annotate(f"method $>$ originator\nin {above} of {len(sc)}\nprominent methods",
                 xy=(0.50, 0.09), fontsize=7.8, color="#555555")
axb.set_xlim(0, 1); axb.set_ylim(0, 1)
axb.set_xlabel("originator recognition")
axb.set_ylabel("method recognition")
axb.set_title("(b) Prominent named methods vs. their originators", fontsize=8.4,
              loc="left")
axb.grid(color="#ececec", linewidth=0.6, zorder=0)
axb.set_axisbelow(True)

fig.tight_layout()
fig.savefig(HERE / "fig_inversion.pdf")
fig.savefig(HERE / "fig_inversion.png", dpi=150)
print(f"wrote fig_inversion.pdf ({len(rows)} pairs, {len(sc)} method scatter)")
