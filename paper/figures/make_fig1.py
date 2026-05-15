"""Figure 1: per-cohort NameRank distribution (box plot).

Reads ../../data/analysis/namerank_per_entity.csv and writes
fig1_cohort_distribution.pdf into the same figures/ directory.
"""
import csv
import statistics
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
src = REPO / "data" / "analysis" / "namerank_per_entity.csv"
rows = list(csv.DictReader(open(src, encoding="utf-8")))
for r in rows:
    r["namerank"] = float(r["namerank"])

from collections import defaultdict
by_cohort = defaultdict(list)
for r in rows:
    by_cohort[r["cohort"]].append(r["namerank"])

# Filter: cohorts with n >= 10
cohorts_sorted = sorted([(c, scores) for c, scores in by_cohort.items() if len(scores) >= 10],
                         key=lambda x: statistics.mean(x[1]))

names = [c for c, _ in cohorts_sorted]
data = [scores for _, scores in cohorts_sorted]
means = [statistics.mean(s) for s in data]
ns = [len(s) for s in data]

# Color: silent zone red, discriminative blue, universal green
def color(m):
    if m <= 0.1: return "#d62728"   # silent red
    if m <= 0.6: return "#1f77b4"   # discriminative blue
    return "#2ca02c"                  # universal green

colors = [color(m) for m in means]

# Highlight key cohorts
HIGHLIGHT = {"gpt5_system_card_author", "imo_gold", "cs_faculty",
             "long_tail_researcher_openalex", "mid_tier_filmmaker",
             "msra_phd_fellowship", "rhodes_scholar"}

fig, ax = plt.subplots(figsize=(11, 13))
positions = list(range(len(names)))

# Box plot
bp = ax.boxplot(data, positions=positions, vert=False, widths=0.6,
                 patch_artist=True, showfliers=False, manage_ticks=False)
for patch, c in zip(bp['boxes'], colors):
    patch.set_facecolor(c)
    patch.set_alpha(0.35)
    patch.set_edgecolor(c)

# Mean markers
for i, (m, c) in enumerate(zip(means, colors)):
    ax.plot(m, i, 'o', color=c, markersize=7, markeredgecolor='black', markeredgewidth=0.8, zorder=10)

# Labels — highlight selected cohorts
labels = []
for c, n in zip(names, ns):
    safe_c = c.replace('_', r'\_')
    if c in HIGHLIGHT:
        labels.append(r"$\bf{" + safe_c + "}$ " + f"(n={n})")
    else:
        labels.append(f"{c} (n={n})".replace('_', ' '))

ax.set_yticks(positions)
ax.set_yticklabels(labels, fontsize=9)
ax.set_xlabel("NameRank", fontsize=12)
ax.set_xlim(-0.02, 1.05)
ax.axvline(0.1, ls=":", color="#d62728", alpha=0.6)
ax.axvline(0.3, ls=":", color="grey", alpha=0.5)
ax.axvline(0.6, ls=":", color="grey", alpha=0.5)
ax.axvline(0.7, ls=":", color="#2ca02c", alpha=0.6)
ax.text(0.05, -1.5, "silent", color="#d62728", ha="center", fontsize=10)
ax.text(0.45, -1.5, "discriminative", color="#1f77b4", ha="center", fontsize=10)
ax.text(0.85, -1.5, "universal", color="#2ca02c", ha="center", fontsize=10)
ax.set_ylim(-2, len(names))
ax.grid(True, axis='x', alpha=0.3)
ax.set_title("Per-cohort NameRank distribution ($n \\geq 10$ cohorts)\n"
              "Boxes: IQR; line: median; dot: mean. Three zones visible on a single instrument.",
              fontsize=11)
plt.tight_layout()
out = HERE / "fig1_cohort_distribution.pdf"
plt.savefig(out, bbox_inches="tight")
print(f"Wrote {out}")
