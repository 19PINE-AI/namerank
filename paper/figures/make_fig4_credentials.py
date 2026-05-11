"""Figure 4: Credential treadmill bar chart."""
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

credentials = [
    ("GPT-5 system-card author", 80, 0.042, "#7f0000"),
    ("DeepSeek-V3 paper author", 69, 0.178, "#7f0000"),
    ("CPhO China first prize", 50, 0.182, "#d62728"),
    ("CMO China gold", 131, 0.302, "#ff7f0e"),
    ("Rhodes Scholarship", 36, 0.315, "#ff7f0e"),
    ("IOI gold (2005-15)", 68, 0.341, "#ff7f0e"),
    ("MSRA PhD Fellowship", 237, 0.343, "#ff7f0e"),
    ("IMO gold (2005-15)", 197, 0.362, "#ff7f0e"),
    ("NOI China gold", 29, 0.368, "#ff7f0e"),
    # Baseline:
    ("OpenAlex working researcher", 771, 0.464, "#aaaaaa"),
    ("Putnam top-25 fellow", 35, 0.608, "#1f77b4"),
    ("ICPC World Finalist gold", 18, 0.610, "#1f77b4"),
]

fig, ax = plt.subplots(figsize=(9, 6))
ys = list(range(len(credentials)))
names = [c[0] for c in credentials]
vals = [c[2] for c in credentials]
ns = [c[1] for c in credentials]
colors = [c[3] for c in credentials]

bars = ax.barh(ys, vals, color=colors, edgecolor='black', linewidth=0.6)
ax.set_yticks(ys)
ax.set_yticklabels([f"{n} (n={k})" for n, k in zip(names, ns)], fontsize=10)

# Baseline line
ax.axvline(0.464, ls='--', color='#888', linewidth=1.5, label='OpenAlex working-researcher baseline (0.464)')

# Annotate values
for i, (v, n) in enumerate(zip(vals, ns)):
    ax.text(v + 0.008, i, f"{v:.3f}", va='center', fontsize=9)

ax.set_xlabel("Mean NameRank", fontsize=11)
ax.set_xlim(0, 0.75)
ax.legend(loc='lower right', fontsize=10, framealpha=0.92)
ax.set_title("The credential treadmill: 7 of 9 once-prestigious intellectual credentials\n"
              "sit at or below the working-researcher NameRank baseline.",
              fontsize=10.5)
ax.grid(True, axis='x', alpha=0.3)
plt.tight_layout()
out = "/home/ubuntu/namerank/paper/figures/fig4_credentials.pdf"
plt.savefig(out, bbox_inches="tight")
print(f"Wrote {out}")
