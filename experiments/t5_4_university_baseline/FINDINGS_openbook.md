# t5_4 findings under the open-book v3 recognition judge (2026-07-12)

32,112 verdicts, 0 judge errors. Headline = detection rate (fraction of the
36-model panel that recognizes the researcher); depth = cov*acc (appendix).

## Famous-name regression FIXED (validation gate — PASS)
Closed-book S2-gold judge scored these 0.000 ("known but not gold-matched");
open-book judge recovers them:
- Pieter Abbeel 1.000, Matei Zaharia 0.972, Patrick Winston 0.972,
  Russ Tedrake 0.917, Antonio Torralba 0.833.

## University ladder — FACULTY design (rankable; CSRankings, no bibliometric conditioning)
MIT 0.789 > UC Berkeley 0.733 > UCSD 0.640 > UC Irvine 0.621.
ANOVA p<1e-4; MIT>Berkeley p=0.025; MIT/Berkeley >> UCSD/Irvine p<1e-3.
100% grounded gold. **These are the rows for the paper's credential/institution
figure.**

## University ladder — WINDOWED design (citation-matched 500–30k; cannot rank, but informative)
MIT 0.554 ≈ Berkeley 0.550 > UCSD 0.430 ≈ Irvine 0.446. ANOVA p=0.001;
MIT|Berkeley p=0.92 (indistinguishable), both > UCSD/Irvine p=0.002–0.011.
**Sharp result: at MATCHED citations, top-school researchers are recognized
~25% more — pure institutional corpus-density, not productivity. Strengthens
the §3 institution-gradient thesis (v1's echo-contaminated score washed this
out; v1 windowed ANOVA was p=0.94).**

## Controls / credential treadmill under recognition
- long_tail_researcher_openalex baseline: 0.415
- imo_gold: 0.226 — well below the working-researcher baseline. Credential
  treadmill holds under the recognition metric.

## Robustness
- Grounded-only sensitivity: detection is slightly HIGHER on grounded-only
  golds (windowed MIT 0.592 vs 0.554), so the 52 ungrounded (zero-source) golds
  DEPRESS rather than inflate — finding is not a parametric-memory artifact.
- 0 judge errors / 32,112.

## Paper integration (deferred to unified v3 rewrite)
Faculty rows (MIT/Berkeley/UCSD/Irvine) → credential figure + institution table
+ §3.2, alongside the main t6 v3 institution gradient. Windowed rows are the
matched companion demonstrating the corpus-density-at-fixed-citations point.
Depth (cov*acc) → appendix diagnostic. Data: outputs/summary_final.json.
