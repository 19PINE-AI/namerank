"""Refusal vs NameRank: silent-zone diagnostic.

Two visualisations of refusal behaviour at the cohort level.

(a) Scatter of cohort mean NameRank vs cohort refusal rate, demonstrating
    threshold cleanliness: low-NameRank cohorts refuse, they do not
    fabricate.

(b) Stacked composition for the lowest-NameRank cohorts: fraction of probe
    records that scored zero (silent), fraction that scored in (0, 0.1]
    (near-silent), and fraction $> 0.1$ (substantive).
"""
import csv
import statistics
from collections import defaultdict
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


def main() -> None:
    coh = list(csv.DictReader(open(ANALYSIS / "cohort_summary.csv",
                                   encoding="utf-8")))
    for r in coh:
        for k in ("mean", "refusal_rate", "frac_silent", "frac_recognized",
                  "median", "sd"):
            r[k] = float(r[k])
        r["n"] = int(r["n"])

    fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.4),
                              gridspec_kw=dict(width_ratios=[1.0, 1.1]))

    # ── Panel (a) cohort mean NameRank vs refusal ────────────
    ax = axes[0]
    xs = [r["mean"] for r in coh]
    ys = [r["refusal_rate"] for r in coh]
    ns = [r["n"] for r in coh]
    # Marker size scales with cohort n.
    sizes = [min(900, 20 + 4 * n ** 0.5) for n in ns]
    colors = [PALETTE["silent"] if x <= 0.10
              else (PALETTE["cat0"] if x <= 0.60 else "#2f8f4f")
              for x in xs]
    ax.scatter(xs, ys, s=sizes, c=colors, alpha=0.55,
               edgecolors="white", linewidths=1.0, zorder=5)

    # Annotate the lowest- and highest-NameRank cohorts.
    HIGHLIGHT = {
        "gpt5_system_card_author":   (0.06, 0.0),
        "mid_tier_yc_company":       (0.04, -0.02),
        "deepseek_v3_author":        (0.03, 0.04),
        "long_tail_researcher_ikp":  (0.03, -0.02),
        "research_paper":            (-0.02, 0.05),
        "mid_tier_filmmaker":        (-0.02, 0.06),
        "cs_faculty":                (0.04, 0.0),
        "long_tail_researcher_openalex": (0.04, -0.02),
        "imo_gold":                  (0.04, 0.0),
    }
    for r in coh:
        c = r["cohort"]
        if c in HIGHLIGHT:
            dx, dy = HIGHLIGHT[c]
            ax.annotate(c.replace("_", " "),
                        xy=(r["mean"], r["refusal_rate"]),
                        xytext=(r["mean"] + dx, r["refusal_rate"] + dy),
                        fontsize=8, color="#333",
                        ha="left" if dx > 0 else "right",
                        arrowprops=dict(arrowstyle="-", color="#999", lw=0.5))

    # Inverse-trend reference (visual).
    ax.text(0.65, 0.96,
            "Refusal almost perfectly inverts\n"
            "NameRank at the cohort level:\n"
            "models honestly refuse rather\nthan fabricate when the entity\n"
            "is below the corpus-presence\nthreshold.",
            transform=ax.transAxes,
            ha="left", va="top", fontsize=9, color="#222",
            bbox=dict(boxstyle="round,pad=0.4",
                      facecolor="white", edgecolor="#ddd", linewidth=0.6))

    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.03, 0.65)
    ax.set_xlabel("Cohort mean NameRank", fontsize=10.5)
    ax.set_ylabel("Cohort refusal rate", fontsize=10.5)
    grid_x(ax, alpha=0.25)
    grid_y(ax, alpha=0.25)
    thin_spines(ax)
    ax.set_title("(a)  Cohort refusal $\\propto$ $-$NameRank.  "
                 "Marker size $\\propto \\sqrt{n}$.",
                 fontsize=10.5, loc="left")

    # ── Panel (b) silent / near-silent / substantive composition ─
    ax = axes[1]
    # Recompute from per_entity to get the full composition, since
    # cohort_summary only has frac_silent.
    by_cohort = defaultdict(list)
    for r in csv.DictReader(open(ANALYSIS / "namerank_per_entity.csv",
                                 encoding="utf-8")):
        by_cohort[r["cohort"]].append(float(r["namerank"]))

    # Pick the 10 lowest-mean cohorts with n >= 10.
    means = []
    for c, vals in by_cohort.items():
        if len(vals) >= 10:
            means.append((c, len(vals), statistics.mean(vals), vals))
    means.sort(key=lambda x: x[2])
    bottom = means[:12]

    cohorts = [c for c, _, _, _ in bottom]
    ns = [n for _, n, _, _ in bottom]
    frac_silent = [sum(1 for v in vals if v <= 0.05) / len(vals)
                   for _, _, _, vals in bottom]
    frac_near   = [sum(1 for v in vals if 0.05 < v <= 0.10) / len(vals)
                   for _, _, _, vals in bottom]
    frac_low    = [sum(1 for v in vals if 0.10 < v <= 0.30) / len(vals)
                   for _, _, _, vals in bottom]
    frac_disc   = [sum(1 for v in vals if 0.30 < v <= 0.60) / len(vals)
                   for _, _, _, vals in bottom]
    frac_high   = [sum(1 for v in vals if v > 0.60) / len(vals)
                   for _, _, _, vals in bottom]

    ys = list(range(len(cohorts)))
    colors_stack = ["#b3322c", "#e09b96",   # silent / near-silent
                    "#f1cba2", "#9ab4d2",   # low disc / mid disc
                    "#7fae90"]              # universal
    labels = ["NR $\\leq 0.05$  (silent)",
              "$0.05 < $ NR $\\leq 0.10$  (near-silent)",
              "$0.10 < $ NR $\\leq 0.30$  (low-disc.)",
              "$0.30 < $ NR $\\leq 0.60$  (mid-disc.)",
              "NR $> 0.60$  (universal)"]
    fracs = [frac_silent, frac_near, frac_low, frac_disc, frac_high]
    left = np.zeros(len(cohorts))
    for fr, c, lbl in zip(fracs, colors_stack, labels):
        ax.barh(ys, fr, left=left, color=c, edgecolor="white",
                linewidth=0.6, height=0.78, label=lbl, zorder=3)
        left = left + np.array(fr)

    ax.set_yticks(ys)
    ax.set_yticklabels([f"{c.replace('_', ' ')}  (n={n})"
                        for c, n in zip(cohorts, ns)], fontsize=9.5)
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("Fraction of probe records in each NameRank band",
                  fontsize=10.5)
    ax.legend(loc="lower right", fontsize=8.0, framealpha=0.95, ncol=2)
    grid_x(ax, alpha=0.25)
    thin_spines(ax)
    ax.set_title("(b)  Composition of the 12 lowest-NameRank cohorts.",
                 fontsize=10.5, loc="left")

    plt.tight_layout()
    out = HERE / "fig_refusal.pdf"
    plt.savefig(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
