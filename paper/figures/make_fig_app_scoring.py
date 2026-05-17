"""Appendix figure: the multiplicative scoring regime on the (coverage,
accuracy) plane, with worked-example overlays.

Visualises why NameRank uses cov $\\times$ acc rather than additive or
coverage-only scoring: the multiplicative form collapses fluent
hallucinations (high coverage, near-zero accuracy) to score $\\approx 0$.

Three concrete responses from Appendix §H are plotted as the three
prototype points: Karpathy (1.0, 1.0), Sanger (0.4, 1.0), Hao Tang fluent
hallucination (0.7, 0.0).
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from _style import PALETTE, apply_style, thin_spines

apply_style()

HERE = Path(__file__).resolve().parent


def main() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 5.4),
                              gridspec_kw=dict(width_ratios=[1.0, 1.0]))

    # ── Panel (a) score contours over (coverage, accuracy) ──
    ax = axes[0]
    xs = np.linspace(0, 1, 200)
    ys = np.linspace(0, 1, 200)
    X, Y = np.meshgrid(xs, ys)
    Z = X * Y

    cs = ax.contourf(X, Y, Z, levels=[0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.001],
                     cmap="YlOrRd", alpha=0.85)
    cb = plt.colorbar(cs, ax=ax, fraction=0.046, pad=0.04)
    cb.set_label("NameRank contribution  (coverage $\\times$ accuracy)",
                 fontsize=9.5)
    cb.ax.tick_params(labelsize=8.5)

    # Decoy contour lines for clarity.
    cl = ax.contour(X, Y, Z, levels=[0.1, 0.3, 0.5, 0.7], colors="#222",
                    linewidths=0.5, alpha=0.7)
    ax.clabel(cl, fmt="%.1f", fontsize=8)

    # Plot three worked-example points (from Appendix §H).
    examples = [
        ("Karpathy /\ngpt-5.5-think\n(score 1.0)", 1.0, 1.0, PALETTE["cat0"]),
        ("Sanger /\nllama-3.3-70b\n(score 0.4)",   0.4, 1.0, PALETTE["highlight"]),
        ("Hao Tang /\nclaude-opus-think\n(score $\\approx 0$,\nfluent halluc.)",
         0.7, 0.05, PALETTE["silent"]),
    ]
    for label, x, y, c in examples:
        ax.plot(x, y, "o", color=c, markersize=14,
                markeredgecolor="white", markeredgewidth=1.6, zorder=10)
        # Label offset.
        dx = -0.06 if x > 0.5 else 0.06
        dy = -0.06 if y > 0.5 else 0.06
        ha = "right" if dx < 0 else "left"
        va = "top" if dy < 0 else "bottom"
        ax.annotate(label, xy=(x, y), xytext=(x + dx, y + dy),
                    fontsize=9, color="#222",
                    ha=ha, va=va,
                    arrowprops=dict(arrowstyle="-", color="#666", lw=0.6))

    ax.set_xlim(-0.01, 1.01)
    ax.set_ylim(-0.01, 1.01)
    ax.set_xlabel("Coverage", fontsize=10.5)
    ax.set_ylabel("Accuracy", fontsize=10.5)
    ax.set_aspect("equal", adjustable="box")
    thin_spines(ax)
    ax.set_title("(a)  NameRank contribution = $\\mathrm{cov}\\times \\mathrm{acc}$.  "
                 "Hallucinations collapse on the bottom edge.",
                 fontsize=10.5, loc="left")

    # ── Panel (b) alternative scoring rules, evaluated on the same 3 points ──
    ax = axes[1]
    rules = [
        ("Multiplicative\n$\\mathrm{cov}\\cdot \\mathrm{acc}$",
         lambda cov, acc: cov * acc),
        ("Coverage only\n$\\mathrm{cov}$",
         lambda cov, acc: cov),
        ("Embedding-like\n(coverage proxy)",
         lambda cov, acc: 0.65 + 0.18 * (cov + acc)),
        ("Average\n$\\frac{1}{2}(\\mathrm{cov}+\\mathrm{acc})$",
         lambda cov, acc: 0.5 * (cov + acc)),
    ]
    pts = [("Karpathy", 1.0, 1.0, PALETTE["cat0"]),
           ("Sanger",   0.4, 1.0, PALETTE["highlight"]),
           ("Hao Tang\n(fluent halluc.)", 0.7, 0.05, PALETTE["silent"])]

    bar_w = 0.22
    x_indices = np.arange(len(rules))
    for i, (lbl, x, y, c) in enumerate(pts):
        scores = [r[1](x, y) for r in rules]
        offset = (i - 1) * bar_w
        bars = ax.bar(x_indices + offset, scores, width=bar_w,
                      color=c, alpha=0.85, edgecolor="white",
                      linewidth=0.6, label=lbl)
        for j, s in enumerate(scores):
            ax.text(x_indices[j] + offset, s + 0.02, f"{s:.2f}",
                    ha="center", va="bottom", fontsize=7.5, color="#222")

    ax.set_xticks(x_indices)
    ax.set_xticklabels([r[0] for r in rules], fontsize=9.5)
    ax.set_ylim(0, 1.10)
    ax.set_ylabel("Per-record score under each rule", fontsize=10.5)
    ax.set_title("(b)  Only the multiplicative rule sends the fluent\n"
                 "hallucination to $\\approx 0$.",
                 fontsize=10.5, loc="left")
    ax.legend(loc="upper right", fontsize=8.5, framealpha=0.95)
    ax.grid(True, axis="y", color="#d6d6d6", linewidth=0.5, alpha=0.4)
    ax.set_axisbelow(True)
    thin_spines(ax)

    plt.tight_layout()
    out = HERE / "fig_app_scoring.pdf"
    plt.savefig(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
