"""Figure 3: external validity panel — h-index dominates citations.

Two-panel chart:
(a) Scatter of NameRank vs log(h-index) and log(citations).
(b) Decile means showing h-index drives the relationship.
"""
import csv
import json
import math
import statistics
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from _style import (PALETTE, apply_style, grid_x, grid_y, thin_spines)

apply_style()

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent

ents = {e["id"]: e for e in json.loads(
    (REPO / "data/inputs/pilot_entities.json").read_text())}
nr = {row["entity_id"]: float(row["namerank"]) for row in csv.DictReader(
    open(REPO / "data/analysis/namerank_per_entity.csv", encoding="utf-8"))}

xs_h, xs_c, ys = [], [], []
for eid, e in ents.items():
    if e.get("cohort") != "long_tail_researcher_openalex":
        continue
    if eid not in nr:
        continue
    cit = e.get("cited_by_count") or 0
    hi = e.get("h_index") or 0
    if cit <= 0 or hi <= 0:
        continue
    xs_c.append(cit)
    xs_h.append(hi)
    ys.append(nr[eid])

log_h = np.array([math.log10(x) for x in xs_h])
log_c = np.array([math.log10(x) for x in xs_c])
ys = np.array(ys)

C_H, C_C = PALETTE["cat0"], PALETTE["highlight"]   # blue h-index, orange citations

fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.0))

# ── Panel (a): scatter NameRank vs log(predictor) ─────────────
ax = axes[0]
ax.scatter(log_c, ys, s=10, color=C_C, alpha=0.22, edgecolors="none",
           label=r"$\log_{10}(\mathrm{citations})$,  $R^2 = 0.14$")
ax.scatter(log_h, ys, s=10, color=C_H, alpha=0.45, edgecolors="none",
           label=r"$\log_{10}(h\text{-index})$,  $R^2 = 0.40$")

# Linear fits.
def fit(x, y):
    n = len(x)
    mx, my = np.mean(x), np.mean(y)
    num = np.sum((x - mx) * (y - my))
    den = np.sum((x - mx) ** 2)
    slope = num / den if den else 0.0
    inter = my - slope * mx
    return slope, inter

sh, ih_ = fit(log_h, ys)
sc, ic_ = fit(log_c, ys)
# Draw each fit only across the span its data actually covers (no extrapolation).
xs_h_line = np.linspace(log_h.min(), log_h.max(), 50)
xs_c_line = np.linspace(log_c.min(), log_c.max(), 50)
ax.plot(xs_h_line, sh * xs_h_line + ih_, "-",
        color=C_H, linewidth=2.6, zorder=5)
ax.plot(xs_c_line, sc * xs_c_line + ic_, "-",
        color=C_C, linewidth=2.6, zorder=5)

# In-axes annotation summarising the joint regression.
ax.text(0.05, 0.93,
        r"$h$-index is the dominant signal:" + "\n"
        r"joint regression coefficient on" + "\n"
        r"$\log(\mathrm{citations})$ is $-0.002$,"
        + "\nindistinguishable from zero.",
        transform=ax.transAxes,
        ha="left", va="top", fontsize=9, color="#222",
        bbox=dict(boxstyle="round,pad=0.45",
                  facecolor="white", edgecolor="#ddd", linewidth=0.6))

ax.set_xlabel("Bibliometric value  ($\\log_{10}$)", fontsize=10.5)
ax.set_ylabel("NameRank", fontsize=10.5)
ax.set_xlim(0, 5)
ax.set_ylim(-0.02, 1.02)
ax.legend(loc="lower right", fontsize=9.5, framealpha=0.95)
grid_y(ax, alpha=0.30)
thin_spines(ax)
ax.set_title("(a)  Within-cohort scatter ($n = 771$ OpenAlex researchers)",
             fontsize=10.5, loc="left")

# ── Panel (b): decile means ───────────────────────────────────
ax = axes[1]
pairs_h = sorted(zip(xs_h, ys.tolist()))
pairs_c = sorted(zip(xs_c, ys.tolist()))
n = len(pairs_h)
dsz = n // 10
dec_h_y, dec_c_y = [], []
for d in range(10):
    chunk_h = pairs_h[d * dsz:(d + 1) * dsz]
    chunk_c = pairs_c[d * dsz:(d + 1) * dsz]
    dec_h_y.append(statistics.mean([p[1] for p in chunk_h]))
    dec_c_y.append(statistics.mean([p[1] for p in chunk_c]))

xs_d = list(range(1, 11))
ax.plot(xs_d, dec_h_y, "o-", color=C_H, markersize=9, linewidth=2.4,
        markeredgecolor="white", markeredgewidth=1.0,
        label=r"by $h$-index decile")
ax.plot(xs_d, dec_c_y, "s-", color=C_C, markersize=8.5, linewidth=2.4,
        markeredgecolor="white", markeredgewidth=1.0,
        label=r"by citations decile")

# Direct-label the D1->D10 rise of each series at the right edge.
ax.text(10.35, dec_h_y[-1],
        f"$h$-index: {dec_h_y[0]:.2f} $\\rightarrow$ {dec_h_y[-1]:.2f}",
        fontsize=8.8, color=C_H, va="center", ha="left")
ax.text(10.35, dec_c_y[-1] - 0.035,
        f"citations: {dec_c_y[0]:.2f} $\\rightarrow$ {dec_c_y[-1]:.2f}",
        fontsize=8.8, color=C_C, va="center", ha="left")

ax.set_xticks(xs_d)
ax.set_xticklabels([f"D{i}" for i in xs_d])
ax.set_xlim(0.4, 13.2)
ax.set_xlabel("Bibliometric decile", fontsize=10.5)
ax.set_ylabel("Mean NameRank in decile", fontsize=10.5)
ax.set_ylim(0.15, 0.7)
ax.legend(loc="lower right", fontsize=9.5, framealpha=0.95)
grid_y(ax, alpha=0.30)
thin_spines(ax)
ax.set_title("(b)  Decile-by-decile:  $h$-index is steeper and monotonic",
             fontsize=10.5, loc="left")

plt.tight_layout()
out = HERE / "fig3_external.pdf"
plt.savefig(out)
print(f"Wrote {out}")
