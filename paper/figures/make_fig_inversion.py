"""Figure: the artifact-over-creator inversion and the context-injection
experiment, as one two-panel exhibit.

(a) Dumbbell plot: creator vs artifact NameRank for the 11 verified pairs
    (values from data/analysis/namerank_per_entity.csv, as in Table
    tab:inversion of the paper).
(b) Forest plot: per-pair context-injection lift (arm B - arm A) with paired
    t-statistics (values from experiments/t2_7_artifact_mediation).

Replaces the two body tables; full tables remain in the appendix.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

from _style import PALETTE, apply_style, grid_x, thin_spines

apply_style()

HERE = Path(__file__).resolve().parent

# (creator, NR_c, artifact, NR_a) — released per-entity values (Table 4).
PAIRS = [
    ("Simon Willison",   0.594, "Datasette",             0.899),
    ("Dario Amodei",     0.584, "Anthropic",             0.811),
    ("Andrej Karpathy",  0.614, "nanoGPT",               0.707),
    ("Jiayi Weng",       0.331, "Tianshou",              0.420),
    ("Tri Dao",          0.532, "FlashAttention",        0.607),
    ("Lilian Weng",      0.590, "lilianweng.github.io",  0.614),
    ("Harrison Chase",   0.479, "LangChain",             0.502),
    ("Aman Sanger",      0.289, "Cursor",                0.305),
    ("Demis Hassabis",   0.664, "Google DeepMind",       0.490),
    ("Mira Murati",      0.442, "Thinking Machines Lab", 0.222),
    ("Aravind Srinivas", 0.663, "Perplexity",            0.193),
]

# (creator, artifact, delta, t) — context-injection experiment (Table 5).
INJECTION = [
    ("Jiayi Weng",       "Tianshou",              +0.288,  5.8),
    ("Harrison Chase",   "LangChain",             +0.151,  3.3),
    ("Tri Dao",          "FlashAttention",        +0.094,  2.5),
    ("Simon Willison",   "Datasette",             +0.073,  2.8),
    ("Aman Sanger",      "Cursor",                +0.042,  1.8),
    ("Lilian Weng",      "lilianweng.github.io",  +0.029,  0.8),
    ("Demis Hassabis",   "Google DeepMind",       +0.023,  0.7),
    ("Andrej Karpathy",  "nanoGPT",               +0.018,  0.7),
    ("Mira Murati",      "Thinking Machines Lab", -0.014, -0.3),
    ("Aravind Srinivas", "Perplexity",            -0.022, -0.9),
    ("Dario Amodei",     "Anthropic",             -0.047, -2.2),
]

C_CREATOR = PALETTE["cat0"]      # blue: person
C_ARTIFACT = PALETTE["highlight"]  # orange: artifact
C_NEG = PALETTE["baseline"]

fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.6),
                         gridspec_kw={"width_ratios": [1.15, 1.0]})

# ── (a) dumbbell: creator vs artifact ─────────────────────────
ax = axes[0]
order = sorted(range(len(PAIRS)), key=lambda i: PAIRS[i][3] - PAIRS[i][1])
ys = np.arange(len(PAIRS))
for row, i in enumerate(order):
    c, nc, a, na = PAIRS[i]
    invert = na > nc
    ax.plot([nc, na], [row, row], "-",
            color="#b9c6d3" if invert else "#dcc9b5", lw=2.2, zorder=1)
    ax.plot(nc, row, "o", color=C_CREATOR, markersize=7.5,
            markeredgecolor="white", markeredgewidth=0.9, zorder=3)
    ax.plot(na, row, "o", color=C_ARTIFACT, markersize=7.5,
            markeredgecolor="white", markeredgewidth=0.9, zorder=3)
    lab = f"{c} / {a}"
    ax.text(-0.03, row, lab, ha="right", va="center", fontsize=8.6,
            color="#222")
ax.set_yticks([])
ax.set_xlim(-0.02, 1.0)
ax.set_ylim(-0.7, len(PAIRS) - 0.3)
ax.set_xlabel("NameRank", fontsize=10.5)
ax.plot([], [], "o", color=C_CREATOR, label="creator")
ax.plot([], [], "o", color=C_ARTIFACT, label="artifact")
ax.legend(loc="lower right", fontsize=9.5, framealpha=0.95)
grid_x(ax, alpha=0.30)
thin_spines(ax)
ax.spines["left"].set_visible(False)
ax.set_title("(a)  The artifact out-ranks its creator in 8 of 11 pairs",
             fontsize=10.5, loc="left")

# ── (b) forest: injection lift ────────────────────────────────
ax = axes[1]
for row, (c, a, d, t) in enumerate(reversed(INJECTION)):
    sig = abs(t) >= 2.0
    col = (C_ARTIFACT if d > 0 else C_NEG)
    ax.barh(row, d, height=0.62, color=col, alpha=0.9 if sig else 0.45,
            edgecolor="white", linewidth=0.5)
    xt = d + (0.008 if d >= 0 else -0.008)
    ax.text(xt, row, f"$t={t:+.1f}$", ha="left" if d >= 0 else "right",
            va="center", fontsize=7.8, color="#555")
    ax.text(-0.125, row, c, ha="right", va="center", fontsize=8.6,
            color="#222")
ax.axvline(0, color=PALETTE["rule"], lw=0.8)
ax.set_yticks([])
ax.set_xlim(-0.135, 0.34)
ax.set_ylim(-0.7, len(INJECTION) - 0.3)
ax.set_xlabel("$\\Delta$ creator NameRank when artifact is named in context",
              fontsize=10.5)
grid_x(ax, alpha=0.30)
thin_spines(ax)
ax.spines["left"].set_visible(False)
ax.set_title("(b)  Injection lift concentrates where the creator is barely stored",
             fontsize=10.5, loc="left")

plt.tight_layout()
out = HERE / "fig_inversion.pdf"
plt.savefig(out)
print(f"Wrote {out}")
