# NOI 2009 medal tiers under the adopted tightened open-book judge (2026-07-13)

Re-judged the complete NOI 2009 roster (103 medalists) from retained responses
under the canonical tightened (anti-confabulation) open-book judge — the correct
judge for a competition cohort. Metric = panel recognition rate (fraction of 36
models recognizing the person; refusal = not recognized).

## Numbers (supersede the closed-book precursor in the appendix)
| tier | n | mean | median | silent (0 models) | recognized (≥1 model) |
|---|---|---|---|---|---|
| Gold | 20 | 0.104 | 0.056 | 2/20 | 18/20 |
| Silver | 34 | 0.026 | 0.028 | 16/34 | 18/34 |
| Bronze | 49 | 0.019 | 0.000 | 28/49 | 21/49 |

- **Synthetic-NOI floor = 0.000** (n=3, tightened judge) — the noise floor the
  appendix flagged as "not yet quoted." No confabulation floor for NOI under the
  tightened judge, so the gold mean 0.104 is entirely above-floor signal.
- Kruskal–Wallis H=25.9, p=2.4e-6. Gold vs silver Cliff's δ=+0.62.
  Silver vs bronze NOT distinguishable (Cliff +0.13, MWU p=0.27).
- Top recognized: Wu Jiajun 0.389 (Stanford CV prof), Mo Tao 0.333, Wu Yi 0.222,
  Fan Haoqiang 0.222 (top silver; Megvii), Li Bojie 0.222 (top bronze; this
  paper's author), Lin Yankai 0.194.

## What holds vs the closed-book version
- Gold/non-gold cliff SURVIVES (δ=+0.62, p=2e-6); silver/bronze still do not
  separate. Recognition still tracks post-medal career, not contest score.
- Floor is now a hard 0.000 (was "not quoted"): the gold tier is a clear
  above-floor signal; silver/bronze (0.026/0.019) sit just above zero.
- Distribution: gold 18/20 have SOME recognition but median only 0.056
  (~2 of 36 models) — the typical gold medalist is recognized by a handful of
  models, not widely; most of silver/bronze near the floor. "Most near-floor
  with a career-driven tail," consistent with the main-run NOI cohort.

Data: outputs/tier_openbook_summary.json, tier_openbook_per_entity.csv.
Regenerate fig_medal_tiers.pdf from tier_openbook_per_entity.csv.
