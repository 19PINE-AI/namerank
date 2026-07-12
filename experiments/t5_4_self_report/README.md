# t5_4 — Self-reported recognition: do models know their own NameRank?

**Question.** NameRank measures recognition *behaviorally*: a model's judged
coverage×accuracy against a gold answer. This experiment asks whether models
have *introspective access* to that quantity — and whether the expensive
verification pipeline could be replaced by simply asking a frontier model
which names it knows. Two stacked measurements:

1. **Binary self-knowledge** — can the model tell which of two entities it
   knows at all? (pairs straddling the model's own known/unknown boundary,
   plus fictional-entity traps from T1.3);
2. **Graded introspection** — among entities the model demonstrably knows,
   does its self-reported ordering reproduce the ordering of its own
   behavioral scores?

**Design.** 430 entities (400 real, stratified over six panel-NameRank bands
with a 12-per-cohort cap, from `data/inputs/pilot_entities.json` + released
scores; 30 fictional from T1.3). 3,350 unique pairs in five strata
(within-recognized close-gap 1,100 / within-recognized random 1,100 /
cross-boundary 500 / within-low 250 / traps 400) + 335 reversed-order
duplicates (position-bias probe) = 3,685 presentations per model. One shared
pair list, A/B order randomized once (seed 42).

Self-report models: `gpt-5.5-think`, `claude-opus-4.6-think`,
`gemini-3.1-pro` — the exact main-run checkpoints/settings (same OpenRouter
ids, same reasoning config), so each model's pairwise verdicts can be
compared against **its own** main-run per-entity behavioral scores
(`data/raw/pilot_summary_en.csv.gz`). Prompt
(`inputs/pairwise_prompt.txt`) asks which entity the model knows more about;
verdict ∈ {A, B, EQUAL, NEITHER}.

**Analysis** (`analyze.py`):
- own-label per entity per model: known = score ≥ 0.15 & no refusal;
  unknown = refusal or score < 0.05; mid excluded from binary analysis.
- binary: known-vs-unknown pairs → fraction picking the known side.
- traps: fictional vs model-known real → false-recognition = fictional wins
  or EQUAL.
- graded: both-known pairs → directional accuracy at own-score margins
  0.15/0.30; Davidson (1970) tie-extended Bradley–Terry fit on all decided
  real-real pairs (vectorized MLE, ridge-pinned gauge), Spearman of BT theta
  vs own behavioral score (primary; model-known entities, degree ≥ 5) and vs
  panel NameRank (secondary), 200-fold pair-bootstrap CIs.
- position bias: verdict-consistency on the reversed-duplicate subset.

**Caveat.** The behavioral ground truth is one judged response per
(entity, model), so response-level noise attenuates all graded correlations;
the margin-restricted directional accuracies are the cleaner statistic.

**Results** (all 11,055 calls returned parseable verdicts; full numbers in
`outputs/summary.json`, tables in paper §3.7 + App. "Self-Reported
Recognition"):

1. **Partial reconstruction** — BT self-ranking vs panel NameRank ρ =
   0.61/0.53/0.57 (GPT-5.5/Opus-4.6/Gemini-3.1-pro); directional accuracy
   0.81 on both-known pairs at panel gaps ≥ 0.15. A usable prior, not a
   substitute for verification.
2. **Self-report reads the corpus prior, not the model's own state** —
   ρ(BT, prevalence component) = 0.72–0.76 vs ρ(BT, conditional level) =
   0.11–0.19; ρ(BT, own score | known) = +0.04/−0.06/−0.09; the three
   vendors' self-rankings agree pairwise at ρ = 0.90–0.91, i.e. better with
   each other's introspection than with their own behavior. On
   fame-incongruent boundary pairs (model knows the obscure name, not the
   famous one) abstention jumps to 35–64% and only GPT-5.5 mostly sides
   with its own knowledge (0.65 vs 0.36/0.36; n = 26/14/69).
3. **Claims are precise; errors are under-claims** — fictional side
   preferred once in 684 fictional-vs-known trap pairs (0.1%, ties
   included); NEITHER on 95–100% of fictional–fictional pairs; boundary
   errors go to abstention (14–23%) more than to picking the unknown side
   (9–14%).
4. **No position artifact** — reversal consistency 0.85–0.90, first-position
   win rate 0.46–0.49.

Directional accuracy against *raw own-score* gaps is below chance
(0.34–0.40) — deliberately not a headline: raw per-model scores are
gold-conditional (own score tracks the panel's conditional level ρ =
0.60–0.71, a property of gold density, not fame), so they are not a valid
cross-entity depth scale. The prevalence/conditional decomposition above is
the correct form of the within-model question.

**Reproduce.**
```
python build_inputs.py      # inputs/entities.json, inputs/pairs.json
python run_pairwise.py      # outputs/pairwise_results.json  (OPENROUTER_API_KEY)
python analyze.py           # outputs/summary.json, outputs/bt_theta.csv
```
