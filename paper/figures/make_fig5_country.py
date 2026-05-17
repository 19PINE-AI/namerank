"""Figure 5: CS faculty NameRank by country (corpus-density gradient).

Reads aggregated means from data/analysis/cs_faculty_by_country.csv. The
"Other/Unknown" bucket is excluded from the figure (the paper discusses it
as a residual bucket in the text only).
"""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from _style import (PALETTE, apply_style, annotate_value, grid_x, thin_spines)

apply_style()

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
ANALYSIS = REPO / "data" / "analysis"

EXCLUDE = {"Other/Unknown"}

# Region grouping for soft colour shading (intra-region variation is what we
# want the eye to see — between-region is implied by the gradient itself).
REGION = {
    "USA":            "north_america",
    "Canada":         "north_america",
    "Brazil":         "south_america",
    "Israel":         "middle_east",
    "Singapore":      "asia_other",
    "Sweden":         "europe",
    "Germany":        "europe",
    "Switzerland":    "europe",
    "Netherlands":    "europe",
    "UK":             "europe",
    "Portugal":       "europe",
    "France":         "europe",
    "Spain":          "europe",
    "Hong Kong":      "asia_other",
    "Australia":      "oceania",
    "China":          "china",
    "India":          "india",
}

REGION_COLOR = {
    "north_america": "#6e6e6e",          # baseline grey (USA)
    "south_america": "#9b6a3a",
    "middle_east":   "#7a5dad",
    "europe":        "#2a6fb5",
    "asia_other":    "#0f9aa8",
    "oceania":       "#2f8f4f",
    "china":         "#b3322c",
    "india":         "#d97826",
}


def main() -> None:
    rows = []
    for r in csv.DictReader(open(ANALYSIS / "cs_faculty_by_country.csv", encoding="utf-8")):
        if r["country"] in EXCLUDE:
            continue
        rows.append((r["country"], int(r["n"]), float(r["mean"])))

    usa_mean = next(m for c, _, m in rows if c == "USA")
    rows.sort(key=lambda x: x[2])

    def color_for(country: str) -> str:
        return REGION_COLOR[REGION[country]]

    fig, ax = plt.subplots(figsize=(10.0, 6.8))
    ys = list(range(len(rows)))
    names = [r[0] for r in rows]
    ns = [r[1] for r in rows]
    vals = [r[2] for r in rows]
    colors = [color_for(c) for c, _, _ in rows]

    ax.barh(ys, vals, color=colors, edgecolor="white",
            linewidth=0.6, height=0.72, zorder=3,
            alpha=0.92)
    ax.set_yticks(ys)
    ax.set_yticklabels([f"{n}  (n={k})" for n, k in zip(names, ns)],
                       fontsize=10)
    ax.axvline(usa_mean, ls="--", color=PALETTE["baseline"], linewidth=1.4,
               zorder=5, label=f"USA baseline  ({usa_mean:.3f})")

    for i, (v, name) in enumerate(zip(vals, names)):
        annotate_value(ax, v, i, f"{v:.3f}", dx=0.006,
                       fontsize=9, color="#222")
        # Highlight USA differently.
        if name == "USA":
            ax.text(v + 0.043, i, "(baseline)",
                    va="center", ha="left",
                    fontsize=8.5, color="#666", style="italic")

    lo = min(vals) - 0.04
    hi = max(vals) + 0.07
    ax.set_xlim(max(0.0, lo), hi)
    ax.set_xlabel("Mean NameRank (CS faculty cohort)", fontsize=10.5)

    # Region legend — only show the regions that actually appear.
    from matplotlib.patches import Patch
    used_regions = []
    seen = set()
    for name in names:
        r = REGION[name]
        if r not in seen:
            used_regions.append(r)
            seen.add(r)
    handles = [Patch(color=REGION_COLOR[r], label=r.replace("_", " ").title(),
                     alpha=0.92) for r in used_regions]
    from matplotlib.lines import Line2D
    handles.append(Line2D([0], [0], ls="--", color=PALETTE["baseline"],
                          linewidth=1.4, label=f"USA baseline  ({usa_mean:.3f})"))
    ax.legend(handles=handles, loc="lower right", fontsize=8.5,
              framealpha=0.95, ncol=2)

    ax.set_title(
        "Corpus-density gradient.  Small high-output Western tech ecosystems "
        "(Israel, Singapore, Sweden) lead;\n"
        "China, India, Spain, France cluster at the bottom.  "
        "Region colour groups countries; the gradient is corpus-density, not research-quality.",
        fontsize=10.0, pad=10,
    )
    grid_x(ax, alpha=0.28)
    thin_spines(ax)
    plt.tight_layout()
    out = HERE / "fig5_country.pdf"
    plt.savefig(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
