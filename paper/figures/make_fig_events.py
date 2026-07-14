"""F22 — News events: the attention ledger (recognition metric).
(a) recognition vs log10 total first-year pageviews, with decile means.
(b) quintile ladders for the two components of total attention: peak salience
    (rises) vs effective duration (flat) — recognition follows how loudly a
    story peaked, not how long it lasted.
Data: t4_1 event metadata (pageviews) + recognition verdicts via _data('events').
Output: fig_events.pdf
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import _data
import _style
from _style import RECOG

_style.apply_style()

meta = {r["id"]: r for r in csv.DictReader(
    open(REPO / "experiments/t4_1_news_events/inputs/event_metadata.csv"))}
rec = _data.per_entity("events")
print("data sources:", _data.source_report())
rec = rec[~rec.synthetic].set_index("entity_id")

rows = []
for eid, r in rec.iterrows():
    m = meta.get(eid)
    if not m:
        continue
    try:
        tv, pk, dur = float(m["total_views"]), float(m["peak_views"]), float(m["eff_duration"])
    except (ValueError, KeyError):
        continue
    if tv > 0:
        rows.append((r.recognition, tv, pk, dur))
df = pd.DataFrame(rows, columns=["rec", "total", "peak", "dur"])
df["ltot"] = np.log10(df.total)

fig, (axa, axb) = plt.subplots(1, 2, figsize=(6.9, 3.0))

# (a) dose-response
axa.scatter(df.ltot, df.rec, s=8, alpha=0.25, color=RECOG["person"],
            edgecolor="none", zorder=2)
dec = pd.qcut(df.ltot.rank(method="first"), 8, labels=False)
dm = df.groupby(dec).agg(x=("ltot", "mean"), y=("rec", "mean"))
axa.plot(dm.x, dm.y, "-o", color="#12457f", markersize=5, linewidth=1.6, zorder=4)
r2 = np.corrcoef(df.ltot, df.rec)[0, 1] ** 2
axa.set_xlabel(r"$\log_{10}$ first-year pageviews")
axa.set_ylabel("recognition rate")
axa.set_ylim(0, 1)
axa.set_title(f"(a) Dose–response ($R^2={r2:.2f}$)", fontsize=9, loc="left")
axa.grid(color="#ececec", linewidth=0.6, zorder=0)
axa.set_axisbelow(True)

# (b) peak vs duration quintile ladders
for col, name, color, marker in [("peak", "peak salience", RECOG["person"], "o"),
                                 ("dur", "effective duration", RECOG["accent"], "s")]:
    q = pd.qcut(df[col].rank(method="first"), 5, labels=False)
    ladder = df.groupby(q).rec.mean()
    axb.plot(range(5), ladder.values, "-", marker=marker, color=color,
             markersize=5, linewidth=1.6, label=name)
axb.set_xlabel("quintile of component")
axb.set_ylabel("mean recognition rate")
axb.set_xticks([0, 2, 4], ["Q1", "Q3", "Q5"])
axb.set_ylim(0, max(0.6, df.rec.max() * 1.1))
axb.legend(loc="upper left", frameon=False, fontsize=7.6)
axb.set_title("(b) How loud, not how long", fontsize=9, loc="left")
axb.grid(color="#ececec", linewidth=0.6, zorder=0)
axb.set_axisbelow(True)

fig.tight_layout()
fig.savefig(HERE / "fig_events.pdf")
fig.savefig(HERE / "fig_events.png", dpi=150)
print(f"wrote fig_events.pdf ({len(df)} events, R2={r2:.3f})")
