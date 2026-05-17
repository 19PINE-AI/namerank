"""Figure 0: page-1 teaser placing a curated set of landmark entities on the
NameRank axis.

Single-panel "ruler with annotations" that lets the reader see, in one
glance, what the three zones look like in entity terms. Per-entity scores
are read live from data/analysis/namerank_per_entity.csv so the figure
stays in sync with the released data.
"""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from _style import (PALETTE, ZONE_BANDS, add_zone_bands, apply_style,
                    thin_spines, zone_color)

apply_style()

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
ANALYSIS = REPO / "data" / "analysis"


def load_namerank_priority() -> dict[str, float]:
    """Map entity_name -> NameRank, preferring reference_pilot on collision."""
    priority = {"reference_pilot": 0}
    best: dict[str, tuple[int, float]] = {}
    for r in csv.DictReader(open(ANALYSIS / "namerank_per_entity.csv", encoding="utf-8")):
        p = priority.get(r["cohort"], 10)
        n = r["entity_name"]
        if n not in best or p < best[n][0]:
            best[n] = (p, float(r["namerank"]))
    return {n: v for n, (_, v) in best.items()}


# Curated landmark set: one per visual slot, spanning the full NameRank range.
# (name, label override or None, kind) — kind is "person" or "artifact".
LANDMARKS = [
    ("Yuval Noah Harari", None, "person"),
    ("Anthropic",         None, "artifact"),
    ("ChatGPT",           None, "artifact"),
    ("Demis Hassabis",    None, "person"),
    ("Geoffrey Hinton",   None, "person"),
    ("Andrej Karpathy",   None, "person"),
    ("Tri Dao",           None, "person"),
    ("Tianshou",          None, "artifact"),
    ("Jiayi Weng",        None, "person"),
    ("LangChain",         None, "artifact"),
    ("tuixue.online",     None, "artifact"),
    ("Bojie Li",          None, "person"),
]
GPT5_MEAN = 0.042   # taken from cohort_summary; published in paper as cohort label


def main() -> None:
    nr = load_namerank_priority()

    points = []   # (x, label, kind)
    for name, lbl, kind in LANDMARKS:
        if name not in nr:
            raise SystemExit(f"missing NameRank for {name}")
        points.append((nr[name], lbl or name, kind))
    points.append((GPT5_MEAN,
                   "GPT-5 system-card cohort\n(silent, mean 0.042)",
                   "cohort"))
    points.sort(key=lambda p: p[0])

    fig, ax = plt.subplots(figsize=(12.0, 4.4))

    # Zone bands span the whole vertical extent.
    Y_MIN, Y_MAX = 0.0, 4.6
    add_zone_bands(ax, y_extent=(Y_MIN, Y_MAX), alpha=0.18, label=False)

    # The horizontal axis itself — a thick "NameRank ruler" at y = 1.
    Y_AXIS = 0.75
    ax.plot([0.0, 1.0], [Y_AXIS, Y_AXIS], color="#222",
            linewidth=2.2, zorder=4, solid_capstyle="round")
    # Tick marks at .1 steps.
    for x in [i / 10 for i in range(11)]:
        ax.plot([x, x], [Y_AXIS - 0.05, Y_AXIS + 0.05],
                color="#222", linewidth=1.0, zorder=4)
        ax.text(x, Y_AXIS - 0.16, f"{x:.1f}",
                ha="center", va="top", fontsize=9, color="#444")
    ax.text(0.5, Y_AXIS - 0.40, "NameRank",
            ha="center", va="top", fontsize=11, color="#222",
            style="italic")

    # Zone titles top of axis.
    for x0, x1, name in [(0.0, 0.10, "silent"),
                         (0.10, 0.60, "discriminative"),
                         (0.60, 1.0, "universal")]:
        cmid = 0.5 * (x0 + x1)
        ax.text(cmid, Y_MAX - 0.05, name,
                ha="center", va="top", fontsize=11.5,
                color=ZONE_BANDS[name][1], weight="bold")

    # Place landmarks. Alternate label heights to dodge overlap.
    label_levels = [1.55, 2.20, 2.85, 3.50]
    last_x_at_level = {lv: -1.0 for lv in label_levels}
    MIN_SPACING = 0.075

    def assign_level(x: float) -> float:
        # Choose the lowest level whose previous label is far enough away.
        best = label_levels[-1]
        for lv in label_levels:
            if x - last_x_at_level[lv] > MIN_SPACING:
                best = lv
                break
        last_x_at_level[best] = x
        return best

    for x, label, kind in points:
        # Marker shape & colour: dot for person, square for artifact, triangle
        # for the GPT-5 cohort exemplar.
        if kind == "person":
            marker, msize = "o", 9
        elif kind == "artifact":
            marker, msize = "s", 8.5
        else:
            marker, msize = "^", 10
        c = zone_color(x)
        ax.plot(x, Y_AXIS, marker, color=c, markersize=msize,
                markeredgecolor="white", markeredgewidth=1.2, zorder=10)

        # Label callout above the axis.
        y_lbl = assign_level(x)
        # Drop line from label to marker.
        ax.plot([x, x], [Y_AXIS + 0.05, y_lbl - 0.05],
                color="#a0a0a0", linewidth=0.6, alpha=0.8, zorder=3)
        # Two-line: name + numeric value.
        if "\n" in label:
            # The cohort annotation already has its own newline.
            txt = label
        else:
            txt = f"{label}\n{x:.2f}"
        bg_alpha = 0.0   # transparent box; white is rendered through the band
        ax.text(x, y_lbl, txt,
                ha="center", va="bottom",
                fontsize=8.8, color="#222",
                bbox=dict(boxstyle="round,pad=0.20",
                          facecolor="white", edgecolor="#cccccc",
                          linewidth=0.5, alpha=0.85),
                zorder=12)

    # Legend for the marker glyphs.
    from matplotlib.lines import Line2D
    legend_elems = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#888",
               markersize=9, markeredgecolor="white", label="Person"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#888",
               markersize=8.5, markeredgecolor="white", label="Artifact"),
        Line2D([0], [0], marker="^", color="w", markerfacecolor="#888",
               markersize=10, markeredgecolor="white", label="Cohort mean"),
    ]
    ax.legend(handles=legend_elems, loc="lower left",
              fontsize=9, framealpha=0.95, ncol=3,
              bbox_to_anchor=(0.0, -0.02))

    ax.set_xlim(-0.02, 1.04)
    ax.set_ylim(Y_MIN, Y_MAX)
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)

    plt.tight_layout()
    out = HERE / "fig0_teaser.pdf"
    plt.savefig(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
