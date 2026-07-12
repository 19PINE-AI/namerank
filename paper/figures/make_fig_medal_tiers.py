"""Figure: NOI 2009 complete medal roster under the v2 measurement protocol.

Golds are length-normalized, web-grounded person profiles (~55 words), scored
by the echo-discounting judge (context restatement earns nothing). Under this
protocol recognition is genuinely sparse: most medalists are silent (score ~0)
because frontier models know only a small share of the population, and only a
career-documented tail is recognized. The y-axis is a square-root scale so the
dense near-zero band is legible while the recognized tail (to ~0.22) stays on
the same panel.

(a) Per-medalist NameRank by tier (jittered strips) with tier means.
(b) NameRank vs NOI 2009 contest score with within-tier means: the recognized
    tail is career-driven, not contest-score-driven.

Data: experiments/t5_3_noi_medal_tiers/outputs/tier_per_entity_v2.csv.
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
SRC = REPO / "experiments" / "t5_3_noi_medal_tiers" / "outputs" / "tier_per_entity_v2.csv"

TIER_COLOR = {"gold": "#a87800", "silver": "#2a6fb5", "bronze": "#a04f22"}
TIER_ORDER = ["gold", "silver", "bronze"]
YTICKS = [0, 0.01, 0.025, 0.05, 0.1, 0.15, 0.2]
YMAX = 0.245

rows = [r for r in csv.DictReader(open(SRC, encoding="utf-8"))
        if r["tier"] in TIER_COLOR and r["control"] == "False"]
for r in rows:
    r["nr"] = float(r["namerank"])
    r["score"] = int(r["noi_score"])
by_name = {r["entity_name"]: r for r in rows}


def sqrt_scale(ax):
    ax.set_yscale("function",
                  functions=(lambda y: np.sqrt(np.clip(y, 0, None)),
                             lambda y: np.power(y, 2)))
    ax.set_ylim(0, YMAX)
    ax.set_yticks(YTICKS)
    ax.set_yticklabels([f"{t:g}" for t in YTICKS])


fig, (ax_a, ax_b) = plt.subplots(
    1, 2, figsize=(12.0, 4.4), gridspec_kw={"width_ratios": [1.0, 1.35]})

# ── (a) strips by tier ─────────────────────────────────────────
rng = np.random.RandomState(0)
for i, tier in enumerate(TIER_ORDER):
    vals = np.array([r["nr"] for r in rows if r["tier"] == tier])
    x = i + rng.uniform(-0.17, 0.17, size=len(vals))
    ax_a.scatter(x, vals, s=26, color=TIER_COLOR[tier], alpha=0.72,
                 edgecolors="white", linewidths=0.5, zorder=3)
    m = vals.mean()
    ax_a.hlines(m, i - 0.28, i + 0.28, color=TIER_COLOR[tier],
                linewidth=2.6, zorder=4)
    ax_a.text(i + 0.30, m, f"{m:.3f}", va="center", ha="left", fontsize=8.5,
              color=TIER_COLOR[tier])

# annotate the silent band once, in clear upper-centre space
ax_a.text(1.5, 0.175, "most medalists silent (score $\\approx$ 0):\n"
          "models recognize only a small\nshare of the population",
          ha="left", va="center", fontsize=8, color=PALETTE["baseline"],
          style="italic")

for name in ("Wu Jiajun (吴佳俊)", "Fan Haoqiang (范浩强)", "Li Bojie (李博杰)"):
    r = by_name.get(name)
    if r:
        i = TIER_ORDER.index(r["tier"])
        ax_a.annotate(name.split(" (")[0], xy=(i, r["nr"]),
                      xytext=(i + 0.33, r["nr"]), fontsize=9, va="center",
                      color=PALETTE["highlight"],
                      arrowprops=dict(arrowstyle="-", lw=0.8,
                                      color=PALETTE["highlight"]))

ax_a.set_xticks(range(3))
ax_a.set_xticklabels([f"{t.capitalize()}\n$n={sum(1 for r in rows if r['tier']==t)}$"
                      for t in TIER_ORDER])
ax_a.set_ylabel("NameRank  (v2 protocol, square-root scale)")
ax_a.set_xlim(-0.55, 2.62)
ax_a.set_title("(a) Recognition by medal tier", loc="left")
sqrt_scale(ax_a)
grid_y(ax_a)
thin_spines(ax_a)

# ── (b) dose-response on contest score ─────────────────────────
for tier in TIER_ORDER:
    sub = [r for r in rows if r["tier"] == tier]
    xs = np.array([r["score"] for r in sub], dtype=float)
    ys = np.array([r["nr"] for r in sub])
    ax_b.scatter(xs, ys, s=26, color=TIER_COLOR[tier], alpha=0.72,
                 edgecolors="white", linewidths=0.5, zorder=3,
                 label=f"{tier.capitalize()} (mean {ys.mean():.3f})")
    ax_b.hlines(ys.mean(), xs.min(), xs.max(), color=TIER_COLOR[tier],
                linewidth=2.0, zorder=4)

# Right-margin column: every gold scoring >=500 contest points (rightmost
# points). Three are recognized, three are near-silent despite top scores --
# the crux of "not score-driven". Ordered by NameRank so leaders don't cross.
ABOVE500 = sorted([r["entity_name"] for r in rows
                   if r["tier"] == "gold" and r["score"] >= 500],
                  key=lambda n: -by_name[n]["nr"])
COL_X = 600.0
GAP_SQRT = 0.030   # min spacing in sqrt space
prev = None
for name in ABOVE500:
    r = by_name[name]
    ty = r["nr"]
    if prev is not None and np.sqrt(prev) - np.sqrt(max(ty, 0)) < GAP_SQRT:
        ty = (np.sqrt(prev) - GAP_SQRT) ** 2
    prev = ty
    ax_b.annotate(name.split(" (")[0], xy=(r["score"], r["nr"]),
                  xytext=(COL_X, ty), fontsize=9, color=PALETTE["highlight"],
                  ha="left", va="center", annotation_clip=False,
                  arrowprops=dict(arrowstyle="-", lw=0.8,
                                  color=PALETTE["highlight"], shrinkB=3))

# interior labels: the two low-contest-score medalists who ARE recognized.
# Placed up-and-right of each point, into open space, staying inside the axes.
for name, (tx, ty) in {"Fan Haoqiang (范浩强)": (250, 0.135),
                       "Li Bojie (李博杰)": (250, 0.048)}.items():
    r = by_name[name]
    ax_b.annotate(name.split(" (")[0], xy=(r["score"], r["nr"]),
                  xytext=(tx, ty), fontsize=9, color=PALETTE["highlight"],
                  ha="left", va="center",
                  arrowprops=dict(arrowstyle="-", lw=0.8,
                                  color=PALETTE["highlight"]))

ax_b.set_xlabel("NOI 2009 contest score")
ax_b.set_ylabel("NameRank  (v2 protocol, square-root scale)")
ax_b.set_xlim(150, 600)
ax_b.set_title("(b) The recognized tail is career-driven, not score-driven",
               loc="left")
ax_b.legend(loc="upper left", frameon=True, fontsize=8.5)
sqrt_scale(ax_b)
grid_y(ax_b)
thin_spines(ax_b)

fig.tight_layout(w_pad=2.2)
out = HERE / "fig_medal_tiers.pdf"
plt.savefig(out)
print(f"wrote {out}")
