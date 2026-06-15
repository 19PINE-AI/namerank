# T1.4 — Does Wikipedia presence dominate NameRank?

**Question.** NameRank correlates with h-index in the long-tail OpenAlex
cohort (R² ≈ 0.40). The published paper does not test the simpler hypothesis
that NameRank is dominated by a single binary signal — "does this entity
have a Wikipedia page?" — with bibliometrics entering only conditional on
Wikipedia presence. If true, this would reframe the external-validity story.

## Data

* 5 719 pilot entities (`data/inputs/pilot_entities.json`)
* Per-entity NameRank (`data/analysis/namerank_per_entity.csv`)
* For each entity, MediaWiki + Wikidata + Wikipedia pageviews API:
  * `has_wikipedia` — does an English Wikipedia article describing *this*
    entity exist?
  * `sitelinks` — number of Wikipedia language editions linked from the
    matching Wikidata item.
  * `pageviews_30d` — last 30 days of English-Wikipedia views.

Disambiguation uses a two-stage check: (a) the candidate page title must
contain the entity name (substring match for artifacts; ≥2 token overlap
for people, after Unicode-fold), and (b) the article's intro paragraph
must mention either the entity's institution / subfield (from the
`context` field) or a cohort-specific keyword set (e.g. "professor",
"mathematician", "language model"). Disambiguation pages are skipped.

**Coverage.** 5 719 / 5 719 entities queried (full census). 1 681 (29.4 %)
matched a Wikipedia article under the strict rule. A robustness pass
with a **lenient** rule (counting "family" pages like `Claude (language
model)` as covering `Claude 4 Opus`) bumps the rate to 32.1 %; results
are virtually unchanged.

## Findings

### (1) Does Wikipedia presence dominate NameRank on long-tail researchers?

Regression on `long_tail_researcher_openalex` (n = 771):

| Model                                                   |     R²    | marginal R² added |
| ------------------------------------------------------- | --------: | ----------------: |
| `has_wikipedia` only                                    | **0.022** |             0.022 |
| + `log(sitelinks)`                                      |     0.029 |             0.007 |
| + `log(pageviews_30d)`                                  |     0.029 |             0.000 |
| + `log(h_index)`                                        | **0.405** |         **0.376** |
| + `log(citations)`                                      |     0.405 |             0.000 |
| Reference: `log(h_index)` **alone**                     | **0.398** |                 — |
| Reference: `has_wikipedia + log(h_index)`               |     0.399 |             0.000 |

**`has_wikipedia` explains 2 % of NameRank variance among long-tail
researchers; `log(h_index)` explains 40 %.** Adding the full Wikipedia
block (binary + sitelinks + pageviews) before h-index gains 2.9 % of R²;
adding h-index on top adds another **37.6 %**. The opposite ordering —
h-index first, then Wikipedia — gains only 0.1 % from Wikipedia. **The
"Wikipedia dominance" hypothesis is rejected for long-tail researchers.**

Crucially, h-index R² is **virtually identical** in the two regimes:

| Sub-sample        |     n |  mean NR | R² of `log(h_index)` |
| ----------------- | ----: | -------: | -------------------: |
| With Wikipedia    |    60 |    0.55  |              **0.38** |
| Without Wikipedia |   711 |    0.46  |              **0.39** |

The paper's bibliometric correlation is **not** an artefact of "h-index
proxies notability via Wikipedia". h-index continues to track NameRank
even among the 92 % of researchers with no Wikipedia article.

### (2) Cross-cohort variance decomposition (all 5 719 entities)

| Predictor block                            |     R²   |
| ------------------------------------------ | -------: |
| `has_wikipedia` only                       |    0.078 |
| + log pageviews + log sitelinks            |    0.095 |
| Cohort fixed effects (54 cohorts) only     | **0.470** |
| `has_wikipedia` + cohort FE                |    0.474 |
| Wiki block + cohort FE                     |    0.480 |

Cohort identity explains **47 % of the variance in NameRank across the
whole pilot**, while Wikipedia presence adds only **0.5 percentage
points** on top. Most of the cross-entity variation NameRank captures
lives in cohort-level structure (entity type, prominence tier, language
of origin), not in a Wikipedia-yes/no flag. The lenient definition
gives essentially the same picture (R² for `has_wikipedia` = 0.12,
marginal over cohort FE = 0.21 pp).

### (3) Does Wikipedia presence explain the credential treadmill?

Per-cohort coverage (`credential_wiki_coverage.csv`):

| Cohort                                  |    n | wiki % | mean NR |
| --------------------------------------- | ---: | -----: | ------: |
| reference\_pilot                        |   37 |   40.5 |   0.452 |
| cs\_faculty                             |  698 |   12.5 |   0.417 |
| icpc\_world\_finals\_gold               |   18 |   11.1 |   0.610 |
| long\_tail\_researcher\_openalex        |  771 |    7.8 |   0.464 |
| cmo\_china\_gold                        |  131 |    6.1 |   0.302 |
| msra\_phd\_fellowship                   |  237 |    5.1 |   0.343 |
| ioi\_gold                               |   68 |    4.4 |   0.341 |
| cpho\_china\_first\_prize               |   50 |    4.0 |   0.182 |
| imo\_gold                               |  197 |    3.5 |   0.362 |
| putnam\_fellow                          |   35 |    2.9 |   0.608 |
| long\_tail\_researcher\_ikp             |  159 |    0.6 |   0.158 |
| noi\_china\_gold                        |   29 |    0.0 |   0.367 |
| rhodes\_scholar                         |   36 |    0.0 |   0.315 |

The credential cohorts **do** have markedly lower Wikipedia coverage
than the reference cohort (40.5 %) or working researchers (7.8 %): all
nine credential cohorts sit in the 0–11 % band. But the mapping from
Wikipedia coverage to NameRank is loose. Putnam fellows have only
2.9 % coverage yet a mean NR of 0.608 — higher than every cohort
except ICPC golds. cmo\_china\_gold has *higher* wiki coverage than
imo\_gold yet a *lower* mean NameRank (0.302 vs 0.362). The credential
treadmill therefore involves **at least two distinct mechanisms**: low
Wikipedia coverage is one, but base-rate model familiarity with
specific credentials (IMO vs CPhO) and English-language exposure
operate on top.

### (4) Stanford vs. Tsinghua, conditional on Wikipedia

CS-faculty subset (n = 332 with country tag, of which 302 USA / 30
China; full per-row data in `stanford_tsinghua_wiki.csv`):

|                       | mean NR |  wiki % | mean PV |
| --------------------- | ------: | ------: | ------: |
| USA (all)             |   0.460 |   23.5 |     —   |
| China (all)           |   0.311 |    0.0 |     —   |
| **Stanford (n = 19)** |   0.537 |   36.8 |   332.4 |
| **Tsinghua (n = 4)**  |   0.258 |    0.0 |     0.0 |

Regressing NR on a US-dummy gives β = 0.149 (R² = 0.083). Adding
`has_wikipedia`: β\_US drops to **0.115** (a 22 % reduction) and R²
jumps to 0.236. Restricted to entities WITHOUT Wikipedia, the US-China
gap is still **β = 0.115** with R² = 0.064 — essentially the same as
in the full sample. **Wikipedia presence accounts for ≈ 1/4 of the
Stanford-Tsinghua gap, but ≈ 3/4 of the gap remains after controlling
for it.** The institution effect therefore reflects more than just
"American institutions get Wikipedia articles" — base-rate exposure of
English-language LLMs to anglophone researchers is the rest.

## Bottom line

* **Wikipedia presence does NOT dominate NameRank.** Across the full
  5 719-entity pilot it explains 8 % of variance; among long-tail
  researchers, 2 %. Cohort identity explains 47 %; h-index explains
  40 % (long-tail researchers).
* **h-index dominance survives Wikipedia controls.** Marginal R² of
  log h-index after the full Wikipedia block is 37.6 %, and the
  log-h-index regression has R² ≈ 0.38 in both the Wikipedia-present
  and Wikipedia-absent subsamples. NameRank tracks bibliometric
  productivity, not a Wikipedia-yes-or-no flag.
* **Wikipedia partially explains the credential treadmill — but only
  partially.** All credential cohorts have ≤ 11 % Wikipedia coverage,
  yet their NameRank means span a wide range (0.18 – 0.61) and don't
  line up with coverage rates.
* **Wikipedia partially explains the Stanford-Tsinghua gap (~1/4),
  not most of it (~3/4 survives).** Anglocentric LLM exposure is the
  larger story.

The simpler "NameRank = has\_wikipedia" hypothesis is therefore
**rejected**. The external-validity story in the paper holds: NameRank
correlates with measurable bibliometric productivity in a way that is
not reducible to whether the entity happens to have its own English
Wikipedia article.

## Files

* `wiki_lookup.py`         – bulk MediaWiki / Wikidata / pageviews lookup.
* `wikipedia_lookup.json`  – per-entity cache (5 719 records).
* `wikipedia_lookup.csv`   – flattened, one row per entity.
* `analyze.py`             – all four headline analyses.
* `regression_results.json` – every R², β, and marginal contribution.
* `credential_wiki_coverage.csv` – per-cohort coverage and NR means.
* `stanford_tsinghua_wiki.csv` – per-faculty (US + China cs\_faculty)
  with NR, has\_wiki, sitelinks, pageviews.
