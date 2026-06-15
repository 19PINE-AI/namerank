# T3.1 — Training-cutoff gradient: is the "silent zone" a timing effect?

## Question

NameRank's silent zone could be one of two things:

* **Intrinsic obscurity** — the entity is below the corpus-density
  recognition threshold, full stop; or
* **Corpus timing** — the entity is recent, and models simply have not yet
  ingested the text that names them. Newer models would "fix" it.

These have opposite implications for the §6.2 longitudinal predictions. If
the silent zone is a timing artifact, a 2027 re-run mechanically lifts the
recent cohorts and the credential gap could *close* for the wrong reason.

## Design (zero new API cost — existing released data only)

Two cohorts are **first-appearance** cohorts: their members became nameable
in *any* indexable corpus on a sharp date, and their gold answer is
literally "X is listed as a contributor on [document]."

| cohort | n | emergence | document |
|---|---:|---|---|
| `deepseek_v3_author` | 69 | **2024-12** | DeepSeek-V3 Technical Report (arXiv:2412.19437) |
| `gpt5_system_card_author` | 80 | **2025-08** | OpenAI GPT-5 System Card |

The 37-model panel's training cutoffs span **2023-10 → 2026-03**
(`data/analysis/model_cutoffs.json`), straddling both dates. A model whose
cutoff *predates* an emergence date **cannot** have seen the document, so it
must refuse or hallucinate. If the silent zone is a timing effect,
recognition of these cohorts should jump at the emergence date.

The essential control: **every other cohort is nameable since well before
2023** (Hinton, established CS faculty, IMO 2005–2015 golds). Their
recognition should be flat in cutoff — any rise is a model-capability/
generosity confound, not corpus growth. We net it out with a matched-split
difference-in-differences.

## Result 1 — the cutoff gradient is dominated by a capability confound

Per-cohort slope of (model-mean score) on (model cutoff), all 37 models:

```
mid_tier_comedian      +0.196 /yr   r=+0.66
cs_faculty             +0.158 /yr   r=+0.57
reference_pilot        +0.157 /yr   r=+0.77   (Hinton, Altman, …)
research_paper         +0.125 /yr   r=+0.74
imo_gold (2005–2015)   +0.043 /yr   r=+0.15
...
deepseek_v3_author     +0.065 /yr   r=+0.23   <-- RECENCY
gpt5_system_card_author−0.021 /yr   r=−0.25   <-- RECENCY
```

**Every established cohort rises ~+0.10 to +0.20 NameRank per year of
training cutoff.** Geoffrey Hinton did not become more nameable in 2025;
`reference_pilot` (which includes him) rises +0.157/yr anyway. This is
model-capability and willingness-to-commit drift: newer models are larger,
better, and less prone to refuse. **It affects the recency cohorts *less*
than the established ones, not more.**

> **Methodological consequence (new caveat for the paper).** NameRank is
> **not comparable across model vintages**. A naive longitudinal re-run
> (§6.2) will conflate corpus growth with capability drift: the whole panel
> floats upward ~0.13/yr regardless of corpus change. Longitudinal claims
> must be made on **within-run relative gaps** (e.g. IMO-minus-OpenAlex),
> not absolute levels, and the §6.2 predictions should be restated that way.

## Result 2 — crossing the cutoff is necessary but NOT sufficient

Naive pre/post split looks like a timing effect for DeepSeek — until you
control for the drift in Result 1.

| cohort | pre-cutoff mean | post-cutoff mean | raw jump | matched DiD |
|---|---:|---:|---:|---:|
| `deepseek_v3_author` (split @2024-12) | 0.113 | 0.233 | **+0.121** | **−0.016** |
| `gpt5_system_card_author` (split @2025-08) | 0.051 | 0.020 | −0.031 | **−0.061** |

The matched DiD subtracts the same-split jump averaged over the stable
controls (`cs_faculty`, `long_tail_researcher_openalex`, `imo_gold`):

* DeepSeek raw jump +0.121 ≈ control jump +0.137 → **DiD −0.016**. The
  entire +0.121 "timing jump" is explained by general capability drift over
  the same cutoff range. There is **no recency-specific corpus-absorption
  signal.**
* GPT-5 system-card cohort actually goes **more silent** post-cutoff:
  refusal rises **0.49 → 0.79**. The post-2025-08 fleet is dominated by
  RL-tuned-against-hallucination frontier models (gpt-5.3, grok-4.20,
  minimax-m2.7 all refuse ~100%) that *demonstrably could have ingested the
  GPT-5 system card* yet correctly refuse on a name appearing only in a
  486-person contributor list.

The regression DiD agrees: DeepSeek −0.034/yr, GPT-5 −0.120/yr (both ≤ 0).

The per-model DeepSeek breakdown (`outputs/per_model_cohort_means.csv`)
makes the mechanism visible: the high scorers are the *generous* models
(claude-sonnet-4.6 0.74, claude-opus-4.6 0.65, gemma-4-31b 0.47) and the
zeros are the *strict* ones (gpt-5.3, grok-4.20 at ~100% refusal) — and both
groups span the whole cutoff range. The variance is per-model refusal
policy, not cutoff.

## Bottom line

**The silent zone is intrinsic, not a timing artifact.** Being one of
200–486 listed contributors does not manufacture recognition, even in models
trained after the document was published and that plausibly ingested it.
This is a **positive validation of threshold-cleanliness**: corpus
*presence* above a density threshold is what NameRank measures; mere
*inclusion* in the training set is necessary but nowhere near sufficient.

Two things for the paper:

1. **Add a caveat:** NameRank is not comparable across model vintages
   (~+0.13/yr capability drift on every cohort). Longitudinal §6.2 claims
   must use within-run relative gaps. *(This is the more important output of
   this experiment than the silent-zone result.)*
2. **Strengthen threshold-cleanliness §3.2:** post-cutoff models that
   ingested the GPT-5 system card still refuse on its contributors
   (refusal 0.49→0.79) — recognition ≠ ingestion.

## Files

* `analyze.py` — full analysis (reads only released artifacts).
* `outputs/per_model_cohort_means.csv` — (model × cohort) mean score,
  refusal, cutoff. 37 × 54.
* `outputs/cohort_cutoff_slopes.csv` — per-cohort slope of mean score on
  cutoff month + Pearson r.
* `outputs/natural_experiment.csv` — pre/post splits for the two recency
  cohorts plus same-split placebos on the three stable controls.
* `outputs/did.csv` — regression difference-in-differences.
* `outputs/summary.json` — everything, including matched-split DiD.

## Reproduction

```
cd experiments/t3_1_cutoff_gradient
python3 analyze.py
```
