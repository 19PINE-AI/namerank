"""Decile plot: mean NameRank by decile of h_index, fractional_citations,
cited_by_count, first_last_citations and n_works.

Reads decile_comparison.csv produced by analyze.py and produces a single PNG
overlay so the shapes are directly comparable to Appendix F's h-index curve.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

EXP_DIR = Path("/home/ubuntu/namerank/experiments/t2_9_fractional_citations")
IN_CSV = EXP_DIR / "decile_comparison.csv"
OUT_PNG = EXP_DIR / "decile_comparison.png"

COLORS = {
    "h_index": "tab:blue",
    "fractional_citations": "tab:red",
    "cited_by_count": "tab:green",
    "first_last_citations": "tab:purple",
    "n_works": "tab:orange",
    "mean_authors": "tab:brown",
}


def main() -> None:
    by_pred: dict[str, list[tuple[int, float]]] = defaultdict(list)
    with IN_CSV.open() as f:
        for r in csv.DictReader(f):
            by_pred[r["predictor"]].append(
                (int(r["decile"]), float(r["mean_namerank"]))
            )

    fig, ax = plt.subplots(figsize=(8, 5))
    for pred, pts in by_pred.items():
        pts.sort()
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        ax.plot(
            xs,
            ys,
            marker="o",
            color=COLORS.get(pred, "gray"),
            linewidth=2,
            label=pred,
        )
    ax.set_xlabel("Decile (1 = lowest predictor, 10 = highest)")
    ax.set_ylabel("Mean NameRank")
    ax.set_title(
        "Mean NameRank by predictor decile\n"
        "long_tail_researcher_openalex (n=771)"
    )
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    print(f"wrote {OUT_PNG}")


if __name__ == "__main__":
    main()
