# NameRank robustness experiments

Post-hoc audits of the headline findings in the paper. Each subdirectory is
self-contained: an `analyze.py` (reading only released artifacts under
`../data/`), its derived CSV/JSON outputs, and a `README.md` stating the
headline and the reproduction command.

The large raw per-(entity, model) probe dumps (`pilot_results*.json`) are **not
committed** — they are regenerable via `code/run_probe.py`, and the derived
`pilot_summary*.csv` / summary files that the analyses actually consume are
kept.

| Dir | Question | Headline |
|---|---|---|
| `t1_1_gold_length` | Gold-length confound on the credential gap? | Treadmill ordering survives every length adjustment. → §6.7.8, App. N. |
| `t1_2_context_ab` | Does the disambiguating context leak the answer? | Drops levels but preserves the Stanford–Tsinghua gradient (~5%). → §6.7.8, App. N. |
| `t1_3_synthetic_null` | What does a never-seen name score? | Floor ~0.04 (dense), ~0.20 (short-gold); floor-adjusting widens the credential gap. → §6.7.7, Fig. 18, App. M. |
| `t1_4_wikipedia` | Is NameRank just "has a Wikipedia page"? | No; Wikipedia explains 2–8% of variance. → §6.7.8, App. N. |
| `t2_6_prompt_sensitivity` | Robust to probe wording? | Ordering robust (r 0.93–0.98); levels wording-conditional. → §6.7.4, Fig. 14, App. I. |
| `t2_7_artifact_mediation` | Is named-artifact amplification causal? | Yes; +0.058 mean lift, +0.288 (t=5.8) on Jiayi, via retrieval-deficient models. → §6.3.4. |
| `t2_8_gendered_names` | Gender bias? | Small reproducible man-coded lift (+0.038 / +0.027), within-cohort controlled. → §7.5, App. O. |
| `t2_9_fractional_citations` | Is h-index dominance attribution-density? | No — name-recurrence across works, not per-paper attribution. → §6.4.1, Fig. 7, App. K. |
| `t2_10_cross_judge` | A Gemini-judge artifact? | No; r 0.87–0.93 across three judges, ladder preserved; in-family lift Gemini +0.06. → §6.7.6, Fig. 17, App. L. |
| `t3_1_cutoff_gradient` | Is the silent zone corpus-timing? | No — intrinsic; matched DiD ≈ 0; ~0.13/yr vintage drift. → §6.7.5, Fig. 15, App. J. |

All ten experiments are written into the paper (Sections 6.3.4, 6.4.1,
6.7.4–6.7.8, and 7.5; Figures 7/14/15/17/18; Appendices I–O). The limitations
summary is Appendix P.

```bash
cd <experiment-dir> && python3 analyze.py
```
