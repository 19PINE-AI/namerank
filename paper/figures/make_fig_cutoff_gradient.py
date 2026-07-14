"""Figure: Training-cutoff gradient (T3.1).

(a) Per-model mean NameRank vs training cutoff for the two first-appearance
    "recency" cohorts and two stable controls. Every cohort -- including ones
    nameable since well before any cutoff -- rises with cutoff: this is a
    model-capability/generosity confound, not corpus timing.
(b) Natural experiment: pre/post-emergence recognition for the two recency
    cohorts vs the same-split jump on the stable controls. The matched
    difference-in-differences is ~0: crossing the cutoff is necessary but not
    sufficient for recognition.

Reads experiments/t3_1_cutoff_gradient/outputs/{per_model_cohort_means.csv,
natural_experiment.csv,summary.json}.
"""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from _style import PALETTE, apply_style, grid_y, thin_spines

apply_style()

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
T31 = REPO / "experiments" / "t3_1_cutoff_gradient" / "outputs"

# Cohorts to plot in panel (a): two recency + two stable controls.
SERIES = [
    ("deepseek_v3_author",      "DeepSeek-V3 authors (emergence 2024-12)", PALETTE["silent"],   "o"),
    ("gpt5_system_card_author", "GPT-5 system-card authors (2025-08)",     PALETTE["highlight"], "s"),
    ("cs_faculty",              "CS faculty (control, pre-2023)",          PALETTE["discriminative"], "^"),
    ("reference_pilot",         "reference pilot (control: Hinton, ...)",  PALETTE["universal"], "D"),
]
EMERGENCE = {"deepseek_v3_author": "2024-12", "gpt5_system_card_author": "2025-08"}


def ym_to_month(ym):
    y, m = ym.split("-")
    return (int(y) - 2000) * 12 + (int(m) - 1)


def ols(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    return slope, my - slope * mx


def main() -> None:
    rows = list(csv.DictReader(open(T31 / "per_model_cohort_means.csv")))
    summary = json.loads((T31 / "summary.json").read_text())
    natexp = {r["cohort"]: {} for r in csv.DictReader(open(T31 / "natural_experiment.csv"))}
    for r in csv.DictReader(open(T31 / "natural_experiment.csv")):
        natexp.setdefault(r["cohort"], {})[r["group"]] = r

    by_cohort = {}
    for r in rows:
        by_cohort.setdefault(r["cohort"], []).append(
            (ym_to_month(r["cutoff"]), float(r["mean_score"])))

    fig, (axa, axb) = plt.subplots(1, 2, figsize=(11.0, 4.5),
                                   gridspec_kw={"width_ratios": [1.35, 1.0]})

    # ── (a) recognition vs cutoff ──
    xmin = ym_to_month("2023-08")
    xmax = ym_to_month("2026-05")
    for coh, label, color, marker in SERIES:
        pts = sorted(by_cohort[coh])
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        axa.scatter(xs, ys, s=26, color=color, marker=marker, alpha=0.7,
                    edgecolor="white", linewidth=0.4, zorder=3)
        slope, intc = ols(xs, ys)
        xx = [xmin, xmax]
        axa.plot(xx, [slope * x + intc for x in xx], color=color,
                 linewidth=1.6, zorder=2,
                 label=f"{label}  ({slope*12:+.2f}/yr)")
    # emergence verticals, labelled above the axes so the labels never
    # collide with the scatter or the legend
    for coh, ym in EMERGENCE.items():
        m = ym_to_month(ym)
        axa.axvline(m, ls=":", color="#999", linewidth=1.0, zorder=1)
        axa.annotate(f"emergence {ym}", xy=(m, 1.0), xycoords=("data", "axes fraction"),
                     xytext=(0, 3), textcoords="offset points",
                     ha="center", va="bottom", fontsize=7.3, color="#777")
    # x ticks as year labels
    ticks = [ym_to_month(f"{y}-01") for y in (2024, 2025, 2026)]
    axa.set_xticks(ticks)
    axa.set_xticklabels(["2024", "2025", "2026"])
    axa.set_xlim(xmin, xmax)
    axa.set_ylim(0, 0.8)
    axa.set_xlabel("Model training cutoff")
    axa.set_ylabel("Per-model mean NameRank")
    axa.set_title("(a) Every cohort rises with cutoff: capability drift, not corpus timing",
                  fontsize=10.0, pad=16)
    axa.legend(loc="upper left", fontsize=7.6, framealpha=0.95)
    grid_y(axa, alpha=0.25)
    thin_spines(axa)

    # ── (b) natural experiment + matched DiD ──
    did = summary["matched_did"]
    cohorts_b = ["deepseek_v3_author", "gpt5_system_card_author"]
    disp = {"deepseek_v3_author": "DeepSeek-V3\nauthors\n(@2024-12)",
            "gpt5_system_card_author": "GPT-5 system-card\nauthors\n(@2025-08)"}
    x = range(len(cohorts_b))
    w = 0.26
    pre_vals = [float(natexp[c]["pre"]["mean_score"]) for c in cohorts_b]
    post_vals = [float(natexp[c]["post"]["mean_score"]) for c in cohorts_b]
    ctrl_jump = [did[c]["control_jump_mean"] for c in cohorts_b]
    # bars: pre, post, and a "pre + control jump" expectation marker
    b1 = axb.bar([i - w for i in x], pre_vals, width=w, color="#b8c4d0",
                 edgecolor="white", label="pre-cutoff models", zorder=3)
    b2 = axb.bar([i for i in x], post_vals, width=w, color=PALETTE["discriminative"],
                 edgecolor="white", label="post-cutoff models", zorder=3)
    exp_vals = [pre_vals[i] + ctrl_jump[i] for i in range(len(cohorts_b))]
    axb.bar([i + w for i in x], exp_vals, width=w, color="none",
            edgecolor=PALETTE["highlight"], linewidth=1.6, hatch="///",
            label="pre + control-cohort drift\n(capability-only expectation)", zorder=3)

    for i, c in enumerate(cohorts_b):
        axb.text(i - w, pre_vals[i] + 0.006, f"{pre_vals[i]:.2f}",
                 ha="center", va="bottom", fontsize=8)
        axb.text(i, post_vals[i] + 0.006, f"{post_vals[i]:.2f}",
                 ha="center", va="bottom", fontsize=8)
        axb.text(i, max(post_vals[i], exp_vals[i]) + 0.045,
                 f"matched DiD\n{did[c]['matched_did']:+.3f}",
                 ha="center", va="bottom", fontsize=8.2,
                 color=PALETTE["silent"], fontweight="bold")
    axb.set_xticks(list(x))
    axb.set_xticklabels([disp[c] for c in cohorts_b], fontsize=8.5)
    axb.set_ylim(0, max(0.42, max(exp_vals) + 0.06))
    axb.set_ylabel("Mean NameRank")
    axb.set_title("(b) Crossing the cutoff $\\neq$ recognition:\nrecency cohorts fall short of capability drift (DiD $<0$)",
                  fontsize=10.0)
    axb.legend(loc="upper right", fontsize=7.4, framealpha=0.95)
    grid_y(axb, alpha=0.25)
    thin_spines(axb)

    plt.tight_layout()
    out = HERE / "fig_cutoff_gradient.pdf"
    plt.savefig(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
