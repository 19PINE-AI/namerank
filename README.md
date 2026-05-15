# NameRank

**NameRank: Measuring LLM-Mediated Recognition as the Post-Bibliometric Impact Channel**
*by Bojie Li, Pine AI.*

A continuous cross-model recognition metric for people and named artifacts in the LLM era. NameRank operationalizes the 65% recognition-variance residual that bibliometrics cannot explain (Li 2026, IKP §5.7) into a $[0,1]$ score computed against a 37-model frontier panel.

- **Paper:** [`paper/main.pdf`](paper/main.pdf) (39 pages) · source: [`paper/main.tex`](paper/main.tex)
- **Companion site:** [`web/index.html`](web/index.html) — interactive cohort explorer, per-entity lookup, conditional-pair attribution-flow visualizer, cross-language deltas. Mirror: <https://01.me/research/namerank>.
- **Released artifacts:** 5,719 entities, 37-model panel, 211,603 English probe records, 8,880 Chinese-prompt records.

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
│   ├── main.tex                   # main paper (39 pages)
│   ├── appendix.tex               # appendices
│   ├── references.bib
│   ├── main.pdf                   # compiled paper
│   └── figures/
│       ├── fig{1..5}*.pdf         # figure PDFs included by main.tex
│       └── make_fig{1..5}*.py     # regenerate any figure from data/
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
│   ├── build_web_data.py          # JSON slices for the companion site
│   ├── regenerate_all.sh          # rebuild every CSV from data/raw
│   └── _paths.py                  # repo-relative path helpers
└── web/                            # static companion site (no build step)
    ├── index.html  cohorts.html  lookup.html  inversion.html
    ├── crosslang.html  about.html
    └── assets/{style.css, app.js, data/*.json}
```

## Reproducing the paper

### 1. Compile the paper PDF

```bash
cd paper
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

Required LaTeX packages: `natbib`, `amsmath`, `booktabs`, `hyperref`, `longtable`, `subcaption`, `tabularx`, `pdflscape`, `enumitem`. All standard texlive-latex-extra.

### 2. Regenerate all figures from the released CSVs

```bash
cd paper/figures
python3 make_fig1.py        # cohort distribution
python3 make_fig2_inversion.py
python3 make_fig3_external.py
python3 make_fig4_credentials.py
python3 make_fig5_country.py
```

Requires `matplotlib` and `numpy`. Each script reads `../../data/analysis/*.csv` and writes the corresponding `figN_*.pdf` next to itself. No internet access required.

### 3. Regenerate every analysis CSV from the record-level data

```bash
cd code
bash regenerate_all.sh
```

This reads `data/raw/pilot_summary_en.csv.gz` and `pilot_summary_zh.csv.gz` and rewrites every CSV under `data/analysis/`. Each script is also runnable on its own (`python3 cohort_summary.py`, etc.).

### 4. Re-run the full probe pipeline (~$2,500, ~10h wall-clock)

```bash
export OPENROUTER_API_KEY=...
export GEMINI_API_KEY=...

cd code
python3 run_probe.py --lang en --parallel 96
python3 run_probe.py --lang zh --parallel 24
```

`run_probe.py` is resumable — existing rows in `outputs/pilot_results_<lang>.json` are honored and only missing (entity, model) pairs are dispatched. The pipeline writes a checkpoint every 200 completed pairs and writes the flat record-level CSV to `data/raw/pilot_summary_<lang>.csv` on completion.

Dependencies: `pip install openai google-genai sentence-transformers numpy`. The BGE-large embedding model is downloaded on first run (~1.3 GB).

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
| `about.html`  | method, probe template, panel, judge, caveats |

The companion-site data files in `web/assets/data/` are regenerated from `data/analysis/` via `python3 code/build_web_data.py`.

## Data schemas

- **`data/raw/pilot_summary_en.csv.gz`** — one row per (entity, model). Columns: `entity_id, entity_name, model_id, is_refusal, coverage, accuracy, score, embedding_sim`. 211,603 rows.
- **`data/analysis/namerank_per_entity.csv`** — one row per entity. Columns: `entity_id, entity_name, cohort, n_models, namerank, namerank_sd, refusal_rate, embedding_sim_mean`. 5,719 rows.
- **`data/analysis/namerank_matrix.json`** — `{entity_id: {model_id: score}}` map for all 5,719 entities × 37 models.
- **`data/analysis/cohort_summary.csv`** — one row per cohort (n=54): mean, median, SD, p10/25/75/90, frac ≥ 0.5, frac ≤ 0.05.
- **`data/inputs/pilot_entities.json`** — list of `{id, name, cohort, context, ...}` records with disambiguating context per entity; cohort-specific fields like `cited_by_count`, `h_index`, `institution`, `credential_year`.
- **`data/inputs/gold_answers.json`** — `{entity_id: gold_answer_text}` (100–200 words each).
- **`data/inputs/model_set.json`** — list of model definitions (id, openrouter_id, thinking flag, provider_only).

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
