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
