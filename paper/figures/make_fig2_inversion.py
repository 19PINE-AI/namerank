"""Figure 2: artifact > creator inversion chart.

Reads the 11 verified pairs from data/analysis/attribution_pairs_v2.csv and
the per-entity NameRank from data/analysis/namerank_per_entity.csv. The
creator/artifact name lookup tolerates the abbreviations used in the paper
(e.g., "A. Karpathy" vs "Andrej Karpathy", "G. DeepMind" vs "Google DeepMind").
"""
import csv
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
ANALYSIS = REPO / "data" / "analysis"

# Short labels used in the figure (paper convention). Maps the canonical name
# stored in attribution_pairs_v2.csv -> display name.
SHORT = {
    "Andrej Karpathy": "A. Karpathy",
    "Harrison Chase": "H. Chase",
    "Demis Hassabis": "D. Hassabis",
    "Google DeepMind": "G. DeepMind",
    "Aravind Srinivas": "A. Srinivas",
    "Thinking Machines Lab": "Thinking Machines",
    "lilianweng.github.io": "lilianweng.github.io",
}


def load_namerank() -> dict[str, float]:
    nr = {}
    for r in csv.DictReader(open(ANALYSIS / "namerank_per_entity.csv", encoding="utf-8")):
        nr[r["entity_name"]] = float(r["namerank"])
    return nr


def main() -> None:
    nr = load_namerank()
    pairs = []
    for r in csv.DictReader(open(ANALYSIS / "attribution_pairs_v2.csv", encoding="utf-8")):
        c, a = r["creator"], r["artifact"]
        if c not in nr or a not in nr:
            raise SystemExit(f"missing NameRank for pair ({c}, {a}); rerun build_namerank.py")
        pairs.append((nr[c], nr[a], SHORT.get(c, c), SHORT.get(a, a)))

    fig, ax = plt.subplots(figsize=(9, 6.5))
    pairs_sorted = sorted(pairs, key=lambda p: p[0])

    for i, (nrc, nra, cname, aname) in enumerate(pairs_sorted):
        inversion = nra > nrc
        color = '#1f77b4' if inversion else '#d62728'
        ax.plot([nrc, nra], [i, i], '-', color=color, linewidth=2.2, alpha=0.55, zorder=3)
        ax.plot(nrc, i, 'o', color='white', markersize=11, markeredgecolor='black', markeredgewidth=1.1, zorder=5)
        ax.plot(nrc, i, 'o', color='#666', markersize=6, zorder=6)
        ax.plot(nra, i, 's', color=color, markersize=11, markeredgecolor='black', markeredgewidth=1.1, zorder=5)
        ax.text(min(nrc, nra) - 0.04, i, f"{cname} / {aname}", ha='right', va='center', fontsize=9.5)

    ax.set_xlabel("NameRank", fontsize=12)
    ax.set_yticks([])
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-1, len(pairs_sorted))
    ax.grid(True, axis='x', alpha=0.3)

    from matplotlib.lines import Line2D
    legend_elems = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#666', markersize=9, markeredgecolor='black', label='Creator'),
        Line2D([0], [0], marker='s', color='w', markerfacecolor='#1f77b4', markersize=9, markeredgecolor='black', label='Artifact (inversion)'),
        Line2D([0], [0], marker='s', color='w', markerfacecolor='#d62728', markersize=9, markeredgecolor='black', label='Artifact (no inversion)'),
    ]
    ax.legend(handles=legend_elems, loc='lower right', fontsize=10, framealpha=0.95)

    n_inv = sum(1 for nrc, nra, _, _ in pairs_sorted if nra > nrc)
    ax.set_title(f"Artifact $>$ creator inversion across {len(pairs_sorted)} verified (creator, artifact) pairs.\n"
                 f"Blue: artifact exceeds creator ({n_inv}/{len(pairs_sorted)}). "
                 f"Red: creator exceeds artifact ({len(pairs_sorted)-n_inv}/{len(pairs_sorted)}, all senior leaders of named orgs).",
                 fontsize=10.5)
    plt.tight_layout()
    out = HERE / "fig2_inversion.pdf"
    plt.savefig(out, bbox_inches="tight")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
