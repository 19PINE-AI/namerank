"""Figure 5: CS faculty NameRank by country (corpus-density gradient).

Reads aggregated means from data/analysis/cs_faculty_by_country.csv. The
"Other/Unknown" bucket is excluded from the figure (the paper discusses it
as a residual bucket in the text only).

Design: color carries the argument, not geography. The three focal
countries the text ranks (USA baseline; China and India, whose 95% CIs do
not overlap the USA's) are highlighted; every other country is a muted
single-hue bar. 95% CIs (mean +/- 1.96 sd/sqrt(n)) are drawn for every row
so the firm-vs-suggestive distinction is visible rather than asserted.
"""
import csv
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from _style import PALETTE, apply_style, grid_x, thin_spines

apply_style()

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
ANALYSIS = REPO / "data" / "analysis"

EXCLUDE = {"Other/Unknown"}
FOCAL_LOW = {"China", "India"}       # the firm low-side contrast
MUTED = "#a8c4de"                    # light step of the blue ramp
SOLID = PALETTE["cat0"]              # well-sampled, non-focal
LOW = PALETTE["silent"]              # focal low-side (China, India)
USA = "#3d3d3d"                      # baseline anchor


def main() -> None:
    rows = []
    for r in csv.DictReader(open(ANALYSIS / "cs_faculty_by_country.csv",
                                 encoding="utf-8")):
        if r["country"] in EXCLUDE:
            continue
        rows.append((r["country"], int(r["n"]), float(r["mean"]),
                     float(r["sd"])))

    usa_mean = next(m for c, _, m, _ in rows if c == "USA")
    rows.sort(key=lambda x: x[2])

    fig, ax = plt.subplots(figsize=(9.6, 6.6))
    ys = list(range(len(rows)))
    names = [r[0] for r in rows]
    ns = [r[1] for r in rows]
    vals = [r[2] for r in rows]
    cis = [1.96 * sd / math.sqrt(n) if n > 1 else 0.0
           for _, n, _, sd in rows]

    def color_for(country, n):
        if country == "USA":
            return USA
        if country in FOCAL_LOW:
            return LOW
        return SOLID if n >= 10 else MUTED

    colors = [color_for(c, n) for c, n in zip(names, ns)]
    ax.barh(ys, vals, color=colors, edgecolor="white",
            linewidth=0.6, height=0.72, zorder=3)

    # 95% CI whiskers on every row: the firm/suggestive distinction itself.
    ax.errorbar(vals, ys, xerr=cis, fmt="none", ecolor="#333",
                elinewidth=0.9, capsize=2.4, capthick=0.9, zorder=6)

    ax.axvline(usa_mean, ls="--", color=PALETTE["baseline"], linewidth=1.3,
               zorder=5)

    for i, (v, ci, k) in enumerate(zip(vals, cis, ns)):
        ax.text(v + ci + 0.008, i, f"{v:.3f}", va="center", ha="left",
                fontsize=9, color="#222" if k >= 10 else "#888")

    ax.set_yticks(ys)
    ax.set_yticklabels([f"{n}  (n={k})" for n, k in zip(names, ns)],
                       fontsize=10)
    for tick, k in zip(ax.get_yticklabels(), ns):
        if k >= 10:
            tick.set_fontweight("bold")

    lo = min(v - c for v, c in zip(vals, cis)) - 0.02
    hi = max(v + c for v, c in zip(vals, cis)) + 0.06
    ax.set_xlim(max(0.0, lo), hi)
    ax.set_xlabel("Mean NameRank (CS faculty cohort)", fontsize=10.5)

    handles = [
        Patch(color=USA, label=f"USA baseline  (n=302, mean {usa_mean:.3f})"),
        Patch(color=LOW, label="China / India: 95% CI below the USA's"),
        Patch(color=SOLID, label=r"other countries, $n \geq 10$"),
        Patch(color=MUTED, label=r"$n < 10$: point estimate only"),
        Line2D([0], [0], ls="--", color=PALETTE["baseline"],
               linewidth=1.3, label="USA mean"),
    ]
    ax.legend(handles=handles, loc="lower right", fontsize=8.8,
              framealpha=0.95)

    ax.set_title(
        "Corpus-density gradient in CS-faculty NameRank, by country of "
        "affiliation (whiskers: 95% CI).",
        fontsize=10.5, pad=10,
    )
    grid_x(ax, alpha=0.28)
    thin_spines(ax)
    plt.tight_layout()
    out = HERE / "fig5_country.pdf"
    plt.savefig(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
