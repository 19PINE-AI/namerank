"""Figure: mid/late-career award ladder + the lifetime (award-year) effect.

Reads the t5_1 award-ladder experiment outputs:
  experiments/t5_1_award_ladder/outputs/cohort_summary.csv     (panel a)
  experiments/t5_1_award_ladder/outputs/award_namerank.csv     (panel b)

(a) Extended credential ladder: the eight award cohorts plus the in-run
    OpenAlex baseline and IMO-gold anchor, coloured by career stage, showing
    that the three marquee late-career awards invert the credential treadmill.
(b) The lifetime signal: for the singular marquee awards, older laureates
    score HIGHER (recognition keeps accumulating decades after the award).
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
OUT = REPO / "experiments" / "t5_1_award_ladder" / "outputs"

DISPLAY = {
    "nobel_physics": "Nobel Prize in Physics",
    "turing_award": "Turing Award",
    "fields_medal": "Fields Medal",
    "acm_prize_computing": "ACM Prize in Computing",
    "sloan_fellow": "Sloan Research Fellowship",
    "long_tail_researcher_openalex": "OpenAlex working researcher",
    "acm_fellow": "ACM Fellow",
    "godel_prize": "Gödel Prize",
    "macarthur_fellow": "MacArthur Fellowship",
    "imo_gold": "IMO gold (early credential)",
}
STAGE_COLOR = {"late": PALETTE["universal"], "mid": PALETTE["highlight"],
               "early": PALETTE["cat4"], "None": PALETTE["baseline"]}
MARQUEE = {"nobel_physics", "turing_award", "fields_medal"}
LADDER = list(DISPLAY)


def load_cohorts():
    rows = {r["cohort"]: r for r in csv.DictReader(
        open(OUT / "cohort_summary.csv", encoding="utf-8"))}
    return rows


def panel_ladder(ax, rows):
    baseline = float(rows["long_tail_researcher_openalex"]["mean"])
    items = []
    for cid in LADDER:
        r = rows[cid]
        items.append((DISPLAY[cid], cid, int(r["n"]), float(r["mean"]),
                      float(r["sem"]) if r["sem"] else 0.0,
                      r["career_stage"]))
    items.sort(key=lambda x: x[3])
    ys = range(len(items))
    for i, (name, cid, n, mean, sem, stage) in zip(ys, items):
        is_base = cid == "long_tail_researcher_openalex"
        color = PALETTE["baseline"] if is_base else STAGE_COLOR[stage]
        ax.barh(i, mean, color=color, edgecolor="white", linewidth=0.6,
                height=0.70, zorder=3,
                hatch="////" if cid == "imo_gold" else "")
        ax.errorbar(mean, i, xerr=sem, fmt="none", ecolor="#444",
                    elinewidth=0.9, capsize=2.4, zorder=6)
        delta = mean - baseline
        dcol = PALETTE["universal"] if delta > 0.001 else (
            PALETTE["silent"] if delta < -0.001 else "#666")
        txt = f"{mean:.3f}" if is_base else f"{mean:.3f}  ({delta:+.3f})"
        ax.text(mean + sem + 0.012, i, txt, va="center", ha="left",
                fontsize=8.6, color=dcol, zorder=8)
    ax.axvline(baseline, ls="--", color=PALETTE["baseline"], lw=1.4, zorder=5,
               label=f"OpenAlex working-researcher baseline ({baseline:.3f})")
    ax.set_yticks(list(ys))
    ax.set_yticklabels([f"{name}  (n={n})" for name, _, n, _, _, _ in items],
                       fontsize=9.3)
    ax.set_xlabel("Mean NameRank")
    ax.set_xlim(0, 0.92)
    from matplotlib.patches import Patch
    handles = [
        Patch(facecolor=STAGE_COLOR["late"], label="late-career award"),
        Patch(facecolor=STAGE_COLOR["mid"], label="mid-career honour"),
        Patch(facecolor=STAGE_COLOR["early"], label="early-career fellowship"),
        Patch(facecolor=PALETTE["baseline"], hatch="////",
              edgecolor="white", label="IMO gold (early credential, main run)"),
    ]
    h2, _ = ax.get_legend_handles_labels()
    ax.set_title("(a)  Marquee late-career awards invert the credential treadmill",
                 fontsize=10.2)
    grid_x(ax, alpha=0.28)
    thin_spines(ax)
    # Legend is placed outside the axes (below panel a) in main().
    return h2 + handles


def panel_lifetime(ax, rows):
    recs = list(csv.DictReader(open(OUT / "award_namerank.csv", encoding="utf-8")))
    PROBE_YEAR = 2026
    # Standardize NameRank within each marquee award, then pool: isolates the
    # post-award accumulation from each award's own level and year-span.
    by = {}
    for r in recs:
        if r["cohort"] in MARQUEE and r["award_year"] not in ("", "None"):
            by.setdefault(r["cohort"], []).append(
                (PROBE_YEAR - int(r["award_year"]), float(r["namerank"])))
    xs, zs = [], []
    for pts in by.values():
        v = np.array([p[1] for p in pts]); m, sd = v.mean(), v.std()
        for age, nr in pts:
            xs.append(age); zs.append((nr - m) / sd)
    xs = np.array(xs, float); zs = np.array(zs)
    edges = [0, 10, 20, 30, 40, 100]
    labels = ["0–10", "10–20", "20–30", "30–40", "40+"]
    means, ns = [], []
    for lo, hi in zip(edges, edges[1:]):
        sel = zs[(xs >= lo) & (xs < hi)]
        means.append(sel.mean() if len(sel) else 0.0)
        ns.append(len(sel))
    xpos = np.arange(len(labels))
    cols = [PALETTE["silent"] if m < 0 else PALETTE["universal"] for m in means]
    ax.bar(xpos, means, color=cols, edgecolor="white", linewidth=0.7,
           width=0.72, zorder=3)
    ax.axhline(0, color=PALETTE["baseline"], lw=1.0, zorder=4)
    for i, (m, n) in enumerate(zip(means, ns)):
        va = "bottom" if m >= 0 else "top"
        off = 0.03 if m >= 0 else -0.03
        ax.text(i, m + off, f"{m:+.2f}\n(n={n})", ha="center", va=va,
                fontsize=8.3, color="#333")
    r = np.corrcoef(xs, zs)[0, 1]
    ax.text(0.5, 0.97,
            f"pooled corr = {r:+.2f}: recognition keeps\n"
            "accumulating for ~30 years after the award",
            transform=ax.transAxes, fontsize=8.5, va="top", ha="center",
            color="#333",
            bbox=dict(facecolor="white", edgecolor="#ccc", boxstyle="round,pad=0.4"))
    ax.set_xticks(xpos); ax.set_xticklabels(labels)
    ax.set_xlabel("Years since award")
    ax.set_ylabel("NameRank, standardized within award")
    ax.set_ylim(-0.75, 0.6)
    ax.set_title("(b)  The lifetime signal (Nobel, Turing, Fields)", fontsize=10.2)
    grid_y(ax, alpha=0.28)
    thin_spines(ax)


def main():
    rows = load_cohorts()
    fig, axes = plt.subplots(1, 2, figsize=(13.0, 5.8),
                             gridspec_kw={"width_ratios": [1.55, 1.0]})
    ladder_handles = panel_ladder(axes[0], rows)
    panel_lifetime(axes[1], rows)
    plt.tight_layout(w_pad=2.0, rect=(0, 0.11, 1, 1))
    # Legend outside the plot area, below panel (a), spanning its width.
    axes[0].legend(handles=ladder_handles, loc="upper center",
                   bbox_to_anchor=(0.5, -0.14), ncol=3, fontsize=8.4,
                   framealpha=0.96, columnspacing=1.4, handlelength=1.6,
                   borderaxespad=0.0)
    out = HERE / "fig_awards.pdf"
    plt.savefig(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
