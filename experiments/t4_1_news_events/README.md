# t4_1 — News events: recognition vs. the recorded attention ledger

**Question.** For every other cohort in the study, the corpus exposure behind
a NameRank score can only be proxied (bibliometrics, stars, tutorials). News
events have a public, time-stamped attention record. Does recognition track
it — and through which component?

**Design.** 258 discrete news events from 2021–2023 (all safely inside every
panel model's training cutoff), sampled from the Events sections of English
Wikipedia's year pages (2021/2022/2023) and 32 country-year pages, classified
by Gemini 3 Flash (discrete-event test, start date, country/region, category),
and stratified by log10(first-year en-Wikipedia pageviews) band × 8 region
groups so the cohort spans ~4 orders of magnitude of attention. Golds are the
event article's intro (100–200 words, the main run's Wikipedia recipe);
contexts are deterministic type/place/date phrases. Probe template, judge,
refusal detection, and scoring are unchanged from the main run.

**Attention measures** (Wikimedia REST pageviews, user traffic, 365 days from
event-month start): total views, peak daily views, effective duration
(total/peak, days). Identity: log(total) = log(peak) + log(duration).
Google Trends' public endpoints return only normalized indices under heavy
rate limits, so pageviews (absolute, archived, reproducible) are the primary
ledger; a GDELT news-volume cross-check is in `outputs/gdelt.json`.

**Panel.** 9 of the 37 main-run models could not complete the event run
(2026-07): 8 lost all OpenRouter routing (provider churn), and grok-4.20-think
— initially recovered via the direct xAI API — lost access when that account
exhausted its credits at 143/258 events (partial coverage discarded). The 8
delisted models are replaced by the representative newly released models
evaluated in the IKP v2 revision (`inputs/model_set_replacements.json`):
Claude Fable 5, GLM-5.2, Qwen3.7-Max, Kimi-K2.7-code, MiniMax-M3,
Step-3.7-Flash, Nemotron-3-Ultra-550b, Nemotron-3-Nano-30b (one per new
vendor family + a second NVIDIA entry to restore the small-model tier; all
thinking mode). **Event panel = 36 models (28 survivors + 8 replacements),
9,288 records.** Comparability holds twice over: the full main run recomputed
on the 28 survivors correlates r = 0.993 with the released 37-model scores
(mean shift +0.011, `outputs/subpanel_baseline.json`), and the 8 replacements
rank events at r = 0.905 with the 28 survivors (level shift +0.091 — the
2026-vintage models know 2021–2023 events uniformly better).

## Headlines

1. **Dose–response, carried by accuracy.** NameRank ~ log10(total views):
   R² = 0.10 (repeated 10-fold CV 0.09 ± 0.11), decile means 0.38 → 0.50
   across ~2.4K → ~3.3M views; refusal rate falls 12% → 1%. Gold answers get
   denser as events get bigger (a suppressor): controlling gold length,
   slope +0.042 → +0.063, R² = 0.17. The channel is mostly accuracy
   (0.61 → 0.88 by decile) rather than coverage (0.46 → 0.54): attention
   buys getting the specifics right.

2. **How loud, not how long.** In joint regression of the two log-components,
   peak: std-β = +0.042 (se 0.008); duration: −0.008 (se 0.009); marginal R²
   of duration given peak = 0.003. Survives recurring-name + gold-length
   controls (peak +0.070, duration +0.005). The h-index analogy (recurrence
   over time should beat volume) fails informatively: recognition is set by
   how widely a name is reproduced at climax, not how long readers stayed.

3. **Templated names dilute (name-uniqueness replicates).** 106/258 events
   are recurring-series instances (an article with the same base name exists
   under another year: elections, tournaments). At matched attention they
   score −0.061 (se 0.015). The 2022 Malaysian general election, 1.3M
   first-year views, scores 0.174 — the series name recurs, the edition does
   not propagate.

4. **No residual region gradient at matched EN attention.** Controlling log
   views, region deltas vs. Anglo-America are −0.060…+0.038 (only South &
   Southeast Asia marginally negative). The corpus-density gradient enters
   through the ledger itself (how much English attention an event gets), not
   as a post-attention discount.

5. **Vintage echo.** 2023 events score −0.049 (se 0.018) vs. 2021 at matched
   attention — consistent with the ~0.1/yr derivative-text accumulation drift
   of t3_1.

6. **Levels.** On the main-run-comparable survivor sub-panel the cohort
   averages 0.432 ≈ CS faculty (0.440 on the same sub-panel). Even the 2022
   Russian invasion of Ukraine (52M first-year views) scores 0.431 there
   (0.449 on the full 36-model event panel) — an average-faculty score; no
   event reaches the artifact/universal zone. Event golds are dense with
   one-off specifics, and a 150-word answer can cover only part of them
   (levels are gold-conditional, as in the paper).

7. **GDELT cross-check (weak).** The rate-limited GDELT DOC API returned
   data for 159/258 name-phrase queries (118 nonzero). log GDELT volume
   correlates r = 0.33 with log pageviews but predicts NameRank at only
   R² = 0.006 — mostly phrase-matching noise; the pageview ledger is primary.

## Reproduce

```bash
# 1-5: build cohort (Wikipedia year pages -> classify -> pageviews -> sample)
python3 scripts/01_collect_candidates.py && python3 scripts/02_fetch_summaries.py
python3 scripts/03_classify.py && python3 scripts/04_fetch_salience.py
python3 scripts/05_build_inputs.py
# probes (OPENROUTER_API_KEY, GEMINI_API_KEY) + flags + baselines
python3 scripts/06_run_probe.py --parallel 40
python3 scripts/09_flag_recurring.py && python3 scripts/08_subpanel_baseline.py
python3 scripts/07_fetch_gdelt.py   # optional cross-check; heavily rate-limited
python3 analyze.py && python3 scripts/10_cutoff_sensitivity.py
```

Paper: Section "News Events: The Attention Ledger" + Appendix "News-Event
Cohort"; figure `paper/figures/make_fig_events.py`.
