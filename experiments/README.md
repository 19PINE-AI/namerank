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
| `t1_3_synthetic_null` | What does a never-seen name score? | Floor ~0.04 (dense), ~0.20 (short-gold); floor-adjusting widens the credential gap. → §6.7.7, App. M. |
| `t1_4_wikipedia` | Is NameRank just "has a Wikipedia page"? | No; Wikipedia explains 2–8% of variance. → §6.7.8, App. N. |
| `t2_6_prompt_sensitivity` | Robust to probe wording? | Ordering robust (r 0.93–0.98); levels wording-conditional. → §6.7.4, App. I. |
| `t2_7_artifact_mediation` | Is named-artifact amplification causal? | Yes; +0.058 mean lift, +0.288 (t=5.8) on Jiayi, via retrieval-deficient models. → §6.3.4. |
| `t2_8_gendered_names` | Gender bias? | Small reproducible man-coded lift (+0.038 / +0.027), within-cohort controlled. → §7.5, App. O. |
| `t2_9_fractional_citations` | Is h-index dominance attribution-density? | No — name-recurrence across works, not per-paper attribution. → §6.4.1, App. K. |
| `t2_10_cross_judge` | A Gemini-judge artifact? | No; r 0.87–0.93 across three judges, ladder preserved; in-family lift Gemini +0.06. → §6.7.6, App. L. |
| `t3_1_cutoff_gradient` | Is the silent zone corpus-timing? | No — intrinsic; matched DiD ≈ 0; ~0.13/yr vintage drift. → §6.7.5, App. J. |
| `t4_1_news_events` | *(extension cohort)* Does recognition track a directly recorded attention ledger? | Yes (R² 0.10/0.17 gold-adjusted) — via **peak**, not duration; templated series names −0.061. → §3.5 + App. "News-Event Cohort". |
| `t5_2_attention_baseline` | Is NameRank just Wikipedia pageviews / attention flow? | No — undefined for 71% of entities, R² 0.06 where defined; sign flips by cohort (celebrity +, technical −). → §3.1, App. confounds. |
| `t5_4_self_report` | Can a model report its own NameRank? | Partially (ρ 0.53–0.61 vs panel) — self-report reads corpus prevalence, not the model's own knowledge; fictional traps ~never claimed. → §3.7 + App. "Self-Reported Recognition". |

All ten audits are written into the paper (Sections 6.3.4, 6.4.1,
6.7.4–6.7.8, and 7.5; Appendices I–O), as is the t4_1 news-events extension
(own Results subsection + appendix). The limitations summary is Appendix P.
Unlike the audits, t4_1 has its own probe run (258 events × 36 models: 28
surviving main-run models + 8 replacements — the representative July-2026
releases from IKP v2; survivor equivalence r=0.993, replacement-vs-survivor
event ranking r=0.905) and its own `inputs/`; see its README.

```bash
cd <experiment-dir> && python3 analyze.py
```
