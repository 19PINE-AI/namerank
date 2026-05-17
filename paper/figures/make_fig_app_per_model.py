"""Appendix figure: per-model generosity and refusal across the 37-model
panel, sorted by mean score.

A horizontal bar chart with overlaid refusal-rate markers, so each row
shows both per-model statistics together. The chart is the graphical form
of the per-model table in Appendix §C.
"""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from _style import PALETTE, apply_style, grid_x, thin_spines

apply_style()

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SRC = REPO / "data" / "analysis" / "per_model_summary.csv"

CHINESE_VENDORS = {"deepseek", "alibaba", "qwen", "moonshot", "kimi",
                   "minimax", "baidu", "zhipu", "z_ai"}


def main() -> None:
    rows = list(csv.DictReader(open(SRC, encoding="utf-8")))
    for r in rows:
        r["mean_score"] = float(r["mean_score"])
        r["refusal_rate"] = float(r["refusal_rate"])
        r["chinese"] = r["vendor"] in CHINESE_VENDORS
    rows.sort(key=lambda r: r["mean_score"])

    fig, ax = plt.subplots(figsize=(11.5, 11.0))
    ys = list(range(len(rows)))
    means = [r["mean_score"] for r in rows]
    refs = [r["refusal_rate"] for r in rows]
    colors = [PALETTE["silent"] if r["chinese"] else PALETTE["cat0"] for r in rows]

    # Mean-score bars
    ax.barh(ys, means, color=colors, edgecolor="white",
            linewidth=0.5, height=0.74, alpha=0.85, zorder=3)
    for i, m in enumerate(means):
        ax.text(m + 0.003, i, f"{m:.3f}", va="center", ha="left",
                fontsize=8, color="#222")

    # Refusal markers — secondary axis on top.
    ax2 = ax.twiny()
    ax2.plot(refs, ys, "o", color=PALETTE["highlight"],
             markersize=7, markeredgecolor="white", markeredgewidth=1.0,
             zorder=8, linestyle="none")
    for i, ref in enumerate(refs):
        if ref > 0.001:
            ax2.text(ref + 0.005, i, f"{ref:.0%}",
                     va="center", ha="left", fontsize=7,
                     color=PALETTE["highlight"])
    ax2.set_xlim(0, 0.62)
    ax2.set_xlabel("Refusal rate",
                   color=PALETTE["highlight"], fontsize=10.5)
    ax2.tick_params(axis="x", colors=PALETTE["highlight"])
    for s in ("top", "right", "left"):
        ax2.spines[s].set_visible(False)
    ax2.spines["bottom"].set_visible(False)

    ax.set_yticks(ys)
    ax.set_yticklabels([r["model_id"] for r in rows], fontsize=8.5)
    ax.set_xlim(0, 0.78)
    ax.set_xlabel("Mean score across $5{,}719$ entities",
                  color=PALETTE["cat0"], fontsize=10.5)
    ax.tick_params(axis="x", colors=PALETTE["cat0"])
    grid_x(ax, alpha=0.25)
    thin_spines(ax)

    # Custom legend.
    handles = [
        Line2D([0], [0], marker="s", color="w",
               markerfacecolor=PALETTE["cat0"], markersize=10,
               label="Mean score  (Western)"),
        Line2D([0], [0], marker="s", color="w",
               markerfacecolor=PALETTE["silent"], markersize=10,
               label="Mean score  (Chinese)"),
        Line2D([0], [0], marker="o", color="w",
               markerfacecolor=PALETTE["highlight"], markersize=8,
               markeredgecolor="white", label="Refusal rate"),
    ]
    ax.legend(handles=handles, loc="lower right", fontsize=9,
              framealpha=0.95)

    ax.set_title(
        "Per-model generosity and refusal across the 37-model panel  "
        "(graphical form of Table~3, Appendix~C).  Sorted by mean score.",
        fontsize=10.5, pad=14,
    )
    plt.tight_layout()
    out = HERE / "fig_app_per_model.pdf"
    plt.savefig(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
