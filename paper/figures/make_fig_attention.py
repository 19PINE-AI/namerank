#!/usr/bin/env python3
"""Attention-metric baseline figure (Appendix, confound checks).

Three panels arguing that NameRank is not Wikipedia-pageview rank:
(a) among the 28% of entities with a resolvable article, NameRank vs
    24-month log pageviews is weak (R^2 = 0.06);
(b) the within-cohort correlation has a sign structure — positive for
    celebrity cohorts, negative for technical/production cohorts
    (attention flow vs corpus stock);
(c) the metric is undefined for the 71% with no article, whose NameRank
    nonetheless spans the axis.

Data: experiments/t5_2_attention_baseline (T5.2) + t1_4 lookup.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from _style import PALETTE, apply_style, grid_x, grid_y, pretty_cohort, thin_spines

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
EXP = ROOT / "experiments" / "t5_2_attention_baseline"

apply_style()


def read_csv(p):
    return list(csv.DictReader(open(p)))


res = json.loads((EXP / "outputs/results.json").read_text())
nr_rows = read_csv(ROOT / "data/analysis/namerank_per_entity.csv")
nr = {r["entity_id"]: float(r["namerank"]) for r in nr_rows}
names = {r["entity_id"]: r["entity_name"] for r in nr_rows}
lookup = read_csv(ROOT / "experiments/t1_4_wikipedia/wikipedia_lookup.csv")

# reproduce the analysis filters: window-covered + plausible title
import re


def title_plausible(eid, title):
    base = re.sub(r"\s*\(.*\)", "", names.get(eid, "")).lower()
    toks = set(re.findall(r"[a-z0-9]+", base))
    return bool(toks & set(re.findall(r"[a-z0-9]+", title.lower())))


pv = {r["entity_id"]: int(r["views_24m"])
      for r in read_csv(EXP / "outputs/pageviews_24m.csv")
      if int(r["months_returned"]) > 0
      and title_plausible(r["entity_id"], r["title"])}
matched = [e for e in pv if e in nr]
unmatched = [r["entity_id"] for r in lookup
             if r["has_wikipedia"] == "0" and r["entity_id"] in nr]

fig, (ax1, ax2, ax3) = plt.subplots(
    1, 3, figsize=(11.0, 3.5), gridspec_kw={"width_ratios": [1.15, 0.95, 1.0]})

# ── (a) scatter: log pageviews vs NameRank ────────────────────────────
x = np.array([math.log10(pv[e] + 1) for e in matched])
y = np.array([nr[e] for e in matched])
ax1.scatter(x, y, s=7, color=PALETTE["cat0"], alpha=0.25, lw=0, zorder=2)
deciles = np.percentile(x, np.linspace(0, 100, 11))
for lo, hi in zip(deciles[:-1], deciles[1:]):
    m = (x >= lo) & (x <= hi)
    if m.sum() >= 5:
        ax1.scatter(x[m].mean(), y[m].mean(), s=52, zorder=4,
                    color=PALETTE["highlight"], edgecolor="white", lw=0.8)
b, a = np.polyfit(x, y, 1)
xs = np.linspace(x.min(), x.max(), 50)
ax1.plot(xs, a + b * xs, color=PALETTE["rule"], lw=1.1, ls="--", zorder=3)
r2_all = res["matched_overall"]["r2"]
r2_within = res["within_cohort"]["pooled_partial_r2"]
ax1.text(0.03, 0.96,
         f"$R^2 = {r2_all:.2f}$ overall\n$R^2 = {r2_within:.2f}$ within cohort",
         transform=ax1.transAxes, va="top", fontsize=9,
         bbox=dict(facecolor="white", edgecolor="#cccccc", pad=3.0))
ax1.set_xlabel("$\\log_{10}$ article pageviews (24 mo)")
ax1.set_ylabel("NameRank")
ax1.set_ylim(-0.03, 1.03)
ax1.set_title(f"(a) Entities with an article ($n = {len(matched):,}$)",
              fontsize=10.5)
thin_spines(ax1)
grid_y(ax1)

# ── (b) within-cohort correlation ladder ─────────────────────────────
pc = {c: v for c, v in res["within_cohort"]["per_cohort"].items()
      if v["n"] >= 40}
order = sorted(pc, key=lambda c: pc[c]["r"])
ys = np.arange(len(order))
for i, c in enumerate(order):
    r = pc[c]["r"]
    col = PALETTE["cat2"] if r >= 0 else PALETTE["cat3"]
    ax2.plot([0, r], [i, i], color=col, lw=1.4, zorder=2)
    ax2.scatter([r], [i], s=26, color=col, zorder=3)
ax2.axvline(0, color=PALETTE["rule"], lw=0.8)
ax2.set_yticks(ys)
ax2.set_yticklabels([pretty_cohort(c) for c in order], fontsize=8)
ax2.set_xlabel("within-cohort $r$ (pageviews, NameRank)")
ax2.set_xlim(-0.75, 0.95)
ax2.set_title("(b) Correlation by cohort ($n \\geq 40$)", fontsize=10.5)
thin_spines(ax2)
grid_x(ax2)

# ── (c) NameRank distribution: article vs no article ──────────────────
bins = np.linspace(0, 1, 41)
un_nr = np.array([nr[e] for e in unmatched])
ma_nr = np.array([nr[e] for e in matched])
ax3.hist(un_nr, bins=bins, density=True, color=PALETTE["cat1"], alpha=0.55,
         label=f"no article ($n = {len(unmatched):,}$)", zorder=3)
ax3.hist(ma_nr, bins=bins, density=True, histtype="step", lw=1.4,
         color=PALETTE["cat0"],
         label=f"article ($n = {len(matched):,}$)", zorder=4)
ax3.set_xlabel("NameRank")
ax3.set_ylabel("density")
ax3.set_xlim(0, 1)
ax3.set_title("(c) Metric undefined for 71% of entities", fontsize=10.5)
ax3.legend(loc="upper right", fontsize=8.5)
thin_spines(ax3)
grid_y(ax3)

fig.tight_layout(w_pad=1.6)
out = HERE / "fig_attention.pdf"
fig.savefig(out)
print(f"wrote {out}")
