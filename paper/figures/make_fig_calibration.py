"""F5/F6 — Instrument calibration, two panels.
(a) Synthetic-null floor by gold recipe: fictional entities through the full
    pipeline earn ~0 recognition, except descriptive paper titles (floor kept
    and used for adjustment).
(b) Variance decomposition of the per-record verdicts: the score measures the
    entity, not the panel.
Output: fig_calibration.pdf
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import matplotlib.pyplot as plt
import numpy as np
import _data
import _style
from _style import RECOG

_style.apply_style()

SYN_NAMES = {
    "synthetic_founder_v2": "founders",
    "synthetic_oss_project_v2": "OSS projects",
    "synthetic_msra_v2": "fellowship recipients",
    "synthetic_mid_tier_musician_v2": "musicians",
    "synthetic_mid_tier_journalist_v2": "journalists",
    "synthetic_mid_tier_podcast_v2": "podcasts",
    "synthetic_mid_tier_chef_v2": "chefs",
    "synthetic_cs_faculty_v2": "CS faculty",
    "synthetic_openalex_researcher_v2": "researchers",
    "synthetic_noi_v2": "NOI medalists",
    "synthetic_imo_gold_v2": "IMO medalists",
    "synthetic_paper_v2": "papers (descriptive titles)",
}

df = _data.per_entity("main")
syn = df[df.synthetic].groupby("cohort").recognition.mean()
syn = syn.reindex([k for k in SYN_NAMES if k in syn.index])
print("data sources:", _data.source_report())

# variance decomposition from raw verdicts
ents = _data.entities("main")
rec = []
src = (_data.FINAL if _data.FINAL.exists() else None)
vd_file = _data.T6 / "outputs" / "recognition_v3.jsonl"
for line in open(vd_file):
    try:
        r = json.loads(line)
    except json.JSONDecodeError:
        continue
    e = ents.get(r["entity_id"])
    if e and not e.get("synthetic") and e.get("gold_v2"):
        rec.append((r["entity_id"], r["model_id"],
                    e.get("cohort", "?"), r["recognized"]))
import pandas as pd
V = pd.DataFrame(rec, columns=["e", "m", "c", "y"])
tot = ((V.y - V.y.mean()) ** 2).sum()
shares = {}
for name, key in [("entity", "e"), ("cohort", "c"), ("model", "m")]:
    mu = V.groupby(key).y.transform("mean")
    shares[name] = float(((mu - V.y.mean()) ** 2).sum() / tot)

fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(6.9, 2.9),
                                 gridspec_kw={"width_ratios": [1.5, 1.0]})

# (a) floors
ypos = np.arange(len(syn))
colors = [RECOG["accent"] if "paper" in c else RECOG["floor"] for c in syn.index]
ax_a.barh(ypos, syn.values, height=0.62, color=colors, zorder=3)
ax_a.set_yticks(ypos)
ax_a.set_yticklabels([SYN_NAMES[c] for c in syn.index], fontsize=7.6)
ax_a.set_xlim(0, 0.30)
ax_a.set_xlabel("recognition rate of fictional entities")
ax_a.invert_yaxis()
for y, v in zip(ypos, syn.values):
    ax_a.annotate(f"{v:.3f}" if v > 0 else "0",
                  xy=(max(v, 0.002) + 0.004, y), va="center", fontsize=7)
ax_a.set_title("(a) Synthetic-null floor by gold recipe", fontsize=9, loc="left")
ax_a.grid(axis="x", color="#ececec", linewidth=0.6, zorder=0)
ax_a.set_axisbelow(True)

# (b) variance decomposition
names = ["entity", "cohort", "model"]
vals = [shares[n] * 100 for n in names]
cols = [RECOG["person"], "#7aa5cf", RECOG["muted"]]
ax_b.bar(names, vals, width=0.58, color=cols, zorder=3)
for i, v in enumerate(vals):
    ax_b.annotate(f"{v:.0f}%", xy=(i, v + 1.2), ha="center", fontsize=8.5)
ax_b.set_ylabel("share of verdict variance (%)")
ax_b.set_ylim(0, max(vals) * 1.22)
ax_b.set_title("(b) What the verdicts vary with", fontsize=9, loc="left")
ax_b.grid(axis="y", color="#ececec", linewidth=0.6, zorder=0)
ax_b.set_axisbelow(True)

fig.tight_layout()
fig.savefig(HERE / "fig_calibration.pdf")
fig.savefig(HERE / "fig_calibration.png", dpi=150)
print("wrote fig_calibration.pdf; shares:", {k: round(v, 3) for k, v in shares.items()})
