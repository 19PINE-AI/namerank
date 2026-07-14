"""Methodology pipeline schematic.

A data-free figure: probe template + entity + gold + 36-model panel ->
per-(entity, model) judge & embedding scoring -> aggregated NameRank.

Drawn entirely with matplotlib primitives (no external draw library).
Columns use equal gaps and every flow label is centered in a gap so no
text overlaps a box.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from _style import PALETTE, apply_style

apply_style()

HERE = Path(__file__).resolve().parent


def box(ax, x, y, w, h, *, text, facecolor, edgecolor=None, subtitle=None,
        fontsize=10, subtitle_fontsize=8.5, text_color="#111"):
    """Rounded rectangle with a centered title and optional subtitle."""
    ec = edgecolor or facecolor
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.04",
        linewidth=1.1, facecolor=facecolor, edgecolor=ec, alpha=0.95,
    )
    ax.add_patch(patch)
    if subtitle is None:
        ax.text(x + w / 2, y + h / 2, text,
                ha="center", va="center",
                fontsize=fontsize, color=text_color, weight="bold")
    else:
        ax.text(x + w / 2, y + h * 0.64, text,
                ha="center", va="center",
                fontsize=fontsize, color=text_color, weight="bold")
        ax.text(x + w / 2, y + h * 0.30, subtitle,
                ha="center", va="center",
                fontsize=subtitle_fontsize, color="#333", style="italic")


def arrow(ax, x0, y0, x1, y1, color="#444", lw=1.4, dashed=False):
    """Plain right-pointing connector arrow."""
    arr = FancyArrowPatch((x0, y0), (x1, y1),
                          arrowstyle="-|>", mutation_scale=14,
                          color=color, linewidth=lw, zorder=2,
                          linestyle=(0, (4, 2)) if dashed else "solid")
    ax.add_patch(arr)


def flow_label(ax, x, y, text, color="#3a3a3a"):
    """Italic flow label, centered in a gap (never overlaps a box)."""
    ax.text(x, y, text, ha="center", va="center",
            fontsize=8.7, color=color, style="italic")


def main() -> None:
    fig, ax = plt.subplots(figsize=(12.6, 4.9))
    ax.set_xlim(0, 12.6)
    ax.set_ylim(0, 5.0)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ("top", "bottom", "left", "right"):
        ax.spines[s].set_visible(False)

    # ── Column geometry: equal 0.75-wide gaps between the four columns ──
    C_INPUT = "#eef3fa"
    C_PROBE = "#fff1de"
    C_JUDGE = "#dceee2"
    C_EMB   = "#f3e7ee"
    C_AGG   = "#f5d7d4"

    # gap centers (used for flow labels): 3.025, 6.275, 9.575
    GAP1, GAP2, GAP3 = 3.025, 6.275, 9.575
    LABEL_Y = 4.62  # common band for flow labels, above every box top

    # ── Column 1: inputs (entity + probe template + gold) ─────
    box(ax, 0.2, 3.55, 2.45, 0.95,
        text="Entity  +  context",
        subtitle="e.g.  \"Bojie Li, who is\nChief Scientist of Pine AI\"",
        facecolor=C_INPUT, edgecolor="#9ab4d2")
    box(ax, 0.2, 2.35, 2.45, 0.95,
        text="Probe template",
        subtitle="\"Tell me what you know\nabout [name], who [context].\"",
        facecolor=C_INPUT, edgecolor="#9ab4d2")
    box(ax, 0.2, 1.05, 2.45, 0.95,
        text="Gold answer",
        subtitle="100-200 word reference,\ncurated per entity",
        facecolor=C_INPUT, edgecolor="#9ab4d2")

    # ── Column 2: probe execution against the panel ───────────
    box(ax, 3.4, 2.5, 2.5, 2.0,
        text=r"$M = 36$ frontier models",
        subtitle="Western (20) + Chinese (16)\nthinking-mode where available\nopen-ended response per entity",
        facecolor=C_PROBE, edgecolor="#d9b07b")

    # arrows: entity + probe -> panel
    arrow(ax, 2.65, 4.02, 3.4, 3.85)
    arrow(ax, 2.65, 2.82, 3.4, 3.10)
    flow_label(ax, GAP1, LABEL_Y, "prompt")

    # ── Column 3: per-record scoring ──────────────────────────
    # Judge box is taller than one grid cell so the three-line subtitle
    # clears the bold title; top-aligned with the panel/NameRank boxes.
    box(ax, 6.65, 3.15, 2.55, 1.35,
        text="Recognition judge",
        subtitle="binary verdict: $\\geq 1$ specific,\nnon-guessable, verified fact\nbeyond the context?",
        facecolor=C_JUDGE, edgecolor="#7fae90")
    box(ax, 6.65, 2.0, 2.55, 1.0,
        text="Diagnostics",
        subtitle="graded cov$\\times$acc + embedding\nretained, not in NameRank",
        facecolor=C_EMB, edgecolor="#cba3b7")

    # arrows: panel -> judge & embedding
    arrow(ax, 5.9, 3.85, 6.65, 3.9)
    arrow(ax, 5.9, 3.05, 6.65, 2.5)
    flow_label(ax, GAP2, LABEL_Y, "response")

    # Gold -> judge & embedding: route along the bottom, branch up at the gap.
    ax.plot([2.65, GAP2], [1.50, 1.50], color="#444", lw=1.4, zorder=1)
    arrow(ax, GAP2, 1.50, 6.65, 3.45)   # to judge
    arrow(ax, GAP2, 1.50, 6.65, 2.05)   # to embedding
    flow_label(ax, 4.45, 1.30, "gold (identity anchor)")

    # ── Column 4: aggregation ─────────────────────────────────
    box(ax, 9.95, 2.5, 2.45, 2.0,
        text="NameRank (entity)",
        subtitle=r"$\frac{1}{M}\sum_m \mathrm{rec}_{e,m}$"
                 + "\npanel recognition rate,\nread against the\nsynthetic-null floor",
        facecolor=C_AGG, edgecolor="#c98a83",
        fontsize=10.5, subtitle_fontsize=8.5)
    arrow(ax, 9.2, 3.55, 9.95, 3.55)            # judge -> NameRank (solid)
    flow_label(ax, GAP3, LABEL_Y, "recognized?")
    # Diagnostics are terminal (not part of NameRank); label it below its box.
    ax.text(7.925, 1.78, "diagnostic only", ha="center", va="center",
            fontsize=8.0, color="#9a7a8a", style="italic")

    # ── Below: data scale callout ────────────────────────────
    ax.add_patch(FancyBboxPatch((0.3, 0.28), 12.0, 0.52,
                                boxstyle="round,pad=0.02,rounding_size=0.04",
                                linewidth=0.8, facecolor="#fbfbfb",
                                edgecolor="#d4d4d4", zorder=0))
    ax.text(6.3, 0.54,
            r"NameRank is the fraction of the panel that recognizes the entity; "
            r"a fluent hallucination, a context echo, or a lucky guess all score $0$.",
            ha="center", va="center", fontsize=9.8, color="#222", zorder=1)

    # Title
    ax.set_title(
        "NameRank pipeline.  Open-ended probe $\\to$ 36-model panel $\\to$ "
        "binary recognition verdict per record $\\to$ panel recognition rate.",
        fontsize=10.5, pad=8, loc="center",
    )

    out = HERE / "fig_pipeline.pdf"
    plt.savefig(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
