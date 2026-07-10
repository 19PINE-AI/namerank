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

**Panel.** 8 of the 37 main-run models were no longer routable on OpenRouter
at run time (2026-07 provider churn); grok-4.20-think was recovered via the
direct xAI API → 29-model panel, 7,482 records. Recomputing the full main run
on the same 29 models correlates r = 0.994 with the released 37-model scores
(mean shift +0.007), so main-run numbers are quoted unadjusted
(`outputs/subpanel_baseline.json`).

## Headlines

1. **Dose–response, carried by accuracy.** NameRank ~ log10(total views):
   R² = 0.13 (repeated 10-fold CV 0.13 ± 0.13), decile means 0.35 → 0.48
   across ~2.4K → ~3.3M views; refusal rate falls 11% → 1%. Gold answers get
   denser as events get bigger (a suppressor): controlling gold length,
   slope +0.048 → +0.067, R² = 0.19. The channel is mostly accuracy
   (0.58 → 0.86 by decile) rather than coverage (0.43 → 0.53): attention
   buys getting the specifics right.

2. **How loud, not how long.** In joint regression of the two log-components,
   peak: std-β = +0.048 (se 0.008); duration: −0.003 (se 0.009); marginal R²
   of duration given peak = 0.000. Survives recurring-name + gold-length
   controls (peak +0.074, duration +0.008). The h-index analogy (recurrence
   over time should beat volume) fails informatively: recognition is set by
   how widely a name is reproduced at climax, not how long readers stayed.

3. **Templated names dilute (name-uniqueness replicates).** 106/258 events
   are recurring-series instances (an article with the same base name exists
   under another year: elections, tournaments). At matched attention they
   score −0.057 (se 0.015). The 2022 Malaysian general election, 1.3M
   first-year views, scores 0.164 — the series name recurs, the edition does
   not propagate.

4. **No residual region gradient at matched EN attention.** Controlling log
   views, region deltas vs. Anglo-America are −0.055…+0.039 (only South &
   Southeast Asia marginally negative). The corpus-density gradient enters
   through the ledger itself (how much English attention an event gets), not
   as a post-attention discount.

5. **Vintage echo.** 2023 events score −0.046 (se 0.017) vs. 2021 at matched
   attention — consistent with the ~0.1/yr derivative-text accumulation drift
   of t3_1.

6. **Levels.** Cohort mean 0.427 ≈ CS faculty (0.436 on the same sub-panel).
   Even the 2022 Russian invasion of Ukraine (52M first-year views) scores
   0.437 — an average-faculty score; no event reaches the artifact/universal
   zone. Event golds are dense with one-off specifics, and a 150-word answer
   can cover only part of them (levels are gold-conditional, as in the paper).

## Reproduce

```bash
# 1-5: build cohort (Wikipedia year pages -> classify -> pageviews -> sample)
python3 scripts/01_collect_candidates.py && python3 scripts/02_fetch_summaries.py
python3 scripts/03_classify.py && python3 scripts/04_fetch_salience.py
python3 scripts/05_build_inputs.py
# probes (OPENROUTER_API_KEY, GEMINI_API_KEY, XAI_API_KEY) + flags + baselines
python3 scripts/06_run_probe.py --parallel 40
python3 scripts/09_flag_recurring.py && python3 scripts/08_subpanel_baseline.py
python3 scripts/07_fetch_gdelt.py   # optional cross-check; heavily rate-limited
python3 analyze.py
```

Paper: Section "News Events: The Attention Ledger" + Appendix "News-Event
Cohort"; figure `paper/figures/make_fig_events.py`.
