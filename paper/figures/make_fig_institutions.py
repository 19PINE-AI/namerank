"""CS faculty NameRank by institution.

Bar chart over the 15 institutions with $\\geq 4$ sampled faculty (matches
the table in §6.6.2). Bars are split visually by country group so the
Stanford / Tsinghua spread is reinforced by colour, not just height.
"""
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from _style import PALETTE, apply_style, annotate_value, grid_x, thin_spines

apply_style()

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent

# Hand-assigned country grouping (only institutions appearing in the chart).
COUNTRY = {
    "Stanford University":              "USA",
    "University of Washington":         "USA",
    "Cornell University":               "USA",
    "Carnegie Mellon University":       "USA",
    "Princeton University":             "USA",
    "Johns Hopkins University":         "USA",
    "University of Michigan":           "USA",
    "Georgia Institute of Technology":  "USA",
    "Univ. of Illinois at Urbana-Champaign": "USA",
    "HKUST":                            "Hong Kong",
    "TU Delft":                         "Netherlands",
    "Universidade de Lisboa":           "Portugal",
    "Peking University":                "China",
    "Tsinghua University":              "China",
    "USTC":                             "China",
    "Wuhan University":                 "China",
    "University of A Coruña":           "Spain",
    "Univ. of A Coruna":                "Spain",   # ASCII fallback if used
    "UFRGS":                            "Brazil",
    "Monash University":                "Australia",
}

COUNTRY_COLOR = {
    "USA":          PALETTE["baseline"],
    "Hong Kong":    "#0f9aa8",
    "Netherlands":  "#2a6fb5",
    "Portugal":     "#2a6fb5",
    "China":        "#b3322c",
    "Spain":        "#7a5dad",
    "Brazil":       "#9b6a3a",
    "Australia":    "#2f8f4f",
}


def main() -> None:
    ents = {e["id"]: e for e in json.loads(
        (REPO / "data/inputs/pilot_entities.json").read_text())}
    nr = {row["entity_id"]: float(row["namerank"]) for row in csv.DictReader(
        open(REPO / "data/analysis/namerank_per_entity.csv", encoding="utf-8"))}

    by_inst: dict[str, list[float]] = defaultdict(list)
    for eid, e in ents.items():
        if e.get("cohort") != "cs_faculty":
            continue
        if eid not in nr:
            continue
        inst = e.get("institution") or "Unknown"
        by_inst[inst].append(nr[eid])

    # Substitute display labels for any names containing non-ASCII that won't
    # round-trip through matplotlib's CM-serif font.
    DISPLAY = {"University of A Coruña": "Univ. of A Coruna"}
    rows = [(DISPLAY.get(inst, inst), len(scores), statistics.mean(scores))
            for inst, scores in by_inst.items()
            if len(scores) >= 4 and inst in COUNTRY]
    rows.sort(key=lambda x: x[2])

    fig, ax = plt.subplots(figsize=(10.6, 6.8))
    ys = list(range(len(rows)))
    names = [r[0] for r in rows]
    ns = [r[1] for r in rows]
    vals = [r[2] for r in rows]
    colors = [COUNTRY_COLOR[COUNTRY[name]] for name in names]

    ax.barh(ys, vals, color=colors, edgecolor="white",
            linewidth=0.6, height=0.72, zorder=3, alpha=0.92)

    # Per-bar numeric label.
    for i, v in enumerate(vals):
        annotate_value(ax, v, i, f"{v:.3f}", dx=0.006,
                       fontsize=9, color="#222")

    # Reference rule: USA-mean (Stanford set) as a stand-in for top-US cluster.
    usa_vals = [v for name, _, v in rows if COUNTRY[name] == "USA"]
    if usa_vals:
        usa_mean = statistics.mean(usa_vals)
        ax.axvline(usa_mean, ls="--", color=PALETTE["baseline"],
                   linewidth=1.4, zorder=5,
                   label=f"US-institution mean  ({usa_mean:.3f})")

    # Highlight the Stanford/Tsinghua extremes.
    annot_specs = [
        ("Stanford University",
         "Top US: Stanford 0.54", (0.10, -0.6)),
        ("Tsinghua University",
         "China lead: Tsinghua 0.26\n($\\approx 2\\times$ gap to Stanford)",
         (0.10, 1.0)),
    ]
    for marker_name, txt, (dx, dy) in annot_specs:
        for i, name in enumerate(names):
            if name == marker_name:
                ax.annotate(txt,
                            xy=(vals[i], i),
                            xytext=(vals[i] + dx, i + dy),
                            fontsize=9, color="#222",
                            arrowprops=dict(arrowstyle="-",
                                            color="#888", lw=0.7,
                                            connectionstyle="arc3,rad=0.2"))

    ax.set_yticks(ys)
    ax.set_yticklabels([f"{n}  (n={k})" for n, k in zip(names, ns)],
                       fontsize=9.5)
    ax.set_xlim(0, max(vals) + 0.20)
    ax.set_xlabel("Mean NameRank (CS faculty)", fontsize=10.5)

    from matplotlib.patches import Patch
    used = []
    seen = set()
    for name in names:
        cnt = COUNTRY[name]
        if cnt not in seen:
            used.append(cnt)
            seen.add(cnt)
    handles = [Patch(color=COUNTRY_COLOR[c], label=c, alpha=0.92) for c in used]
    from matplotlib.lines import Line2D
    handles.append(Line2D([0], [0], ls="--", color=PALETTE["baseline"],
                          linewidth=1.4, label="US-institution mean"))
    ax.legend(handles=handles, loc="center right", fontsize=8.5,
              framealpha=0.95, ncol=1, bbox_to_anchor=(0.99, 0.50))

    ax.set_title(
        "CS faculty NameRank by institution (sampled institutions with $n \\geq 4$).  "
        "Stanford-affiliated faculty score $\\approx 2\\times$ Tsinghua-affiliated.",
        fontsize=10.5, pad=10,
    )
    grid_x(ax, alpha=0.28)
    thin_spines(ax)
    plt.tight_layout()
    out = HERE / "fig_institutions.pdf"
    plt.savefig(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
