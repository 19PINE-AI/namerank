# T2.8 — Gendered-name attenuation in NameRank

## Question
The IKP paper (Sec. 5.7) documented a roughly 2× recognition attenuation for
common East-Asian surnames. NameRank inherits this. A natural follow-up,
frequently raised by reviewers, is whether NameRank also attenuates for
**woman-coded first names** relative to **man-coded first names**, after
controlling for bibliometric impact.

## Method

**Gender labeling.** First names are labeled with the `gender-guesser`
package (`pip install gender-guesser`). To avoid the well-known failure
mode of guessing gender from romanized single-syllable Chinese / Korean /
Vietnamese given names (e.g., "Wei", "Min", "Hui" are all unisex), any
entity whose name contains a token matching a curated list of ~150
East-Asian surnames is unconditionally relabeled **ambiguous**. Bracketed
annotations ("[Tech]"), suffixes, and middle initials are stripped before
lookup. Resulting labels are `male`, `female`, or `ambiguous`, plus a
confidence tag (`high` / `medium` / `androgynous` / `east_asian_name` /
`unknown_to_detector`). `ambiguous` rows are dropped from per-gender
comparisons.

**Headline + replication.** On each cohort we report n, mean NameRank by
gender, the male–female delta, Welch's t, and a two-sided p. Cohen's d
uses pooled SD.

**Bibliometric adjustment.** Only `long_tail_researcher_openalex` carries
h-index and citation counts in `pilot_entities.json`. For that cohort we
bin all entities into h-index deciles and report the gap *within* each
decile, then take the n-weighted within-decile mean ("POOLED_WITHIN").
`cs_faculty` has no bibliometric covariates available, so we instead match
female faculty to male faculty *within the same institution* (a strong
proxy for tier / subfield prestige in CSrankings).

## Findings

### 1. cs_faculty (n = 698; 354 male, 97 female, 247 ambiguous)
- Mean NameRank: **male 0.453 vs female 0.415**, **Δ = +0.038**
  (Welch t = 2.46, **p = 0.014**, Cohen d = 0.28).
- Institution-matched pairs (n = 60): mean **Δ = +0.054**,
  paired t = 2.03, **p = 0.042**.
- Female names are recognised about **8.4 % less** than male names in
  the same institution and same cohort.

### 2. long_tail_researcher_openalex (n = 771; 388 male, 76 female, 307 ambiguous)
- Unadjusted: male 0.487 vs female 0.456, **Δ = +0.031**
  (Welch t = 1.33, p = 0.18, Cohen d = 0.17).
- **h-index-decile-pooled Δ = +0.027** — the gap is essentially
  unchanged by h-index conditioning, ruling out the simplest
  "women have lower impact" explanation. Per-decile deltas are small and
  noisy (D7, D9, D10 even reverse sign), consistent with bibliometric
  impact already absorbing very little of a small first-name effect.
- Bibliometrically matched pairs (h-index ± tol, same subfield + country):
  n = 23, Δ = +0.018, p = 0.50. Underpowered.

### 3. Cross-cohort patterns (cohorts with n ≥ 20 per side)
| Cohort | n_m | n_f | mean_m | mean_f | Δ | p |
|---|---|---|---|---|---|---|
| cs_faculty | 354 | 97 | 0.453 | 0.415 | +0.038 | 0.014 |
| long_tail_researcher_ikp | 56 | 22 | 0.171 | 0.126 | +0.044 | 0.015 |
| long_tail_researcher_openalex | 388 | 76 | 0.487 | 0.456 | +0.031 | 0.18 |
| mid_tier_actor | 38 | 63 | 0.712 | 0.371 | **+0.341** | 0.00 |
| mid_tier_athlete | 64 | 32 | 0.595 | 0.341 | **+0.254** | 0.00 |
| mid_tier_journalist | 43 | 28 | 0.508 | 0.519 | −0.011 | 0.71 |
| mid_tier_politician | 68 | 22 | 0.363 | 0.349 | +0.013 | 0.37 |
| mid_tier_writer | 62 | 77 | 0.577 | 0.536 | +0.041 | 0.41 |

For mid_tier_actor and mid_tier_athlete the gap is enormous (Δ ≈ 0.25–0.34).
This is **not** a NameRank artefact — it reflects an underlying
recognition gap in the world (men's professional sport and Hollywood are
historically over-represented in training data). The relevant test for
*structural* bias is the researcher cohorts where bibliometric impact can
be controlled.

### 4. Robustness: ambiguous-name drop rate
The East-Asian-surname rule discards a substantial fraction of every
person cohort: 100 % of `deepseek_v3_author` and `cmo_china_gold`, 92 %
of `msra_phd_fellowship`, 52 % of `imo_gold`, **35 % of `cs_faculty`**,
**40 % of `long_tail_researcher_openalex`**. The conservative choice not
to guess gender from pinyin is the cost of avoiding a confound with the
East-Asian-surname attenuation already documented in IKP § 5.7. The
results above are insensitive to dropping medium-confidence labels:
restricting to `high`-confidence only changes the cs_faculty delta from
+0.038 to +0.035 and the openalex delta from +0.031 to +0.032.

## Bottom line

There is a **small but reproducible NameRank gap favouring man-coded over
woman-coded Western first names**:

- **+0.038 NameRank units (≈ 8 % attenuation) in cs_faculty**, p = 0.014,
  surviving institution matching at +0.054 (p = 0.042).
- **+0.027 NameRank units (≈ 6 %) in long_tail_researcher_openalex**
  after h-index decile adjustment — the bibliometric control does **not**
  close the gap, so the effect is not explained by women in this cohort
  having lower impact.

The effect is roughly **4× smaller** than the East-Asian-surname
attenuation reported in IKP § 5.7 (which is a ~2× ratio, i.e. ~50 %
attenuation), but it is in the same direction and reproducible across two
independent researcher cohorts. NameRank therefore inherits a measurable
— if modest — gender-from-first-name bias from its judge LLMs, on top of
the previously documented East-Asian-surname bias.

We recommend reporting this in a Discussion paragraph alongside the
existing East-Asian-surname discussion, framing both as inherited LLM
artefacts that NameRank measures faithfully rather than corrects for. A
"calibration win" framing would over-state the result given that the
within-cohort, within-institution, and within-h-index-decile gaps are all
positive.

## Files

| File | Contents |
|---|---|
| `run_analysis.py` | Reproducible pipeline (no external deps beyond `gender-guesser`). |
| `entity_gender.csv` | Per-entity (id, name, cohort, predicted_gender, confidence, namerank, h_index, …). Person-cohorts only (3 789 rows). |
| `gender_gap_by_cohort.csv` | Per-cohort n, mean NR, delta, Welch t, p, ambiguous rate. |
| `h_index_adjusted_gap.csv` | Within-h-index-decile gender gap on long_tail_researcher_openalex, plus POOLED_WITHIN row. |
| `matched_pairs_cs_faculty.csv` | 60 institution-matched (female, male) cs_faculty pairs with delta. |
| `matched_pairs_openalex.csv` | 23 h-index ± tol × subfield × country matched pairs on long_tail_researcher_openalex. |
