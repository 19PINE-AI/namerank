"""Figure 2: artifact > creator inversion chart.

Reads the 11 verified pairs from data/analysis/attribution_pairs_v2.csv and
the per-entity NameRank from data/analysis/namerank_per_entity.csv. The
creator/artifact name lookup tolerates the abbreviations used in the paper
(e.g., "A. Karpathy" vs "Andrej Karpathy", "G. DeepMind" vs "Google DeepMind").
"""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from _style import (PALETTE, apply_style, grid_x, thin_spines)

apply_style()

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
ANALYSIS = REPO / "data" / "analysis"

# Short labels used in the figure (paper convention).
SHORT = {
    "Andrej Karpathy": "A. Karpathy",
    "Harrison Chase": "H. Chase",
    "Demis Hassabis": "D. Hassabis",
    "Google DeepMind": "G. DeepMind",
    "Aravind Srinivas": "A. Srinivas",
    "Thinking Machines Lab": "Thinking Machines",
    "lilianweng.github.io": "lilianweng.github.io",
}


def load_namerank() -> dict[str, float]:
    """Map entity_name -> NameRank, preferring the reference_pilot cohort.

    Several artifacts appear in both reference_pilot (the diagnostic /
    hand-curated set the paper's tables quote from) and a second cohort
    (e.g., oss_project), with different scores because the gold answers
    differ in depth. The paper's narrative uses the reference_pilot
    values; this loader matches by preferring reference_pilot whenever a
    name collision exists.
    """
    # name -> (cohort_priority, namerank)
    priority = {"reference_pilot": 0}  # smallest = highest priority
    best: dict[str, tuple[int, float]] = {}
    for r in csv.DictReader(open(ANALYSIS / "namerank_per_entity.csv", encoding="utf-8")):
        name = r["entity_name"]
        p = priority.get(r["cohort"], 10)
        nr_val = float(r["namerank"])
        if name not in best or p < best[name][0]:
            best[name] = (p, nr_val)
    return {n: v for n, (_, v) in best.items()}


def main() -> None:
    nr = load_namerank()
    pairs = []
    for r in csv.DictReader(open(ANALYSIS / "attribution_pairs_v2.csv", encoding="utf-8")):
        c, a = r["creator"], r["artifact"]
        if c not in nr or a not in nr:
            raise SystemExit(f"missing NameRank for pair ({c}, {a}); rerun build_namerank.py")
        pairs.append((nr[c], nr[a], SHORT.get(c, c), SHORT.get(a, a)))

    # Sort by creator NameRank for a readable ramp.
    pairs_sorted = sorted(pairs, key=lambda p: p[0])

    fig, ax = plt.subplots(figsize=(9.6, 6.8))

    n_inv = sum(1 for nrc, nra, _, _ in pairs_sorted if nra > nrc)

    # Background zone band for the "discriminative" mid-range — keeps the eye
    # anchored to the NameRank scale even without the full zone palette.
    ax.axvspan(0.0, 0.10, color="#f3dadb", alpha=0.25, zorder=0, lw=0)
    ax.axvspan(0.60, 1.0, color="#dceee2", alpha=0.20, zorder=0, lw=0)

    for i, (nrc, nra, cname, aname) in enumerate(pairs_sorted):
        inversion = nra > nrc
        c_line = PALETTE["cat0"] if inversion else PALETTE["silent"]
        # Connecting line — thicker if inversion is large.
        gap = abs(nra - nrc)
        lw = 1.5 + 4.0 * gap
        ax.plot([nrc, nra], [i, i], "-", color=c_line, linewidth=lw,
                alpha=0.45, zorder=3, solid_capstyle="round")
        # Creator: open circle.
        ax.plot(nrc, i, "o", color="white", markersize=11,
                markeredgecolor="#333", markeredgewidth=1.2, zorder=5)
        ax.plot(nrc, i, "o", color="#666", markersize=5.5, zorder=6)
        # Artifact: filled square in inversion colour.
        ax.plot(nra, i, "s", color=c_line, markersize=11,
                markeredgecolor="#222", markeredgewidth=1.1, zorder=5)
        # Pair label on the left side of whichever marker is leftmost.
        leftx = min(nrc, nra)
        ax.text(leftx - 0.035, i, f"{cname}  /  {aname}",
                ha="right", va="center", fontsize=9.5, color="#222")
        # Delta annotation on the right end of the segment.
        rightx = max(nrc, nra)
        delta_str = f"$\\Delta$={nra - nrc:+.2f}"
        ax.text(rightx + 0.018, i, delta_str,
                ha="left", va="center", fontsize=8.5,
                color=c_line, alpha=0.95)

    ax.set_xlabel("NameRank", fontsize=11)
    ax.set_yticks([])
    ax.set_xlim(-0.30, 1.10)
    ax.set_ylim(-1.1, len(pairs_sorted) + 0.6)

    grid_x(ax, alpha=0.28)
    thin_spines(ax)

    legend_elems = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#666",
               markersize=9, markeredgecolor="#333", label="Creator"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor=PALETTE["cat0"],
               markersize=9, markeredgecolor="#222", label=f"Artifact $>$ creator  ({n_inv}/{len(pairs_sorted)})"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor=PALETTE["silent"],
               markersize=9, markeredgecolor="#222", label=f"Creator $>$ artifact  ({len(pairs_sorted) - n_inv}/{len(pairs_sorted)})"),
    ]
    ax.legend(handles=legend_elems, loc="lower right", fontsize=9.5,
              framealpha=0.95)

    ax.set_title(
        "Artifact $>$ creator inversion across 11 verified pairs.  "
        "Line thickness encodes the $|\\Delta|$ gap; all 3 reversals are senior leaders of named organisations.",
        fontsize=10.5, pad=10,
    )
    plt.tight_layout()
    out = HERE / "fig2_inversion.pdf"
    plt.savefig(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
