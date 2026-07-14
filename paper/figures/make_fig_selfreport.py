"""F23 — Self-report is not measurement (recognition metric).
(a) Self-report Bradley-Terry scale vs measured panel recognition: recovers the
    ordering in aggregate.
(b) But per model, self-report tracks cross-panel FAME far better than the
    model's OWN behavioral record, and the three vendors agree with each other
    more than any agrees with ground truth: introspection reads the corpus
    prior, not the model's own state.
Data: t5_4_self_report bt_theta.csv + recognition via _data('main').
Output: fig_selfreport.pdf
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import spearmanr
import _data
import _style
from _style import RECOG

_style.apply_style()

rows = list(csv.DictReader(
    open(REPO / "experiments/t5_4_self_report/outputs/bt_theta.csv")))
theta = defaultdict(list)
per_model = defaultdict(lambda: {"theta": [], "panel": [], "own": []})
for r in rows:
    try:
        t = float(r["bt_theta"])
    except ValueError:
        continue
    theta[r["entity_id"]].append(t)
    per_model[r["model_id"]]["theta"].append(t)
    per_model[r["model_id"]]["panel"].append(float(r["panel_nr"]))
    per_model[r["model_id"]]["own"].append(float(r["own_score"]))

df = _data.per_entity("main").set_index("entity_id")
ent_theta = {e: np.mean(v) for e, v in theta.items()}
common = [e for e in ent_theta if e in df.index and not df.loc[e, "synthetic"]]
x = np.array([ent_theta[e] for e in common])
y = np.array([df.loc[e, "recognition"] for e in common])
rho = spearmanr(x, y).statistic
print("data sources:", _data.source_report())

fig, (axa, axb) = plt.subplots(1, 2, figsize=(6.9, 3.0),
                               gridspec_kw={"width_ratios": [1.0, 1.15]})

# (a) self-report vs recognition
axa.scatter(y, x, s=10, alpha=0.35, color=RECOG["person"], edgecolor="none")
axa.set_xlabel("measured recognition rate")
axa.set_ylabel("self-report scale (BT)")
axa.set_title(f"(a) Aggregate ($\\rho={rho:.2f}$)", fontsize=9, loc="left")
axa.grid(color="#ececec", linewidth=0.6, zorder=0)
axa.set_axisbelow(True)

# (b) per-model: vs panel fame vs own behavior
models = list(per_model)
short = [m.split("-think")[0].replace("-", " ")[:12] for m in models]
rp = [spearmanr(per_model[m]["theta"], per_model[m]["panel"]).statistic for m in models]
ro = [spearmanr(per_model[m]["theta"], per_model[m]["own"]).statistic for m in models]
xpos = np.arange(len(models))
w = 0.36
axb.bar(xpos - w / 2, rp, w, color=RECOG["person"], label="vs panel fame", zorder=3)
axb.bar(xpos + w / 2, ro, w, color=RECOG["muted"], label="vs own behavior", zorder=3)
axb.set_xticks(xpos)
axb.set_xticklabels(short, fontsize=7, rotation=15)
axb.set_ylabel("Spearman $\\rho$")
axb.set_ylim(0, 0.8)
axb.legend(loc="upper right", frameon=False, fontsize=7.5)
axb.set_title("(b) Self-report reads fame, not own state", fontsize=8.6, loc="left")
axb.grid(axis="y", color="#ececec", linewidth=0.6, zorder=0)
axb.set_axisbelow(True)

fig.tight_layout()
fig.savefig(HERE / "fig_selfreport.pdf")
fig.savefig(HERE / "fig_selfreport.png", dpi=150)
print(f"wrote fig_selfreport.pdf (rho={rho:.3f}, n={len(common)})")
