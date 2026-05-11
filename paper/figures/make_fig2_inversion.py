"""Figure 2: artifact > creator inversion chart."""
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import numpy as np

# 11 verified pairs (creator NR, artifact NR, creator name, artifact name)
pairs = [
    (0.594, 0.899, "Simon Willison", "Datasette"),
    (0.584, 0.811, "Dario Amodei", "Anthropic"),
    (0.614, 0.707, "A. Karpathy", "nanoGPT"),
    (0.331, 0.420, "Jiayi Weng", "Tianshou"),
    (0.532, 0.607, "Tri Dao", "FlashAttention"),
    (0.590, 0.614, "Lilian Weng", "lilianweng.github.io"),
    (0.479, 0.502, "H. Chase", "LangChain"),
    (0.289, 0.305, "Aman Sanger", "Cursor"),
    (0.663, 0.490, "D. Hassabis", "G. DeepMind"),
    (0.442, 0.222, "Mira Murati", "Thinking Machines"),
    (0.663, 0.193, "A. Srinivas", "Perplexity"),
]

fig, ax = plt.subplots(figsize=(9, 6.5))

# Sort by creator NR
pairs_sorted = sorted(pairs, key=lambda p: p[0])
y_positions = list(range(len(pairs_sorted)))

for i, (nrc, nra, cname, aname) in enumerate(pairs_sorted):
    inversion = nra > nrc
    color = '#1f77b4' if inversion else '#d62728'
    # Draw line between
    ax.plot([nrc, nra], [i, i], '-', color=color, linewidth=2.2, alpha=0.55, zorder=3)
    # Creator marker
    ax.plot(nrc, i, 'o', color='white', markersize=11, markeredgecolor='black', markeredgewidth=1.1, zorder=5)
    ax.plot(nrc, i, 'o', color='#666', markersize=6, zorder=6)
    # Artifact marker
    ax.plot(nra, i, 's', color=color, markersize=11, markeredgecolor='black', markeredgewidth=1.1, zorder=5)
    # Label
    label_x = min(nrc, nra) - 0.04
    ax.text(label_x, i, f"{cname} / {aname}", ha='right', va='center', fontsize=9.5)

ax.set_xlabel("NameRank", fontsize=12)
ax.set_yticks([])
ax.set_xlim(-0.05, 1.05)
ax.set_ylim(-1, len(pairs_sorted))
ax.grid(True, axis='x', alpha=0.3)

# Legend
from matplotlib.lines import Line2D
legend_elems = [
    Line2D([0], [0], marker='o', color='w', markerfacecolor='#666', markersize=9, markeredgecolor='black', label='Creator'),
    Line2D([0], [0], marker='s', color='w', markerfacecolor='#1f77b4', markersize=9, markeredgecolor='black', label='Artifact (inversion)'),
    Line2D([0], [0], marker='s', color='w', markerfacecolor='#d62728', markersize=9, markeredgecolor='black', label='Artifact (no inversion)'),
]
ax.legend(handles=legend_elems, loc='lower right', fontsize=10, framealpha=0.95)

ax.set_title("Artifact $>$ creator inversion across 11 verified (creator, artifact) pairs.\n"
              "Blue: artifact exceeds creator (8/11). Red: creator exceeds artifact (3/11, all senior leaders of named orgs).",
              fontsize=10.5)
plt.tight_layout()
out = "/home/ubuntu/namerank/paper/figures/fig2_inversion.pdf"
plt.savefig(out, bbox_inches="tight")
print(f"Wrote {out}")
