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
| `t1_1_gold_length` | Gold-length confound on the credential gap? | Treadmill ordering survives every length adjustment. |
| `t1_2_context_ab` | Does the disambiguating context leak the answer? | Minimal-context ablation drops levels but preserves the Stanford–Tsinghua gradient. |
| `t1_3_synthetic_null` | What does a never-seen name score? | Noise floor ~0.04 (~0.20 for short-gold cohorts). |
| `t1_4_wikipedia` | Is NameRank just "has a Wikipedia page"? | No; Wikipedia explains 8% of variance. |
| `t2_6_prompt_sensitivity` | Robust to probe wording? | **Ordering robust (r 0.93–0.98); levels wording-conditional. → paper §6.7.4, App. I.** |
| `t2_7_artifact_mediation` | Is named-artifact amplification causal? | Yes; +0.058 mean lift, +5.8σ on Jiayi. |
| `t2_8_gendered_names` | Gender bias? | Small reproducible man-coded lift (+0.038 / +0.027). |
| `t2_9_fractional_citations` | Is h-index dominance attribution-density? | **No — name-recurrence across works, not per-paper attribution. → paper §5.5.1, App. K.** |
| `t2_10_cross_judge` | A Gemini-judge artifact? | **No; r 0.87–0.93 across three judges, ladder preserved; in-family lift Gemini +0.06. → paper §6.7.6, App. L.** |
| `t3_1_cutoff_gradient` | Is the silent zone corpus-timing? | **No — intrinsic; matched DiD ≈ 0; ~0.13/yr vintage drift. → paper §6.7.5, App. J.** |

The four bold-faced experiments are written into the paper (Sections 5.5.1 and
6.7.4–6.7.6, Figures 7/14/15/17, Appendices I–L); the rest inform the Discussion
and the Appendix M limitations table.

```bash
cd <experiment-dir> && python3 analyze.py
```
