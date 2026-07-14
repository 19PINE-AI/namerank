# NameRank final findings under the recognition metric (2026-07-13)

Full run complete: 170,280 verdicts, 0 judge errors, all 4,623 gold entities at
full 36-model coverage. Metric = panel recognition rate (open-book judge).

## Variance decomposition (the score measures the entity)
entity 55.7% / cohort 34.1% / model 9.8%. Entity share rose from v1's 35.8% —
the recognition metric is far more about the entity, far less about model
generosity. Model share nearly halved (10.9%→9.8% with a cleaner definition).

## Synthetic floor (calibration)
people/artifacts 0.000–0.037; papers 0.104 (title-guessability, floor-adjust);
synthetic IMO 0.083 (residual confabulation, floor-adjusted in credential ladder).

## 1. Credential treadmill — CONFIRMED, sharper
All Olympic-style credentials below the working-researcher baseline (0.410;
floor-adj 0.393):
  IMO 0.238 (adj 0.169), IOI 0.267 (0.229), NOI 0.130 (0.097),
  CMO 0.062 (0.026), Rhodes 0.163 (0.119), MSRA 0.243, CPhO 0.045.
  Putnam 0.400 (adj 0.368) ≈ baseline — the informative exception (US-tracked,
  English-corpus careers). Credential no longer propagates a name; named
  post-credential production does.

## 2. Marquee-tier inversion (awards appendix, separate 36-panel run)
Nobel/Turing/Fields clear the baseline and accrue for decades — the treadmill
inverts at the marquee tier (see FINDINGS in t5_1; award ladder).

## 3. Artifact over creator — CONFIRMED
Reference-set pairs: Jiayi Weng 0.25 vs Tianshou 0.81 (artifact >> creator);
Karpathy 0.92 vs nanoGPT 0.83 (creator > artifact — famous-for-many-things
exception, as predicted). t5_5 gives a fresh method-vs-originator panel.

## 4. h-index carries the bibliometric signal
OpenAlex researchers (n=603): corr(log h, recognition)=0.469, R²=0.220.
Still leaves most variance unexplained (the paper's "~60% residual" point).

## 5. Institution / corpus-density gradient — CONFIRMED
CS faculty by institution: Stanford 0.801, UW 0.761, CMU 0.722, Princeton 0.670,
Cornell 0.647, Michigan 0.633. Top-corpus-density schools recognized well above
the long-tail researcher baseline (0.410). (t5_4 adds the matched-citation
version: MIT/Berkeley > UCSD/Irvine even at fixed citations.)

## 6. Cross-domain axis calibration (textbook)
Silent (near floor): GPT-5 authors 0.049, DeepSeek authors 0.081, CPhO 0.045.
Discriminative: credentials 0.06–0.27, researchers 0.41, faculty 0.57.
Universal: named methods 0.844, OSS 0.818, AI companies 0.819, foundation
models 0.697, politicians 0.943, mid-tier professions 0.73–0.92.

## 7. LLM-area cohorts (t5_5, probe ~77% done)
Method originators (partial) 0.669 — well above the researcher baseline;
supports named-artifact-propagates-creator. Full numbers + method-vs-creator
inversion pending probe completion.

## Data
experiments/t6_v2_protocol/outputs/recognition_v3.jsonl (verdicts),
outputs/analysis/recognition_{per_entity,cohort}_v3.csv,
variance_decomposition, per_model_summary.

## REVISIONS from the final rewrite pass (2026-07-13)

**Context injection is now a NULL (important revision).** Re-running the A/B
injection under the recognition judge: mean lift -0.013 (was +0.058 under
coverage×accuracy), only 4/11 pairs positive, weak positive only for the
lowest-baseline creators (Jiayi Weng +0.11, Tri Dao +0.06). The recognition
judge structurally closes the echo channel — the injected artifact name is
context, so echoing it earns nothing. Reading: the artifact>creator inversion
is OBSERVATIONAL (corpus attribution asymmetry), NOT causally inducible by
naming the artifact. The old "corroborates the mechanism / upper bound" claim
is replaced by "the apparent lift was the echo confound; the clean estimate is
~0." Cleaner and more honest.

**25 mis-resolved artifact golds fixed** (short names -> wrong repos): e.g.
FlashAttention 0.00->0.92, CUDA 0.94, R 1.00, contrastive learning 1.00. The
recognition judge's wrong-entity guard had correctly suppressed these. Inversion
count improves to 7/10 (was 5/10); every independent-creator pair now inverts,
the 3 exceptions are senior leaders (Hassabis, Karpathy, Murati).

**Inversion pairs (final):** Weng<Tianshou, Chase<LangChain, Sanger<Cursor,
Willison<Datasette, Srinivas<Perplexity, Dao<FlashAttention, Amodei<Anthropic;
exceptions Hassabis=DeepMind, Karpathy>nanoGPT, Murati>Thinking Machines Lab.

**h-index joint regression:** R2 h-only 0.220, cites-only 0.203, joint 0.266;
h adds +0.063 beyond cites, cites adds +0.047 beyond h. h-index leads but the
old "citations add ZERO" is now "citations add little"; ~73% of variance
unexplained.

## REVISION 2 (bibliometric decomposition — 2026-07-13)
Under recognition, the old "h-index uniquely wins via name-recurrence" finding does NOT hold.
Sole R² on recognition (n=603): fractional cites 0.24, first/last cites 0.24, h-index 0.22, raw cites 0.20, n_works 0.16, mean_authors 0.00.
Attribution-weighted measures ADD signal beyond h (frac +0.074, firstlast +0.061) — opposite of the old claim.
NEW FRAMING: no bibliometric dominates; all ~0.20-0.24; the point is the ceiling (~75% unexplained). Dropped name-recurrence mechanism claim + fig_bibliometric_decomp. Abstract finding (iv), contribution (iv), §6.1, app:bibliometric all updated.

## 2026-07-13 — Awards ladder finalized + marquee time-trend claim RETRACTED

Awards dataset complete under the tightened uniform judge (recognition_final, dataset=awards).
Cohort recognition means (all above-floor, 36-model panel):
  Nobel 0.976, Turing 0.971, Fields 0.963, ACM Prize 0.951, MacArthur 0.848,
  Godel 0.807, ACM Fellow 0.787, Sloan 0.778 | embedded controls: OpenAlex baseline
  0.456, IMO gold 0.188 (validates tightened IMO ~0.19).

**Retraction:** The earlier claim "standardized recognition keeps rising for ~3 decades
after a Nobel/Turing/Fields prize" is FALSE under recognition data. The marquee cohorts
SATURATE (0.96-0.98), so there is no headroom for a time trend. Pooled marquee
std-recognition vs years-since-award: slope +0.0007/yr (flat), non-monotonic decade bins
(-0.15/+0.09/-0.03/+0.16). Fixed in main.tex x4 (abstract L49, thesis L81, awards §L214,
clock §L374), appendix award-ladder caption + "lifetime signal" para (now "Saturation,
not a lifetime clock"). The cumulative-ledger thesis now rests on: cohort ladder,
IMO medal-year-uncorrelated, events peak-not-persistence, cutoff gradient, NOI post-medal
careers — NOT on a marquee time trend. Dead fig make_fig_awards.py (unreferenced) still
shows the old panel; not included in paper.

## 2026-07-13 ~17:50 — main dataset COMPLETE: final cohort means + prose impact

main uniform pass done (4730 entities, median 36 verdicts). Final means (final rubric):
  baseline(openalex) 0.396, faculty 0.552, IMO 0.120, IOI 0.154, CMO 0.032, CPhO 0.028,
  NOI 0.086, MSRA 0.182, Rhodes 0.152, Putnam 0.343, ICPC 0.338, gpt5 0.089, deepseek 0.098,
  oss 0.872, named_method 0.919, foundation_model 0.725, ai_company 0.825, proglang 0.966,
  benchmark 0.744, dataset 0.956. Individuals: LeCun/Hinton 1.0, Karpathy 0.86, Tri Dao 0.72,
  FlashAttention 0.94, Tianshou 0.78, nanoGPT 0.78, Jiayi Weng 0.22.
  country: USA 0.643 (n=206), China 0.326, India 0.258. injection lift -0.013 (NULL).
  self-report: agg 0.83 / panel-fame 0.57 / own 0.30 / inter-model 0.90.
  variance: entity 56.0 / cohort 37.4 / model 9.1 (entity/model = 6.2x, was "5.7x").

**PROSE IMPACT (fixed / to fix):**
- FIXED main.tex L202: Putnam (0.34) and ICPC (0.34) NO LONGER clear the 0.40 baseline
  (were claimed as the two exceptions). Treadmill now EXCEPTIONLESS — stronger. Filled
  final numbers in that paragraph.
- IMO dropped 0.24->0.12; MSRA 0.24->0.18; CMO 0.06->0.03. All still below baseline (thesis holds).
- RECONCILE at fill: awards-ladder "IMO gold (control)" row = 0.19 (awards roster n=40) vs
  main credential IMO = 0.12 (main roster n=197). Different rosters; note or align.
- L340 "5.7x" -> ~6.2x (entity/model variance ratio).
- L405 IMO-vs-researcher gap "-0.22" -> -0.28 (0.396-0.12).
- Remaining numeric \tbd fill deferred to ONE pass after llm/univ/events/zh complete.

## 2026-07-13 ~18:30 — UNIFORM PASS COMPLETE (234574 verdicts). Downstream findings CHANGED:

**(1) Cross-language effect is essentially NULL under recognition** (was a headline
graded-metric effect). Per-cohort |Δ(zh-en)| all ≤0.04; abs mean per-model delta 0.023;
class avgs west -0.005 / china +0.002. Old dramatic per-entity swings (Wei Dongyi +0.27,
Saad Albawi -0.43) GONE; new extremes only ±0.11-0.19 (Pan Zhou +0.14, Harrison Chase -0.19).
Interpretation: recognition (binary, non-guessable fact) is language-invariant; the old
effect was language-matched verbosity inflating graded coverage. REWRITE app:cross-lang as null.

**(2) Events recurring-series penalty VANISHED**: adj_delta +0.006 (se 0.019), was -0.061.
Attention r2 UP under recognition: peak 0.342, total 0.387 (was 0.119/0.095 graded).
peak_vs_duration standardized: beta_peak +0.127 (se .011), beta_dur +0.043 (se .012),
joint_r2 0.387, marg_dur 0.045. "Loads on peak not persistence" HOLDS (peak 3x dur), but
duration now weakly POSITIVE (was -0.01). REWRITE events regressions + drop recurring penalty.

**(3) Gender gap significant only for cs_faculty** (+0.085, p=0.004); the two researcher
cohorts NOT significant (openalex +0.025 p=0.48; ikp +0.055 p=0.33). Cross-profession big
(actors +0.206, athletes +0.270, both p<.001). Old "reproducible across three researcher
cohorts" WEAKENS to "significant in faculty, directional-only in researchers." Update tab:gender + L396.

## 2026-07-13 ~19:30 — PAPER COMPLETE. All numbers filled, all figures regenerated.

- main.tex + appendix.tex: 0 \tbd remaining, compiles clean (pdflatex x2 + bibtex), 51 pages, 0 undefined refs/cites.
- All 14 included figures regenerate on recognition data. Fixed two stale-data figures:
  regenerated data/analysis/namerank_per_entity.csv (recognition) for fig_attention;
  regenerated t3_1 cutoff CSVs (per_model_cohort_means/natural_experiment/did) for fig_cutoff_gradient.
- Cross-judge fresh re-run (538 recs): gemini-claude κ=0.89, GPT-5.1 stricter (0.42 vs 0.57/0.58),
  ladder preserved under all 3 judges.
- Downstream recomputed: events (analyze.py: peak-dominant β0.127/dur0.043, recurring penalty NULL,
  attention r2 up to 0.34-0.39, 2023 recency -0.132), crosslang (NULL, all |Δ|≤0.04),
  gender (cs_faculty +0.085 sig; researchers directional only).
- Limitations table + all prose reconciled to final numbers.
- Abstract entity count fixed 4812/56 -> 4730/54 (measured); pipeline caption 234,574 verdicts / 6,512 entities.

## 2026-07-14 — Deep line-edit + number audit + paraphrase experiment

**Number audit (subagent cross-check vs computed_numbers.json + downstream json):** found and fixed
- Injection table missing its 11th pair (Lilian Weng -0.11); added → mean -0.01 now matches 11-pair rows.
- Limitations Wikipedia row said h-index R²=40% / wiki~2% → corrected to ~22% / ~10% (matches confounds appendix).
- External-validity cohort n=771 → 603 (matches hindex.n).
- Cross-judge n=615 → 538 (limitations row; matches the fresh 3-family run).
- h-index R² 0.23→0.22 in both bibliometric tables + marginals (+0.05→+0.06) for consistency with headline 0.22.
- Award-ladder vs-base drift: Fields +0.51→+0.50, named-method +0.20→+0.19, best-paper +0.08→+0.07.
- NOI synthetic floor "exactly 0.000" → 0.009 (one of 3 fictional NOI got 0.028); softened "no facts at all".
- Cohort-groups table counts were stale (summed 5,953); recomputed real per-group (4,685 core) + dropped LLM-area (extension).
- Headline entity count 4,730 → 4,685 real (45 synthetic nulls are controls, counted separately).
- Peak-0.34 marginal-vs-sole labeling clarified; cross-language "~0.1" → "~0.14" (max 0.139).

**Deep line-edit (body + appendix):** fixed broken transitions and stale claims left by piecemeal number edits —
validation-table DiD "≈0"→negative, cross-judge "own-family lift"→"GPT stricter/ranking preserved",
related-work "negatively correlated"→"weakly correlated", discussion attention "can invert"→"largely decouple",
inversion fig caption 11→10 pairs, conclusion list parallelism, several concision passes. 0 \tbd, compiles clean 51pp.

**Paraphrase experiment (t6 script 25):** RUNNING — 136 entities × 36 models × T1/T2/T3 templates (T0 reused from
main run), tightened judge. ~14k probes at ~100/min. On completion: compute variance decomp (entity/model/template)
+ per-template cohort agreement, fill app:prompt-sensitivity with real numbers, update tab:threats row + Robustness §.
Monitor armed (builebmgn). Output: outputs/paraphrase_results.jsonl.

## 2026-07-14 — Structural review + reorganization (3 parallel reviewers, all executed)

Three independent structural reviewers (framing, method/results org, discussion/redundancy) converged.
User approved: named-artifact spine + full structural+framing execution. Changes:
- **§7 dissolved**: news-events → capstone of §6 (What Predicts Recognition); self-report + cross-language →
  §8 Robustness (as subsections + two new threats-table rows). Body 11→10 sections.
- **§2 method 9→6 subsections**: merged Panel/Cohorts/Execution into one; cut §2.9 Scope (redundant with intro+§3);
  repointed appendix ref{sec:scope}→sec:results-headline.
- **§9 Discussion 9→5**: cut 9.1 (dup of conclusion); merged 9.2→related-work §10.5 (verified duplicate, same cites);
  merged 9.4→9.5; merged 9.6+9.7 into 'Structural Consequences'. Kept clock/lever/limitations/predictions.
- **Spine → named-artifact mechanism**: retitled §4 'Credentials and the Career Arc'→'The Credential Treadmill',
  reframed its intro as consequence-of-mechanism; dropped 'accumulated over a career' from the thesis one-liner
  (abstract + intro); cumulative-ledger point stays in §9.3 where independently established.
- **Opening/closing**: §1 now opens on concrete shock (IMO gold ~1-in-8 vs tool known by ~all 36);
  §11 ends on the normative takeaway + bookends 'post-bibliometric impact channel' instead of the URL.
- **Dedup**: thinned Walmart/nanoGPT/Altman triplet (kept in §3 where the figure earns it); merged §5.2→§5.1
  (attribution asymmetry is the mechanism behind the inversion); merged appendices F+G (Bibliometric Predictors);
  trimmed §4.2 NOI body; added 'how to read a NameRank number' gloss after Eq 1; surfaced cutoff-DiD numbers in §8.
Result: 51→49 pages, 0 errors, 0 undefined refs, 0 tbd. Backup at scratchpad/main.prerestruct.tex.
Paraphrase experiment still running (~2/3 done); its section fills when complete (monitor builebmgn).

## 2026-07-14 — Post-restructure polish pass (independent reader + self-review)
Fresh end-to-end reviewer flagged reorg casualties; all fixed:
- HIGH: two dangling "cross-vendor analysis" forward-refs (§2 Aggregation L139, §2 Panel L153) pointed to the
  prompt-language section which delivers no cross-vendor finding → reworded (per-model stats / cross-language check).
- HIGH: marquee-clock tension (body recruited marquee as cumulative evidence; app:awards disowns it) → added clause:
  non-decay rules out a FLOW reading, but saturated marquee can't trace the accrual slope (unsaturated cohorts do).
- §9 Discussion lead-in added (was cold-opening on a subsection); §8 "three...weight" echo removed + bridge sentence
  before the self-report/cross-language subsections explaining they're standalone experiments.
- Orphaned "Property 2" → named 'silent-not-misleading property'. Utility-website (tuixue) comparison MOVED from
  app:awards to app:asymmetry (where §5.3 points). Roadmap softened (was over-promising strict body-order + mis-scoping
  validation block). Awards-table baseline note (0.46/0.19 subsample vs headline 0.40/0.12). Split the 60-word §8.3 sentence.
- 'career arc' figure caption → 'The credential ladder' (spine consistency).
Result: 49pp, 0 errors, 0 undefined refs, 0 tbd.

## 2026-07-14 — Paraphrase experiment COMPLETE + section filled (last open item)
Ran 136 entities × 36 models × 4 templates (T0 reused from main run), tightened judge, 14,467 verdicts.
RESULT (decisive, confirms the by-construction argument):
- Variance decomposition (balanced 4,680-cell): entity 53% / cohort 37% / model 11% / **template 0%**.
- Per-template overall recognition 0.50-0.53 (within 0.02); per-cohort means correlate ρ=0.997-0.999 across
  template pairs; ladder ordering preserved (Spearman 0.99); per-record pairwise agreement 90-91% (residual
  at the recognized/not-recognized boundary, exactly as the design argument predicts).
Filled app:prompt-sensitivity with a variance table + per-template cohort ladder table (side-by-side, render clean);
strengthened the §8 threats-table paraphrase row (was assertion → now "template ≈0% variance, ρ≥0.997").
PAPER NOW FULLY COMPLETE: 49pp, 0 errors, 0 undefined refs, 0 tbd, all robustness claims backed by measured data.
