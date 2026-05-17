"""Discussion-section figure: three falsifiable predictions for the next
NameRank re-run, plotted as current value vs predicted-2027 range.

Each prediction from §7.7 maps to one row. Bars show the current measured
value; arrows extend to the predicted post-2027 range. The figure makes
the predictions concrete and provides a one-page reference for any
follow-up paper measuring how well the predictions held.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from _style import PALETTE, apply_style, grid_x, thin_spines

apply_style()

HERE = Path(__file__).resolve().parent


def main() -> None:
    # (short label, x_now, x_predicted, units, narrative)
    predictions = [
        ("Credential gap\n(IMO gold $-$ OpenAlex baseline)",
         -0.102, -0.13,
         r"$\Delta$ NameRank",
         "widens by $\\geq 0.03$"),
        ("Artifact $-$ creator median\n(independent-creator pairs)",
         +0.089, +0.14,
         r"$\Delta$ NameRank",
         "deepens by $\\geq 0.05$"),
        ("Stanford $-$ Tsinghua mean gap",
         +0.279, +0.21,
         r"$\Delta$ NameRank",
         "narrows by $\\geq 25\\%$"),
    ]

    fig, ax = plt.subplots(figsize=(10.5, 4.4))
    ys = list(range(len(predictions)))

    # Vertical zero line.
    ax.axvline(0, color="#222", linewidth=0.8, zorder=2)

    for i, (lbl, x_now, x_pred, units, narr) in enumerate(predictions):
        # Current value: circle.
        c_now = PALETTE["baseline"]
        ax.plot(x_now, i, "o", color=c_now, markersize=12,
                markeredgecolor="white", markeredgewidth=1.4, zorder=8)
        # Predicted value: arrow head colored by direction.
        # If prediction moves away from zero, mark in red (gap widens / deepens).
        # If prediction moves toward zero, mark in blue (gap narrows).
        moving_away = abs(x_pred) > abs(x_now)
        c_pred = PALETTE["silent"] if moving_away else PALETTE["cat0"]
        ax.annotate("", xy=(x_pred, i), xytext=(x_now, i),
                    arrowprops=dict(arrowstyle="-|>", mutation_scale=18,
                                    color=c_pred, lw=2.2),
                    zorder=6)
        ax.plot(x_pred, i, "s", color=c_pred, markersize=12,
                markeredgecolor="white", markeredgewidth=1.4, zorder=8)
        # Numeric labels.
        ax.text(x_now, i + 0.35, f"now: {x_now:+.3f}",
                ha="center", va="bottom", fontsize=8.5, color="#222")
        ax.text(x_pred, i + 0.35, f"pred ($\\geq$): {x_pred:+.3f}",
                ha="center", va="bottom", fontsize=8.5, color=c_pred)
        # Narrative tail.
        ax.text(0.95, i - 0.32, narr,
                transform=ax.get_yaxis_transform(),
                ha="right", va="center", fontsize=9,
                color=c_pred, style="italic")

    ax.set_yticks(ys)
    ax.set_yticklabels([p[0] for p in predictions], fontsize=10)
    ax.set_xlabel(r"$\Delta$ NameRank  (signed gap)", fontsize=10.5)
    ax.set_xlim(-0.22, 0.40)
    ax.set_ylim(-0.7, len(predictions) - 0.1)
    grid_x(ax, alpha=0.28)
    thin_spines(ax)

    from matplotlib.lines import Line2D
    legend = [
        Line2D([0], [0], marker="o", color="w",
               markerfacecolor=PALETTE["baseline"], markersize=10,
               markeredgecolor="white", label="Current value (2026)"),
        Line2D([0], [0], marker="s", color="w",
               markerfacecolor=PALETTE["silent"], markersize=10,
               markeredgecolor="white", label="Predicted: gap widens / deepens"),
        Line2D([0], [0], marker="s", color="w",
               markerfacecolor=PALETTE["cat0"], markersize=10,
               markeredgecolor="white", label="Predicted: gap narrows"),
    ]
    ax.legend(handles=legend, loc="lower right", fontsize=9, framealpha=0.95)

    ax.set_title(
        "Three falsifiable predictions for the next NameRank re-run (Section~7.7).  "
        "Arrows show the direction and magnitude of the predicted change between\n"
        "the 2026 measurement (circle) and the smallest movement that would constitute confirmation (square).",
        fontsize=10.0, pad=14,
    )

    plt.tight_layout()
    out = HERE / "fig_predictions.pdf"
    plt.savefig(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
