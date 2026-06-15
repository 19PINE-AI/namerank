"""Figure: Cross-judge robustness (T2.10).

Re-judges a 615-record stratified sample with Claude and GPT-5 alongside the
primary Gemini judge.

(a) Cohort-mean NameRank under each of the three judges: the cohort ordering
    is invariant, so the headline findings are not a Gemini-judge artifact.
(b) Capability-controlled in-family residual lift: each judge's deviation
    from the other two judges' mean on the same response, for own-family vs
    other-family responses. Gemini and GPT-5 modestly favor their own family;
    Claude does not.

Reads experiments/t2_10_cross_judge/{cohort_means_per_judge.csv,
family_bias_residual.csv,cross_judge_correlation.csv}.
"""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from _style import PALETTE, apply_style, grid_x, grid_y, thin_spines

apply_style()

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
T210 = REPO / "experiments" / "t2_10_cross_judge"

JUDGES = [("mean_gemini", "Gemini (primary)", PALETTE["cat4"]),
          ("mean_claude", "Claude", PALETTE["discriminative"]),
          ("mean_gpt5", "GPT-5", PALETTE["universal"])]
CDISP = {
    "long_tail_researcher_openalex": "OpenAlex researcher",
    "mid_tier_writer": "writer",
    "oss_project": "OSS project",
    "cs_faculty": "CS faculty",
    "imo_gold": "IMO gold",
    "reference_pilot": "reference pilot",
    "gpt5_system_card_author": "GPT-5 sys-card author",
}


def main() -> None:
    rows = list(csv.DictReader(open(T210 / "cohort_means_per_judge.csv")))
    # order by Gemini mean (matches paper ladder)
    rows.sort(key=lambda r: -float(r["mean_gemini"]))
    resid = {r["judge"]: r for r in csv.DictReader(
        open(T210 / "family_bias_residual.csv"))}
    corr = {r["subset"]: r for r in csv.DictReader(
        open(T210 / "cross_judge_correlation.csv"))}

    fig, (axa, axb) = plt.subplots(1, 2, figsize=(11.0, 4.4),
                                   gridspec_kw={"width_ratios": [1.4, 1.0]})

    # ── (a) cohort means under three judges ──
    ys = list(range(len(rows)))[::-1]
    for key, label, color in JUDGES:
        xs = [float(r[key]) for r in rows]
        axa.plot(xs, ys, marker="o", markersize=5, linewidth=1.1, color=color,
                 label=label, alpha=0.9, zorder=3)
    axa.set_yticks(ys)
    axa.set_yticklabels([CDISP[r["cohort"]] for r in rows], fontsize=9.2)
    axa.set_xlabel("Cohort-mean NameRank")
    axa.set_xlim(0, 0.8)
    pe = corr["ALL"]
    axa.set_title("(a) Cohort ladder preserved across judges\n"
                  f"(pairwise Pearson {min(float(pe['pearson_gem_claude']),float(pe['pearson_gem_gpt5']),float(pe['pearson_claude_gpt5'])):.2f}"
                  f"--{max(float(pe['pearson_gem_claude']),float(pe['pearson_gem_gpt5']),float(pe['pearson_claude_gpt5'])):.2f})",
                  fontsize=9.8)
    axa.legend(loc="lower right", fontsize=8.5, framealpha=0.95)
    grid_x(axa, alpha=0.25)
    thin_spines(axa)

    # ── (b) in-family residual lift ──
    order = ["gemini", "gpt5", "claude"]
    disp = {"gemini": "Gemini", "gpt5": "GPT-5", "claude": "Claude"}
    lifts = [float(resid[j]["lift"]) for j in order]
    colors = [PALETTE["silent"] if l > 0.02 else PALETTE["baseline"] for l in lifts]
    xs = range(len(order))
    axb.bar(xs, lifts, color=colors, edgecolor="white", width=0.6, zorder=3)
    axb.axhline(0, color=PALETTE["rule"], lw=0.8)
    for i, l in enumerate(lifts):
        axb.text(i, l + (0.002 if l >= 0 else -0.002), f"{l:+.2f}",
                 ha="center", va="bottom" if l >= 0 else "top", fontsize=9)
    axb.set_xticks(list(xs))
    axb.set_xticklabels([disp[j] for j in order])
    axb.set_ylabel("In-family residual lift")
    axb.set_ylim(-0.03, 0.08)
    axb.set_title("(b) Capability-controlled own-family lift:\n"
                  "Gemini/GPT-5 modest, Claude clean", fontsize=9.8)
    grid_y(axb, alpha=0.25)
    thin_spines(axb)

    plt.tight_layout()
    out = HERE / "fig_cross_judge.pdf"
    plt.savefig(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
