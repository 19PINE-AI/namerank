# `data/analysis/` — vintage notice

**This directory contains two different analysis vintages. Read this before using any file for numbers that appear in the paper.**

The published NameRank paper reports the **recognition-verdict** metric over a
**36-model** panel. Most files in this directory predate that run: they are an
earlier **coverage×accuracy (graded)** analysis over a **37-model** panel, and
their numbers **do not match the paper**. They are retained for provenance, not
for citation.

## Authoritative (recognition vintage — matches the paper)

| File | Contents |
|---|---|
| `namerank_per_entity.csv` (2026-07-14) | Per-entity recognition scores, 36-model panel — the metric the paper reports. |
| `../../paper/figures/computed_numbers.json` | The exact figures/numbers cited in the paper, computed from the recognition run. |

Every figure in the paper is generated from the recognition run
(`paper/figures/_data.py` loads the recognition records, not the files below).

## Superseded (2026-05-15 — coverage×accuracy, 37-model panel; do NOT use for paper numbers)

`a1_scoring_rule_summary.json`, `a2_panel_size_curve.csv`,
`a3_conditional_namerank.csv`, `a4_artifact_mediation.csv`,
`attribution_pairs.csv`, `attribution_pairs_v2.csv`, `cohort_summary.csv`,
`creator_attribution_dense.csv`, `credential_ladder.csv`,
`cross_language_per_entity.csv`, `cs_faculty_by_country.csv`,
`east_west_per_cohort.csv`, `east_west_per_entity.csv`, `namerank_matrix.json`,
`per_model_summary.csv`.

(`model_cutoffs.json` is training-cutoff metadata; it is metric-independent but
reflects the earlier 37-model panel roster.)

### Why they disagree with the paper

These files score the graded coverage×accuracy metric, which credits partial and
context-derivable overlap; the paper scores a binary recognition verdict, which
credits only a specific, non-guessable, verified fact. The two metrics differ
most on low-recognition cohorts. For example, `credential_ladder.csv` lists
IMO gold at **0.362** (cov×acc) and `per_model_summary.csv` lists **37** models,
whereas the paper reports IMO gold at **0.12** under the recognition metric over
a **36**-model panel.

## Maintainer note

Some scripts still read the superseded files (`code/`, `site/scripts/build_data.py`,
`docs/`, and a few unused `paper/figures/make_fig4_*.py` scripts). Regenerating
this directory from the recognition run — and refreshing the site and docs that
consume it — is tracked as follow-up work; until then, treat the files above as
authoritative and everything dated 2026-05-15 as superseded.
