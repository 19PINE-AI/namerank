"""Shared NeurIPS-style figure aesthetics for the NameRank paper.

Every figure script imports this module and calls ``apply_style()`` before
constructing any Axes. The module also exposes a coherent palette, helpers
for the three NameRank zones (silent / discriminative / universal), and
small drawing utilities that keep figure-to-figure visual language uniform.

Typographic choices are tuned for inclusion in an 11pt LaTeX article with
1-inch margins (textwidth ~ 6.5in), so default figure widths in the call
sites stay in the 6.0--10.0in range. Fonts are matplotlib's built-in
Computer Modern serif so figures blend into the LaTeX body text without
needing the (slow, optional) usetex pipeline.
"""
from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt

# ── Palette ────────────────────────────────────────────────────
# Restrained, slightly-desaturated palette. Each role has one canonical
# colour so the same semantic appears in the same hue across figures.
PALETTE = {
    # Zone colours (silent / discriminative / universal)
    "silent":         "#b3322c",   # warm red, dimmed
    "discriminative": "#2a6fb5",   # mid blue
    "universal":      "#2f8f4f",   # deep green
    # Accents
    "highlight":      "#d97826",   # orange — annotations, key callouts
    "baseline":       "#6e6e6e",   # neutral grey for baselines / dashed lines
    "rule":           "#444444",   # axis / spine
    "bg":             "#fafafa",   # subtle off-white panel background
    # Categorical (when we need >3 distinguishable colours)
    "cat0": "#2a6fb5",
    "cat1": "#d97826",
    "cat2": "#2f8f4f",
    "cat3": "#b3322c",
    "cat4": "#7a5dad",
    "cat5": "#0f9aa8",
}

# Map zone name -> light/dark pair (fill, edge).
ZONE_BANDS = {
    "silent":         ("#f3dadb", "#b3322c"),
    "discriminative": ("#dee9f4", "#2a6fb5"),
    "universal":      ("#dceee2", "#2f8f4f"),
}


def zone_for(value: float) -> str:
    """Return zone name for a NameRank value in [0, 1]."""
    if value <= 0.10:
        return "silent"
    if value <= 0.60:
        return "discriminative"
    return "universal"


def zone_color(value: float) -> str:
    """Convenience: hex color for the zone of a NameRank value."""
    return PALETTE[zone_for(value)]


def apply_style() -> None:
    """Install the global matplotlib rcParams used across all figures.

    Call this at the top of every ``make_*.py`` script before constructing
    Axes. It is safe to call repeatedly.
    """
    mpl.rcParams.update({
        # Font: Times-clone serif so figures blend into the mathptmx (Times)
        # LaTeX body. Nimbus Roman is the URW Times metric-compatible clone;
        # STIX supplies matching Times-like math glyphs.
        "font.family":        "serif",
        "font.serif":         ["Nimbus Roman", "Times New Roman",
                               "Liberation Serif", "DejaVu Serif"],
        "mathtext.fontset":   "stix",
        "axes.formatter.use_mathtext": True,

        # Sizes — tuned for an 11pt body
        "font.size":          10.0,
        "axes.titlesize":     11.0,
        "axes.labelsize":     10.5,
        "xtick.labelsize":    9.5,
        "ytick.labelsize":    9.5,
        "legend.fontsize":    9.5,

        # Axes / spines
        "axes.edgecolor":     PALETTE["rule"],
        "axes.linewidth":     0.8,
        "axes.spines.top":    False,
        "axes.spines.right":  False,
        "axes.titlepad":      9.0,
        "axes.labelpad":      4.0,

        # Ticks
        "xtick.direction":    "out",
        "ytick.direction":    "out",
        "xtick.major.size":   3.2,
        "ytick.major.size":   3.2,
        "xtick.major.width":  0.7,
        "ytick.major.width":  0.7,
        "xtick.color":        PALETTE["rule"],
        "ytick.color":        PALETTE["rule"],

        # Grid
        "axes.grid":          False,
        "grid.color":         "#cccccc",
        "grid.alpha":         0.55,
        "grid.linewidth":     0.55,

        # Legend
        "legend.frameon":     True,
        "legend.framealpha":  0.92,
        "legend.edgecolor":   "#cccccc",
        "legend.fancybox":    False,
        "legend.borderpad":   0.4,

        # Figure
        "figure.facecolor":   "white",
        "figure.dpi":         120,
        "savefig.dpi":        300,
        "savefig.bbox":       "tight",
        "pdf.fonttype":       42,
        "ps.fonttype":        42,
    })


def add_zone_bands(ax, *, y_extent=None, alpha=0.10, label=True,
                   silent_to=0.10, disc_to=0.60) -> None:
    """Shade the three NameRank zones along the x-axis.

    Parameters
    ----------
    ax : matplotlib Axes
    y_extent : (ymin, ymax) or None (uses ax.get_ylim())
    alpha : fill alpha
    label : if True, write the zone names along the top inside the axes
    silent_to, disc_to : zone breakpoints
    """
    if y_extent is None:
        y_extent = ax.get_ylim()
    y0, y1 = y_extent
    spans = [
        (0.0,        silent_to, "silent"),
        (silent_to,  disc_to,   "discriminative"),
        (disc_to,    1.0,       "universal"),
    ]
    for x0, x1, name in spans:
        fill, edge = ZONE_BANDS[name]
        ax.axvspan(x0, x1, color=fill, alpha=alpha, zorder=0, lw=0)
    if label:
        for x0, x1, name in spans:
            mid = 0.5 * (x0 + x1)
            ax.text(mid, y1, name,
                    ha="center", va="bottom",
                    fontsize=8.5, color=ZONE_BANDS[name][1],
                    transform=ax.get_xaxis_transform(),
                    clip_on=False)


def grid_x(ax, alpha=0.35) -> None:
    """Add a subtle x-axis-only grid (matches the rest of the figures)."""
    ax.grid(True, axis="x", linestyle="-", color="#d6d6d6",
            alpha=alpha, linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)


def grid_y(ax, alpha=0.35) -> None:
    ax.grid(True, axis="y", linestyle="-", color="#d6d6d6",
            alpha=alpha, linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)


def thin_spines(ax) -> None:
    """Hide top/right spines and tone down remaining spines."""
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(PALETTE["rule"])
        ax.spines[side].set_linewidth(0.8)


def annotate_value(ax, x, y, text, *, dx=0.008, fontsize=9, color="#222") -> None:
    """Place a small numeric label just past a bar end."""
    ax.text(x + dx, y, text, va="center", ha="left",
            fontsize=fontsize, color=color)


# ── Readable cohort names ──────────────────────────────────────
# Dataset cohort identifiers -> reader-facing names (matches paper prose).
COHORT_NAMES = {
    "mid_tier_gov_ai_policy": "AI-policy officials",
    "mid_tier_filmmaker": "Filmmakers",
    "programming_language": "Programming languages",
    "mid_tier_artist": "Artists",
    "database_or_data_system": "Databases & data systems",
    "award": "Awards",
    "benchmark": "ML benchmarks",
    "ai_hardware": "AI hardware",
    "dataset": "ML datasets",
    "mid_tier_musician": "Musicians",
    "mid_tier_chef": "Chefs",
    "ai_startup_or_company": "AI startups & companies",
    "mid_tier_comedian": "Comedians",
    "research_paper": "Research papers (>10K cites)",
    "mid_tier_historical": "Historical figures",
    "conference": "Conferences",
    "icpc_world_finals_gold": "ICPC World Finals gold",
    "putnam_fellow": "Putnam top-25",
    "mid_tier_medical": "Medical figures",
    "mid_tier_product": "Consumer products",
    "industry_product": "Industry products",
    "named_method": "Named ML methods",
    "mid_tier_actor": "Actors",
    "mid_tier_founder": "Founders",
    "mid_tier_oss_maintainer": "OSS maintainers",
    "mid_tier_writer": "Writers",
    "oss_project": "OSS projects",
    "foundation_model": "Foundation models",
    "mid_tier_journalist": "Journalists",
    "mid_tier_religious": "Religious figures",
    "mid_tier_athlete": "Athletes",
    "long_tail_researcher_openalex": "OpenAlex researchers (long tail)",
    "reference_pilot": "Diagnostic reference set",
    "website_or_service": "Websites & services",
    "mid_tier_online_course": "Online courses",
    "mid_tier_podcast": "Podcasts",
    "cs_faculty": "CS faculty",
    "mid_tier_vc": "VCs",
    "long_tail_paper": "Long-tail papers (50-500 cites)",
    "noi_china_gold": "NOI China gold",
    "mid_tier_book": "Books",
    "imo_gold": "IMO gold",
    "mid_tier_politician": "Politicians",
    "msra_phd_fellowship": "MSRA PhD Fellowship",
    "ioi_gold": "IOI gold",
    "rhodes_scholar": "Rhodes Scholars",
    "cmo_china_gold": "CMO China gold",
    "mid_tier_architect": "Architects",
    "cpho_china_first_prize": "CPhO China first prize",
    "deepseek_v3_author": "DeepSeek-V3 authors",
    "long_tail_researcher_ikp": "IKP researchers (long tail)",
    "mid_tier_activist": "Activists",
    "mid_tier_yc_company": "YC companies",
    "gpt5_system_card_author": "GPT-5 system-card authors",
}

# The nine credential cohorts (bold labels in cohort-level figures).
CREDENTIAL_COHORTS = {
    "imo_gold", "ioi_gold", "cmo_china_gold", "noi_china_gold",
    "cpho_china_first_prize", "rhodes_scholar", "msra_phd_fellowship",
    "icpc_world_finals_gold", "putnam_fellow",
}


def pretty_cohort(slug: str) -> str:
    """Reader-facing cohort name for a dataset identifier."""
    return COHORT_NAMES.get(slug, slug.replace("_", " "))
