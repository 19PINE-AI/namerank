"""Figure 4: Credential treadmill bar chart.

Reads cohort means from data/analysis/credential_ladder.csv plus the two
silent-tier cohorts (gpt5_system_card_author, deepseek_v3_author) and the
long_tail_researcher_openalex baseline from data/analysis/cohort_summary.csv.
"""
import csv
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
ANALYSIS = REPO / "data" / "analysis"

# Map credential_ladder.csv -> figure label (paper convention).
DISPLAY = {
    "International Math Olympiad gold (2005-2015)": "IMO gold (2005-15)",
    "International Olympiad in Informatics gold": "IOI gold (2005-15)",
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
    if mean < 0.1:
        return "#7f0000"
    if mean < 0.25:
        return "#d62728"
    if mean < baseline:
        return "#ff7f0e"
    return "#1f77b4"


def main() -> None:
    cohort_summary = {r["cohort"]: r for r in csv.DictReader(
        open(ANALYSIS / "cohort_summary.csv", encoding="utf-8"))}
    baseline_row = cohort_summary["long_tail_researcher_openalex"]
    baseline = float(baseline_row["mean"])
    baseline_n = int(baseline_row["n"])

    credentials = []
    for r in csv.DictReader(open(ANALYSIS / "credential_ladder.csv", encoding="utf-8")):
        label = DISPLAY.get(r["credential"], r["credential"])
        credentials.append((label, int(r["n"]), float(r["mean"]), color_for(float(r["mean"]), baseline)))

    credentials.append(("OpenAlex working researcher", baseline_n, baseline, "#aaaaaa"))
    credentials.sort(key=lambda x: x[2])

    fig, ax = plt.subplots(figsize=(9, 6.5))
    ys = list(range(len(credentials)))
    names = [c[0] for c in credentials]
    vals = [c[2] for c in credentials]
    ns = [c[1] for c in credentials]
    colors = [c[3] for c in credentials]

    ax.barh(ys, vals, color=colors, edgecolor='black', linewidth=0.6)
    ax.set_yticks(ys)
    ax.set_yticklabels([f"{n} (n={k})" for n, k in zip(names, ns)], fontsize=10)
    ax.axvline(baseline, ls='--', color='#888', linewidth=1.5,
               label=f'OpenAlex working-researcher baseline ({baseline:.3f})')

    for i, v in enumerate(vals):
        ax.text(v + 0.008, i, f"{v:.3f}", va='center', fontsize=9)

    ax.set_xlabel("Mean NameRank", fontsize=11)
    ax.set_xlim(0, max(vals) + 0.10)
    ax.legend(loc='lower right', fontsize=10, framealpha=0.92)
    n_below = sum(1 for label, _, v, _ in credentials
                  if label != "OpenAlex working researcher" and v <= baseline)
    n_cred = len(credentials) - 1
    ax.set_title(f"The credential treadmill: {n_below} of {n_cred} once-prestigious intellectual credentials\n"
                 "sit at or below the working-researcher NameRank baseline.",
                 fontsize=10.5)
    ax.grid(True, axis='x', alpha=0.3)
    plt.tight_layout()
    out = HERE / "fig4_credentials.pdf"
    plt.savefig(out, bbox_inches="tight")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
