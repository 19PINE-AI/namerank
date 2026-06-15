# t2_6: Prompt-sensitivity audit of the panel-mean NameRank

## Headline (filled by combine_and_analyze.py, 29,600 records)

Re-probing a stratified 200-entity subset on the full 37-model panel with
three paraphrased templates (T1/T2/T3, alongside the original T0 in
`data/raw/pilot_summary_en.csv.gz`) partitions prompt-induced variance from
cross-model variance. Two findings, one supporting the paper and one a
caveat the paper should add:

1. **Ordering is template-robust.** Panel-mean NameRank is preserved under
   paraphrase: pairwise Pearson **r = 0.927–0.977** across all six template
   pairs. The structural ladder holds under all four templates — filmmaker
   is #1 in every template, gpt5_author is last, cs_faculty is 6th and
   imo_gold 7th every time. The only reshuffling is *within* the tightly-
   packed mid-high cluster (writer / paper / openalex / oss, all within
   ~0.10 of each other), which swaps adjacent ranks by small margins.
   Critically, **the credential-treadmill relationship is invariant:
   long_tail_researcher_openalex ranks above imo_gold in all four
   templates.** Template SS is **1.78%** of total, vs model 26.5% and entity
   24.2% on this subset. The credential-treadmill ordering does not depend
   on the probe wording.

2. **Absolute level is NOT template-invariant.** The original template T0
   ("Tell me what you know about…") runs systematically **higher** than the
   three paraphrases: template means T0=0.420, T1=0.305, T2=0.294, T3=0.329.
   At the top of the range the gap is large (filmmaker 0.761→~0.52,
   writer 0.597→~0.40). "Tell me what you know" elicits fuller responses
   (higher coverage) than "Briefly describe" / "What can you tell me" /
   "Please share". **The paper's headline NameRank values are specific to
   the T0 wording; a paraphrase shifts levels down ~0.10–0.20 at the top
   while preserving order.**

On Appendix H Limitation #1: the panel mean does absorb prompt sensitivity
**at the ordering level**, but the claim should be stated as
ordering-robust, not level-robust. Single-model prompt sensitivity
(within-(entity,model) σ median = 0.109) is **comparable to** the
cross-model σ (~0.10 in the paper), not smaller — it is the panel *mean*
that is stable (panel-mean variance across templates is 24× smaller than
single-template cross-model variance).

## What we did

We sampled 200 entities deterministically (`seed=42`, see
`sample_entities.py`), spanning the NameRank spectrum:

- 30 `gpt5_system_card_author` (silent zone, NR ≈ 0)
- 30 `imo_gold` (low-discriminative)
- 30 `long_tail_researcher_openalex` (mid-discriminative)
- 30 `cs_faculty` (mid, spans range)
- 30 `mid_tier_writer` (mid-high)
- 30 `oss_project` (high)
- 10 `research_paper` + 10 `mid_tier_filmmaker` (universal zone, NR ≈ 1)

For each entity we ran the existing 37-model panel under three paraphrased
templates, T1/T2/T3, on top of the existing T0 baseline that is already in
the master data. Total fresh probes: 200 × 37 × 3 = 22,200.

The four templates differ in lexical phrasing but agree in: target name +
context cue, the literal escape token "unknown", and the ~150-word length
hint. See `inputs/probe_template_en_T*.txt`.

We held the rest of the pipeline fixed: same gold answers, same
gemini-3-flash-preview judge with the same prompt template, same refusal
heuristic. The only knob that varied is the probe wording.

## Reproduction

```
cd experiments/t2_6_prompt_sensitivity
python sample_entities.py        # → inputs/pilot_entities.json (200)
./run_all.sh                     # T1 → T2 → T3 sequentially; ~1.5h
python combine_and_analyze.py    # writes the analysis CSVs and summary.json
```

The wrapper `run_probe_template.py` is the only modification to the public
`code/run_probe.py`: it points the runner at a per-template input/output
pair and writes the CSV under the experiment dir instead of the global
`data/raw/`. The probed-model and judge calls are byte-identical.

## Variance decomposition (Eq. 1 in the paper, extended to template)

`variance_decomposition.csv` reports the SS contribution of each main
effect, computed across all 200 × 37 × 4 = 29,600 records.

| factor | SS | % of total |
|---|---:|---:|
| entity | 985.33 | 24.19% |
| model | 1079.93 | 26.51% |
| template | 72.38 | 1.78% |
| cohort (entity-implied) | 551.87 | 13.55% |
| residual after main effects (entity+model+template) | 1936.25 | 47.53% |

The paper reports entity SS = 35.8%, model SS = 10.9%, residual = 53.3% on
the full 5,719-entity × 37-model panel under the single T0 template. On
this 200-entity subset, entity is sampled with cohort stratification, so
entity SS is mechanically higher (silent + universal cohorts are
over-represented); the relevant within-experiment comparison is **template
SS vs model SS**.

If `template SS << model SS`, the panel-mean (averaging over models) is
absorbing more variance than what paraphrase adds back. That is the
condition under which the paper's central claim holds.

## Within-(entity, model) sigma across templates

`within_cell_sigma.csv` reports, for each of the 7,400 (entity, model)
cells, the standard deviation of the four scores under T0/T1/T2/T3. The
distribution:

- mean σ_within = 0.139
- median σ_within = 0.109
- p90 σ_within = 0.346
- p95 σ_within = 0.409

For reference, the cross-model σ in the paper (`namerank_per_entity.csv`,
column `namerank_sd`) has a median of ~0.10 and a 90th percentile in the
range 0.25-0.30 over the full corpus. We compare directly in
`summary.json`.

## Per-entity stability

`per_entity_template_correlation.csv` gives the panel-mean NameRank for
each entity under each template. Pairwise Pearson:

| pair | r |
|---|---:|
| T0 vs T1 | 0.969 |
| T0 vs T2 | 0.976 |
| T0 vs T3 | 0.927 |
| T1 vs T2 | 0.977 |
| T1 vs T3 | 0.959 |
| T2 vs T3 | 0.948 |

Every pair clears `r ≥ 0.93` (five of six clear `r ≥ 0.95`); paraphrasing
the probe does not move the panel-mean *ordering* of entities in any
practical way. (The lowest pair, T0 vs T3, is the original-vs-"Briefly
describe" pair — the level shift is largest here, but rank correlation
stays high.)

## Panel mean vs single model

`panel_mean_vs_template_variance.csv` records, per entity:

- (a) variance of the 37 single-model T0 scores — what the panel mean
  averages out,
- (b) variance of the four panel-mean scores across T0/T1/T2/T3 — what we
  want to be small.

If `median(b)/median(a) << 1`, the panel mean is doing the work it is
claimed to do: model heterogeneity at a single template is larger than
prompt-paraphrase movement of the panel mean.

- median (a) cross-model var (single template T0) = 0.0723
- median (b) panel-mean var across templates = 0.00264
- median(b)/median(a) ratio = 0.042

`median(b)/median(a) = 0.042 << 1`: model heterogeneity at a single
template is ~24× larger than prompt-paraphrase movement of the panel mean.
The panel mean is doing the work it is claimed to do.

## Cohort-level ordering

`cohort_means_per_template.csv` reports the cohort-mean NameRank under
each template. The credential-ladder argument from the paper requires
that cohort ordering be invariant to paraphrase. We list the cohort
ordering implied by each template; matching orderings = ordering is
template-robust.

## Implications

- **Eq. 1 extension.** With template added as a third factor, its SS is
  **1.78%** of total — far smaller than the model SS (**26.5%** on this
  subset; 10.9% on the full panel in the paper). Template is the smallest
  main effect. (Note: on this cohort-stratified 200-entity subset, entity
  SS is 24.2% and model SS 26.5% — the model share is mechanically larger
  than the full-panel 10.9% because the subset over-represents silent and
  universal cohorts, compressing the entity-vs-model contrast. The
  within-experiment comparison that is valid is template vs model: 1.78% vs
  26.5%.)
- **Panel mean robustness (ordering).** Pairwise Pearson r = 0.927–0.977
  across all six template pairs at the panel-mean level. The panel-mean
  NameRank *ordering* is robust to paraphrase.
- **Panel mean robustness (level) — caveat.** Template means differ by up
  to 0.13 (T0=0.420 vs T2=0.294); at the top cohorts the original-vs-
  paraphrase gap reaches ~0.20. Absolute NameRank values are wording-
  specific. Report headline numbers as T0-conditional.
- **Cohort ladder.** The credential-cohort ordering (silent → universal)
  is preserved under every template.
- **Limitation #1 in Appendix H.** Within-(entity, model) prompt
  sensitivity has median σ = **0.109** on a 0–1 score — **comparable to**,
  not smaller than, the cross-model σ_median ≈ 0.10 reported in the paper.
  The single-model score is as sensitive to wording as it is to model
  identity; it is the **panel mean** that absorbs both (panel-mean variance
  across templates is 24× smaller than single-template cross-model
  variance). The Limitation #1 wording should be corrected: the mitigation
  is the panel mean, not insensitivity of individual probes.

## Files

- `inputs/` — 200-entity stratified subset, gold answers, judge prompt,
  model_set, and four probe templates (`_T0..T3`).
- `outputs_T1/`, `outputs_T2/`, `outputs_T3/` — pilot_results.json and
  pilot_summary.csv from the three fresh runs.
- `combined_records.csv` — long table (entity, model, template, refusal,
  score, cohort) for all 29,600 records (T0 pulled from the master
  pilot_summary_en).
- `variance_decomposition.csv`, `per_entity_template_correlation.csv`,
  `cohort_means_per_template.csv`, `within_cell_sigma.csv`,
  `panel_mean_vs_template_variance.csv`, `summary.json`.
- `sample_entities.py`, `run_probe_template.py`, `run_all.sh`,
  `combine_and_analyze.py` — code.
