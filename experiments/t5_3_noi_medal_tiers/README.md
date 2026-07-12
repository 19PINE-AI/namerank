# t5_3 — NOI 2009 medal tiers: does the medal grade predict NameRank?

**Question.** The main run's credential-treadmill finding used only *gold*
medalists (NOI cohort: 29 golds, 20 of them from NOI 2009). This experiment
probes the **complete NOI 2009 medal roster** — 20 gold, 34 silver, 49 bronze
(103 medalists) — to ask: (a) do the three tiers differ in NameRank; (b) is
there a dose-response on the underlying contest score beyond the tier cuts;
(c) what covariates (grade at contest, gender, province) carry signal.

**Roster.** OIerDb raw data (github.com/OIerDb-ng/OIer, `model/data.txt`),
cross-validated line-by-line against the official CCF medal list
(https://www.noi.cn/hjmd/mdgs/2009/2009-09-18/710218.shtml): identical names,
schools, and scores; official 一等奖/二等奖/三等奖 map to gold/silver/bronze.
Score bands: gold 366–577, silver 263–352, bronze 165–260. Contest rank
(1–103, ties share min rank) is derived from the score column and released in
`inputs/noi2009_roster.csv`.

**Entities** (`inputs/tier_entities.json`):
- 20 NOI 2009 golds — copied verbatim from the main run (ids, names,
  contexts, golds unchanged), so the gold arm doubles as the anchor.
- 83 new silver/bronze entities. Probe names follow the main-run convention
  "Pinyin (汉字)" with year+school context, so common-Pinyin collisions stay
  disambiguated. Romanization: pypinyin + passport ü→yu (matches the main
  run's 吕→"Lyu"), surname 缪→Miao fix; four names flagged
  `pinyin_uncertain` (阿拉法特 Uyghur, no surname split; 胡张广达 combined
  double surname; 梁錦鴻 Macau/likely Cantonese-romanized; 黄偲 polyphonic
  偲). The 汉字 in every probe carries the identity signal regardless.
- Golds follow the main-run NOI boilerplate recipe with only the tier band
  changed (63–74 words in all tiers), so gold density is matched and the
  ~0.20 short-boilerplate synthetic-null floor (App. M) applies equally to
  all three tiers.

**In-run controls** (golds/contexts verbatim from the main run): the 9
non-2009 NOI golds (2012/2013), 30 OpenAlex long-tail researchers (seed-42
sample), tuixue.online + nanoGPT, and the diagnostic-reference and
MSRA-fellowship Bojie Li entities — 李博杰 is himself an NOI 2009 bronze
medalist, so the run contains a within-person triple (bronze-roster
boilerplate gold vs 2017-fellowship framing vs dense reference gold).

**Panel.** The t4_1/t5_1 event panel: 28 main-run survivors + 8 IKP-v2
replacement models = 36 models, thinking where available. Probe template,
judge (Gemini 3 Flash Preview), refusal detector, and multiplicative
coverage×accuracy scoring unchanged from the main run. 146 entities × 36
models = 5,256 records.

**Scripts.**
- `01_build_inputs.py` — roster → entities/golds + in-run controls
- `02_run_probe.py` — 36-model probe run (resumable)
- `03_analyze.py` — tier distributions/tests, dose-response, covariates,
  main-run anchor, within-person triple

## Results (run 2026-07-12, 5,256/5,256 records clean)

| tier | n | mean [95% CI] | median | sd | range | above floor (0.199) |
|---|---|---|---|---|---|---|
| gold | 20 | 0.319 [0.281, 0.362] | 0.303 | 0.095 | 0.209–0.589 | 20/20 |
| silver | 34 | 0.180 [0.160, 0.204] | 0.169 | 0.065 | 0.063–0.425 | 8/34 |
| bronze | 49 | 0.165 [0.152, 0.179] | 0.162 | 0.050 | 0.077–0.353 | 8/49 |

- **Gold vs non-gold is a cliff, silver vs bronze is nothing.** Kruskal-Wallis
  H=39.3 (p<1e-8); gold>silver Cliff's δ=+0.85 (p<1e-6); silver vs bronze
  p=0.245, δ=+0.15. Every gold clears the short-boilerplate synthetic-null
  floor; the silver and bronze *means* sit at/below it — as cohorts they are
  statistically silent, with a recognized tail of 16 individuals.
- **Dose-response is the tier cliff, not the score.** Pooled NameRank ~
  contest score R²=0.397 (ρ=+0.56), but within-tier R² collapses (gold 0.11,
  silver 0.04, bronze 0.07): crossing the gold line matters; marginal points
  do not. Consistent with the mechanism — NOI gold rosters are documented
  (~top 20, 保送 coverage, media), silver/bronze rosters barely propagate.
- **The recognized non-golds are career effects, pure treadmill.** Top
  non-golds: Fan Haoqiang (范浩强, silver, 0.425 — above the *gold mean*;
  Megvii researcher), Li Bojie (李博杰, bronze, 0.353 — contest rank 68,
  recognition rank 7 of 103), Li Guanru (0.304). Post-medal named output,
  not the medal, carries the name.
- **Covariates.** Gender gap vanishes within tier (non-gold: men 0.173,
  women 0.164; no female golds in 2009). Grade at contest is uninformative
  (the 初二 outlier is Fan Haoqiang alone).
- **Anchor.** 63 entities shared with the released main run: ρ=0.915, mean
  shift −0.006 (panel equivalent). NOI golds alone ρ=0.66, shift −0.029 —
  consistent with this cohort having the highest within-entity σ (0.404) in
  the main run.
- **Within-person triple (李博杰).** Bronze-roster boilerplate gold 0.353 /
  MSRA-2017 framing 0.414 / dense reference gold 0.118 (released 0.090):
  the same person spans 0.12–0.41 depending on gold density and framing —
  NameRank levels are gold-recipe-conditional (matches App. M); only
  within-recipe comparisons (the tier ladder above) are valid.

Outputs: `outputs/tier_per_entity.csv` (per-entity), `outputs/tier_analysis.json`
(stats), `outputs/pilot_results_tiers.json` (raw records, gitignored pattern).
