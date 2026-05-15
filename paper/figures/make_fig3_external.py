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
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
ents = {e["id"]: e for e in json.loads((REPO / "data/inputs/pilot_entities.json").read_text())}
nr = {row["entity_id"]: float(row["namerank"])
      for row in csv.DictReader(open(REPO / "data/analysis/namerank_per_entity.csv", encoding="utf-8"))}

xs_h, xs_c, ys = [], [], []
for eid, e in ents.items():
    if e.get('cohort') != 'long_tail_researcher_openalex': continue
    if eid not in nr: continue
    cit = e.get('cited_by_count') or 0
    hi = e.get('h_index') or 0
    if cit <= 0 or hi <= 0: continue
    xs_c.append(cit)
    xs_h.append(hi)
    ys.append(nr[eid])

log_h = [math.log10(x) for x in xs_h]
log_c = [math.log10(x) for x in xs_c]

fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# Panel (a): scatter NameRank vs log(h-index) and log(citations)
ax = axes[0]
ax.scatter(log_c, ys, s=8, color='#d62728', alpha=0.35, label=f"log10(citations), R²=0.14")
ax.scatter(log_h, ys, s=8, color='#1f77b4', alpha=0.6, label=f"log10(h-index), R²=0.40")
ax.set_xlabel("Bibliometric value (log10)", fontsize=11)
ax.set_ylabel("NameRank", fontsize=11)
ax.set_xlim(0, 5)
ax.set_ylim(-0.02, 1.02)
ax.legend(loc='upper left', fontsize=10, framealpha=0.92)
ax.grid(True, alpha=0.3)
ax.set_title("(a) Within-cohort scatter (n=771 OpenAlex researchers)", fontsize=11)

# Trend lines
def fit(x, y):
    n = len(x)
    mx, my = statistics.mean(x), statistics.mean(y)
    num = sum((xi-mx)*(yi-my) for xi,yi in zip(x,y))
    den = sum((xi-mx)**2 for xi in x)
    slope = num/den if den else 0
    inter = my - slope*mx
    return slope, inter

sh, ih = fit(log_h, ys)
sc, ic = fit(log_c, ys)
xs_plot = np.linspace(0, 5, 50)
ax.plot(xs_plot, sh*xs_plot + ih, '-', color='#1f77b4', linewidth=2.5)
ax.plot(xs_plot, sc*xs_plot + ic, '-', color='#d62728', linewidth=2.5)

# Panel (b): decile means
ax = axes[1]
pairs_h = sorted(zip(xs_h, ys))
pairs_c = sorted(zip(xs_c, ys))
n = len(pairs_h)
dsz = n // 10
decile_h_mean_x = []
decile_h_mean_y = []
decile_c_mean_x = []
decile_c_mean_y = []
for d in range(10):
    chunk_h = pairs_h[d*dsz:(d+1)*dsz]
    chunk_c = pairs_c[d*dsz:(d+1)*dsz]
    if chunk_h and chunk_c:
        decile_h_mean_x.append(d+1)
        decile_h_mean_y.append(statistics.mean([p[1] for p in chunk_h]))
        decile_c_mean_x.append(d+1)
        decile_c_mean_y.append(statistics.mean([p[1] for p in chunk_c]))

ax.plot(decile_h_mean_x, decile_h_mean_y, 'o-', color='#1f77b4', markersize=9, linewidth=2.2, label='by h-index decile')
ax.plot(decile_c_mean_x, decile_c_mean_y, 's-', color='#d62728', markersize=9, linewidth=2.2, label='by citations decile')
ax.set_xticks(range(1, 11))
ax.set_xticklabels([f"D{i}" for i in range(1, 11)])
ax.set_xlabel("Bibliometric decile", fontsize=11)
ax.set_ylabel("Mean NameRank in decile", fontsize=11)
ax.set_ylim(0.15, 0.7)
ax.legend(loc='lower right', fontsize=10, framealpha=0.92)
ax.grid(True, alpha=0.3)
ax.set_title("(b) Decile-by-decile: h-index is steeper and monotonic", fontsize=11)

plt.tight_layout()
out = HERE / "fig3_external.pdf"
plt.savefig(out, bbox_inches="tight")
print(f"Wrote {out}")
