"""F20 — Country gradient in CS-faculty recognition.
Institution -> country via code/country_affiliation.py keyword map; dot + 95%
CI per country (n>=8 firm, smaller faded).
Output: fig_country.pdf
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "code"))

import matplotlib.pyplot as plt
import numpy as np
import _data
import _style
from _style import RECOG

# import the keyword map without running the script's main
import importlib.util
spec = importlib.util.spec_from_file_location(
    "ca", REPO / "code" / "country_affiliation.py")
ca = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(ca)
except Exception:
    pass  # module main may fail on paths; we only need the map


def lookup(inst):
    for country, kws in ca.COUNTRY_KEYWORDS.items():
        for kw in kws:
            if kw.lower() in inst.lower():
                return country
    return None


_style.apply_style()
meta = {e["id"]: e for e in json.loads(
    (REPO / "data/inputs/pilot_entities.json").read_text())}
df = _data.per_entity("main")
df = df[~df.synthetic & (df.cohort == "cs_faculty")].copy()
df["country"] = df.entity_id.map(
    lambda i: lookup(meta.get(i, {}).get("institution", "") or ""))
df = df.dropna(subset=["country"])
print("data sources:", _data.source_report(), f"| n={len(df)} faculty mapped")

g = df.groupby("country").recognition
tab = (np.round if False else (lambda x: x))(None) or None
import pandas as pd
tab = pd.DataFrame({"m": g.mean(), "ci": 1.96 * g.std() / np.sqrt(g.size()),
                    "n": g.size()}).sort_values("m")
tab = tab[tab.n >= 4]

fig, ax = plt.subplots(figsize=(5.6, 0.32 * len(tab) + 1.2))
for i, (c, r) in enumerate(tab.iterrows()):
    firm = r.n >= 8
    col = RECOG["person"] if firm else RECOG["muted"]
    _style.ci_dot(ax, i, r.m, r.ci, col, size=30 if firm else 18)
    ax.annotate(f"n={int(r.n)}", xy=(1.02, i), xycoords=("axes fraction", "data"),
                fontsize=6.6, color="#888888", va="center")
ax.set_yticks(range(len(tab)))
ax.set_yticklabels(tab.index, fontsize=8.2)
ax.set_ylim(-0.7, len(tab) - 0.3)
_style.recog_xaxis(ax, 0, 1.0)
ax.set_xlabel("CS-faculty recognition rate")
ax.grid(axis="x", color="#ececec", linewidth=0.6, zorder=0)
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(HERE / "fig_country.pdf")
fig.savefig(HERE / "fig_country.png", dpi=150)
print(f"wrote fig_country.pdf ({len(tab)} countries)")
