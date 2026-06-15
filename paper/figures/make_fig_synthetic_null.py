"""Figure: Synthetic-null floor (T1.3).

30 entirely fictional entities (ungoogleable names, cohort-matched contexts and
gold answers) run through the full pipeline establish the score a name absent
from any pretraining corpus receives.

(a) Synthetic floor by archetype: dense-gold cohorts (founder, CS faculty)
    floor near ~0.04; the short-boilerplate-gold IMO archetype floors near
    ~0.20, because generic year+country+medal golds admit context-prior
    leakage.
(b) Per-model synthetic floor: it is concentrated in small open-weights fluent
    hallucinators (gemma-3-4b at 0.29); ~16 of 37 models score exactly 0.

Reads experiments/t1_3_synthetic_null/{synthetic_namerank_per_entity.csv,
per_model_breakdown.csv}.
"""
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from _style import PALETTE, apply_style, grid_x, grid_y, thin_spines

apply_style()

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
T13 = REPO / "experiments" / "t1_3_synthetic_null"

CDISP = {
    "synthetic_imo_gold": "IMO gold (short gold)",
    "synthetic_mid_tier_chef": "chef",
    "synthetic_mid_tier_journalist": "journalist",
    "synthetic_mid_tier_podcast": "podcast",
    "synthetic_oss_project": "OSS project",
    "synthetic_mid_tier_musician": "musician",
    "synthetic_cs_faculty": "CS faculty",
    "synthetic_founder": "founder",
}


def main() -> None:
    rows = list(csv.DictReader(open(T13 / "synthetic_namerank_per_entity.csv")))
    by_c = defaultdict(list)
    for r in rows:
        by_c[r["cohort"]].append(float(r["namerank"]))
    cohorts = sorted(by_c, key=lambda c: sum(by_c[c]) / len(by_c[c]))
    means = [sum(by_c[c]) / len(by_c[c]) for c in cohorts]

    models = list(csv.DictReader(open(T13 / "per_model_breakdown.csv")))
    models.sort(key=lambda r: float(r["mean_namerank"]))

    fig, (axa, axb) = plt.subplots(1, 2, figsize=(11.0, 4.5),
                                   gridspec_kw={"width_ratios": [1.0, 1.25]})

    # ── (a) floor by archetype ──
    ys = range(len(cohorts))
    colors = [PALETTE["silent"] if c == "synthetic_imo_gold"
              else PALETTE["baseline"] for c in cohorts]
    axa.barh(list(ys), means, color=colors, edgecolor="white", height=0.66,
             zorder=3)
    for y, m in zip(ys, means):
        axa.text(m + 0.004, y, f"{m:.3f}", va="center", ha="left", fontsize=8.5)
    axa.axvline(0.04, ls="--", color=PALETTE["discriminative"], lw=1.2,
                label="dense-gold floor $\\approx 0.04$")
    axa.axvline(0.20, ls=":", color=PALETTE["silent"], lw=1.2,
                label="short-gold floor $\\approx 0.20$")
    axa.set_yticks(list(ys))
    axa.set_yticklabels([CDISP[c] for c in cohorts], fontsize=9)
    axa.set_xlabel("Synthetic-null NameRank")
    axa.set_xlim(0, 0.27)
    axa.set_title("(a) Floor by archetype: short-boilerplate\n"
                  "gold answers admit more leakage", fontsize=9.8)
    axa.legend(loc="lower right", fontsize=8.0, framealpha=0.95)
    grid_x(axa, alpha=0.25)
    thin_spines(axa)

    # ── (b) per-model floor ──
    mvals = [float(m["mean_namerank"]) for m in models]
    mids = [m["model_id"] for m in models]
    n_zero = sum(1 for v in mvals if v == 0)
    xs = range(len(models))
    bcolors = [PALETTE["silent"] if v >= 0.20 else
               (PALETTE["highlight"] if v >= 0.08 else PALETTE["baseline"])
               for v in mvals]
    axb.bar(list(xs), mvals, color=bcolors, edgecolor="white", width=0.82,
            zorder=3)
    axb.set_xlim(-0.7, len(models) - 0.3)
    axb.set_ylim(0, 0.32)
    axb.set_xlabel("Panel model (sorted)")
    axb.set_ylabel("Mean synthetic-null NameRank")
    # label the top offenders
    for i, (v, mid) in enumerate(zip(mvals, mids)):
        if v >= 0.25:
            axb.text(i, v + 0.005, mid, rotation=90, va="bottom", ha="center",
                     fontsize=7, color="#444")
    axb.annotate(f"{n_zero} of 37 models\nscore exactly 0",
                 xy=(4, 0.0), xytext=(6, 0.13), fontsize=8.3, color="#444",
                 arrowprops=dict(arrowstyle="-", color="#999", lw=0.7))
    axb.set_title("(b) Floor concentrated in small open-weights\n"
                  "fluent hallucinators", fontsize=9.8)
    axb.set_xticks([])
    grid_y(axb, alpha=0.25)
    thin_spines(axb)

    plt.tight_layout()
    out = HERE / "fig_synthetic_null.pdf"
    plt.savefig(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
