"""Figure: Bibliometric predictor decomposition (T2.9).

Tests the mechanistic claim that h-index dominates raw citations *because* it
weights per-paper name attribution. If so, attribution-weighted citations
(fractional, first/last-author) should match or beat h-index. They do not.

(a) Sole-predictor R^2 (log1p) on NameRank for the n=771 OpenAlex long-tail
    cohort. h-index and n_works lead; fractional citations barely beat raw
    citations; mean_authors is ~0.
(b) Mean NameRank by decile of each of four predictors: h-index and n_works
    rise steeply and monotonically, while fractional citations track raw
    citations on a flatter slope.

Reads experiments/t2_9_fractional_citations/{regression_results.csv,
decile_comparison.csv}.
"""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from _style import PALETTE, apply_style, grid_x, grid_y, thin_spines

apply_style()

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
T29 = REPO / "experiments" / "t2_9_fractional_citations"

LABEL = {
    "h_index": "h-index",
    "n_works": "num. works",
    "first_last_citations": "first/last-author cites",
    "fractional_citations": "fractional cites",
    "cited_by_count": "raw citations",
    "mean_authors": "mean authors/paper",
}
ORDER = ["h_index", "n_works", "first_last_citations", "fractional_citations",
         "cited_by_count", "mean_authors"]


def main() -> None:
    sole = {}
    for r in csv.DictReader(open(T29 / "regression_results.csv")):
        if r["section"] == "sole_predictor":
            sole[r["predictor"]] = float(r["value"])

    deciles = {}
    for r in csv.DictReader(open(T29 / "decile_comparison.csv")):
        deciles.setdefault(r["predictor"], []).append(
            (int(r["decile"]), float(r["mean_namerank"])))

    fig, (axa, axb) = plt.subplots(1, 2, figsize=(11.0, 4.5),
                                   gridspec_kw={"width_ratios": [1.05, 1.1]})

    # ── (a) sole-predictor R^2 ──
    ys = list(range(len(ORDER)))[::-1]
    vals = [sole[p] for p in ORDER]
    colors = [PALETTE["discriminative"] if p == "h_index"
              else (PALETTE["cat5"] if p == "n_works" else PALETTE["baseline"])
              for p in ORDER]
    axa.barh(ys, vals, color=colors, edgecolor="white", height=0.68, zorder=3)
    for y, v in zip(ys, vals):
        axa.text(v + 0.006, y, f"{v:.3f}", va="center", ha="left", fontsize=8.7)
    axa.set_yticks(ys)
    axa.set_yticklabels([LABEL[p] for p in ORDER], fontsize=9.3)
    axa.set_xlabel("Sole-predictor $R^2$ on NameRank ($n=771$)")
    axa.set_xlim(0, 0.46)
    axa.axvline(sole["h_index"], ls=":", color=PALETTE["discriminative"],
                lw=1.0, zorder=1)
    axa.set_title("(a) Attribution-weighting does not beat $h$-index;\n"
                  "author count carries no signal", fontsize=9.8)
    grid_x(axa, alpha=0.25)
    thin_spines(axa)

    # ── (b) decile curves ──
    show = [("h_index", PALETTE["discriminative"], "o", "-"),
            ("n_works", PALETTE["cat5"], "s", "-"),
            ("fractional_citations", PALETTE["highlight"], "^", "--"),
            ("cited_by_count", PALETTE["silent"], "v", "--")]
    for p, color, marker, ls in show:
        pts = sorted(deciles[p])
        xs = [d for d, _ in pts]
        vv = [v for _, v in pts]
        axb.plot(xs, vv, marker=marker, ls=ls, color=color, markersize=4.5,
                 linewidth=1.5, label=LABEL[p], alpha=0.9, zorder=3)
    axb.set_xlabel("Decile of predictor (1 = lowest)")
    axb.set_ylabel("Mean NameRank")
    axb.set_xticks(range(1, 11))
    axb.set_title("(b) $h$-index and works-count rise steeply;\n"
                  "fractional cites track raw cites", fontsize=9.8)
    axb.legend(loc="lower right", fontsize=8.3, framealpha=0.95)
    grid_y(axb, alpha=0.25)
    thin_spines(axb)

    plt.tight_layout()
    out = HERE / "fig_bibliometric_decomp.pdf"
    plt.savefig(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
