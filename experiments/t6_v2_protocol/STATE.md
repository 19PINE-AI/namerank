# NameRank re-run — live pipeline state (autonomous run, 2026-07-12)

Single source of truth for the in-flight v2/v3 re-run + t5_4 takeover. Re-read
this after any context reset to resume without losing the plan.

## >>> CURRENT STATE 2026-07-13 15:5x (read this first) <<<

**Canonical judge = `inputs/judge_prompt_v3_tightened.txt`** (anti-confabulation
open-book). One uniform pass over ALL datasets → `outputs/recognition_final.jsonl`
(tagged by `dataset`: main/events/awards/llm/univ). Awards already complete.

**IN FLIGHT:**
- Uniform judge `19_uniform_final_judge.py --parallel 120 --only main,llm,univ,events`,
  PID in `outputs/judge.pid`, log `outputs/final_judge4.log`. main is ~120k records
  to judge at ~1000/min (~2h), then llm/univ/events. Touches `outputs/FINAL_JUDGE_DONE`
  at end. Monitor armed on that log for "UNIFORM PASS COMPLETE".
  NOTE: the 44888 pre-existing main verdicts were a STALE PARTIAL (Karpathy had 1/36);
  resume fills the rest. Deduped once already (removed 1423 race dups).
- zh sub-run `20_probe_judge_generic.py --job zh`, PID 2059175, log `outputs/zh_run.log`,
  out `outputs/zh_results.jsonl` (~4000/8640). Judges inline (has `recognized`).

**POST-COMPLETION PIPELINE (run in order once FINAL_JUDGE_DONE + zh done):**
1. Dedup `recognition_final.jsonl` (dataset,eid,mid) — races can dup lines.
2. `python paper/figures/compute_all_numbers.py` → `computed_numbers.json`
   (headline cohort means/floors/hindex/variance; variance now reads recognition_final).
3. `python experiments/t6_v2_protocol/scripts/24_recompute_downstream.py`
   → `outputs/paper_numbers_downstream.json` (events via analyze.py rebuild,
   crosslang zh-vs-en, gender). Rebuilds `t4_1/outputs/event_summary.csv` (score=recognition)
   + reruns `t4_1/analyze.py` → `analysis.json`. TESTED on partial data, plumbing OK.
4. Re-run cross-judge fresh: `rm outputs/cross_judge.jsonl outputs/CROSS_JUDGE_DONE;
   python scripts/23_cross_judge.py --per-cohort 60 --parallel 12` (Gemini vs
   Claude opus-4-6 vs GPT-5.1-via-OpenRouter; binary-verdict κ/agreement).
5. Fill ~307 `\tbd{}` in paper/main.tex (55) + appendix.tex (252) from the JSONs above.
6. Regenerate all figures (`make_fig_events.py` only works once events≥9000 in final).
7. `cd paper && pdflatex x2 + bibtex + pdflatex`. Grep for stray un-\tbd stale numbers.

**KEYS/ENV:** OPENAI direct key is READ-ONLY (list yes, infer no) → use OPENROUTER
for GPT. Gemini flash handles parallel 120 fine. compile = plain `pdflatex` (no latexmk).

**PREP DONE (2026-07-13 ~17:00) while judge runs:**
- `compute_all_numbers.py` now COMPREHENSIVE (70 keys): cohorts, floors, hindex,
  variance, + individuals (ent.lecun/hinton/jiayi_weng/tianshou/nanogpt/karpathy/
  tri_dao/flashattention), country (usa/china/india via code/country_affiliation),
  injection.mean_lift (B−A, artifact-injected minus role-only), self-report ρ
  (aggregate/panel_fame/own_behavior/inter_model), extra cohorts (proglang/benchmark/
  dataset). Validated on partial data — matches paper estimates: country USA 0.66 n=206,
  China 0.34, India 0.31; injection −0.013 (NULL confirmed); self-report 0.82/0.57/0.30/0.90.
- AWARDS ladder FILLED (dataset complete). Marquee time-trend claim RETRACTED (saturation),
  see FINDINGS_final.md. Cross-judge section rewritten for binary κ (numbers \tbd pending
  fresh re-run after main completes: `rm outputs/cross_judge.jsonl outputs/CROSS_JUDGE_DONE`
  then rerun `23_cross_judge.py`).
- All 21 figure scripts run (make_fig_events gated: needs events≥9000 in final).
- ~290 `\tbd` remain (main.tex 55, appendix 233); most map directly to computed_numbers.json
  keys. VERIFY at fill: §374 "IMO medal-year uncorrelated" claim; main.named_method vs
  atlas "named ML methods 0.84" (may be different cohort — main.named_method partial=0.94).

## The metric, final form
- **v2 golds**: entity-specific verifiable facts only (no context echo). Built
  from OpenAlex/Crossref/S2/Wikipedia/GitHub/official-records. Contexts stripped
  of bibliometrics/results/named-works (`contexts_v2.json`).
- **v3 recognition (HEADLINE)**: open-book judge, `inputs/judge_prompt_v3.txt`
  (canonical, shared with t5_4). Rule = **asymmetric knowledge**: refute freely
  with own knowledge; credit ONLY positively-verified specific non-guessable
  facts; unknown entity + plausible specific → false, fall back to gold. Gold =
  disambiguation anchor + fallback. NameRank_v3(entity) = fraction of 36-model
  panel that recognizes it. Validated floors: people/artifacts/credentials
  0.010, papers 0.26 (title-guessability, floor-adjust).
- **cov*acc (v2 continuous)**: retained as appendix depth diagnostic only.

## Audit fixes already applied (to source golds; stable)
1. soft-refusal reclassification (analysis-time, 06_build_analysis).
2. credential golds: raw score/rank stripped (08_fix_golds_v2). IMO 0.047→0.095.
3. membership-minimal author golds dropped (echo).
4. researcher/faculty gold too narrow → open-book judge (fixes Guzdial/Satya FN)
   + enriched golds (12_enrich, +papers +collaborators).

## Running pipelines (all chained, resumable, unattended)
- **t6 probe** `04_run_probe_v2` pass1 (~95K/134K) → `07_orchestrate_probing.sh`
  launches pass2 (researchers/faculty). Collects responses (+provisional v2 cov/acc).
- **t6 enrichment** `12_enrich_researcher_golds.py` (~650/1036) → `gold_v2_researchers_s2_rich.json`.
- **t6 v3** `16_orchestrate_v3.sh` (pid waits on enrichment 1239630): reassemble
  → loop `15_recognition_v3_all.py` (open-book, ALL cohorts) → `recognition_v3.jsonl`
  → `outputs/V3_DONE`.
- **t5_4** `15_orchestrate_openbook.sh`: wait univ probe (~25K/25272 done) →
  `13_judge_detect.py` (open-book) → `12_topup_probe_v3.py` (190 unmatched) →
  `14_analyze_final.py` → `outputs/T5_4_DONE`.

## t5_4 DONE (2026-07-12): open-book judged, famous-name gate PASS (Abbeel 1.0), faculty ladder MIT 0.789>Berkeley 0.733>UCSD 0.640>Irvine 0.621, windowed shows corpus-density-at-matched-citations, IMO 0.226<<baseline 0.415. See t5_4/FINDINGS_openbook.md.

## PAPER SINGLE-VERSION reframe (2026-07-13, partial)
- DONE: §2 methodology rewritten to the unified recognition method (recognition verdict, verifiable golds, 36-model panel, panel recognition rate); Results §3 replaced with labeled \tbd placeholders (all sec:results-* + 4 appendix-referenced figure labels preserved); main.tex metric/version language scrubbed; compiles 44pp. NOI appendix updated with adopted-judge numbers + 0.000 floor.
- TODO (task 17, needs unified data): fill \tbd in Results + abstract counts; refill appendix numbers on one 36-model panel; scrub ~27 remaining appendix version tokens ("the main run"/"IKP-v2 replacements"/"multiplicative" in app:scoring); regen figures. NEVER use "corrected/v2/v3/main run vs this study" in prose.

## Remaining work AFTER data lands (needs me)
- [ ] t6 analysis: `06_build_analysis.py full` → v3 credential ladder, h-index,
      institution/country, variance, accuracy-channel. Recompute headline table.
- [ ] t5_4: validate famous-name gate (Abbeel/Torralba/Tedrake/Zaharia high);
      per-university ladder (windowed + faculty); grounded-only sensitivity (52
      zero-source golds).
- [ ] paper update (`paper/main.tex`+`appendix.tex`): metric redefinition
      (recognition-detection headline, cov*acc→appendix), audit story, all v3
      numbers, credential/inversion/h-index/institution/events under v3, t5_4
      faculty rows into Fig 3 + credential table + §3.2. Predictions restated.
- [ ] downstream robustness (t1-t2): re-judge under open-book where it changes
      conclusions (cross-judge, synthetic-null already about the judge; injection
      t2_7 with artifact-redacted gold; prompt-paraphrase). Lower priority.

## Gotchas
- OpenAlex dead until 2026-07-13 00:00 UTC (both IPs). S2 keyless ~1rps; Crossref
  free. Gemini judge shared across 3 streams — keep each ≤ parallel 6-8.
- Sentinels: `experiments/t6_v2_protocol/outputs/V3_DONE`,
  `experiments/t5_4_university_baseline/outputs/T5_4_DONE`.

## PAPER REWRITE STATE (2026-07-13, in progress)
Body (main.tex) FULLY REWRITTEN to career-arc structure; compiles clean 52pp, 0 errors, 0 undef refs.
- New sections: §3 Recognition Atlas, §4 Credentials & the Career Arc (treadmill→NOI roster→LLM-era credential→marquee), §5 Named-Artifact Mechanism (inversion→asymmetry→injection NULL→boundary), §6 What Predicts (h-index→institution matched-citation→country→language), §7 External Calibration (events→self-report), §8 Robustness, §9 Discussion, §10 Related, §11 Conclusion.
- Thesis: "recognition is paid to named indexable artifacts accumulated over a career, not credentials." Career arc is the signature.
- Figures done+validated (recognition metric, dataviz-validated palette): fig1_atlas, fig_calibration, fig_axis_strip, fig_inversion, fig_hindex, fig_universities, fig_country. Style in _style.py (RECOG palette), data via _data.py (auto-switches to recognition_final.jsonl per dataset).
- Figures PLACEHOLDER (await uniform pass reaching their dataset): fig9_career_arc (awards), fig_events, fig_selfreport. Regenerate scripts exist for career-arc; events/selfreport need recognition-metric rewrite.
- Numbers: 52 \tbd{X} placeholders hold CURRENT-DATA values; wrapped for verification vs uniform pass. N=4812,K=56 filled (final). refresh_numbers.py recomputes all; unwrap \tbd after uniform pass.
- KEY REVISIONS baked into prose: injection is now NULL (observational inversion); 25 mis-resolved artifact golds fixed (FlashAttention 0→0.92 etc); inversion 7/10; h-index leads but citations add a little (not "zero").

## STILL TODO on the paper
1. Uniform pass completes -> run refresh_numbers.py, unwrap all \tbd, regenerate career-arc/events/selfreport figures.
2. APPENDIX (appendix.tex): still has old numbers + ~27 version tokens; needs full number refresh + version scrub + fig_events/fig_medal_tiers already updated.
3. Discussion clock §(sec:discussion-clock) + predictions § have specific old numbers (0.312→0.382 MSRA, -0.049 vintage, etc) — refresh from final.
4. Delete unused old figures (fig1_cohort_distribution, fig3_external, fig4_credentials, fig5_country, etc superseded).

## APPENDIX REWRITE (2026-07-13, substantially done)
Compiles clean 50pp. Version language scrubbed (0 "main run"/"IKP-v2"/"survivor"/"multiplicative"/"37-model" tokens).
- app:spec: 36-model panel table (20 west/16 cn), added LLM-area cohort-group row.
- app:credentials: ladder table -> recognition rates (\tbd), career-track + temporal prose reframed.
- app:awards: version scrub, recognition table w/ LLM-area rows woven in, "career arc in one table" prose, lifetime signal.
- app:medal-tiers (NOI): already done prior turn (0.104/0.026/0.019, floor 0.000).
- app:inversion: table -> recognition (7/10 invert, senior-leader exceptions); INJECTION TABLE -> null result (mean -0.01), "observational not inducible" prose.
- app:external: regression table -> recognition R² (h 0.22, cites 0.20, joint 0.27); decile table condensed.
- app:scoring: FULL rewrite — variance decomp (entity 56/cohort 34/model 10), "recognition verdict required" (was multiplicative), embedding table -> recognized-vs-not.
- app:synthetic: FULL rewrite — per-recipe floors (people/artifact ~0.02, papers 0.10), no more 0.04/0.20 story.
- app:confounds: reframed — context-leak & gold-length now "closed by design" (recognition verdict), Wikipedia/attention empirical w/ \tbd.
- limitations table: panel-churn row + synthetic-floor row updated.

## STILL TODO on appendix (number refreshes, \tbd-wrapped, await uniform pass)
- app:geography institution table (line ~370, Stanford 0.537 etc — old metric, needs recognition refresh + \tbd)
- app:crosslang tables (line ~430-490, old zh numbers — await zh re-probe completion)
- app:selfreport (line ~568-610, needs recompute vs recognition ordering)
- app:tianshou-case table (Jiayi Weng peers, old numbers)
- app:prompt-sensitivity, app:cutoff, app:cross-judge, app:gender: method-about sections, mostly still valid, light \tbd refresh
- Then: refresh_numbers.py over all \tbd, unwrap; regenerate career-arc/events/selfreport/attention/sigma figures; delete superseded old figs.

## REWRITE SESSION 2 (2026-07-13 autonomous) — near-complete
Body + appendix fully rewritten to career-arc structure, compiles clean 51pp / 0 err / 0 undef.
NEW FIGURES built & validated (dataviz palette): fig1_atlas, fig_calibration, fig_axis_strip, fig9_career_arc,
  fig_inversion, fig_hindex, fig_universities, fig_country, fig_events, fig_selfreport. Old superseded figs deleted.
KEY FINAL NUMBERS locked in (from data):
  - awards (uniform-pass final): Nobel .98/Turing .97/Fields .96/ACMPrize .95/MacArthur .85/Godel .81/ACMfellow .79/Sloan .78
  - LLM-area: method .65/bestpaper .53/foundational .46; baseline .41
  - credentials (canonical judge, WILL drop ~.05 under uniform tightened): imo .24/ioi .27/noi .13/cmo .06/rhodes .16/msra .24/putnam .40/icpc .41
  - institution: Stanford .80/UW .76/CMU .72/Princeton .67/Cornell .65/Michigan .63; country USA .66 vs China .34
  - h-index R² .22, cites .20, joint .27; floors people .02/papers .10; variance entity ~56/cohort 34/model 10
  - inversion 7/10 (senior-leader exceptions); INJECTION NULL mean -.01; self-report aggregate ρ .82 but per-model panel-fame .57 vs own-behavior .30, inter-model .90
KEY FRAMING CHANGES made: career-arc thesis; injection observational-not-causal; awards saturate (marquee) w/ selection caveat on sampled fellowships; self-report reads fame not own-state; Tianshou reframed to artifact-mediation (peer-σ claim dropped); h-index "leads" not "citations add zero".

## FINAL FILL (when uniform pass FINAL_JUDGE_DONE + zh done — monitor armed, finalize.sh running)
1. compute_all_numbers.py -> computed_numbers.json (final values). refresh figures (auto in 22_finalize.sh).
2. Unwrap all \tbd{X} -> X; UPDATE credential/paper numbers to uniform-pass (tightened) values (imo ~.19 etc, per awards imo control .188).
3. Remaining detail tables to refresh: cross-language (app:cross-lang, awaits zh), gender (app:gender, recompute), bibliometric-decomp (app:bibliometric).
4. Remaining figures to regen under recognition: fig_pipeline (redraw verdict), fig_attention, fig_bibliometric_decomp, fig_cutoff_gradient (or wrap as method-illustrative).
5. Final proofread: grep for any remaining old number not \tbd-wrapped; verify 0 "\tbd" left; final compile.
