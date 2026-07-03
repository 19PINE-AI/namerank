"""Appendix figure: per-model generosity and refusal across the 37-model
panel, sorted by mean score.

Two aligned panels sharing the model axis: mean score (left) and refusal
rate (right). One measure per axis — no overlaid secondary scale.
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

    fig, (axl, axr) = plt.subplots(
        1, 2, figsize=(11.5, 10.5), sharey=True,
        gridspec_kw={"width_ratios": [2.4, 1.0], "wspace": 0.04})

    ys = list(range(len(rows)))
    means = [r["mean_score"] for r in rows]
    refs = [r["refusal_rate"] for r in rows]
    colors = [PALETTE["silent"] if r["chinese"] else PALETTE["cat0"]
              for r in rows]

    # ── Left: mean score ──
    axl.barh(ys, means, color=colors, edgecolor="white",
             linewidth=0.5, height=0.74, alpha=0.88, zorder=3)
    for i, m in enumerate(means):
        axl.text(m + 0.004, i, f"{m:.3f}", va="center", ha="left",
                 fontsize=8, color="#222")
    axl.set_yticks(ys)
    axl.set_yticklabels([r["model_id"] for r in rows], fontsize=8.5)
    axl.set_xlim(0, 0.74)
    axl.set_xlabel("Mean score across $5{,}719$ entities", fontsize=10.5)
    grid_x(axl, alpha=0.25)
    thin_spines(axl)
    handles = [
        Line2D([0], [0], marker="s", color="w",
               markerfacecolor=PALETTE["cat0"], markersize=10,
               label="Western vendor"),
        Line2D([0], [0], marker="s", color="w",
               markerfacecolor=PALETTE["silent"], markersize=10,
               label="Chinese vendor"),
    ]
    axl.legend(handles=handles, loc="lower right", fontsize=9,
               framealpha=0.95)

    # ── Right: refusal rate ──
    axr.barh(ys, refs, color=PALETTE["highlight"], edgecolor="white",
             linewidth=0.5, height=0.74, alpha=0.88, zorder=3)
    for i, ref in enumerate(refs):
        if ref >= 0.005:
            axr.text(ref + 0.008, i, f"{ref:.0%}", va="center", ha="left",
                     fontsize=7.5, color="#222")
    axr.set_xlim(0, 0.66)
    axr.set_xlabel("Refusal rate", fontsize=10.5)
    axr.tick_params(axis="y", length=0)
    grid_x(axr, alpha=0.25)
    thin_spines(axr)
    axr.spines["left"].set_visible(False)

    fig.suptitle(
        "Per-model generosity (left) and refusal rate (right), "
        "sorted by mean score.",
        fontsize=10.5, y=0.995,
    )
    plt.tight_layout(rect=(0, 0, 1, 0.985))
    out = HERE / "fig_app_per_model.pdf"
    plt.savefig(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
