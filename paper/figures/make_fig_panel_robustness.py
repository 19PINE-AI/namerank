"""Panel-size convergence + per-model generosity vs refusal scatter.

(a) Panel-size sensitivity: Pearson(NameRank computed from k-of-37 models,
    NameRank from full 37-model panel) as k grows.

(b) Per-model generosity (mean score) vs refusal rate, coloured by
    West/East partition; the size of each marker tracks (1 - refusal),
    making the fluent-hallucinator cluster visually salient.

Both panels back the methodological-robustness section: cross-model
averaging stabilises the metric (a), and per-model scoring style spans a
wide range that the panel mean integrates out (b).
"""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from _style import PALETTE, apply_style, grid_x, grid_y, thin_spines

apply_style()

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
ANALYSIS = REPO / "data" / "analysis"

# Hand-curated Western / Chinese partition (matches paper).
CHINESE_VENDORS = {"deepseek", "alibaba", "qwen", "moonshot", "kimi",
                   "minimax", "baidu", "zhipu", "z_ai"}


def is_chinese(row) -> bool:
    return row["vendor"] in CHINESE_VENDORS


def main() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.0))

    # ── Panel (a) panel-size convergence ──────────────────────
    ax = axes[0]
    rows = list(csv.DictReader(open(ANALYSIS / "a2_panel_size_curve.csv",
                                    encoding="utf-8")))
    ks = [int(r["k"]) for r in rows]
    pmean = [float(r["pearson_mean"]) for r in rows]
    pmin = [float(r["pearson_min"]) for r in rows]
    pmax = [float(r["pearson_max"]) for r in rows]

    # Shaded min/max envelope.
    ax.fill_between(ks, pmin, pmax, color=PALETTE["cat0"], alpha=0.18,
                    label="min–max across resamples")
    ax.plot(ks, pmean, "o-", color=PALETTE["cat0"], linewidth=2.4,
            markersize=8, markeredgecolor="white", markeredgewidth=1.0,
            label="mean Pearson($k$-subset, 37-panel)")

    # 0.95 reference line — picks out the k at which mean correlation
    # crosses 0.95, since that is the natural "stable" threshold.
    ax.axhline(0.95, ls=":", color="#999", linewidth=1.0)
    ax.text(2.5, 0.951, "0.95 correlation threshold",
            fontsize=8.5, color="#666", style="italic", va="bottom")

    # Mark k at which we cross 0.95 (rounded).
    for k, m in zip(ks, pmean):
        if round(m, 2) >= 0.95:
            ax.annotate(f"$k = {k}$ models suffice\nfor stable ranking",
                        xy=(k, m), xytext=(k + 4.5, m - 0.07),
                        fontsize=9, color="#222",
                        arrowprops=dict(arrowstyle="-",
                                        color="#888", lw=0.7,
                                        connectionstyle="arc3,rad=-0.2"))
            ax.plot(k, m, "o", color=PALETTE["highlight"], markersize=11,
                    markeredgecolor="white", markeredgewidth=1.4, zorder=20)
            break

    ax.set_xlabel("Sub-panel size  $k$  (random subset of 37)", fontsize=10.5)
    ax.set_ylabel("Pearson($k$-subset NameRank,  full-panel NameRank)",
                  fontsize=10.5)
    ax.set_xlim(0, 37)
    ax.set_ylim(0.78, 1.005)
    ax.set_xticks([3, 5, 8, 10, 15, 20, 25, 30, 35])
    ax.legend(loc="lower right", fontsize=9.5, framealpha=0.95)
    grid_y(ax, alpha=0.30)
    thin_spines(ax)
    ax.set_title("(a)  Panel-size convergence:  NameRank stabilises by $k \\approx 10$",
                 fontsize=10.5, loc="left")

    # ── Panel (b) per-model generosity vs refusal scatter ────
    ax = axes[1]
    rows = list(csv.DictReader(open(ANALYSIS / "per_model_summary.csv",
                                    encoding="utf-8")))
    for r in rows:
        r["mean_score"] = float(r["mean_score"])
        r["refusal_rate"] = float(r["refusal_rate"])
    western = [r for r in rows if not is_chinese(r)]
    chinese = [r for r in rows if is_chinese(r)]

    for group, color, label in [(western, PALETTE["cat0"], "Western models"),
                                (chinese, PALETTE["silent"], "Chinese models")]:
        xs = [r["refusal_rate"] for r in group]
        ys = [r["mean_score"] for r in group]
        ax.scatter(xs, ys, s=80, color=color, alpha=0.65,
                   edgecolors="white", linewidths=1.0, label=label, zorder=5)

    # Annotate four anchor models.
    ANNOTATE = {
        "gemini-3-flash-think": (-0.04, 0.025),
        "gpt-oss-20b-think":    (0.02, -0.04),
        "ernie-4.5-300b-a47b":  (0.01, 0.02),
        "llama-3.2-1b":         (0.01, 0.02),
        "claude-opus-4.6-think":(-0.07, -0.04),
        "qwen3-235b-a22b-think":(0.01, 0.02),
    }
    for r in rows:
        if r["model_id"] in ANNOTATE:
            dx, dy = ANNOTATE[r["model_id"]]
            ax.annotate(r["model_id"],
                        xy=(r["refusal_rate"], r["mean_score"]),
                        xytext=(r["refusal_rate"] + dx, r["mean_score"] + dy),
                        fontsize=8.0, color="#333",
                        ha="left" if dx > 0 else "right",
                        arrowprops=dict(arrowstyle="-",
                                        color="#888", lw=0.5))

    # Background regions hint at the two failure modes.
    ax.axhspan(0.0, 0.30, color="#fde4e2", alpha=0.45, zorder=0,
               label=None)
    ax.text(0.025, 0.27, "strict cluster:\nrefuse + score conservatively",
            fontsize=8.5, color="#882017", style="italic", va="top")
    ax.axvspan(0.0, 0.02, color="#fde9d8", alpha=0.45, zorder=0)
    ax.text(0.022, 0.69, "fluent-hallucinator\ncluster (refusal $\\approx 0$,\n"
            "high score, low accuracy)",
            fontsize=8.5, color="#7a4514", style="italic", va="top")

    ax.set_xlabel("Refusal rate  (fraction of records returning ``unknown'')",
                  fontsize=10.5)
    ax.set_ylabel("Mean score across $5{,}719$ records", fontsize=10.5)
    ax.set_xlim(-0.02, 0.55)
    ax.set_ylim(0.15, 0.72)
    ax.legend(loc="upper right", fontsize=9.5, framealpha=0.95)
    grid_x(ax, alpha=0.30)
    grid_y(ax, alpha=0.30)
    thin_spines(ax)
    ax.set_title("(b)  Per-model generosity vs refusal across the 37-model panel",
                 fontsize=10.5, loc="left")

    plt.tight_layout()
    out = HERE / "fig_panel_robustness.pdf"
    plt.savefig(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
