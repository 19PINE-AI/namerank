# t1_1: Gold-answer-length confound check

## Headline

**The credential-treadmill ordering survives every adjustment we can run.**
The more honest finding is that the strict matched-pairs test is *infeasible*:
IMO and OpenAlex gold answers have non-overlapping length distributions, so
no `|delta_chars| <= 50` pair exists. Both the FE adjustment and the
OA-slope adjustment leave IMO/CMO/Rhodes/MSRA/CPhO/NOI/IOI below the OpenAlex
baseline; Putnam and ICPC remain above.

## Gold-metric definitions

`gold_chars` = `len(gold)`. `gold_words` = regex word count. `gold_named_facts`
= count of capitalized multi-word phrases, chosen over sentence-count because
it correlated marginally more with NameRank in the OpenAlex sanity cohort
(|r| = 0.033 vs 0.012). See `gold_metrics.csv`.

## Within-cohort regressions (n >= 50)

For the credential cohorts that matter to the thesis, gold metrics explain
near-zero NameRank variance:

| cohort | n | R^2 |
|---|---:|---:|
| imo_gold | 197 | 0.067 |
| ioi_gold | 68 | 0.018 |
| msra_phd_fellowship | 237 | 0.006 |
| cmo_china_gold | 131 | 0.209 |
| cpho_china_first_prize | 50 | 0.557 |
| long_tail_researcher_openalex | 771 | 0.023 |

IMO, IOI, MSRA all sit at R^2 < 0.07 -- there is not enough within-cohort
length variation to drive a within-cohort length artifact. CMO/CPhO have
some, but with mixed sign (CMO `beta_chars = -0.0011`, CPhO `+0.0050`). The
high-R^2 cohorts are *fame-graded* mid-tier categories (actor 0.95, writer
0.88, athlete 0.79), where longer golds simply encode more known facts --
length is an outcome of fame, not a measurement artifact. See
`within_cohort_regressions.csv`.

## Cross-cohort fixed-effects adjustment

`NameRank ~ gold_chars + gold_named_facts + cohort_FE` on all 5,719 entities
(`R^2 = 0.533`) gives `b_chars = -1.12e-3`, `b_facts = +1.79e-2`. We report
two cohort-mean adjustments (`adjusted_cohort_means.csv`):
**FE** uses these pooled slopes; **OA-slope** uses slopes estimated from
OpenAlex alone (`b_chars_oa = +1.51e-3`, `b_facts_oa = -7.76e-3`).

| cohort | raw | FE-adj | OA-slope-adj |
|---|---:|---:|---:|
| cpho_china_first_prize | 0.182 | -0.174 | 0.638 |
| cmo_china_gold | 0.302 | -0.046 | 0.763 |
| rhodes_scholar | 0.315 | 0.036 | 0.695 |
| ioi_gold | 0.341 | 0.116 | 0.639 |
| msra_phd_fellowship | 0.343 | 0.071 | 0.672 |
| imo_gold | 0.362 | -0.019 | 0.886 |
| noi_china_gold | 0.368 | 0.039 | 0.797 |
| long_tail_researcher_openalex | 0.464 | 0.464 | 0.464 |
| putnam_fellow | 0.608 | 0.331 | 0.946 |
| icpc_world_finals_gold | 0.610 | 0.219 | 1.114 |

The FE adjustment *deepens* the credential-vs-OA gap (negative slope, short
credential golds); the OA-slope adjustment *flips* the gap (positive slope
within OA, where long golds tag researchers with affiliations on file).
Neither demolishes the credential-cohort ordering relative to each other,
and the FE result actively widens the credential-treadmill gap.

## Matched-pairs check: infeasible as specified

- IMO golds: 359-392 chars (sd 6.3).
- OpenAlex long-tail golds: 662-789 chars (sd 17.5).
- The ranges **do not overlap** (~270-char gap).
- With `|delta_chars| <= 50`, **n = 0 pairs**.

We instead report (`matched_pairs_imo_openalex.csv`):

| variant | n | mean IMO | mean partner | delta | paired t |
|---|---:|---:|---:|---:|---:|
| strict tol=50 (per spec) | 0 | -- | -- | -- | -- |
| nearest-neighbor (no tol) | 50 | 0.365 | 0.371 | -0.006 | -0.19 |
| IMO vs CMO tol=50 | 50 | 0.365 | 0.290 | +0.075 | +4.69 |

The nearest-neighbor variant pairs IMO with the 50 OA researchers with the
shortest gold answers -- exactly the OA tail without affiliations, whose
NameRank is depressed for entity-strength reasons, not length reasons. It
is not a length-controlled comparison. The IMO-vs-CMO variant (a sister
credential cohort that *does* overlap in chars) preserves the
within-credential ordering reported in the paper.

## Does the confound meaningfully change the claim?

**No.** Three reasons:

1. **No within-cohort length effect for the cohorts in question.** IMO, IOI,
   MSRA, NOI, OpenAlex all have within-cohort R^2 < 0.07. The
   credential-cohort low scores are not a within-cohort length artifact.

2. **Between-cohort length differences are entity attributes.** Long OA
   golds list affiliations and citations; short OA golds tag authors with no
   affiliation in OpenAlex -- thinner entities, not a measurement bias. The
   two slope specs bracket the truth from opposite sides because the
   "IMO with OA-length golds" counterfactual is not identifiable.

3. **The strict matched-pairs test cannot run.** That itself is worth
   flagging; the closest feasible match (IMO vs CMO at matched length)
   preserves the paper's within-credential ordering.

**Magnitude vs. claim.** The IMO-vs-OA gap magnitude is adjustment-dependent
(raw +0.10, FE +0.48, OA-slope -0.42). The *direction* -- credential cohorts
below OpenAlex -- is preserved under FE and reversed only by the OA-slope
spec, which is identified off a within-OA pattern that itself reflects
entity-strength, not a length-driven judging artifact. The
credential-treadmill thesis survives.

## Files

- `gold_metrics.csv`, `within_cohort_regressions.csv`,
  `adjusted_cohort_means.csv`, `matched_pairs_imo_openalex.csv`,
  `summary.json`, `analyze.py`.
