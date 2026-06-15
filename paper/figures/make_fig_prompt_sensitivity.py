"""Figure: Prompt-paraphrase sensitivity of the panel-mean NameRank (T2.6).

(a) Cohort-mean NameRank under the original probe (T0) and three paraphrases
    (T1/T2/T3). The cohort ordering is preserved, but T0 sits systematically
    higher -- the absolute level is wording-specific.
(b) Variance decomposition over the 29,600 records: template is the smallest
    main effect (1.78%) and the panel mean across templates is 24x more
    stable than a single model at one template.

Reads experiments/t2_6_prompt_sensitivity/{cohort_means_per_template.csv,
variance_decomposition.csv,summary.json}.
"""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from _style import PALETTE, apply_style, grid_x, grid_y, thin_spines

apply_style()

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
T26 = REPO / "experiments" / "t2_6_prompt_sensitivity"

DISP = {
    "mid_tier_filmmaker": "filmmaker",
    "mid_tier_writer": "writer",
    "research_paper": "research paper",
    "oss_project": "OSS project",
    "long_tail_researcher_openalex": "OpenAlex researcher",
    "cs_faculty": "CS faculty",
    "imo_gold": "IMO gold",
    "gpt5_system_card_author": "GPT-5 sys-card author",
}
TEMPLATES = ["T0", "T1", "T2", "T3"]
TCOLOR = {"T0": PALETTE["highlight"], "T1": PALETTE["discriminative"],
          "T2": PALETTE["cat4"], "T3": PALETTE["universal"]}
TLABEL = {"T0": "T0 (original)", "T1": "T1 paraphrase",
          "T2": "T2 paraphrase", "T3": "T3 paraphrase"}


def main() -> None:
    cm = {r["cohort"]: r for r in csv.DictReader(
        open(T26 / "cohort_means_per_template.csv"))}
    var = {r["factor"]: r for r in csv.DictReader(
        open(T26 / "variance_decomposition.csv"))}
    summary = json.loads((T26 / "summary.json").read_text())

    # order cohorts by T0
    cohorts = sorted(DISP, key=lambda c: -float(cm[c]["NR_T0"]))

    fig, (axa, axb) = plt.subplots(1, 2, figsize=(11.0, 4.6),
                                   gridspec_kw={"width_ratios": [1.45, 1.0]})

    # ── (a) cohort means per template ──
    ys = list(range(len(cohorts)))[::-1]
    for t in TEMPLATES:
        xs = [float(cm[c][f"NR_{t}"]) for c in cohorts]
        axa.plot(xs, ys, marker="o", markersize=5, linewidth=1.1,
                 color=TCOLOR[t], label=TLABEL[t], alpha=0.9, zorder=3)
    axa.set_yticks(ys)
    axa.set_yticklabels([DISP[c] for c in cohorts], fontsize=9.2)
    axa.set_xlabel("Cohort-mean NameRank")
    axa.set_xlim(0, 0.85)
    axa.set_title("(a) Ordering preserved under paraphrase;\noriginal probe (T0) "
                  "sits systematically higher", fontsize=10.0)
    axa.legend(loc="lower right", fontsize=8.3, framealpha=0.95)
    grid_x(axa, alpha=0.25)
    thin_spines(axa)

    # ── (b) variance decomposition ──
    factors = [("entity", "entity"), ("model", "model"),
               ("cohort", "cohort"), ("template", "template")]
    labels = [f[1] for f in factors]
    pcts = [float(var[f[0]]["pct_of_total"]) for f in factors]
    colors = [PALETTE["discriminative"], PALETTE["cat4"], PALETTE["baseline"],
              PALETTE["highlight"]]
    bars = axb.bar(range(len(labels)), pcts, color=colors, edgecolor="white",
                   width=0.66, zorder=3)
    for i, p in enumerate(pcts):
        axb.text(i, p + 0.6, f"{p:.1f}%", ha="center", va="bottom", fontsize=9)
    axb.set_xticks(range(len(labels)))
    axb.set_xticklabels(labels, fontsize=9.2)
    axb.set_ylabel("% of total sum of squares")
    axb.set_ylim(0, max(pcts) + 6)
    axb.set_title("(b) Template is the smallest main effect (1.8%)",
                  fontsize=10.0)
    # annotate panel-mean stability
    ratio = summary["variance_ratio_panel_to_cross_model"]["median_b_over_a"]
    pe = summary["pairwise_pearson_panel_mean_NR"]
    rmin = min(pe.values())
    rmax = max(pe.values())
    axb.text(0.5, 0.80,
             f"panel-mean NR across templates:\n"
             f"pairwise Pearson {rmin:.2f}-{rmax:.2f}\n"
             f"variance {ratio*100:.0f}% of single-model\n(24$\\times$ more stable)",
             transform=axb.transAxes, ha="center", va="top", fontsize=8.2,
             bbox=dict(boxstyle="round,pad=0.4", fc=PALETTE["bg"],
                       ec="#cccccc", lw=0.6))
    grid_y(axb, alpha=0.25)
    thin_spines(axb)

    plt.tight_layout()
    out = HERE / "fig_prompt_sensitivity.pdf"
    plt.savefig(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
