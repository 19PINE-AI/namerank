# NameRank

**The Model Knows Your Project, Not You: Measuring Recognition in LLMs with NameRank**
*by Bojie Li (Pine AI) and Noah Shi (University of Washington).*

NameRank is a continuous $[0,1]$ recognition score for people and named artifacts
in the LLM era. Each entity is probed with one open-ended question across a
36-model frontier panel; an independent judge returns a **binary recognition
verdict** against a curated gold answer — *did the model state a specific,
non-guessable fact about this exact entity?* — so hallucination, context echo,
and lucky guesses earn nothing. NameRank is the fraction of the panel that
recognizes the entity. It operationalizes the recognition-variance residual that
bibliometrics cannot explain (Li 2026, IKP §5.7).

- **Paper:** [arXiv:2607.12520](https://arxiv.org/abs/2607.12520) · [HTML](https://arxiv.org/html/2607.12520) · [PDF](https://arxiv.org/pdf/2607.12520) (47 pages) · local copy [`paper/main.pdf`](paper/main.pdf) · source: [`paper/main.tex`](paper/main.tex)
- **Companion site:** [`site/`](site/) — an interactive React explainer (mechanism walkthrough, findings dashboards, and a 4,685-entity explorer with every model's verbatim answer and verdict). Live at <https://01.me/research/namerank>.
- **Scale:** 4,685 entities across 54 cohorts, a 36-model panel, and the record-level recognition verdicts in [`experiments/t6_v2_protocol/outputs/recognition_final.jsonl.gz`](experiments/t6_v2_protocol/outputs/recognition_final.jsonl.gz) (gzipped, ~12 MB).
- **Robustness:** [`experiments/`](experiments/) — 18 self-contained follow-up audits, all folded into the paper. See [§ Robustness experiments](#robustness-experiments-experiments).

## Headline findings

1. **The credential treadmill — and its marquee inversion.** Every Olympic-style
   credential sits *below* a working-researcher baseline (0.40): IMO gold 0.12,
   Rhodes 0.15, MSRA PhD Fellowship 0.18 — because no named artifact ships with
   the medal. Yet the ranking flips at the very top, where Nobel (0.98), Turing
   (0.97), and Fields (0.96) laureates saturate the panel.
2. **Artifact > creator.** For independent creators the tool out-ranks its maker
   (e.g. Tianshou 0.78 vs. its author 0.22); the credential that *does* propagate
   is a named method or an awarded paper. Being one of many named authors on a
   flagship model report or system card earns almost nothing — recognition
   attaches to the artifact's distinctive name, not the roster behind it.
3. **No bibliometric predicts recognition well.** Under the recognition verdict,
   $\log(h\text{-index})$ and $\log(\text{citations})$ each explain only
   $R^2\approx0.22$; neither is a strong instrument for corpus presence.
4. **Corpus-density gradient.** Top-density institutions out-recognize peers at
   matched citations; US CS faculty average 0.64 vs. 0.33 for China.
5. **Attention ≠ recognition, and models can't introspect it.** On 258 news
   events, recognition loads on peak salience, not persistence; a self-report
   probe shows a model's "what do I know?" reads a corpus prior, not its own
   knowledge. Two Chinese-language sites with enormous user bases make the
   boundary concrete: tuixue.online (peak audience ~1M) scores 0.39 and
   icourse.club 0.14, both below nanoGPT (0.78), whose audience is far smaller —
   because those sites spread *functionally*, with no name attached in indexable
   text.

## Repository layout

```
namerank/
├── paper/                         # LaTeX sources + compiled PDF
│   ├── main.tex  appendix.tex  references.bib
│   ├── arxiv.sty                  # single-column tech-report style
│   ├── main.pdf                   # compiled paper (47pp)
│   └── figures/
│       ├── _data.py               # loads the recognition run for every figure
│       ├── compute_all_numbers.py # → computed_numbers.json (every number the paper cites)
│       ├── make_fig*.py           # regenerate each figure PDF
│       └── fig_*.pdf
├── site/                          # React/Vite companion site (source of the live explainer)
│   ├── src/{sections,components,lib,data}/   scripts/build_data.py
│   └── public/data/               # generated chart + entity data
├── docs/                          # reproducibility docs (probe/judge prompts, cohorts, worked examples)
├── data/
│   ├── inputs/                    # entities, gold answers, model set, probe/judge templates
│   └── analysis/                  # derived recognition tables (see data/analysis/README.md)
├── code/
│   ├── run_probe.py               # shared probe → judge → embedding harness
│   ├── build_release_tables.py    # regenerate data/analysis/ from the recognition run
│   ├── country_affiliation.py     # institution → country map (country gradient)
│   └── _paths.py                  # repo-relative path helpers
├── experiments/                   # 18 robustness audits + t6_v2_protocol (the recognition run)
├── tool/                          # self-contained NameRank measurement CLI
├── requirements.txt
└── LICENSE
```

## Reproducing the paper

The record-level source of truth is
`experiments/t6_v2_protocol/outputs/recognition_final.jsonl.gz` — one binary
`recognized` verdict per (entity, model), shipped gzipped (~12 MB; 234,574
records). Everything downstream is a deterministic function of that file.
`build_release_tables.py` reads the `.gz` directly, so no manual
decompression is needed.

```bash
pip install -r requirements.txt

# 1. Rebuild the released aggregate tables from the recognition run.
#    Cross-checks every value against the paper and refuses to write on drift.
python3 code/build_release_tables.py

# 2. Recompute every number the paper cites, and regenerate the figures.
cd paper/figures
python3 compute_all_numbers.py          # → computed_numbers.json
for f in make_fig*.py; do python3 "$f"; done

# 3. Compile the paper.
cd .. && pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```

The paper uses the bundled `arxiv.sty`; required LaTeX packages are all in
`texlive-latex-extra` / `texlive-fonts-extra`. Figures and numbers have no
hard-coded values — they load the recognition records through
`paper/figures/_data.py`.

### Re-running the probe pipeline (~$2.5K end-to-end)

```bash
export OPENROUTER_API_KEY=...   # probed-model calls
export GEMINI_API_KEY=...       # judge

# The recognition run's orchestration lives in experiments/t6_v2_protocol/scripts/
# (probe → open-book recognition judge → uniform final pass). run_probe.py is the
# shared probe/judge harness the experiments import; it is resumable.
```

### Companion site

```bash
cd site
npm install
npm run data     # regenerate JSON assets from ../data and ../experiments
npm run dev      # local preview
npm run build    # → dist/ (base './', works at any mount path)
```

`site/scripts/build_data.py` reads the recognition sources
(`recognition_final.jsonl`, `computed_numbers.json`, the appendix tables). The
per-entity answer shards (`site/public/data/answers/`, ~157 MB) are regenerated
at build time and are gitignored; `answers_index.json` is committed.

## Data schemas

- **`experiments/t6_v2_protocol/outputs/recognition_final.jsonl.gz`** — one JSON object per (entity, model): `{dataset, entity_id, model_id, recognized (0/1), rationale}` (gzipped; `zcat` to read).
- **`data/analysis/namerank_per_entity.csv`** — one row per entity: `entity_id, entity_name, cohort, n_models, namerank, namerank_sd, refusal_rate, embedding_sim_mean`.
- **`data/analysis/namerank_matrix.json`** — `{entity_id: {model_id: recognized}}` for the 4,730-entity × 36-model main run.
- **`data/analysis/cohort_summary.csv` / `credential_ladder.csv` / `per_model_summary.csv` / `cs_faculty_by_country.csv` / `cross_language_per_entity.csv` / `attribution_pairs_v2.csv`** — derived recognition tables; see [`data/analysis/README.md`](data/analysis/README.md).
- **`data/inputs/`** — `pilot_entities.json` (entities + disambiguating context), `gold_answers.json`, `model_set.json`, `probe_template_{en,zh}.txt`, `judge_prompt.txt`. The recognition run's exact v2 inputs (gold answers, contexts, the open-book judge) live under `experiments/t6_v2_protocol/inputs/`.

## Robustness experiments (`experiments/`)

Each subdirectory is self-contained (`analyze.py` / scripts + derived outputs +
`README.md` with the headline and reproduction command). The large raw
per-(entity, model) probe dumps are gitignored; the derived summaries the
analyses consume are committed.

| Experiment | Question | Headline |
|---|---|---|
| `t1_1_gold_length` | Does gold-answer length drive the credential gap? | No; treadmill ordering survives length adjustment. |
| `t1_2_context_ab` | Does the disambiguating context leak the answer? | No; the corpus-density gradient survives context ablation. |
| `t1_3_synthetic_null` | What does a never-seen name score? | Floor near zero; verdicts track the entity, not the model. |
| `t1_4_wikipedia` | Is NameRank just "has a Wikipedia page"? | No; Wikipedia explains little of the variance. |
| `t2_6_prompt_sensitivity` | Robust to probe wording? | Ordering robust (Pearson 0.93–0.98). |
| `t2_7_artifact_mediation` | Is named-artifact amplification causal? | Injecting the artifact into context lifts recognition, via retrieval-deficient models. |
| `t2_8_gendered_names` | Is there a gender bias? | Small reproducible man-coded lift, surviving controls. |
| `t2_9_fractional_citations` | Is the bibliometric signal attribution density? | No — it is name-recurrence across distinct works. |
| `t2_10_cross_judge` | A single-judge artifact? | No; findings hold across Gemini/GPT-5/Claude judges. |
| `t3_1_cutoff_gradient` | Is the silent zone a corpus-timing artifact? | No — intrinsic; matched DiD ≈ 0. |
| `t4_1_news_events` | Attention vs. recognition on 258 events. | Recognition loads on peak salience, not persistence. |
| `t5_1_award_ladder` | Where does the credential ladder invert? | At the marquee tier (Nobel/Turing/Fields). |
| `t5_2_attention_baseline` | Is NameRank just Wikipedia-pageview rank? | No — undefined for most entities; flow vs. stock. |
| `t5_3_noi_medal_tiers` | Gold vs. silver vs. bronze. | A gold-vs-non-gold cliff; silver ≈ bronze. |
| `t5_4_self_report` | Can you just ask the model what it knows? | No — self-report reads a corpus prior, not its own state. |
| `t5_4_university_baseline` | University-faculty baseline. | Institution-density gradient at matched citations. |
| `t5_5_llm_area` | Method originators vs. their methods. | The named method out-ranks its originator. |
| `t5_5_noi_boundary_rd` | Recognition at a naming boundary. | Unique, English-documented names propagate; utility names do not. |
| `t6_v2_protocol` | The recognition run itself. | Probe → open-book recognition judge → uniform final pass. |

## Citation

```bibtex
@article{li2026namerank,
  title={The Model Knows Your Project, Not You: Measuring Recognition in LLMs with NameRank},
  author={Li, Bojie and Shi, Noah},
  journal={arXiv preprint arXiv:2607.12520},
  year={2026},
  eprint={2607.12520},
  archivePrefix={arXiv},
  primaryClass={cs.AI},
  note={Code: https://github.com/19PINE-AI/namerank}
}
```

## License

Dual-licensed — see [`LICENSE`](LICENSE). Code: MIT. Data (probe specifications,
gold answers, recognition verdicts, analysis tables): CC BY 4.0.

## Status

Accompanying the arXiv preprint [arXiv:2607.12520](https://arxiv.org/abs/2607.12520).
The metric is intended for re-runs at each major
frontier-model release cycle; this repo is tagged at preprint freeze and re-tagged
for each subsequent NameRank revision.
