"""Figure 1: per-cohort NameRank distribution (box plot).

Reads ../../data/analysis/namerank_per_entity.csv and writes
fig1_cohort_distribution.pdf into the same figures/ directory.
"""
import csv
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from _style import (CREDENTIAL_COHORTS, PALETTE, ZONE_BANDS, add_zone_bands,
                    apply_style, grid_x, pretty_cohort, thin_spines, zone_color)

apply_style()

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SRC = REPO / "data" / "analysis" / "namerank_per_entity.csv"

rows = list(csv.DictReader(open(SRC, encoding="utf-8")))
for r in rows:
    r["namerank"] = float(r["namerank"])

by_cohort = defaultdict(list)
for r in rows:
    by_cohort[r["cohort"]].append(r["namerank"])

# Filter: cohorts with n >= 10.
cohorts_sorted = sorted(
    [(c, scores) for c, scores in by_cohort.items() if len(scores) >= 10],
    key=lambda x: statistics.mean(x[1]),
)

names = [c for c, _ in cohorts_sorted]
data = [scores for _, scores in cohorts_sorted]
means = [statistics.mean(s) for s in data]
ns = [len(s) for s in data]
colors = [zone_color(m) for m in means]

# Bold-faced cohorts: the nine credential cohorts (matches the caption).
HIGHLIGHT = CREDENTIAL_COHORTS

fig, ax = plt.subplots(figsize=(11, 13))
positions = list(range(len(names)))

# Background zone bands first, so boxes sit on top.
add_zone_bands(ax, y_extent=(-2.4, len(names) + 0.4),
               alpha=0.16, label=False)

# Box plot — translucent fill, opaque edges in the zone colour.
bp = ax.boxplot(
    data, positions=positions, vert=False, widths=0.62,
    patch_artist=True, showfliers=False, manage_ticks=False,
    medianprops=dict(color="#222", linewidth=1.2),
    whiskerprops=dict(color="#666", linewidth=0.9),
    capprops=dict(color="#666", linewidth=0.9),
)
for patch, c in zip(bp["boxes"], colors):
    patch.set_facecolor(c)
    patch.set_alpha(0.32)
    patch.set_edgecolor(c)
    patch.set_linewidth(1.0)

# Mean markers (filled circles outlined in white for contrast against the box).
for i, (m, c) in enumerate(zip(means, colors)):
    ax.plot(m, i, "o", color=c, markersize=7.5,
            markeredgecolor="white", markeredgewidth=1.2, zorder=10)

# Y labels — readable names, credential cohorts bold.
labels = [f"{pretty_cohort(c)}  (n={n})" for c, n in zip(names, ns)]
ax.set_yticks(positions)
ax.set_yticklabels(labels, fontsize=9.0)
for tick, c in zip(ax.get_yticklabels(), names):
    if c in HIGHLIGHT:
        tick.set_fontweight("bold")
ax.set_xlabel("NameRank", fontsize=11)
ax.set_xlim(-0.02, 1.05)
ax.set_ylim(-2.4, len(names) + 0.4)

# Zone boundaries as soft dotted verticals (the bands already cue the eye).
for x in (0.10, 0.60):
    ax.axvline(x, ls=":", color="#888", alpha=0.55, linewidth=0.8, zorder=1)

# Zone labels at top, in-axes.
for x0, x1, name in [(0.0, 0.10, "silent"),
                     (0.10, 0.60, "discriminative"),
                     (0.60, 1.0, "universal")]:
    ax.text(0.5 * (x0 + x1), len(names) + 0.35, name,
            ha="center", va="bottom",
            fontsize=10, color=ZONE_BANDS[name][1], weight="bold")

grid_x(ax, alpha=0.30)
thin_spines(ax)
ax.set_title(
    "Per-cohort NameRank distribution  ($n \\geq 10$ cohorts; credential cohorts in bold).",
    fontsize=11, pad=14,
)

plt.tight_layout()
out = HERE / "fig1_cohort_distribution.pdf"
plt.savefig(out)
print(f"Wrote {out}")
