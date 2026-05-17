"""Methodology pipeline schematic.

A data-free figure: probe template + entity + gold + 37-model panel ->
per-(entity, model) judge & embedding scoring -> aggregated NameRank.

Drawn entirely with matplotlib primitives (no external draw library).
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
        ax.text(x + w / 2, y + h * 0.62, text,
                ha="center", va="center",
                fontsize=fontsize, color=text_color, weight="bold")
        ax.text(x + w / 2, y + h * 0.28, subtitle,
                ha="center", va="center",
                fontsize=subtitle_fontsize, color="#333", style="italic")


def arrow(ax, x0, y0, x1, y1, color="#444", lw=1.4, label=None,
          label_offset=(0, 0.10), label_fontsize=8.5):
    """Right-pointing arrow with optional label above."""
    arr = FancyArrowPatch((x0, y0), (x1, y1),
                          arrowstyle="-|>", mutation_scale=14,
                          color=color, linewidth=lw, zorder=2)
    ax.add_patch(arr)
    if label:
        ax.text((x0 + x1) / 2 + label_offset[0],
                (y0 + y1) / 2 + label_offset[1],
                label,
                ha="center", va="bottom",
                fontsize=label_fontsize, color="#444", style="italic")


def main() -> None:
    fig, ax = plt.subplots(figsize=(12.5, 5.0))
    ax.set_xlim(0, 12.5)
    ax.set_ylim(0, 5.0)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ("top", "bottom", "left", "right"):
        ax.spines[s].set_visible(False)

    # ── Column 1: inputs (entity + probe template + gold) ─────
    C_INPUT = "#eef3fa"
    box(ax, 0.2, 3.6, 2.4, 0.95,
        text="Entity  +  context",
        subtitle="e.g.  \"Bojie Li, who is\nChief Scientist of Pine AI\"",
        facecolor=C_INPUT, edgecolor="#9ab4d2")
    box(ax, 0.2, 2.3, 2.4, 0.95,
        text="Probe template",
        subtitle="\"Tell me what you know\nabout [name], who [context].\"",
        facecolor=C_INPUT, edgecolor="#9ab4d2")
    box(ax, 0.2, 1.0, 2.4, 0.95,
        text="Gold answer",
        subtitle="100-200 word reference,\ncurated per entity",
        facecolor=C_INPUT, edgecolor="#9ab4d2")

    # ── Column 2: probe execution against the panel ───────────
    C_PROBE = "#fff1de"
    box(ax, 3.3, 2.6, 2.6, 1.8,
        text=r"$M = 37$ frontier models",
        subtitle="Western (23) + Chinese (14)\nthinking-mode where available\nopen-ended response per entity",
        facecolor=C_PROBE, edgecolor="#d9b07b")

    # arrows: entity+probe -> panel
    arrow(ax, 2.6, 4.07, 3.3, 3.7, label="prompt")
    arrow(ax, 2.6, 2.77, 3.3, 3.2)

    # ── Column 3: per-record scoring ──────────────────────────
    C_JUDGE = "#dceee2"
    box(ax, 6.6, 3.5, 2.6, 1.0,
        text="LLM judge",
        subtitle="Gemini 3 Flash Preview\ncoverage  $\\times$  accuracy",
        facecolor=C_JUDGE, edgecolor="#7fae90")
    C_EMB = "#f3e7ee"
    box(ax, 6.6, 2.1, 2.6, 1.0,
        text="Embedding cross-check",
        subtitle="BGE-large cosine sim.\nsanity check, not in NR",
        facecolor=C_EMB, edgecolor="#cba3b7")

    # arrows: panel -> judge & embedding
    arrow(ax, 5.9, 3.7, 6.6, 4.0, label="response")
    arrow(ax, 5.9, 3.2, 6.6, 2.6)

    # Gold -> judge: route along the bottom to avoid the model-panel box.
    # Two-segment connector via a low waypoint, then straight up.
    ax.plot([2.6, 5.9], [1.47, 1.47], color="#444", lw=1.4, zorder=1)
    arrow(ax, 5.9, 1.47, 6.6, 3.5)
    ax.text(4.2, 1.30, "gold (reference)",
            ha="center", va="top", fontsize=8.5, color="#444", style="italic")

    # ── Column 4: aggregation ─────────────────────────────────
    C_AGG = "#f5d7d4"
    box(ax, 9.6, 2.6, 2.6, 1.8,
        text="NameRank (entity)",
        subtitle=r"$\frac{1}{M}\sum_m \mathrm{cov}_{e,m}\cdot \mathrm{acc}_{e,m}$"
                 + "\nplus $\\sigma_e$, refusal rate,\nW / C sub-means",
        facecolor=C_AGG, edgecolor="#c98a83",
        fontsize=10.5, subtitle_fontsize=8.5)
    arrow(ax, 9.2, 4.0, 9.6, 3.7, label="per-record score")
    arrow(ax, 9.2, 2.6, 9.6, 3.0)

    # ── Below: data scale callout ────────────────────────────
    ax.text(6.25, 0.55,
            r"$N = 5{,}719$ entities  $\times$  $M = 37$ models  "
            r"$=\;211{,}603$ probe records (English run)  $+$  $8{,}880$ records (Chinese sub-run, $n = 240$ entities)",
            ha="center", va="bottom", fontsize=10.5, color="#222")
    ax.add_patch(FancyBboxPatch((1.0, 0.30), 10.5, 0.50,
                                boxstyle="round,pad=0.02,rounding_size=0.04",
                                linewidth=0.8, facecolor="#fbfbfb",
                                edgecolor="#d4d4d4"))

    # Title
    ax.set_title(
        "NameRank pipeline.  Open-ended probe $\\to$ 37-model panel $\\to$ "
        "multiplicative coverage $\\times$ accuracy per record $\\to$ entity-level mean.",
        fontsize=10.5, pad=8, loc="center",
    )

    out = HERE / "fig_pipeline.pdf"
    plt.savefig(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
