# T2.9 — Fractional Citations vs h-Index as NameRank Predictors

Direct test of the "named-attribution-per-paper density" mechanism proposed
in the NameRank paper. If h-index dominates raw citations because h-index
captures sustained named-output rather than viral high-co-author papers,
then **fractional citations** (citations divided by co-author count, summed
across works) should be the cleaner primitive — they explicitly down-weight
hyper-authored papers and reward sole/first/last contributions.

We pulled every work for each of the 771 `long_tail_researcher_openalex`
authors via the OpenAlex `/works` endpoint (one paginated request per
author, ~84 s wall time at 8-way concurrency), then computed per-author
aggregates. All 771 authors returned at least one work; the summed
`total_citations_from_works` matches the entity-level `cited_by_count`
within a median ratio of 1.00, confirming we collected the full
publication record.

## Headline result

| Sole predictor (log1p)  | R²    | Spearman ρ |
|-------------------------|-------|-----------|
| **h_index**             | **0.398** | +0.604 |
| n_works                 | 0.337 | +0.552 |
| first_last_citations    | 0.268 | +0.505 |
| fractional_citations    | 0.154 | +0.421 |
| cited_by_count          | 0.137 | +0.382 |
| mean_authors            | 0.000 | −0.005 |

**Fractional citations do not beat h-index.** They land at R² = 0.154,
barely above raw citations (0.137) and less than half of h-index (0.398).
The attribution-density mechanism, in its sharpest operational form,
**does not receive direct empirical support**: re-weighting citations by
the inverse of the author count produces no meaningful gain over the raw
citation count it was meant to clean up.

The features that *do* beat raw citations are h-index, n_works, and
first/last-author citation sum — all three of which are bounded or
discounted versions of citation count that emphasize **breadth of named
output** rather than **per-paper attribution share**.

## What dominates? h-index, with no marginal room

Adding any of the other five log1p features on top of `log1p(h_index)`
moves R² by at most +0.027 (from `first_last_citations`); fractional
citations contribute Δ = +0.003. The joint OLS over all six predictors
reaches R² = 0.428 — only 0.030 above h-index alone — and the
standardized coefficient on `log1p_h_index` (+0.579) is roughly **three
times** the next-largest absolute coefficient. h-index already absorbs
nearly all the predictable variance.

## Decile pattern (Appendix-F style)

| Decile | h_index mean NR | frac_cites mean NR |
|--------|----------------:|--------------------:|
| D1 | 0.220 | 0.328 |
| D5 | 0.466 | 0.447 |
| D10 | 0.600 | 0.544 |

The h-index curve spans **0.38 NameRank units** end-to-end; the
fractional-citations curve spans only **0.22**. The D1 cell is the
decisive one: low-h authors are almost twice as anonymous to LLMs as
low-fractional-citation authors. Stretching the bottom of the curve is
exactly what a "sustained named output" signal should do, and it is
exactly where fractional citations under-perform.

See `decile_comparison.png` for the overlaid curves.

## Interpretation

The cleanest reading is that **h-index is not a proxy for attribution
density** — it has its own structural property that fractional citations
fail to recover. Two specific things that h-index does and fractional
citations don't:

1. **It is a min-threshold count, not a weighted sum.** An author with
   h = 30 must have *30 papers each cited ≥30 times*. Fractional
   citations can be inflated by a single co-authored blockbuster
   (`Yoon Kim`, `Wes McKinney` at the top of the fractional list both
   have h-indices well below their fractional rank). The harsh
   min-threshold is what tracks how often a name *recurs* in scholarly
   discourse, which is what LLM training corpora actually see.
2. **It saturates at one paper per citation rank.** A 5000-citation
   solo paper and a 5000-citation 10-author paper contribute identically
   to h. They diverge by 9× under fractional citations. Empirically,
   NameRank does not seem to penalize the 10-author paper much: the
   `mean_authors` regressor has R² ≈ 0 and ρ ≈ 0.

So the mechanism the paper proposed is *directionally* right —
discount-by-author-count helps a little (frac > raw cites by Δ R² = 0.02)
— but it is not the **primary** lever. The dominant signal is closer to
"how many distinct works does the author have, each with non-trivial
citation mass?" — i.e. h-index itself, or its near-cousin n_works
(R² = 0.337).

## Bottom line

**h-index wins, fractional citations do not confirm the attribution-density
story.** The mechanistic prose in the paper should be tightened: the
empirical pattern is "h-index captures number-of-recurrent-named-papers,"
not "h-index captures attribution-per-paper density." The latter would
predict that explicitly attribution-weighted citations should match or
beat h-index, and they do not — they sit closer to raw citations.

## Files

- `fetch_works.py` — OpenAlex `/works` fetcher (resumable, 8-way, polite).
- `analyze.py` — sole-predictor, joint-OLS, and decile computations.
- `plot_deciles.py` — overlay plot of all five predictors.
- `author_works_metrics.csv` — per-author features (n=771).
- `regression_results.csv` — sole-R², joint OLS, two-way-vs-h tables.
- `decile_comparison.csv` — mean/median NameRank per predictor decile.
- `decile_comparison.png` — overlay figure.
- `fetch.log`, `analyze.log` — run logs.
