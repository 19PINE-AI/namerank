"""Figure: NOI 2009 complete medal roster under the v2 measurement protocol.

Golds are length-normalized, web-grounded person profiles (~55 words), scored
by the echo-discounting judge (context restatement earns nothing). Under this
protocol recognition is genuinely sparse: most medalists are silent (score ~0)
because frontier models know only a small share of the population, and only a
career-documented tail is recognized. The y-axis is a square-root scale so the
dense near-zero band is legible while the recognized tail (to ~0.22) stays on
the same panel.

Single panel: NameRank vs NOI 2009 contest score with within-tier means. The
recognized tail is career-driven, not contest-score-driven -- only the five
medalists above 0.2 are labelled, with short leader lines.

Data: experiments/t5_3_noi_medal_tiers/outputs/tier_per_entity_v3.csv.
Palette (validated, CVD-safe; tier is also position-encoded):
gold #a87800, silver #2a6fb5, bronze #a04f22.
"""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from _style import PALETTE, apply_style, grid_y, thin_spines

apply_style()

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SRC = REPO / "experiments" / "t5_3_noi_medal_tiers" / "outputs" / "tier_per_entity_v3.csv"

TIER_COLOR = {"gold": "#a87800", "silver": "#2a6fb5", "bronze": "#a04f22"}
TIER_ORDER = ["gold", "silver", "bronze"]
YTICKS = [0, 0.025, 0.05, 0.1, 0.2, 0.3, 0.4]
YMAX = 0.42
LABEL_MIN = 0.2   # only annotate the recognized tail (top five, NameRank > 0.2)

# Curated label anchors (short leader lines to each dot above LABEL_MIN).
LABELS = {
    "Wu Jiajun (吴佳俊)":    (548, 0.405),
    "Mo Tao (莫涛)":         (596, 0.350),
    "Wu Yi (吴翼)":          (566, 0.235),
    "Fan Haoqiang (范浩强)":  (368, 0.258),
    "Li Bojie (李博杰)":      (232, 0.258),
}

rows = [r for r in csv.DictReader(open(SRC, encoding="utf-8"))
        if r["tier"] in TIER_COLOR and r["control"] == "False"]
for r in rows:
    r["nr"] = float(r["namerank"])
    r["score"] = int(r["noi_score"]) if r["noi_score"].lstrip("-").isdigit() else 0
by_name = {r["entity_name"]: r for r in rows}


def sqrt_scale(ax):
    ax.set_yscale("function",
                  functions=(lambda y: np.sqrt(np.clip(y, 0, None)),
                             lambda y: np.power(y, 2)))
    ax.set_ylim(0, YMAX)
    ax.set_yticks(YTICKS)
    ax.set_yticklabels([f"{t:g}" for t in YTICKS])


fig, ax = plt.subplots(figsize=(7.4, 4.8))

# ── dose-response on contest score ─────────────────────────────
for tier in TIER_ORDER:
    sub = [r for r in rows if r["tier"] == tier]
    xs = np.array([r["score"] for r in sub], dtype=float)
    ys = np.array([r["nr"] for r in sub])
    ax.scatter(xs, ys, s=26, color=TIER_COLOR[tier], alpha=0.72,
               edgecolors="white", linewidths=0.5, zorder=3,
               label=f"{tier.capitalize()} (mean {ys.mean():.3f})")
    ax.hlines(ys.mean(), xs.min(), xs.max(), color=TIER_COLOR[tier],
              linewidth=2.0, zorder=4)

# Label only the recognized tail (NameRank > LABEL_MIN); short leader lines.
for name, (tx, ty) in LABELS.items():
    r = by_name.get(name)
    if not r or r["nr"] < LABEL_MIN:
        continue
    ax.annotate(name.split(" (")[0], xy=(r["score"], r["nr"]),
                xytext=(tx, ty), fontsize=9, color=PALETTE["highlight"],
                ha="left", va="center", annotation_clip=False,
                arrowprops=dict(arrowstyle="-", lw=0.8,
                                color=PALETTE["highlight"],
                                shrinkA=2, shrinkB=3))

ax.set_xlabel("NOI 2009 contest score")
ax.set_ylabel("NameRank  (v2 protocol, square-root scale)")
ax.set_xlim(150, 640)
ax.set_title("Recognition tracks the post-medal career, not the contest score",
             loc="left")
ax.legend(loc="upper left", frameon=True, fontsize=8.5)
sqrt_scale(ax)
grid_y(ax)
thin_spines(ax)

fig.tight_layout()
out = HERE / "fig_medal_tiers.pdf"
plt.savefig(out)
print(f"wrote {out}")
