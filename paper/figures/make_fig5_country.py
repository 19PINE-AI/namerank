"""Figure 5: CS faculty NameRank by country (corpus-density gradient).

Reads aggregated means from data/analysis/cs_faculty_by_country.csv. The
"Other/Unknown" bucket is excluded from the figure (the paper discusses it
as a residual bucket in the text only).
"""
import csv
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
ANALYSIS = REPO / "data" / "analysis"

EXCLUDE = {"Other/Unknown"}


def main() -> None:
    rows = []
    for r in csv.DictReader(open(ANALYSIS / "cs_faculty_by_country.csv", encoding="utf-8")):
        if r["country"] in EXCLUDE:
            continue
        rows.append((r["country"], int(r["n"]), float(r["mean"])))

    usa_mean = next(m for c, _, m in rows if c == "USA")
    rows.sort(key=lambda x: x[2])

    def color_for(country: str, val: float) -> str:
        if country == "USA":
            return "#aaaaaa"
        return "#1f77b4" if val > usa_mean else "#d62728"

    fig, ax = plt.subplots(figsize=(9, 6.5))
    ys = list(range(len(rows)))
    names = [r[0] for r in rows]
    ns = [r[1] for r in rows]
    vals = [r[2] for r in rows]
    colors = [color_for(c, v) for c, _, v in rows]

    ax.barh(ys, vals, color=colors, edgecolor='black', linewidth=0.5)
    ax.set_yticks(ys)
    ax.set_yticklabels([f"{n} (n={k})" for n, k in zip(names, ns)], fontsize=10)
    ax.axvline(usa_mean, ls='--', color='#888', linewidth=1.5, label=f'USA baseline ({usa_mean:.3f})')

    for i, v in enumerate(vals):
        ax.text(v + 0.005, i, f"{v:.3f}", va='center', fontsize=9)

    lo = min(vals) - 0.04
    hi = max(vals) + 0.06
    ax.set_xlim(max(0.0, lo), hi)
    ax.set_xlabel("Mean NameRank (CS faculty cohort)", fontsize=11)
    ax.legend(loc='upper left', fontsize=10, framealpha=0.92)
    ax.set_title("Corpus-density gradient: CS faculty NameRank by country of affiliation.\n"
                 "Small high-output Western tech ecosystems (Israel, Singapore, Sweden) lead;\n"
                 "China, India, Spain, France cluster at the bottom.",
                 fontsize=10.5)
    ax.grid(True, axis='x', alpha=0.3)
    plt.tight_layout()
    out = HERE / "fig5_country.pdf"
    plt.savefig(out, bbox_inches="tight")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
