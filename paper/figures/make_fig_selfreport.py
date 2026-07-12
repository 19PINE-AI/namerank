#!/usr/bin/env python3
"""Self-reported recognition figure (Section 3.7 / self-report appendix).

Three panels for the T5.4 pairwise self-report experiment:
(a) Bradley-Terry self-ranking vs panel NameRank (representative model,
    decile means): partial reconstruction;
(b) correlation ladder -- what the self-ranking tracks: other vendors'
    self-rankings and the prevalence component sit high, the model's own
    behavioral record sits at zero;
(c) verdict composition on known-vs-unknown boundary pairs split by whether
    corpus fame agrees with the model's own knowledge, plus the fictional
    trap arm: disagreement resolves to abstention, not fabrication.

Data: experiments/t5_4_self_report outputs.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from _style import PALETTE, apply_style, grid_x, grid_y, thin_spines

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
EXP = ROOT / "experiments" / "t5_4_self_report"

apply_style()

MODELS = ["gpt-5.5-think", "claude-opus-4.6-think", "gemini-3.1-pro"]
MODEL_LABEL = {"gpt-5.5-think": "GPT-5.5",
               "claude-opus-4.6-think": "Claude Opus 4.6",
               "gemini-3.1-pro": "Gemini 3.1 Pro"}
MODEL_COLOR = {"gpt-5.5-think": PALETTE["cat0"],
               "claude-opus-4.6-think": PALETTE["cat1"],
               "gemini-3.1-pro": PALETTE["cat2"]}
MODEL_MARKER = {"gpt-5.5-think": "o",
                "claude-opus-4.6-think": "s",
                "gemini-3.1-pro": "^"}

summary = json.loads((EXP / "outputs/summary.json").read_text())
ents = {e["id"]: e for e in json.loads((EXP / "inputs/entities.json").read_text())}
res = json.loads((EXP / "outputs/pairwise_results.json").read_text())
theta_rows = [dict(zip(("entity_id", "model_id", "bt_theta", "own_score",
                        "panel_nr", "own_label"), ln.rstrip("\n").split(",")))
              for ln in open(EXP / "outputs/bt_theta.csv").readlines()[1:]]

fig, (ax1, ax2, ax3) = plt.subplots(
    1, 3, figsize=(11.0, 3.5), gridspec_kw={"width_ratios": [1.0, 1.25, 1.05]})

# ── (a) BT self-ranking vs panel NameRank (representative model) ──────
REP = "gpt-5.5-think"
pts = [(float(r["bt_theta"]), float(r["panel_nr"])) for r in theta_rows
       if r["model_id"] == REP and r["panel_nr"] not in ("", "None")]
x = np.array([p[0] for p in pts])
x = (x - x.mean()) / x.std()  # display in standardized units
y = np.array([p[1] for p in pts])
ax1.scatter(x, y, s=8, color=PALETTE["cat0"], alpha=0.30, lw=0, zorder=2)
deciles = np.percentile(x, np.linspace(0, 100, 11))
for lo, hi in zip(deciles[:-1], deciles[1:]):
    m = (x >= lo) & (x <= hi)
    if m.sum() >= 5:
        ax1.scatter(x[m].mean(), y[m].mean(), s=52, zorder=4,
                    color=PALETTE["highlight"], edgecolor="white", lw=0.8)
rhos = [summary[m]["bt"]["rho_panel_all"] for m in MODELS]
ax1.text(0.03, 0.97,
         f"GPT-5.5: $\\rho = {rhos[0]:.2f}$ (shown)\n"
         f"others: ${rhos[1]:.2f}$ / ${rhos[2]:.2f}$",
         transform=ax1.transAxes, va="top", fontsize=9,
         bbox=dict(facecolor="white", edgecolor="#cccccc", pad=3.0))
ax1.set_xlabel("self-ranking (Bradley–Terry $\\theta$, std.)")
ax1.set_ylabel("panel NameRank")
ax1.set_ylim(-0.03, 1.03)
ax1.set_title("(a) Partial reconstruction", fontsize=10.5)
thin_spines(ax1)
grid_y(ax1)

# ── (b) what the self-ranking tracks ──────────────────────────────────
inter = summary["_inter_model_bt_spearman"]


def inter_mean(m):
    vals = [v for k, v in inter.items() if m in k]
    return float(np.mean(vals))


rows = [
    ("other vendors'\nself-rankings", {m: inter_mean(m) for m in MODELS}),
    ("prevalence\n(share of panel knowing it)",
     {m: summary[m]["decomposition"]["rho_bt_prevalence"] for m in MODELS}),
    ("panel NameRank",
     {m: summary[m]["bt"]["rho_panel_all"] for m in MODELS}),
    ("conditional depth\n(score among knowers)",
     {m: summary[m]["decomposition"]["rho_bt_cond_level"] for m in MODELS}),
    ("model's own score\n(entities it knows)",
     {m: summary[m]["bt"]["rho_own_known"] for m in MODELS}),
]
ys = np.arange(len(rows))[::-1]
for yi, (label, vals) in zip(ys, rows):
    lo, hi = min(vals.values()), max(vals.values())
    ax2.plot([lo, hi], [yi, yi], color="#c9c9c9", lw=2.4, zorder=1,
             solid_capstyle="round")
    for m in MODELS:
        ax2.scatter([vals[m]], [yi], s=34, zorder=3,
                    color=MODEL_COLOR[m], marker=MODEL_MARKER[m],
                    edgecolor="white", lw=0.6,
                    label=MODEL_LABEL[m] if yi == ys[0] else None)
ax2.axvline(0, color=PALETTE["rule"], lw=0.8)
ax2.set_yticks(ys)
ax2.set_yticklabels([r[0] for r in rows], fontsize=8.5)
ax2.set_xlabel("Spearman $\\rho$ with the self-ranking")
ax2.set_xlim(-0.18, 1.0)
ax2.set_title("(b) Self-report reads the corpus prior", fontsize=10.5)
ax2.legend(loc="lower right", fontsize=8, handletextpad=0.2,
           borderpad=0.35, labelspacing=0.3)
thin_spines(ax2)
grid_x(ax2)

# ── (c) boundary verdicts: own knowledge vs corpus fame ───────────────
def own_label(eid, m):
    e = ents[eid]
    if e["kind"] == "fictional":
        return "fictional"
    if e[f"refusal__{m}"] or e[f"score__{m}"] < 0.05:
        return "unknown"
    if e[f"score__{m}"] >= 0.15:
        return "known"
    return "mid"


ctx = {"congruent": [0, 0, 0, 0], "incongruent": [0, 0, 0, 0],
       "trap": [0, 0, 0, 0]}  # sides-with-own, equal, abstain, claims-unknown
for r in res:
    if r["rev_of"] is not None or r["verdict"] not in ("A", "B", "EQUAL",
                                                       "NEITHER"):
        continue
    m = r["model_id"]
    la, lb = own_label(r["a"], m), own_label(r["b"], m)
    if {la, lb} == {"known", "fictional"}:
        grp = "trap"
    elif {la, lb} == {"known", "unknown"}:
        ka = "a" if la == "known" else "b"
        ua = "b" if ka == "a" else "a"
        gap = ents[r[ka]]["panel_nr"] - ents[r[ua]]["panel_nr"]
        if abs(gap) < 0.05:
            continue
        grp = "congruent" if gap > 0 else "incongruent"
    else:
        continue
    ks = "A" if (la == "known") else "B"
    us = "B" if ks == "A" else "A"
    i = (0 if r["verdict"] == ks else 1 if r["verdict"] == "EQUAL"
         else 2 if r["verdict"] == "NEITHER" else 3)
    ctx[grp][i] += 1

order = [("congruent", "boundary pair,\nfame agrees"),
         ("incongruent", "boundary pair,\nfame contradicts"),
         ("trap", "fictional trap\nvs known name")]
cats = ["sides with own knowledge", "“equal”",
        "abstains (“neither”)", "claims the unknown name"]
cat_colors = [PALETTE["cat0"], PALETTE["cat1"], PALETTE["baseline"],
              PALETTE["cat3"]]
ybar = np.arange(len(order))[::-1]
for yi, (key, label) in zip(ybar, order):
    counts = np.array(ctx[key], float)
    shares = counts / counts.sum()
    left = 0.0
    for s, c in zip(shares, cat_colors):
        ax3.barh(yi, s, left=left, height=0.58, color=c,
                 edgecolor="white", lw=1.2, zorder=3)
        if s >= 0.06:
            ax3.text(left + s / 2, yi, f"{100*s:.0f}", ha="center",
                     va="center", fontsize=8, color="white", zorder=4)
        left += s
    ax3.text(1.015, yi, f"$n={int(counts.sum()):,}$", va="center",
             fontsize=8, color="#555")
ax3.set_yticks(ybar)
ax3.set_yticklabels([o[1] for o in order], fontsize=8.5)
ax3.set_xlim(0, 1.0)
ax3.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
ax3.set_xticklabels(["0", "25", "50", "75", "100%"])
ax3.set_title("(c) Errors are abstentions, not claims", fontsize=10.5)
handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in cat_colors]
ax3.legend(handles, cats, loc="upper center", bbox_to_anchor=(0.5, -0.16),
           fontsize=7.8, ncol=2, frameon=False,
           handlelength=1.0, handletextpad=0.4, columnspacing=0.9)
thin_spines(ax3)

fig.tight_layout(w_pad=1.5)
out = HERE / "fig_selfreport.pdf"
fig.savefig(out)
print(f"wrote {out}")
