"""Figure: news-event calibration — recognition tracks recorded attention
through its peak, not its persistence.

Two-panel chart on the 2021-2023 news-event cohort:
(a) Scatter of NameRank vs log10(total first-year pageviews) with decile means.
(b) Decile ladders for peak attention vs effective duration (the two log
    components of total attention): peak is steep, duration is flat — the
    inverse of the citations-vs-h-index panel.
"""
import csv
import math
import statistics
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from _style import PALETTE, apply_style, grid_y, thin_spines

apply_style()

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
EXP = REPO / "experiments/t4_1_news_events"

rows = list(csv.DictReader(open(EXP / "outputs/event_namerank.csv",
                                encoding="utf-8")))
y = np.array([float(r["namerank"]) for r in rows])
lt = np.array([math.log10(float(r["total_views"])) for r in rows])
lp = np.array([math.log10(max(float(r["peak_views"]), 1)) for r in rows])
ld = np.array([math.log10(max(float(r["eff_duration"]), 1.0)) for r in rows])


def fit(x, yy):
    mx, my = np.mean(x), np.mean(yy)
    num = np.sum((x - mx) * (yy - my))
    den = np.sum((x - mx) ** 2)
    slope = num / den if den else 0.0
    return slope, my - slope * mx


def r2(x, yy):
    s, i = fit(x, yy)
    resid = yy - (s * x + i)
    return 1 - float((resid ** 2).sum()) / float(((yy - yy.mean()) ** 2).sum())


C_T = PALETTE["cat0"]        # blue: total (a) / peak (b) — the carrying signal
C_P = PALETTE["highlight"]   # orange: duration — the null channel

fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.0))

# ── Panel (a): dose-response scatter ──────────────────────────
ax = axes[0]
r2_t = r2(lt, y)
ax.scatter(lt, y, s=13, color=C_T, alpha=0.35, edgecolors="none")
s, i = fit(lt, y)
xs_line = np.linspace(lt.min(), lt.max(), 50)
ax.plot(xs_line, s * xs_line + i, "-", color=C_T, linewidth=2.6, zorder=5,
        label=f"linear fit,  $R^2 = {r2_t:.2f}$")

# decile means overlay
order = np.argsort(lt)
dx, dy = [], []
for d in range(10):
    chunk = order[d * len(rows) // 10:(d + 1) * len(rows) // 10]
    dx.append(float(np.mean(lt[chunk])))
    dy.append(float(np.mean(y[chunk])))
ax.plot(dx, dy, "o", color="#1d4e80", markersize=8.5,
        markeredgecolor="white", markeredgewidth=1.0, zorder=6,
        label="decile means")

ax.set_xlabel("Total en-Wikipedia pageviews, first year  ($\\log_{10}$)",
              fontsize=10.5)
ax.set_ylabel("NameRank", fontsize=10.5)
ax.set_ylim(-0.02, 1.02)
ax.legend(loc="upper left", fontsize=9.5, framealpha=0.95)
grid_y(ax, alpha=0.30)
thin_spines(ax)
ax.set_title(f"(a)  Recognition tracks recorded attention ($n = {len(rows)}$ events)",
             fontsize=10.5, loc="left")

# ── Panel (b): peak vs duration quintile ladders ──────────────
ax = axes[1]
pairs_p = sorted(zip(lp.tolist(), y.tolist()))
pairs_d = sorted(zip(ld.tolist(), y.tolist()))
n = len(pairs_p)
NQ = 5
qsz = n // NQ
dec_p, dec_d = [], []
for d in range(NQ):
    dec_p.append(statistics.mean([p[1] for p in pairs_p[d * qsz:(d + 1) * qsz]]))
    dec_d.append(statistics.mean([p[1] for p in pairs_d[d * qsz:(d + 1) * qsz]]))

xs_d = list(range(1, NQ + 1))
ax.plot(xs_d, dec_p, "o-", color=C_T, markersize=9, linewidth=2.4,
        markeredgecolor="white", markeredgewidth=1.0,
        label="by peak-attention quintile")
ax.plot(xs_d, dec_d, "s-", color=C_P, markersize=8.5, linewidth=2.4,
        markeredgecolor="white", markeredgewidth=1.0,
        label="by effective-duration quintile")

ax.text(NQ + 0.18, dec_p[-1],
        f"peak: {dec_p[0]:.2f} $\\rightarrow$ {dec_p[-1]:.2f}",
        fontsize=8.8, color=C_T, va="center", ha="left")
ax.text(NQ + 0.18, dec_d[-1] - 0.012,
        f"duration: {dec_d[0]:.2f} $\\rightarrow$ {dec_d[-1]:.2f}",
        fontsize=8.8, color=C_P, va="center", ha="left")

ax.set_xticks(xs_d)
ax.set_xticklabels([f"Q{i}" for i in xs_d])
ax.set_xlim(0.6, NQ + 1.6)
ax.set_xlabel("Attention-component quintile", fontsize=10.5)
ax.set_ylabel("Mean NameRank in quintile", fontsize=10.5)
ax.legend(loc="lower right", fontsize=9.5, framealpha=0.95)
grid_y(ax, alpha=0.30)
thin_spines(ax)
ax.set_title("(b)  How loud, not how long:  peak carries the signal",
             fontsize=10.5, loc="left")

plt.tight_layout()
out = HERE / "fig_events.pdf"
plt.savefig(out)
print(f"Wrote {out}")
