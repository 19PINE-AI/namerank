# NameRank

**NameRank: Measuring LLM-Mediated Recognition as the Post-Bibliometric Impact Channel**

By Bojie Li, Pine AI.

A continuous cross-model recognition metric for people and named artifacts in the LLM era. NameRank operationalizes the 65% recognition-variance residual that bibliometrics cannot explain (Li 2026, IKP §5.7) into a $[0,1]$ score computed against a 37-model frontier panel. Five headline findings:

1. **The credential treadmill.** IMO gold, Rhodes, MSRA Fellowship sit *at or below* the long-tail-OpenAlex-researcher baseline.
2. **Artifact > creator inversion.** In 8 of 11 verified (creator, artifact) pairs, the artifact's NameRank exceeds the creator's.
3. **h-index ≫ raw citations.** log(h-index) explains R²=0.40 of NameRank variance; raw citations explain 0.14 with zero marginal value beyond h-index.
4. **Corpus-density gradient.** Stanford CS faculty mean NameRank 0.54 vs. Tsinghua 0.26. Country effects place Israel/Singapore/Sweden above the USA baseline.
5. **C6 falsification.** tuixue.online (∼1M Chinese-language users) registers NameRank 0.25, less than half of nanoGPT (0.71), with a flat cross-language null.

## Repository contents

- `paper/main.tex` — main paper (39 pages)
- `paper/appendix.tex` — appendices (worked examples, full cohort table, per-model statistics, limitations summary)
- `paper/references.bib` — bibliography
- `paper/figures/` — figure generation scripts and PDFs
- `paper/main.pdf` — compiled paper

## Reproducing the paper

```bash
cd paper
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

Figures are generated from analysis CSVs (in the data release):

```bash
python3 figures/make_fig1.py        # Cohort distribution
python3 figures/make_fig2_inversion.py  # Artifact > creator inversion
python3 figures/make_fig3_external.py   # h-index vs citations
python3 figures/make_fig4_credentials.py # Credential treadmill
python3 figures/make_fig5_country.py    # Country gradient
```

## Data release

The full probe set (5,719 entities), gold answers, and 211,603 raw response records (+ 8,880 Chinese-prompt records) will be released alongside the public preprint.

## Citation

```bibtex
@article{li2026namerank,
  title={NameRank: Measuring LLM-Mediated Recognition as the Post-Bibliometric Impact Channel},
  author={Li, Bojie},
  journal={arXiv preprint},
  year={2026}
}
```

## Status

Draft. Private repository. Public release accompanying arXiv submission.
