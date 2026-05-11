"""Figure 5: CS faculty NameRank by country (corpus-density gradient)."""
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

data = [
    ("Israel", 7, 0.506),
    ("Singapore", 7, 0.497),
    ("Sweden", 5, 0.492),
    ("Germany", 9, 0.490),
    ("Switzerland", 4, 0.489),
    ("Canada", 9, 0.478),
    ("USA", 302, 0.460),
    ("Netherlands", 9, 0.447),
    ("UK", 16, 0.438),
    ("Hong Kong", 11, 0.431),
    ("Brazil", 10, 0.388),
    ("Australia", 11, 0.341),
    ("France", 3, 0.312),
    ("China", 30, 0.311),
    ("Spain", 8, 0.303),
    ("India", 10, 0.292),
]

data.sort(key=lambda x: x[2])
fig, ax = plt.subplots(figsize=(9, 6.5))

ys = list(range(len(data)))
names = [d[0] for d in data]
ns = [d[1] for d in data]
vals = [d[2] for d in data]

# Color: USA baseline gold, above blue, below red
def color_for(c, v):
    if c == "USA":
        return "#aaaaaa"
    if v > 0.460:
        return "#1f77b4"
    return "#d62728"

colors = [color_for(c, v) for c, v in zip(names, vals)]

ax.barh(ys, vals, color=colors, edgecolor='black', linewidth=0.5)
ax.set_yticks(ys)
ax.set_yticklabels([f"{n} (n={k})" for n, k in zip(names, ns)], fontsize=10)
ax.axvline(0.460, ls='--', color='#888', linewidth=1.5, label='USA baseline (0.460)')

for i, v in enumerate(vals):
    ax.text(v + 0.005, i, f"{v:.3f}", va='center', fontsize=9)

ax.set_xlabel("Mean NameRank (CS faculty cohort)", fontsize=11)
ax.set_xlim(0.25, 0.58)
ax.legend(loc='upper left', fontsize=10, framealpha=0.92)
ax.set_title("Corpus-density gradient: CS faculty NameRank by country of affiliation.\n"
              "Small high-output Western tech ecosystems (Israel, Singapore, Sweden) lead;\n"
              "China, India, Spain, France cluster at the bottom.",
              fontsize=10.5)
ax.grid(True, axis='x', alpha=0.3)
plt.tight_layout()
out = "/home/ubuntu/namerank/paper/figures/fig5_country.pdf"
plt.savefig(out, bbox_inches="tight")
print(f"Wrote {out}")
