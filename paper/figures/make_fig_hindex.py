"""F18 — Bibliometric predictors of recognition (OpenAlex researchers).
(a) recognition vs log10 h-index (dots + logistic-like trend via decile means)
    with citations overlaid as the weaker predictor.
(b) decile ladders for h-index vs raw citations.
Output: fig_hindex.pdf
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import _data
import _style
from _style import RECOG

_style.apply_style()

pe_meta = {e["id"]: e for e in json.loads(
    ( _data.REPO / "data/inputs/pilot_entities.json").read_text())}
df = _data.per_entity("main")
df = df[~df.synthetic & (df.cohort == "long_tail_researcher_openalex")].copy()
df["h"] = df.entity_id.map(lambda i: pe_meta.get(i, {}).get("h_index"))
df["cites"] = df.entity_id.map(lambda i: pe_meta.get(i, {}).get("cited_by_count"))
df = df.dropna(subset=["h", "cites"])
df["logh"] = np.log10(df.h)
df["logc"] = np.log10(df.cites.clip(lower=1))
print("data sources:", _data.source_report(), f"| n={len(df)}")

r_h = np.corrcoef(df.logh, df.recognition)[0, 1]
r_c = np.corrcoef(df.logc, df.recognition)[0, 1]

fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(6.9, 3.0))

# (a) scatter + decile means for h-index
ax_a.scatter(df.logh, df.recognition, s=7, alpha=0.25,
             color=RECOG["person"], edgecolor="none", zorder=2)
dec = pd.qcut(df.logh.rank(method="first"), 10, labels=False)
dm = df.groupby(dec).agg(x=("logh", "mean"), y=("recognition", "mean"))
ax_a.plot(dm.x, dm.y, "-o", color="#12457f", markersize=5, linewidth=1.6,
          zorder=4, label=f"$h$-index decile means ($R^2={r_h**2:.2f}$)")
ax_a.set_xlabel(r"$\log_{10}(h\mathrm{-index})$")
ax_a.set_ylabel("recognition rate")
ax_a.set_ylim(0, 1)
ax_a.legend(loc="upper left", frameon=False, fontsize=7.6)
ax_a.set_title("(a) Recognition vs. $h$-index", fontsize=9, loc="left")
ax_a.grid(color="#ececec", linewidth=0.6, zorder=0)
ax_a.set_axisbelow(True)

# (b) decile ladders: h vs citations
dech = pd.qcut(df.h.rank(method="first"), 10, labels=False)
decc = pd.qcut(df.cites.rank(method="first"), 10, labels=False)
lh = df.groupby(dech).recognition.mean()
lc = df.groupby(decc).recognition.mean()
x = np.arange(10)
ax_b.plot(x, lh.values, "-o", color=RECOG["person"], markersize=5,
          linewidth=1.6, label=f"$h$-index ($R^2={r_h**2:.2f}$)")
ax_b.plot(x, lc.values, "-s", color=RECOG["accent"], markersize=5,
          linewidth=1.6, label=f"citations ($R^2={r_c**2:.2f}$)")
ax_b.set_xlabel("bibliometric decile")
ax_b.set_ylabel("mean recognition rate")
ax_b.set_xticks([0, 3, 6, 9], ["D1", "D4", "D7", "D10"])
ax_b.set_ylim(0, 1)
ax_b.legend(loc="upper left", frameon=False, fontsize=7.6)
ax_b.set_title("(b) Decile ladders", fontsize=9, loc="left")
ax_b.grid(color="#ececec", linewidth=0.6, zorder=0)
ax_b.set_axisbelow(True)

fig.tight_layout()
fig.savefig(HERE / "fig_hindex.pdf")
fig.savefig(HERE / "fig_hindex.png", dpi=150)
print(f"wrote fig_hindex.pdf  R2(h)={r_h**2:.3f} R2(cites)={r_c**2:.3f}")
