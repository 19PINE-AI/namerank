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

    # The two large-team co-authorship cohorts are shown for context but are
    # NOT credentials; hatch them and exclude them from the "k of 9" count.
    COAUTHOR = {"DeepSeek-V3 paper author", "GPT-5 system-card author"}

    fig, ax = plt.subplots(figsize=(10.0, 6.8))
    ys = list(range(len(creds)))
    names = [c[0] for c in creds]
    vals = [c[2] for c in creds]
    ns = [c[1] for c in creds]
    colors = [c[3] for c in creds]

    hatches = ["////" if n in COAUTHOR else "" for n in names]
    bars = ax.barh(ys, vals, color=colors, edgecolor="white",
                   linewidth=0.6, height=0.72, zorder=3)
    for bar, h in zip(bars, hatches):
        if h:
            bar.set_hatch(h)
            bar.set_edgecolor("white")

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
    ylabels = []
    for n, k in zip(names, ns):
        tag = "  †" if n in COAUTHOR else ""
        ylabels.append(f"{n}  (n={k}){tag}")
    ax.set_yticklabels(ylabels, fontsize=10)
    ax.set_xlabel("Mean NameRank", fontsize=10.5)
    ax.set_xlim(0, max(vals) + 0.24)

    # Bracket the two credentials that clear the baseline, in clear open space
    # to the right of the bars (no crossing leader lines).
    above = [i for i, (n, _, v, _) in enumerate(creds)
             if v > baseline and n != "OpenAlex working researcher"
             and n not in COAUTHOR]
    if above:
        y_lo, y_hi = min(above), max(above)
        x_br = max(vals[i] for i in above) + 0.085
        ax.plot([x_br, x_br], [y_lo - 0.34, y_hi + 0.34],
                color="#555", lw=1.0, zorder=6)
        for yy in (y_lo - 0.34, y_hi + 0.34):
            ax.plot([x_br - 0.012, x_br], [yy, yy], color="#555", lw=1.0, zorder=6)
        ax.text(x_br + 0.018, 0.5 * (y_lo + y_hi),
                "only ICPC and Putnam\nclear the baseline\n(2 of 9 credentials)",
                ha="left", va="center", fontsize=9.0, color="#333")

    n_below = sum(1 for label, _, v, _ in creds
                  if label not in COAUTHOR
                  and label != "OpenAlex working researcher" and v <= baseline)
    n_cred = sum(1 for label, _, _, _ in creds
                 if label not in COAUTHOR and label != "OpenAlex working researcher")
    ax.set_title(
        f"The credential treadmill: {n_below} of {n_cred} once-prestigious "
        "credentials sit at or below the working-researcher baseline.",
        fontsize=10.5, pad=10,
    )
    handles, labs = ax.get_legend_handles_labels()
    from matplotlib.patches import Patch
    handles.append(Patch(facecolor="#bbb", edgecolor="white", hatch="////",
                         label="† large-team co-authorship cohort (not a credential)"))
    ax.legend(handles=handles, loc="lower right", fontsize=9.0, framealpha=0.95)
    grid_x(ax, alpha=0.28)
    thin_spines(ax)
    plt.tight_layout()
    out = HERE / "fig4_credentials.pdf"
    plt.savefig(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
