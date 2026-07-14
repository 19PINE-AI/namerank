# T6 — Protocol v2: construct-validity fixes and full re-run

## Why (audit findings, 2026-07-12)

A record-level audit of the released run found that the scoring pipeline
credits **context echo** and that most gold answers are **templates** whose
entity-specific content is already given in the probe context:

1. **Templated golds.** Outside the 37-entity reference set and the news-event
   cohort, golds are recipe-generated: the OpenAlex-researcher gold's only
   specifics (field, affiliation, citations, h-index) appear verbatim in the
   probe context; the cs_faculty gold's only specific is the affiliation (in
   the context); credential golds contain the credential (in the context) plus
   cohort-generic text; mid-tier golds are Wikidata sitelink boilerplate, not
   the Wikipedia intros the paper describes.
2. **Context leakage.** Contexts leak bibliometrics (OpenAlex/IKP cohorts),
   competition results incl. exact scores and schools (CMO), and identifying
   works ("The Martian, Project Hail Mary" for mid_tier_writer).
3. **Echo credit.** The v1 judge credits responses that restate the context
   against golds that contain little else. Panel-mean score on *fictional*
   IMO medalists with the same recipe is 0.199 vs 0.362 for real ones (55%
   echo share); per-model fictional floors reach 0.72 (claude-opus); a 4B
   model (gemma-3-4b) scores median 0.80 on long-tail researchers with zero
   item-total correlation — pure echo, no signal.
4. **Recipe-mismatched synthetic nulls.** t1_3's fictional faculty carry dense
   hand-written golds, not the real cohorts' template golds, so the released
   floor (0.04 "dense") does not calibrate the real researcher cohorts, and
   the "floor-adjusting widens the credential gap" claim is not identified.
5. **Downstream**: on the flagship OpenAlex cohort NameRank correlates 0.94
   with simple answer rate; the h-index R^2=0.40 result is carried by refusal
   behavior (R^2=0.402 from answer rate alone). Findings that survive
   echo-robust re-measurement: institution/country gradient, h-index-vs-
   citations ordering, silent zone, events cohort. Findings with unidentified
   magnitude: credential-treadmill gap.

## The v2 protocol

- **Judge v2** (`inputs/judge_prompt.txt`): the judge sees the probe context
  and gives zero coverage/accuracy weight to statements that restate it; a
  context-paraphrase-plus-filler response scores 0.0 like a refusal.
  Validated on saved responses (`outputs/judge_v2_validation.csv`):
  boilerplate stratum collapses 0.51→0.16 (59% of answered records → 0.0),
  dense-gold strata track v1 (events r=0.90).
- **Golds v2** (`inputs/gold_answers_v2.json`): entity-specific verifiable
  facts only, composed from sources — OpenAlex author/work records
  (researchers, faculty, papers, author-list cohorts), Wikipedia intros
  (mid-tier, companies, artifacts with articles), GitHub metadata + READMEs
  (OSS projects), official competition records (IMO/IOI/OIerDb) plus the v1
  roster metadata that previously leaked into contexts (schools, scores).
  Style guide below. Per-entity provenance and match confidence recorded.
- **Contexts v2** (`inputs/pilot_entities_v2.json`): role + field +
  country/era + minimal disambiguator. No bibliometrics, no results/scores,
  no named works, no meta-statements about notability. Credential results
  move from context to gold: the probe asks about "a Chinese student who
  competed at the IMO 2009"; knowing the medal is now part of recognition.
- **Synthetic nulls v2**: fictional entities matched 1:1 to every v2 gold
  recipe (researcher, faculty, credential, paper, OSS, mid-tier), so every
  cohort family has a calibrated guessing floor by design.
- **Panel**: the 36-model t4_1 panel (28 main-run survivors + 8 IKP-v2
  replacements); the 37-model v1 panel is no longer routable (2026-07 churn).
- **Raw responses are retained** (compressed) — v1's were deleted, which is
  why re-judging was impossible and this re-run necessary.

## Gold style guide (v2)

- 80–180 words; >=3 entity-specific facts beyond the v2 context, else flag
  `thin_gold: true`.
- Facts only from fetched sources; composing sentences is allowed, inventing
  facts is not. No cohort-generic sentences ("many medalists go on to...");
  no meta text ("recognition of this individual reflects..."); no
  bibliometric aggregates (h-index, citation counts) — use named works,
  venues, years, roles, institutions, awards, concrete records instead.
- Match confidence: `high` (resolved by stored ID or verified official
  record), `medium` (name+affiliation/field match), `low` (ambiguous →
  treated as unmatched; entity keeps v1 gold and is excluded from v2
  headline analyses, documented).

## Contents

- `scripts/01_validate_judge_v2.py`, `01b_validate_boilerplate.py` — judge v2
  validation on saved t5_1/t5_3/t4_1 responses.
- `scripts/02_*` — gold builders (OpenAlex people, Wikipedia, artifacts,
  competition records).
- `scripts/03_build_v2_inputs.py` — assembles pilot_entities_v2 +
  gold_answers_v2 + synthetic nulls v2.
- `scripts/04_run_pilot.py` / `05_run_full.py` — probe runs (judge v2).
- `outputs/` — validation, match reports, run outputs.

## Pilot validation (PASSED, 111 entities × 12 models, judge v2)

All five gates pass — the protocol eliminates echo while preserving recognition:
- **Synthetic floors**: every recipe family panel-mean ≤ 0.03 (v1 boilerplate-IMO
  floor was 0.199). `synthetic_cs_faculty_v2` 0.002, `synthetic_openalex_
  researcher_v2` 0.000, `synthetic_imo_gold_v2` 0.029.
- **Echo collapse**: gemma-3-4b on real long-tail researchers 0.000, phi-4 0.013
  (v1: gemma median 0.80 — pure context echo).
- **Recognition preserved**: reference-set ordering vs v1 Spearman 0.905
  (yann_lecun 0.707, nanogpt 0.517, aravind_srinivas 0.580).
- **Judge health**: 0 errors.
- **Cohort sanity**: credential cohorts collapse to near-silent under the clean
  protocol (imo_gold 0.020 vs v1 0.362; msra 0.000) — most v1 credential
  "recognition" was context echo. Mid-tier figures retain recognition
  (writer 0.444, founder 0.417). This SHARPENS the credential-treadmill
  finding: credentials are not merely at/below baseline, they are essentially
  silent once echo is removed.
