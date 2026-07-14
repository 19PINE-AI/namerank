"""F1 — The Recognition Atlas.

Every cohort (n>=10) on the single recognition axis: dot = cohort mean panel
recognition rate, whisker = 95% CI over entities. Person cohorts in blue,
artifact cohorts in amber. Hatched band = synthetic-null floor. Credential
cohorts bold. Zone thresholds annotated at top.

Output: fig1_atlas.pdf (+ .png preview)
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import matplotlib.pyplot as plt
import _data
import _style
from _style import RECOG

_style.apply_style()

ARTIFACT_COHORTS = {
    "oss_project", "named_method", "benchmark", "dataset", "foundation_model",
    "ai_startup_or_company", "ai_hardware", "programming_language",
    "database_or_data_system", "conference", "award", "industry_product",
    "website_or_service", "mid_tier_book", "mid_tier_podcast",
    "mid_tier_online_course", "mid_tier_product", "mid_tier_yc_company",
    "long_tail_paper", "research_paper",
}
CREDENTIAL_COHORTS = {
    "imo_gold", "ioi_gold", "noi_china_gold", "cmo_china_gold",
    "cpho_china_first_prize", "putnam_fellow", "icpc_world_finals_gold",
    "rhodes_scholar", "msra_phd_fellowship",
}

# main cohorts + the three LLM-area cohorts on the same protocol
tab = _data.cohort_table("main", min_n=10)
llm = _data.cohort_table("llm", min_n=10)
llm = llm[llm.cohort.str.startswith("llm_")]
tab = __import__("pandas").concat([tab, llm]).sort_values("recognition")
fl = _data.floors("main")
print("data sources:", _data.source_report())

BASELINE = float(tab.loc[tab.cohort == "long_tail_researcher_openalex",
                         "recognition"].iloc[0])

fig, ax = plt.subplots(figsize=(6.9, 9.6))
_style.floor_band(ax, max(0.02, fl["_people"]), axis="x")

labels = []
for i, r in enumerate(tab.itertuples()):
    color = (RECOG["artifact"] if r.cohort in ARTIFACT_COHORTS
             else RECOG["person"])
    _style.ci_dot(ax, i, r.recognition, r.ci95, color)
    nm = _style.cohort_name(r.cohort) if hasattr(_style, "cohort_name") \
        else _style.COHORT_NAMES.get(r.cohort, r.cohort.replace("_", " "))
    labels.append((nm, r.cohort in CREDENTIAL_COHORTS))

ax.set_yticks(range(len(tab)))
ax.set_yticklabels([l for l, _ in labels], fontsize=7.2)
for tick, (_l, is_cred) in zip(ax.get_yticklabels(), labels):
    if is_cred:
        tick.set_fontweight("bold")
ax.set_ylim(-1, len(tab))
_style.recog_xaxis(ax)

# zone annotations along the top
ax_top = ax.secondary_xaxis("top")
ax_top.set_xticks([])
for x0, x1, name in [(0.0, 0.10, "silent"), (0.10, 0.60, "discriminative"),
                     (0.60, 1.0, "universal")]:
    ax.annotate(name, xy=((x0 + x1) / 2, len(tab) - 0.2),
                ha="center", va="bottom", fontsize=8.5, style="italic",
                color="#555555")
    if x1 < 1.0:
        ax.axvline(x1, color="#cccccc", linewidth=0.7, zorder=1)

# floor label
ax.annotate("synthetic-null floor", xy=(max(0.02, fl["_people"]), 1.0),
            xytext=(0.055, 0.4), fontsize=7.5, color=RECOG["floor"],
            arrowprops=dict(arrowstyle="-", color=RECOG["floor"], lw=0.8))

# legend: person vs artifact
from matplotlib.lines import Line2D
ax.legend(handles=[
    Line2D([0], [0], marker="o", color="none", markerfacecolor=RECOG["person"],
           markersize=6, label="people cohorts"),
    Line2D([0], [0], marker="o", color="none",
           markerfacecolor=RECOG["artifact"], markersize=6,
           label="artifact cohorts"),
], loc="lower right", frameon=False, fontsize=8)

ax.grid(axis="x", color="#e8e8e8", linewidth=0.6, zorder=0)
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(HERE / "fig1_atlas.pdf")
fig.savefig(HERE / "fig1_atlas.png", dpi=150)
print(f"wrote fig1_atlas.pdf ({len(tab)} cohorts, baseline {BASELINE:.3f})")
