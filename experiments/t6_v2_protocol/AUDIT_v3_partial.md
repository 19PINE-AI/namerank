# v3 data audit (partial, ~80K/170K verdicts, 2026-07-13)

0 judge errors / 80K. Reference-set calibration is textbook (see below). One
real anomaly (judge confabulation on guessable-fiction) — measured, correctable.

## GOOD — reference-set entity ordering is exactly right
LeCun/Hinton/Altman/Hassabis/Madry = 1.000; Karpathy 0.96, Amodei 0.88,
Murati 0.87, Srinivas 0.85, LangChain 0.955; Suresh Kumar (Walmart CTO) 0.65;
Jiayi Weng 0.25, Alex Wei 0.12; tuixue.online 0.40 (boundary case, correctly
mid-low); truly-obscure (Adam Fry, Andrea Vallone, Aaditya Singh) = 0.000.

## GOOD — clean real-vs-floor discrimination on people/artifacts
cs_faculty 0.739 vs floor 0.005 · oss_project 0.819 vs 0.000 · msra 0.244 vs
0.000 · synthetic people/artifact floors 0.000–0.024.

## ANOMALY — judge confabulation raises the floor on guessable-fiction cohorts
Open-book judge CONFABULATES verification for plausible fictional names attached
to a real, well-documented event:
- synthetic_imo_gold_v2 floor = 0.106 (was 0.029 under closed-book). E.g. for
  fictional "Vesper Lindblom / IMO 2014 Sweden" the judge wrote "her 2012/2013
  IMO participation and EGMO medal history, verified by official competition
  records" — she does not exist. Also credits the guessable medal tier
  ("won gold, verified by gold answer") since context only says "participant".
- synthetic_paper_v2 floor = 0.134 (descriptive titles → guessable author/venue).
- Confined to these two families; synthetic researchers 0.016, founders/OSS/
  faculty/mid-tier 0.000 — no confabulation where the name isn't anchored to a
  real event/topic.

## Impact — NOT a blocking regression
- Real cohorts clear their floors: floor-adjusted IMO 0.154, NOI 0.076,
  MSRA 0.244, papers 0.152 — all positive, all far below the working-researcher
  baseline (~0.44). Credential treadmill HOLDS, sharper than v1.
- Real IMO recognition is ~75% genuine (cites school/career/handle/other-year
  facts, e.g. David Yang→MIT, Sanghun Song→'ainta', Gunby→Georgetown Day School).
- The synthetic-null floor MEASURES the confabulation and floor-adjustment
  corrects it — this is exactly what the nulls are for.
- Tradeoff vs closed-book: open-book raised the guessable-fiction floor
  (~0.03→0.11) but fixed the far larger real-entity false-negative problem
  (famous faculty 0.000→0.74). Net strongly positive.

## Planned action (post-completion, non-disruptive)
Do NOT interrupt the running judge. After it finishes:
1. Run a confabulation-tightened judge SENSITIVITY on credential + paper cohorts
   and their synthetic floors ("for obscure competition participants, do not
   credit individual details via own-knowledge — other-year/secondary-medal/
   exact-score facts are not reliably in memory; credit only gold-present facts").
   Report headline (floor-adjusted open-book) + sensitivity side by side.
2. Keep floor-adjustment as the headline correction regardless.

## Benign — partial-data coverage skew (will resolve)
Judge processes the JSONL in file order; researchers/faculty were appended in
pass 2 (end of file), so currently long_tail_researcher_openalex 0% judged,
cs_faculty 8%. Their cohort numbers here are NOT yet representative; wait for
full completion before trusting exact researcher/faculty rates.
