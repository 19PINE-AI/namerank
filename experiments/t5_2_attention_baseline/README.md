# T5.2 — Is NameRank just Wikipedia-pageview rank?

**Question.** Web-attention metrics (search volume, Google Trends, Wikipedia
pageviews) also place heterogeneous entities on a single cross-domain axis,
so the §3.1 claim that "no prior instrument supports this placement" is
false as stated. Does NameRank reduce to the strongest freely available
attention metric — en-Wikipedia article pageviews — or does it measure
something the attention ledger does not carry? The defensible claim: no
*verification-based* instrument spans domains, and the attention axis is
empirically a different axis.

## Data

* Article resolution reused from **T1.4** (`wikipedia_lookup.csv`): 1,681 of
  5,719 entities (29.4%) match an en-Wikipedia article under its strict
  disambiguation rule.
* `fetch_pageviews.py` — Wikimedia REST per-article pageviews, user traffic,
  monthly, **2023-07-01 .. 2025-06-30** (24 months; long window suppresses
  event spikes). `repair_titles.py` re-resolves canonical titles and
  re-fetches; NB the REST endpoint 404s if RFC-3986 sub-delims are
  percent-encoded (`Evan_O%27Dorney` → 404, `Evan_O'Dorney` → 200).
* Exclusions: **48** articles created *after* the window (Ollama and vLLM
  were created 2026-04 — the model panel knew these tools years before
  Wikipedia did); **16** T1.4 disambiguation false positives dropped by a
  base-name token filter (e.g. "DSPy (Stanford)" had matched *Stanford
  University*). Final matched set **n = 1,617** (28.3%).
* NameRank from `data/analysis/namerank_per_entity.csv`; h-index from
  T2.9 `author_works_metrics.csv`.

## Findings (`outputs/results.json`)

### (1) The metric is undefined for 71% of the pilot

4,038 entities (70.6%) have no resolvable article. They average NameRank
0.419 with a p10–p90 span of **0.16–0.68** — spanning the entire
discriminative zone, where all the paper's findings live (credential
cohorts, CS faculty, OpenAlex long tail). A pageview ranking is not merely
coarse there; it is undefined.

### (2) Where defined, it explains 6% of NameRank — and 10% within cohort

Among the 1,617 matched entities: Pearson r = 0.245, **R² = 0.06** overall;
pooled cohort-demeaned partial r = 0.315, **R² = 0.10** (29 cohorts with
n ≥ 15).

### (3) The correlation has a sign structure: flow vs stock

Per-cohort r ranges from **+0.81 (actors), +0.77 (athletes), +0.62
(writers)** down to **−0.54 (OSS projects), −0.44 (databases), −0.35
(programming languages), −0.33 (long-tail researchers)**; median cohort
r = −0.16. For celebrity cohorts, current attention aligns with accumulated
corpus presence. For technical cohorts it *anticorrelates*: Chainer (6.4K
views/24m, NameRank 0.94), Theano (26K, 0.89), and Caffe (28K, 0.81) are
corpus-saturated but no longer looked up, while Stable Diffusion (1.3M
views, 0.38) and bare-name Perplexity (1.3M, 0.19) draw enormous current
traffic. Pageviews read the *flow* of current curiosity; NameRank reads the
accumulated *stock* of name-bearing text — the paper's §5.3 clock
distinction, observed directly.

### (4) On the long-tail researcher cohort, pageviews do not compete with h-index

| Predictor (long_tail_researcher_openalex) | n | R² |
|---|---|---|
| log h-index, all | 771 | **0.398** |
| log pageviews (zero-coded where no article), all | 771 | 0.015 |
| log h-index, article-having subset | 58 | 0.388 |
| log pageviews, article-having subset | 58 | 0.110 (r = **−0.33**) |

On the same 58 researchers where both are defined, pageviews correlate
*negatively* with NameRank while h-index explains 39%.

## Paper integration

Figure `paper/figures/fig_attention.pdf` (`make_fig_attention.py`), placed
in Appendix `app:confounds`; argued in §3.1 (single-axis claim restated as
verification-based) and Related Work (attention-metrics paragraph).

## Caveats

* Matched entities are the prominent slice; range restriction attenuates
  the overall r. The within-cohort estimate and the long-tail subset are
  the fair tests, and they agree.
* Pageviews measure attention *to the article*, conditional on it existing —
  the same English-attention conditioning as the T4.1 events ledger (there
  a feature; here the coverage gap).
* The T1.4 strict-rule article match itself has residual false
  positives/negatives beyond the 16 dropped; spot checks suggest they are
  not leverage points after the token filter.
