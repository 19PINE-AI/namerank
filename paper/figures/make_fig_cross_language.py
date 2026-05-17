"""Cross-language delta figure.

Per-cohort aggregation of the 240-entity Chinese-prompt sub-run:
$\\Delta = \\mathrm{NR}_\\mathrm{zh} - \\mathrm{NR}_\\mathrm{en}$, sorted.
Bars are coloured by sign and the strongest per-cohort exemplars are
called out alongside the bar.
"""
import csv
import re
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from _style import PALETTE, apply_style, grid_x, thin_spines

apply_style()

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SRC = REPO / "data" / "analysis" / "cross_language_per_entity.csv"

# Per-cohort cleaner labels.
LABEL = {
    "deepseek_v3_author":      "DeepSeek-V3 paper author",
    "noi_china_gold":          "NOI China gold",
    "cmo_china_gold":          "CMO China gold",
    "cpho_china_first_prize":  "CPhO China first prize",
    "msra_phd_fellowship":     "MSRA PhD Fellowship",
    "mid_tier_filmmaker":      "Mid-tier filmmaker (Western)",
    "mid_tier_writer":         "Mid-tier writer (Western)",
    "mid_tier_politician":     "Mid-tier politician (Western)",
    "reference_pilot":         "reference pilot (mixed)",
}


def main() -> None:
    rows = list(csv.DictReader(open(SRC, encoding="utf-8")))
    by_cohort = defaultdict(list)
    cjk_paren = re.compile(r"\s*\([^A-Za-z0-9 \-.]+\)\s*$")
    for r in rows:
        d = float(r["delta_zh_minus_en"])
        # Strip a trailing all-CJK parenthetical so labels render with
        # matplotlib's CM font (no CJK glyphs available at build time).
        name = cjk_paren.sub("", r["entity_name"])
        by_cohort[r["cohort"]].append((name, d))

    # Cohort means and the strongest signed extreme per cohort.
    summary = []
    for cohort, items in by_cohort.items():
        if len(items) < 3:
            continue
        deltas = [d for _, d in items]
        mean_d = statistics.mean(deltas)
        # Pick the extreme that points in the same direction as the mean.
        if mean_d >= 0:
            ex_name, ex_d = max(items, key=lambda p: p[1])
        else:
            ex_name, ex_d = min(items, key=lambda p: p[1])
        summary.append((cohort, len(items), mean_d, ex_name, ex_d))

    summary.sort(key=lambda x: x[2])

    cohorts = [LABEL.get(c, c.replace("_", " ")) for c, _, _, _, _ in summary]
    ns = [n for _, n, _, _, _ in summary]
    means = [m for _, _, m, _, _ in summary]
    exemplars = [(en, ed) for _, _, _, en, ed in summary]
    colors = [PALETTE["cat0"] if m >= 0 else PALETTE["silent"] for m in means]

    fig, ax = plt.subplots(figsize=(11.0, 6.0))
    ys = list(range(len(cohorts)))
    bars = ax.barh(ys, means, color=colors, edgecolor="white",
                   linewidth=0.6, height=0.70, zorder=3, alpha=0.92)
    ax.axvline(0, color="#222", linewidth=0.9, zorder=4)

    # Numeric labels on bars.
    for i, m in enumerate(means):
        dx = 0.003 if m >= 0 else -0.003
        ha = "left" if m >= 0 else "right"
        ax.text(m + dx, i, f"{m:+.3f}",
                va="center", ha=ha, fontsize=9, color="#222")

    # Exemplar annotation per cohort: rightmost-extreme entity.
    for i, (en, ed) in enumerate(exemplars):
        side = "left" if means[i] >= 0 else "right"
        offset = 0.045 if means[i] >= 0 else -0.045
        ax.text(means[i] + offset, i, f"top: {en}  ({ed:+.2f})",
                va="center", ha=side, fontsize=8.5, color="#666",
                style="italic")

    ax.set_yticks(ys)
    ax.set_yticklabels([f"{lbl}  (n={n})" for lbl, n in zip(cohorts, ns)],
                       fontsize=9.5)
    ax.set_xlim(-0.18, 0.18)
    ax.set_xlabel(r"$\Delta = \mathrm{NR}_\mathrm{zh} - \mathrm{NR}_\mathrm{en}$  "
                  r"(mean across cohort)",
                  fontsize=10.5)
    ax.set_title(
        "Cross-language sub-run ($n = 240$ entities re-probed in Mandarin).  "
        "Chinese-prompt lifts Chinese-name entities; suppresses English-coded ones.",
        fontsize=10.5, pad=10,
    )

    # Side labels for the direction — placed at the top inside the panel.
    ax.text(0.17, len(cohorts) - 0.3, "Chinese prompt $>$ English prompt",
            ha="right", va="center", fontsize=9, color=PALETTE["cat0"],
            weight="bold")
    ax.text(-0.17, len(cohorts) - 0.3, "English prompt $>$ Chinese prompt",
            ha="left", va="center", fontsize=9, color=PALETTE["silent"],
            weight="bold")

    grid_x(ax, alpha=0.30)
    thin_spines(ax)
    plt.tight_layout()
    out = HERE / "fig_cross_language.pdf"
    plt.savefig(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
