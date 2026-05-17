"""East/West model variance: per-entity scatter of Western-mean vs Chinese-mean
NameRank across all 5,719 entities.

The y = x diagonal makes within-entity agreement visible at a glance; the
most divergent entities are labelled. The Chinese-content lift (median
+0.03–0.06 across cohorts) shows up as a faint tilt away from the diagonal.
"""
import csv
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from _style import PALETTE, apply_style, grid_x, grid_y, thin_spines

apply_style()

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SRC = REPO / "data" / "analysis" / "east_west_per_entity.csv"


def main() -> None:
    rows = []
    for r in csv.DictReader(open(SRC, encoding="utf-8")):
        w = float(r["western_mean"])
        c = float(r["chinese_mean"])
        d = float(r["delta_chinese_minus_western"])
        rows.append((r["entity_name"], r["cohort"], w, c, d))

    western = np.array([r[2] for r in rows])
    chinese = np.array([r[3] for r in rows])
    delta = np.array([r[4] for r in rows])

    fig, ax = plt.subplots(figsize=(8.6, 7.2))

    # Color encodes the magnitude / sign of the delta — diverging palette.
    # Cap colour for legibility.
    cap = 0.30
    norm_d = np.clip(delta, -cap, cap)
    sc = ax.scatter(western, chinese, s=10, c=norm_d, cmap="RdBu_r",
                    vmin=-cap, vmax=cap, alpha=0.55,
                    edgecolors="none", zorder=4)

    # y = x reference
    ax.plot([0, 1], [0, 1], "--", color="#444", linewidth=1.0, zorder=3)
    ax.text(0.96, 0.96, "$y = x$", fontsize=10, color="#444",
            ha="right", va="bottom", rotation=45)

    # ±0.15 reference bands.
    xs = np.linspace(0, 1, 100)
    ax.plot(xs, xs + 0.15, ":", color="#888", lw=0.7)
    ax.plot(xs, xs - 0.15, ":", color="#888", lw=0.7)
    ax.text(0.84, 0.99, "$y = x + 0.15$", fontsize=8.5, color="#666",
            ha="right", va="bottom", rotation=45, style="italic")
    ax.text(0.99, 0.84, "$y = x - 0.15$", fontsize=8.5, color="#666",
            ha="right", va="top", rotation=45, style="italic")

    # Label a small set of divergent named-entity exemplars (no paper titles).
    # We restrict labels to people / artifacts whose names are short and
    # recognisable, so the chart stays readable.
    cjk_paren = re.compile(r"\s*\([^A-Za-z0-9 \-.]+\)\s*$")
    skip_cohorts = {"research_paper", "long_tail_paper"}
    sorted_rows = sorted(rows, key=lambda r: -abs(r[4]))
    placed: list[tuple[float, float]] = []
    label_quota = 10
    for ent, cohort, w, c, d in sorted_rows:
        if label_quota <= 0:
            break
        if cohort in skip_cohorts:
            continue
        name = cjk_paren.sub("", ent).strip()
        if len(name) > 26:
            continue
        # Skip if too close to an already-placed label (in display space).
        if any(abs(w - px) < 0.06 and abs(c - py) < 0.05 for px, py in placed):
            continue
        col = PALETTE["cat0"] if d > 0 else PALETTE["silent"]
        ha = "left" if d > 0 else "right"
        dx = 0.022 if d > 0 else -0.022
        ax.annotate(name, xy=(w, c), xytext=(w + dx, c - dx * 0.5),
                    fontsize=7.5, color=col, ha=ha, va="center",
                    arrowprops=dict(arrowstyle="-", color="#999", lw=0.4))
        placed.append((w, c))
        label_quota -= 1

    # Colorbar.
    cb = plt.colorbar(sc, ax=ax, fraction=0.045, pad=0.04)
    cb.set_label(r"$\mathrm{NR}_\mathrm{Chinese\;models} - "
                 r"\mathrm{NR}_\mathrm{Western\;models}$", fontsize=9.5)
    cb.ax.tick_params(labelsize=8.5)

    # Summary stats inside the panel.
    med = float(np.median(delta))
    p_above = float(np.mean(delta > 0))
    ax.text(0.04, 0.96,
            f"$n = {len(rows):,}$ entities\n"
            f"median $\\Delta_{{C-W}}$  = {med:+.3f}\n"
            f"fraction above $y=x$  = {p_above:.0%}",
            transform=ax.transAxes,
            ha="left", va="top", fontsize=9, color="#222",
            bbox=dict(boxstyle="round,pad=0.45",
                      facecolor="white", edgecolor="#ddd", linewidth=0.6))

    ax.set_xlabel("NameRank — Western models  (n = 23)", fontsize=10.5)
    ax.set_ylabel("NameRank — Chinese models  (n = 14)", fontsize=10.5)
    ax.set_xlim(-0.01, 1.01)
    ax.set_ylim(-0.01, 1.01)
    ax.set_aspect("equal", adjustable="box")
    grid_x(ax, alpha=0.20)
    grid_y(ax, alpha=0.20)
    thin_spines(ax)
    ax.set_title("Per-entity NameRank: Chinese-model panel vs Western-model panel  "
                 "(all $5{,}719$ entities)",
                 fontsize=10.5, pad=10)

    plt.tight_layout()
    out = HERE / "fig_east_west_scatter.pdf"
    plt.savefig(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
