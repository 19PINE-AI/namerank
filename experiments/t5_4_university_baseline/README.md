# t5_4 — Per-university working-researcher baselines

**Question.** The credential-treadmill comparison (paper §3.2, Figure 3) uses
the `long_tail_researcher_openalex` cohort (n=771, citations 500–30,000,
globally sampled) as the working-researcher baseline. Is that baseline an
artifact of its construction? This experiment rebuilds it per-university —
MIT, UC Berkeley, UC San Diego, UC Irvine — under two designs:

1. **Windowed** (`univ_*`, v1+v2 protocols): the identical inclusion rule as
   the main baseline (citation window + first-author screen), institution-
   stratified. This is a *matched* design: it tests whether the global
   baseline generalizes per-university (it does — all four sit at the in-run
   baseline, ANOVA p≈0.9), but the citation window conditions on the main
   predictor of NameRank, so it deliberately erases between-university
   composition differences and CANNOT rank universities.
2. **Faculty** (`univ_fac_*`, v2 protocol only): role-defined membership from
   CSRankings rosters (the main run's cs_faculty source), seed-42 sample of
   min(100, roster), NO bibliometric conditioning. This preserves each
   university's real composition and is the design that can show university
   differences. These are the rows intended for the paper's ladder.

**Windowed construction** (replicates the main run's long-tail recipe
exactly):

- OpenAlex authors with `last_known_institutions.id` = the university
- total citations in [500, 30000] (the main-run citation window)
- ≥1 first-author work with ≥500 citations (the main run's implicit rule:
  every released long-tail gold asserts a first-author "well-cited paper",
  minimum observed 500)
- server-side random sample (`sample=2400&seed=42`), screened in sample order
  until 100 qualify per university
- contexts and golds use the main run's long-tail templates verbatim
  (institution, subfield = the qualifying first-author work's primary topic,
  first-author citations, total citations, h-index)

**In-run controls** (entities, contexts, golds copied verbatim from the main
run, same seed-42 resample as t5_1, so all comparisons are within-run and
immune to the ~0.13/yr vintage drift): 60 OpenAlex long-tail researchers and
40 IMO golds.

**Panel.** The t4_1 event panel: 28 main-run survivors + 8 IKP-v2 replacement
models = 36 models. Probe template, judge (Gemini 3 Flash Preview), refusal
detector, and multiplicative coverage×accuracy scoring unchanged from the
main run. Ladder comparisons against released main-run values use the
28-survivor subset with the control-cohort shift reported alongside.

**Protocol v2 sub-run.** Both designs are also measured under the t6 v2
protocol (echo-free contexts, entity-specific golds, context-aware judge).
Windowed v2 golds use the same Semantic Scholar route as the v2 full pass's
flagship researcher cohort (02f functions imported directly; h-index-band
namesake guard); faculty v2 golds use 02f's cs_faculty branch (paperCount
dominance + CS-topical check). Unmatched entities (windowed 61/396, faculty
118/396 — mostly ambiguous common names) are excluded rather than guessed,
per the v2 convention, and are documented in the match reports.

**Scoring-rule fix (2026-07-12, user decision).** The v2 S2 golds exposed a
regression: graded coverage measures the overlap of two small samples from
the entity's fact universe, so famous faculty (Abbeel, Torralba, Tedrake,
Zaharia) scored 0.000 with judge-acknowledged fully-accurate responses
(44% of MIT faculty were "known-but-zero-credited"). Fix, in three layers:
1. **Golds v3** — web-grounded, length-normalized (55-word fact budget,
   namesake guard) via `code/generate_golds.py`, for ALL entities including
   the 190 the S2 matcher dropped;
2. **Headline metric = detection**: a model recognizes an entity iff its
   response states >=1 specific, non-guessable, beyond-context fact
   corroborated by the gold; NameRank-detect = panel fraction recognizing.
   Graded coverage*accuracy is demoted to a depth diagnostic (appendix).
3. **Calibration**: the detection rubric's false-positive floor is measured
   on the t6 v2 synthetic nulls (15_synthetic_floor.py).

**Scripts.**
- `01_sample_authors.py` — OpenAlex institution-stratified sampling + screening (windowed)
- `02_build_inputs.py` — v1 entities/contexts/golds + in-run controls
- `03_run_probe.py` — v1 36-model probe run (resumable)
- `04_analyze.py` — v1 per-cohort means/CIs, survivor-panel control anchoring
- `05_build_v2_inputs.py` — windowed v2 golds (S2) + v2 contexts + controls
- `06_run_probe_v2.py` — v2 probe run, judge v2 (adapted from t6's 04)
- `07_sample_faculty.py` — CSRankings faculty rosters, seed-42 sample
- `08_build_faculty_v2_inputs.py` — faculty v2 golds (S2 cs_faculty branch)
- `09_analyze_v2.py` — v2 per-cohort means/CIs + between-university tests
- (golds v3 via `code/generate_golds.py --entities inputs/gold_v3_entities.json --out inputs/univ_gold_v3.json`)
- `12_topup_probe_v3.py` — probe the 190 S2-unmatched entities, judge v3 inline
- `13_judge_detect.py` — judge-v3 pass over stored responses (headline rule)
- `14_analyze_final.py` — detection-rate ladder + depth diagnostic + validation

**Coordination with the concurrent full-pass session (2026-07-12):** the
judge rubric here is NOT this experiment's own — 13/12 load the canonical
`t6_v2_protocol/inputs/judge_prompt_v3.txt` verbatim (one call returns
recognized + coverage + accuracy), so t5_4 scores are rubric-identical to
the full pass. The synthetic-null false-positive floor for judge v3 is
measured by t6's `10_validate_recognition_judge.py`, not duplicated here.
Caveat for cross-run anchoring: this experiment verifies against its own
generate_golds.py v3 golds (all 892 entities), while the full pass currently
verifies researchers/faculty against S2 works-list golds — for famous
faculty those golds are too narrow a verification pool even under detection
(Abbeel's response names BAIR/Covariant/RL; an S2 titles-only gold matches
none), so full-pass detection for oa_author/cs_faculty should adopt
grounded golds before the two runs are compared at level.
