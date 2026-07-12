# t5_1 — Mid/late-career awards as recognition predictors

**Question.** The main run measures nine *early* credentials (olympiads,
Putnam, ICPC, Rhodes, MSRA) and finds the credential treadmill: most sit at or
below the working-researcher baseline. Do mid- and late-career awards behave
differently — is a Turing Award or Fields Medal a better indicator of
NameRank than early credentials, and does either add signal beyond
bibliometrics?

**Cohorts** (from Wikidata P166 award-received statements, year qualifier
P585):

| cohort | stage | n | roster |
|---|---|---|---|
| turing_award | late | 77 | complete |
| fields_medal | late | 64 | complete |
| nobel_physics (2000–2023) | late | 64 | complete |
| godel_prize | mid | 80 | complete |
| acm_prize_computing | mid | 18 | complete |
| macarthur_fellow (2000–2023, sample) | mid | 60 | Wikidata coverage — upper bound |
| acm_fellow (2000–2023, sample) | mid | 60 | Wikidata coverage — upper bound |
| sloan_fellow (2000–2023, sample) | early | 49 | Wikidata coverage — upper bound |

**In-run controls** (entities, contexts, and golds copied verbatim from the
main run, so all comparisons are within-run and immune to the ~0.13/yr
vintage drift): 60 OpenAlex long-tail researchers (the working-researcher
baseline), 40 IMO golds (the early-credential anchor), tuixue.online and
nanoGPT (reference websites). Plus two new website entities requested for the
boundary-condition set: icourse.club (USTC course-review community) and
Hackergame (USTC's annual CTF).

**Golds.** en-Wikipedia intro trimmed to ~200 words where available;
otherwise the boilerplate recipe of the main run's credential cohorts
(award fact + award description), so gold density mirrors the cohorts being
compared. `gold_source` is recorded per entity; ladder comparisons should be
checked within gold-source strata (the synthetic-null floor differs).

**Bibliometrics.** Best-effort OpenAlex author match per laureate (top search
hit, name-similarity ≥ 0.85 to count as confident); used in the
marginal-predictor regression NameRank ~ log10(h-index) + award dummies.

**Panel.** The t4_1 event panel: 28 main-run survivors + 8 IKP-v2
replacement models = 36 models, thinking mode where available. Probe
template, judge (Gemini 3 Flash Preview), refusal detector, and multiplicative
coverage×accuracy scoring unchanged from the main run.

**Scripts.**
- `01_collect_award_cohorts.py` — Wikidata SPARQL laureate rosters
- `02_fetch_bios.py` — Wikipedia intro + OpenAlex match per laureate
- `03_build_inputs.py` — entities/contexts/golds + in-run controls
- `04_run_probe.py` — 36-model probe run (resumable)
- `05_analyze.py` — ladder, career-stage contrast, h-index-marginal regression
