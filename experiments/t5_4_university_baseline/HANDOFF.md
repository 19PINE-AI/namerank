# HANDOFF — t5_4 per-university baselines → open-book-judge session

Written 2026-07-12 ~15:40 UTC by the t5_4 session, on user instruction: the
full-pass session's **open-book (asymmetric-knowledge) judge is now the
standard v3 judge** and takes over this experiment's scoring, including the
IMO/OpenAlex in-run controls. This file is the complete state transfer.

## What this experiment is

User-directed extension: per-university working-researcher rows (MIT,
UC Berkeley, UCSD, UC Irvine) for the credential-treadmill ladder, under two
designs (see README.md for full construction detail):

- **Windowed** (`univ_mit`, `univ_uc_berkeley`, `univ_ucsd`, `univ_uc_irvine`,
  ~100 each): the main baseline's exact inclusion rule (OpenAlex, citations
  500–30,000 + first-author paper >=500 cites), institution-stratified.
  MATCHED design — cannot rank universities (conditions on the outcome's
  main predictor); tests whether the global 771 baseline generalizes.
- **Faculty** (`univ_fac_*`, CSRankings rosters, seed-42, min(100, roster),
  NO bibliometric conditioning): the design that CAN rank universities.
  These are the rows intended for the paper's Figure 3 / credential table.
- **In-run controls**: 60 `long_tail_researcher_openalex` + 40 `imo_gold`
  entities re-probed with main-run identity (seed-42 resample, same as t5_1).

## Settled findings (safe to rely on)

1. **v1 protocol, windowed (COMPLETE)**: all four university cohorts sit at
   the in-run OpenAlex baseline (0.476–0.493 vs 0.509±0.042 survivor-28;
   ANOVA p=0.94), well above in-run IMO gold (0.403). Control anchoring vs
   released values: +0.019/+0.022 (uniform 2026-panel drift). The published
   baseline is NOT an artifact of global sampling; treadmill unchanged.
   Files: `outputs/pilot_results_univ.json` (17,856 records, responses
   retained), `outputs/univ_summary.csv`, `outputs/summary.json`,
   analysis `scripts/04_analyze.py`.
2. **The S2-sparse-gold regression (evidence the new judge should absorb)**:
   under graded cov*acc + S2 works-list golds, famous faculty score 0.000
   with judge-acknowledged accurate responses (Abbeel/Torralba/Tedrake/
   Zaharia; 44% of MIT faculty "known-but-zero-credited"). Root cause:
   graded coverage = overlap of two small samples of the entity's fact
   universe. Record-level examples in `outputs/univ_v2_results.jsonl`
   (grep entity_id `univ_fac_uc_berkeley_pieter_abbeel`).
3. **Windowed equality is design-implied**: matched citation window ->
   matched recognition; the user's university-ranking question lives in the
   faculty design only.

## Data assets (all under experiments/t5_4_university_baseline/)

- `inputs/univ_entities.json` / `univ_gold.json` — v1 entities+golds (892).
- `inputs/univ_entities_v2.json` / `univ_gold_v2.json` — v2 contexts
  (windowed: "an academic researcher in {field} at {inst}"; faculty:
  "a computer science faculty member at {inst}"); golds = S2 route,
  gold_v2 flag marks the 702 with S2 matches. Controls copied verbatim from
  t6 v2 inputs BEFORE t6's `08_fix_golds_v2.py` — control golds are stale
  w.r.t. their credential-gold fix.
- `inputs/univ_gold_v3.json` + `.meta.json` — 892 web-grounded 55-word
  golds (`code/generate_golds.py`), covering ALL entities incl. the 190
  S2-unmatched. **52 remain zero-source after one retry** (list = meta
  entries with n_sources==0) — parametric-memory risk; treat as a
  sensitivity split (14_analyze_final.py already reports grounded-only).
- `outputs/univ_v2_results.jsonl` — **the main asset**: v2-protocol probe
  records WITH responses, 36-model panel. **COMPLETE: all 25,272 records,
  zero errors** (finished 15:52 UTC, after this handoff was first written).
- `outputs/univ_v3judge_results.jsonl` — 1,202 records from the SUPERSEDED
  closed-book judge_prompt_v3 pass (stopped on user instruction). Discard
  or keep for judge-comparison; do not mix with open-book scores.
- `outputs/pilot_results_univ.json` — complete v1 records (responses kept).
- `outputs/candidates.json`, `faculty_candidates.json`, match reports,
  `_s2_gold_cache.json`, `_s2_faculty_cache.json`, `inputs/csrankings_all.csv`
  (roster snapshot 2026-07-12).

## What remains to do (for the open-book-judge session)

1. **Judge `univ_v2_results.jsonl` with the open-book v3 judge** once the
   probe file is complete (25,272 records). `scripts/13_judge_detect.py` is
   the plumbing for a re-judge pass (resumable, refusals short-circuited);
   it currently loads `t6_v2_protocol/inputs/judge_prompt_v3.txt` + the
   closed-book schema — swap in the open-book judge call. Delete
   `outputs/univ_v3judge_results.jsonl` first if re-using the filename.
2. **Top-up probe the 190 S2-unmatched entities** (they were skipped by the
   v2 run; restoring them removes a name-ambiguity selection bias that
   correlates with East-Asian names). `scripts/12_topup_probe_v3.py` is
   ready — same judge-swap needed. 190x36 = 6,840 probes.
3. **Recompute the ladder**: `scripts/14_analyze_final.py` (detection-rate
   headline + cov*acc depth diagnostic + between-university tests +
   famous-name validation cases + grounded-only sensitivity). Validation
   gate: Abbeel/Torralba/Tedrake/Zaharia must score high; if the open-book
   judge verifies beyond-gold facts, the 52 ungrounded-gold entities and
   the gold-narrowness concern may both dissolve — re-check.
4. **Controls/IMO takeover**: the 100 in-run controls duplicate entities in
   your full pass — use same-entity cross-run agreement as the anchoring
   check, but note the control-gold provenance mismatch (item above).
5. **Paper integration** (original user request, still pending): four
   faculty rows (+ optionally windowed rows as the matched companion) into
   Figure 3 (`paper/figures/make_fig4_credentials.py`), the appendix
   credential table, and §3.2 — under the final open-book numbers, with
   cov*acc demoted to a depth diagnostic in the appendix (user decision).

## Operational gotchas

- **OpenAlex**: all identities exhausted until 2026-07-13 00:00 UTC (paid
  key AND the icourse SOCKS tunnel's IP bucket). S2 keyless is the working
  route (serialized, ~1 rps).
- **Gemini/OpenRouter** are shared with your full pass; this experiment ran
  judges at parallel 8 and probes at 12–16 to stay polite.
- v1 vs v2/v3 comparisons: the 36-model panel runs ~+0.02 above the released
  37-model values (measured on in-run controls, v1).
- User decisions logged in memory `gold_methodology.md` (detection headline,
  cov*acc -> appendix depth diagnostic) and in this README's scoring-rule
  section.
