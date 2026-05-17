"""Embedding–judge agreement (validation figure).

Per-entity scatter of judge-derived NameRank (x) vs mean embedding cosine
similarity to the gold answer (y). The point is to make visible that the
embedding signal is flat across NameRank levels: even entities the judge
correctly scores at 0 show embedding ~0.8 because the response is fluent
and topic-adjacent. This is the empirical case for using a multiplicative
LLM-judge score rather than embedding similarity.
"""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from _style import PALETTE, apply_style, grid_x, grid_y, thin_spines

apply_style()

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SRC = REPO / "data" / "analysis" / "namerank_per_entity.csv"


def main() -> None:
    judge, emb = [], []
    for r in csv.DictReader(open(SRC, encoding="utf-8")):
        judge.append(float(r["namerank"]))
        emb.append(float(r["embedding_sim_mean"]))

    judge = np.array(judge)
    emb = np.array(emb)

    # Pearson correlation across the full set.
    r = float(np.corrcoef(judge, emb)[0, 1])

    fig, axes = plt.subplots(1, 2, figsize=(12.0, 5.4),
                              gridspec_kw=dict(width_ratios=[1.2, 1.0]))

    # ── Panel (a) hexbin scatter ─────────────────────────────
    ax = axes[0]
    hb = ax.hexbin(judge, emb, gridsize=42, cmap="Blues",
                   mincnt=1, linewidths=0.2)
    cb = plt.colorbar(hb, ax=ax, fraction=0.045, pad=0.03)
    cb.set_label("Entity count per cell", fontsize=9)
    cb.ax.tick_params(labelsize=8.5)

    # Fitted regression line.
    slope, inter = np.polyfit(judge, emb, 1)
    xs = np.linspace(0, 1, 50)
    ax.plot(xs, slope * xs + inter, "-", color=PALETTE["highlight"],
            linewidth=2.0, zorder=10,
            label=f"OLS fit  (slope = {slope:+.2f},  $R^2 = {r ** 2:.3f}$)")
    # y = x reference.
    ax.plot([0, 1], [0, 1], "--", color="#888", linewidth=0.9,
            label="$y = x$")

    ax.set_xlabel("NameRank  (judge,  coverage $\\times$ accuracy)", fontsize=10.5)
    ax.set_ylabel("Embedding cosine similarity  (BGE-large)", fontsize=10.5)
    ax.set_xlim(-0.01, 1.01)
    ax.set_ylim(0.55, 1.00)
    ax.legend(loc="lower right", fontsize=9.5, framealpha=0.95)
    grid_x(ax, alpha=0.20)
    grid_y(ax, alpha=0.20)
    thin_spines(ax)
    ax.set_title(f"(a)  Per-entity scatter ($n = {len(judge):,}$).  "
                 f"Entity-level $r = {r:.2f}$;  per-record $r = 0.15$.",
                 fontsize=10.5, loc="left")

    # Inline take-away annotation.
    ax.text(0.04, 0.98,
            "Embedding has a hard floor\nnear 0.65: it cannot distinguish\n"
            "the silent zone from the\ndiscriminative zone.\n"
            "It is correct as a sanity\ncheck, wrong as a primary metric.",
            transform=ax.transAxes,
            ha="left", va="top", fontsize=9, color="#222",
            bbox=dict(boxstyle="round,pad=0.4",
                      facecolor="white", edgecolor="#ddd", linewidth=0.6))

    # ── Panel (b) bucket means with error bars ───────────────
    ax = axes[1]
    edges = [0.0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.01]
    centers, means, sds, counts = [], [], [], []
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (judge >= lo) & (judge < hi)
        if mask.sum() < 3:
            continue
        centers.append(0.5 * (lo + hi))
        vals = emb[mask]
        means.append(float(np.mean(vals)))
        sds.append(float(np.std(vals)))
        counts.append(int(mask.sum()))

    centers = np.array(centers)
    means = np.array(means)
    sds = np.array(sds)

    ax.errorbar(centers, means, yerr=sds, fmt="o-",
                color=PALETTE["cat0"], markersize=8, linewidth=2.0,
                markeredgecolor="white", markeredgewidth=1.0,
                ecolor="#a3b9d4", elinewidth=1.0, capsize=3,
                label="Mean embedding $\\pm$ 1 SD")
    ax.axhline(float(np.mean(emb)), ls=":", color="#888", linewidth=1.0,
               label=f"Overall mean = {float(np.mean(emb)):.3f}")

    # Count annotations above each marker.
    for cx, cy, n in zip(centers, means, counts):
        ax.text(cx, cy + 0.018, f"n={n:,}", ha="center", va="bottom",
                fontsize=7.5, color="#666")

    ax.set_xlabel("NameRank bucket center", fontsize=10.5)
    ax.set_ylabel("Embedding cosine similarity", fontsize=10.5)
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(0.65, 0.92)
    ax.legend(loc="lower right", fontsize=9.5, framealpha=0.95)
    grid_x(ax, alpha=0.25)
    grid_y(ax, alpha=0.25)
    thin_spines(ax)
    ax.set_title("(b)  NameRank bucket $\\to$ embedding mean",
                 fontsize=10.5, loc="left")

    plt.tight_layout()
    out = HERE / "fig_embedding_judge.pdf"
    plt.savefig(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
