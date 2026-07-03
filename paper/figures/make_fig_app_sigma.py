"""Appendix figure: per-cohort within-entity model-disagreement (sigma).

Plots, for each cohort with $n \\geq 10$ entities, the mean of the
within-entity standard deviation of judge scores across the 37-model
panel. High sigma = cross-model disagreement (corpus-pocket-specific
recognition). Low sigma = universal recognition.
"""
import csv
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from _style import PALETTE, apply_style, annotate_value, grid_x, pretty_cohort, thin_spines

apply_style()

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent


def main() -> None:
    rows = list(csv.DictReader(
        open(REPO / "data/analysis/namerank_per_entity.csv", encoding="utf-8")))
    by_cohort = defaultdict(list)
    for r in rows:
        # entity-level standard deviation across models
        by_cohort[r["cohort"]].append(float(r["namerank_sd"]))

    summary = []
    for cohort, sds in by_cohort.items():
        if len(sds) >= 10:
            summary.append((cohort, len(sds), statistics.mean(sds)))
    summary.sort(key=lambda x: x[2])

    cohorts = [pretty_cohort(c) for c, _, _ in summary]
    ns = [n for _, n, _ in summary]
    sigmas = [s for _, _, s in summary]

    # Colour: blue for low (universal), darkening to red for high (pocket-specific).
    def col(s: float) -> str:
        if s < 0.18:
            return "#2f8f4f"   # green: universal
        if s < 0.28:
            return PALETTE["cat0"]    # blue
        if s < 0.35:
            return PALETTE["highlight"]
        return PALETTE["silent"]

    colors = [col(s) for s in sigmas]

    fig, ax = plt.subplots(figsize=(10.0, 11.5))
    ys = list(range(len(cohorts)))
    ax.barh(ys, sigmas, color=colors, edgecolor="white",
            linewidth=0.6, height=0.74, zorder=3, alpha=0.92)

    for i, s in enumerate(sigmas):
        annotate_value(ax, s, i, f"{s:.3f}", dx=0.004, fontsize=8.5)

    ax.set_yticks(ys)
    ax.set_yticklabels([f"{c}  (n={k})" for c, k in zip(cohorts, ns)],
                       fontsize=8.5)
    ax.set_xlim(0, max(sigmas) + 0.06)
    ax.set_xlabel("Mean within-entity $\\sigma$  (sd across 37-model panel)",
                  fontsize=10.5)

    # Legend for the four sigma regimes (replaces in-plot annotations).
    from matplotlib.patches import Patch
    handles = [
        Patch(color=PALETTE["silent"],
              label=r"$\sigma \geq 0.35$: corpus-pocket-specific"),
        Patch(color=PALETTE["highlight"], label=r"$0.28 \leq \sigma < 0.35$"),
        Patch(color=PALETTE["cat0"], label=r"$0.18 \leq \sigma < 0.28$"),
        Patch(color="#2f8f4f",
              label=r"$\sigma < 0.18$: universal corpus presence"),
    ]
    ax.legend(handles=handles, loc="lower right", fontsize=9,
              framealpha=0.95, title="model disagreement", title_fontsize=9)

    ax.set_title(
        "Within-entity model disagreement by cohort.  "
        "$\\sigma$ is the spread of scores across the 37-model panel for a "
        "single entity, averaged within cohort.",
        fontsize=10.5, pad=10,
    )
    grid_x(ax, alpha=0.28)
    thin_spines(ax)
    plt.tight_layout()
    out = HERE / "fig_app_sigma.pdf"
    plt.savefig(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
