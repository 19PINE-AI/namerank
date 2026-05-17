"""Figure 4: Credential treadmill bar chart.

Reads cohort means from data/analysis/credential_ladder.csv plus the two
silent-tier cohorts (gpt5_system_card_author, deepseek_v3_author) and the
long_tail_researcher_openalex baseline from data/analysis/cohort_summary.csv.
"""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from _style import (PALETTE, apply_style, annotate_value, grid_x, thin_spines)

apply_style()

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
ANALYSIS = REPO / "data" / "analysis"

DISPLAY = {
    "International Math Olympiad gold (2005-2015)": "IMO gold (2005--15)",
    "International Olympiad in Informatics gold": "IOI gold (2005--15)",
    "ICPC World Finalist gold": "ICPC World Finalist gold",
    "Putnam top-25 fellow": "Putnam top-25 fellow",
    "China Math Olympiad gold": "CMO China gold",
    "National Olympiad in Informatics China gold": "NOI China gold",
    "China Physics Olympiad first prize": "CPhO China first prize",
    "Rhodes Scholarship recipient": "Rhodes Scholarship",
    "MSRA PhD Fellowship": "MSRA PhD Fellowship",
    "DeepSeek-V3 paper author": "DeepSeek-V3 paper author",
    "GPT-5 system card author": "GPT-5 system-card author",
}


def color_for(mean: float, baseline: float) -> str:
    if mean < 0.10:
        return PALETTE["silent"]
    if mean < 0.25:
        return "#cc4a3a"          # warm orange-red, sub-baseline
    if mean < baseline:
        return PALETTE["highlight"]
    return PALETTE["cat0"]


def main() -> None:
    cohort_summary = {r["cohort"]: r for r in csv.DictReader(
        open(ANALYSIS / "cohort_summary.csv", encoding="utf-8"))}
    baseline_row = cohort_summary["long_tail_researcher_openalex"]
    baseline = float(baseline_row["mean"])
    baseline_n = int(baseline_row["n"])

    creds = []
    for r in csv.DictReader(open(ANALYSIS / "credential_ladder.csv", encoding="utf-8")):
        label = DISPLAY.get(r["credential"], r["credential"])
        creds.append((label, int(r["n"]), float(r["mean"]),
                      color_for(float(r["mean"]), baseline)))

    creds.append(("OpenAlex working researcher",
                  baseline_n, baseline, PALETTE["baseline"]))
    creds.sort(key=lambda x: x[2])

    fig, ax = plt.subplots(figsize=(10.0, 6.8))
    ys = list(range(len(creds)))
    names = [c[0] for c in creds]
    vals = [c[2] for c in creds]
    ns = [c[1] for c in creds]
    colors = [c[3] for c in creds]

    bars = ax.barh(ys, vals, color=colors, edgecolor="white",
                   linewidth=0.6, height=0.72, zorder=3)

    # Baseline rule.
    ax.axvline(baseline, ls="--", color=PALETTE["baseline"], linewidth=1.4,
               zorder=5,
               label=f"OpenAlex working-researcher baseline  ({baseline:.3f})")

    # Per-bar inline value plus baseline-relative delta.
    for i, (v, n, name) in enumerate(zip(vals, ns, names)):
        # Numeric value just past the bar end.
        annotate_value(ax, v, i, f"{v:.3f}", dx=0.008,
                       fontsize=9, color="#222")
        if name != "OpenAlex working researcher":
            delta = v - baseline
            # Baseline-delta annotation, colour-coded by sign.
            dx = 0.064
            color = PALETTE["cat0"] if delta > 0 else PALETTE["silent"]
            ax.text(v + dx, i, f"({delta:+.3f})",
                    va="center", ha="left",
                    fontsize=8.5, color=color, alpha=0.85)

    ax.set_yticks(ys)
    ax.set_yticklabels([f"{n}  (n={k})" for n, k in zip(names, ns)],
                       fontsize=10)
    ax.set_xlabel("Mean NameRank", fontsize=10.5)
    ax.set_xlim(0, max(vals) + 0.22)

    # Annotate the two cohorts that clear baseline.
    above = [(i, n) for i, (n, _, v, _) in enumerate(creds)
             if v > baseline and n != "OpenAlex working researcher"]
    if above:
        idx_top = above[-1][0]
        ax.annotate(
            "Only 2 of 9 prestigious credentials\n"
            "clear the working-researcher baseline",
            xy=(vals[idx_top], idx_top),
            xytext=(vals[idx_top] - 0.32, idx_top - 0.7),
            ha="left", va="top", fontsize=9.5, color="#222",
            arrowprops=dict(arrowstyle="-", color="#888", lw=0.7,
                            connectionstyle="arc3,rad=0.15"),
        )

    n_below = sum(1 for label, _, v, _ in creds
                  if label != "OpenAlex working researcher" and v <= baseline)
    n_cred = len(creds) - 1
    ax.set_title(
        f"The credential treadmill: {n_below} of {n_cred} once-prestigious "
        "intellectual credentials sit at or below the working-researcher baseline.",
        fontsize=10.5, pad=10,
    )
    ax.legend(loc="lower right", fontsize=9.5, framealpha=0.95)
    grid_x(ax, alpha=0.28)
    thin_spines(ax)
    plt.tight_layout()
    out = HERE / "fig4_credentials.pdf"
    plt.savefig(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
