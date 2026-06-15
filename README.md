# NameRank

**NameRank: Measuring LLM-Mediated Recognition as the Post-Bibliometric Impact Channel**
*by Bojie Li, Pine AI.*

A continuous cross-model recognition metric for people and named artifacts in the LLM era. NameRank operationalizes the 65% recognition-variance residual that bibliometrics cannot explain (Li 2026, IKP §5.7) into a $[0,1]$ score computed against a 37-model frontier panel.

- **Paper:** [`paper/main.pdf`](paper/main.pdf) (60 pages) · source: [`paper/main.tex`](paper/main.tex)
- **Companion site:** [`web/index.html`](web/index.html) — interactive cohort explorer, per-entity lookup, conditional-pair attribution-flow visualizer, cross-language deltas. Mirror: <https://01.me/research/namerank>.
- **Released artifacts:** 5,719 entities, 37-model panel, 211,603 English probe records, 8,880 Chinese-prompt records.
- **Robustness experiments:** [`experiments/`](experiments/) — 10 follow-up audits (gold-length, context, synthetic-null, Wikipedia, prompt-paraphrase, artifact-mediation, gender, fractional-citation, cross-judge, training-cutoff), all folded into the paper. See [§ Robustness experiments](#robustness-experiments-experiments).

## Five headline findings

1. **The credential treadmill.** IMO gold (0.36), Rhodes (0.32), MSRA PhD Fellowship (0.34) all sit *below* the long-tail-OpenAlex working-researcher baseline (0.46).
2. **Artifact > creator inversion.** In 8 of 11 verified (creator, artifact) pairs, the artifact's NameRank exceeds the creator's.
3. **$h$-index ≫ raw citations.** $\log(h\text{-index})$ explains $R^2=0.40$ of NameRank variance; $\log(\text{citations})$ explains 0.14 with zero marginal value beyond $h$-index.
4. **Corpus-density gradient.** Stanford CS faculty mean NameRank 0.54 vs. Tsinghua 0.26. Country effects place Israel/Singapore/Sweden above the USA baseline.
5. **C6 falsification.** tuixue.online (~1M Chinese-language users) registers NameRank 0.25, less than half of nanoGPT (0.71), with a flat cross-language null.

## Repository layout

```
namerank/
├── paper/                         # LaTeX sources + compiled PDF
│   ├── main.tex                   # main paper (60 pages)
│   ├── appendix.tex               # appendices
│   ├── references.bib
│   ├── main.pdf                   # compiled paper
│   └── figures/
│       ├── fig*.pdf               # figure PDFs included by main.tex
│       └── make_fig*.py           # regenerate any figure from data/ or experiments/
│                                  #   (incl. fig_prompt_sensitivity, fig_cutoff_gradient)
├── data/
│   ├── inputs/                    # what goes into the probe pipeline
│   │   ├── pilot_entities.json    # 5,719 entities w/ disambiguating context
│   │   ├── gold_answers.json      # curated 100–200 word gold answers
│   │   ├── model_set.json         # 37-model panel definitions
│   │   ├── probe_template_en.txt  # English probe template
│   │   ├── probe_template_zh.txt  # Chinese probe template (240-entity sub-run)
│   │   └── judge_prompt.txt       # judge prompt (cov/acc, JSON output)
│   ├── raw/                       # record-level probe outputs (gzipped)
│   │   ├── pilot_summary_en.csv.gz   # 211,603 (entity, model) records
│   │   └── pilot_summary_zh.csv.gz   # 8,880 Chinese-prompt records
│   └── analysis/                  # downstream CSVs every figure/table reads
│       ├── namerank_per_entity.csv     # primary per-entity table
│       ├── namerank_matrix.json        # per-entity × per-model scores
│       ├── cohort_summary.csv          # 54 cohort × distribution stats
│       ├── credential_ladder.csv       # credential-treadmill table
│       ├── attribution_pairs_v2.csv    # 11 verified inversion pairs
│       ├── cs_faculty_by_country.csv   # country-gradient table
│       ├── cross_language_per_entity.csv  # 240 entities × en/zh delta
│       ├── east_west_per_cohort.csv    # Chinese-minus-Western cohort medians
│       ├── east_west_per_entity.csv    # ... per entity
│       ├── a{1..4}*.csv                # appendix-table CSVs
│       └── model_cutoffs.json
├── code/
│   ├── run_probe.py               # full pipeline: probe → judge → embedding
│   ├── build_namerank.py          # per-entity aggregation from raw records
│   ├── cohort_summary.py          # cohort_summary.csv
│   ├── credential_ladder.py       # credential_ladder.csv
│   ├── country_affiliation.py     # cs_faculty_by_country.csv
│   ├── east_west.py               # east_west_per_{entity,cohort}.csv
│   ├── cross_language.py          # cross_language_per_entity.csv
│   ├── external_validity.py       # h-index vs citations regressions
│   ├── variance_decomposition.py  # σ²_entity vs σ²_model
│   ├── refusal_patterns.py        # per-model / per-cohort refusal
│   ├── embedding_judge_gap.py     # judge vs BGE-large agreement
│   ├── per_model_summary.py       # per_model_summary.csv (Appendix C)
│   ├── build_web_data.py          # JSON slices for the companion site
│   ├── regenerate_all.sh          # rebuild every CSV from data/raw
│   ├── panel.py                   # 37-model Western/Chinese partition
│   └── _paths.py                  # repo-relative path helpers
├── experiments/                   # post-hoc robustness audits (see § below)
│   ├── t1_1_gold_length/  t1_2_context_ab/  t1_3_synthetic_null/
│   ├── t1_4_wikipedia/    t2_6_prompt_sensitivity/  t2_7_artifact_mediation/
│   ├── t2_8_gendered_names/  t2_9_fractional_citations/  t2_10_cross_judge/
│   └── t3_1_cutoff_gradient/      # each: analyze.py + outputs + README.md
├── requirements.txt               # python dependencies
└── web/                            # static companion site (no build step)
    ├── index.html  cohorts.html  lookup.html  inversion.html
    ├── crosslang.html  validation.html  about.html
    └── assets/{style.css, app.js, data/*.json}
```

## Reproducing the paper

Each step below is independent and operates on the layer above it. Step 1 needs only `texlive` (no Python). Steps 2 and 3 only need `pip install matplotlib numpy` (the analysis scripts use only the Python stdlib, but the figure scripts use `matplotlib`). Step 4 is the heavy end-to-end re-run.

### Quick reproduction (no probe re-run)

```bash
pip install -r requirements.txt    # matplotlib + numpy is enough for steps 1–3
cd code && bash regenerate_all.sh  # → all CSVs in data/analysis/ + JSONs in web/assets/data/
cd ../paper/figures
for f in make_fig*.py; do python3 "$f"; done
cd .. && pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```

### 1. Compile the paper PDF

```bash
cd paper
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

Required LaTeX packages: `natbib`, `amsmath`, `booktabs`, `hyperref`, `longtable`, `subcaption`, `tabularx`, `pdflscape`, `enumitem`. All standard `texlive-latex-extra`.

### 2. Regenerate all figures from the released CSVs

```bash
cd paper/figures
python3 make_fig1.py                # cohort distribution
python3 make_fig2_inversion.py      # 11-pair inversion (reads attribution_pairs_v2.csv)
python3 make_fig3_external.py       # h-index vs citations
python3 make_fig4_credentials.py    # credential treadmill (reads credential_ladder.csv + baseline)
python3 make_fig5_country.py        # country gradient (reads cs_faculty_by_country.csv)
```

Requires `matplotlib` and `numpy`. Every figure script reads `../../data/analysis/*.csv` — there are no hard-coded numbers, so editing the input data and re-running these regenerates the figures.

### 3. Regenerate every analysis CSV from the record-level data

```bash
cd code
bash regenerate_all.sh
```

This reads `data/raw/pilot_summary_en.csv.gz` (+ `_zh.csv.gz` for the cross-language step) and rewrites every CSV under `data/analysis/` plus every JSON slice under `web/assets/data/`. Each script is also runnable on its own (`python3 cohort_summary.py`, etc.). The 37-model Western/Chinese partition lives in `code/panel.py` — add a model there and to `data/inputs/model_set.json` to extend the panel.

### 4. Re-run the full probe pipeline (~$2,500, ~10h wall-clock)

```bash
export OPENROUTER_API_KEY=...
export GEMINI_API_KEY=...

cd code
python3 run_probe.py --lang en --parallel 96
python3 run_probe.py --lang zh --parallel 24
```

`run_probe.py` is resumable — existing rows in `outputs/pilot_results_<lang>.json` are honored and only missing (entity, model) pairs are dispatched. The pipeline writes a checkpoint every 200 completed pairs and writes the flat record-level CSV to `data/raw/pilot_summary_<lang>.csv` on completion.

Dependencies: `pip install openai google-genai sentence-transformers numpy` (or `pip install -r requirements.txt`). The BGE-large embedding model is downloaded on first run (~1.3 GB).

## Companion website

Serve `web/` over HTTP (the pages use ES modules and `fetch`, which require an HTTP origin):

```bash
cd web
python3 -m http.server 8000
# → open http://localhost:8000
```

Pages:

| Page | What it shows |
|---|---|
| `index.html`  | overview, headline findings, cite |
| `cohorts.html`  | per-cohort distribution chart, credential ladder, country gradient, full cohort table |
| `lookup.html`  | searchable index of all 5,719 entities with NameRank, cross-model SD, refusal rate |
| `inversion.html`  | 11 (creator, artifact) pairs with conditional-probe attribution flow |
| `crosslang.html`  | 240 entities × en/zh delta with W/C panel splits |
| `validation.html` | panel-size sensitivity curve, per-model generosity/refusal, conditional NameRank |
| `about.html`  | method, probe template, panel, judge, caveats |

The companion-site data files in `web/assets/data/` are regenerated from `data/analysis/` via `python3 code/build_web_data.py` (also invoked by `regenerate_all.sh`).

## Data schemas

- **`data/raw/pilot_summary_en.csv.gz`** — one row per (entity, model). Columns: `entity_id, entity_name, model_id, is_refusal, coverage, accuracy, score, embedding_sim`. 211,603 rows.
- **`data/analysis/namerank_per_entity.csv`** — one row per entity. Columns: `entity_id, entity_name, cohort, n_models, namerank, namerank_sd, refusal_rate, embedding_sim_mean`. 5,719 rows.
- **`data/analysis/namerank_matrix.json`** — `{entity_id: {model_id: score}}` map for all 5,719 entities × 37 models.
- **`data/analysis/cohort_summary.csv`** — one row per cohort (n=54): n, mean, median, SD, p10/25/75/90, frac ≥ 0.5, frac ≤ 0.05, refusal_rate.
- **`data/analysis/per_model_summary.csv`** — one row per panel model (n=37): vendor, family, thinking flag, n_records, mean_score, refusal_rate, mean_score_non_refusal. Source of Appendix C.
- **`data/analysis/a2_panel_size_curve.csv`** — Pearson/Spearman correlation against the full 37-model panel as a function of subset size `k`, mean over 100 random subsets per `k`.
- **`data/analysis/a3_conditional_namerank.csv`** — per-cohort unconditional vs. conditional (non-refusal-restricted) NameRank.
- **`data/inputs/pilot_entities.json`** — list of `{id, name, cohort, context, ...}` records with disambiguating context per entity; cohort-specific fields like `cited_by_count`, `h_index`, `institution`, `credential_year`.
- **`data/inputs/gold_answers.json`** — `{entity_id: gold_answer_text}` (100–200 words each).
- **`data/inputs/model_set.json`** — list of model definitions (`id`, `openrouter_id`, `thinking` flag, `vendor`, `family`, `lab`). The Western/Chinese partition is derived from the `vendor` field by `code/panel.py`.

## Robustness experiments (`experiments/`)

Post-hoc audits of the headline findings. Each subdirectory is self-contained
(`analyze.py` + derived CSV/JSON outputs + a `README.md` with the headline and
reproduction command) and reads only released artifacts under `data/`. The
large raw per-(entity, model) probe dumps are not committed (regenerable via
`code/run_probe.py`); the derived summaries the analyses actually consume are.

| Experiment | Question | Headline |
|---|---|---|
| `t1_1_gold_length` | Does gold-answer length drive the credential gap? | **No; treadmill ordering survives every length adjustment (matched-pairs infeasible — non-overlapping lengths). → §6.7.8, App. N.** |
| `t1_2_context_ab` | Does the disambiguating context leak the answer? | **No; minimal-context ablation drops levels but preserves the Stanford–Tsinghua gradient (~5% shrinkage). → §6.7.8, App. N.** |
| `t1_3_synthetic_null` | What does a never-seen name score? | **Floor ~0.04 (dense gold), ~0.20 (short-gold cohorts); 15/37 models score 0. Floor-adjusting widens the credential gap. → §6.7.7, Fig. 18, App. M.** |
| `t1_4_wikipedia` | Is NameRank just "has a Wikipedia page"? | **No; Wikipedia explains 2–8% of variance, h-index dominance survives. → §6.7.8, App. N.** |
| `t2_6_prompt_sensitivity` | Is the metric robust to probe wording? | **Ordering robust (Pearson 0.93–0.98); absolute levels are wording-conditional. → §6.7.4, Fig. 14, App. I.** |
| `t2_7_artifact_mediation` | Is named-artifact amplification causal? | **Yes; injecting the artifact into context lifts recognition +0.058 mean, +0.288 (t=5.8) on Jiayi, via retrieval-deficient models. → §6.3.4.** |
| `t2_8_gendered_names` | Is there a gender bias? | **Small reproducible +0.038 (CS faculty) / +0.027 (OpenAlex) man-coded lift, surviving controls. → §7.5, App. O.** |
| `t2_9_fractional_citations` | Is h-index dominance about attribution density? | **No — mechanism is name-recurrence across distinct works, not attribution-per-paper (fractional R²=0.15 ≈ raw 0.14). → paper §6.4.1, Fig. 7, App. K.** |
| `t2_10_cross_judge` | Are findings a Gemini-judge artifact? | **No; Pearson 0.87–0.93 across Gemini/GPT-5/Claude, ladder preserved; capability-controlled in-family lift Gemini +0.06. → paper §6.7.6, Fig. 17, App. L.** |
| `t3_1_cutoff_gradient` | Is the silent zone a corpus-timing artifact? | **No — intrinsic; matched DiD ≈ 0. Exposes ~0.13/yr cross-vintage capability drift. → paper §6.7.5, Fig. 15, App. J.** |

All ten experiments are now written into the paper (Sections 6.3.4, 6.4.1,
6.7.4–6.7.8, and 7.5; Figures 7/14/15/17/18; Appendices I–O); the limitations
table is Appendix P. Reproduce any one with
`cd experiments/<name> && python3 analyze.py`.

## Citation

```bibtex
@article{li2026namerank,
  title={NameRank: Measuring LLM-Mediated Recognition as the Post-Bibliometric Impact Channel},
  author={Li, Bojie},
  journal={arXiv preprint},
  year={2026},
  note={Code: https://github.com/19PINE-AI/namerank}
}
```

## License

Code: MIT. Data (probe specifications, gold answers, raw probe responses, analysis CSVs): CC BY 4.0.

## Status

Draft v1, accompanying arXiv preprint. The metric is intended for re-runs at each major frontier-model release cycle; this repo will be tagged `v1.0` at preprint freeze and a new tag created for each subsequent NameRank revision.
