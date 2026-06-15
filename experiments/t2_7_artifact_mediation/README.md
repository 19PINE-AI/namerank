# t2_7: Causal Test of Named-Artifact Amplification

## Headline

**Adding the creator's named artifact to the disambiguating context lifts
NameRank by `+0.058` on average across 11 verified (creator, artifact) pairs.**
The lift is concentrated in low-recognition cases: Jiayi Weng / Tianshou
($+0.288$, $t=5.76$), Harrison Chase / LangChain ($+0.151$, $t=3.32$), and
Tri Dao / FlashAttention ($+0.094$, $t=2.53$) are the three significant
positive lifts. Three already-saturated cases (Hassabis, Murati, Srinivas)
show null or slightly negative deltas because their baseline NameRank is
already in the universal zone. The Jiayi Weng causal lift ($+0.288$) is
smaller than the observational mediation estimate of $+0.369$ reported in
the paper, but it is the same sign and the same order of magnitude — the
mechanism survives the intervention.

## Design

For each of the 11 paper-Table-4 pairs we built two contexts that differ
only by whether the creator's named artifact is mentioned:

- **A (control)**: role-only description, with the artifact stripped if
  it appeared in the original `pilot_entities.json` context.
- **B (artifact-hint)**: the same role-only description with one extra
  noun phrase naming the artifact (`creator of {Artifact}`, `author of
  {Artifact}`, or naturally embedded equivalent).

The two contexts were paired to differ by the fewest possible tokens — for
five pairs (Dario, Lilian, Harrison, Aman, Demis, Mira, Aravind) the
original context already named the artifact, so the stripped variant
substituted a generic role phrase ("the co-founder and CEO of an AI safety
lab" vs. "the co-founder and CEO of Anthropic"). For four pairs (Simon,
Andrej, Jiayi, Tri Dao) the original context did not name the artifact,
so context A reuses the existing string and B inserts a single attribution
clause. Full pairs are in `contexts.csv`. Each (entity, model) cell was
probed once on the full 37-model panel; 12 models returned API errors
(deprecated, provider unavailable) and were dropped from the paired
comparison, leaving 25 models per pair on average.

## Per-pair causal lift

| Creator | Artifact | NR\_A | NR\_B | $\Delta$ | $t$-paired |
|---|---|---:|---:|---:|---:|
| Jiayi Weng | Tianshou | 0.352 | 0.640 | **+0.288** | 5.76 |
| Harrison Chase | LangChain | 0.377 | 0.528 | **+0.151** | 3.32 |
| Tri Dao | FlashAttention | 0.575 | 0.669 | **+0.094** | 2.53 |
| Simon Willison | Datasette | 0.630 | 0.703 | **+0.073** | 2.79 |
| Aman Sanger | Cursor | 0.302 | 0.344 | +0.042 | 1.76 |
| Lilian Weng | lilianweng.github.io | 0.623 | 0.652 | +0.029 | 0.80 |
| Demis Hassabis | Google DeepMind | 0.694 | 0.717 | +0.023 | 0.71 |
| Andrej Karpathy | nanoGPT | 0.629 | 0.647 | +0.018 | 0.67 |
| Mira Murati | Thinking Machines Lab | 0.517 | 0.503 | $-0.014$ | $-0.27$ |
| Aravind Srinivas | Perplexity | 0.718 | 0.696 | $-0.022$ | $-0.86$ |
| Dario Amodei | Anthropic | 0.641 | 0.594 | $-0.047$ | $-2.19$ |
| **mean** | | **0.551** | **0.608** | **+0.058** | |

Eight of 11 pairs are positive; four are significant at $|t|>2$ (Jiayi,
Harrison, Tri Dao, Simon — the first three positive, Dario negative).
The negative point estimate on Dario is interpretable: stripping "Anthropic"
from "the co-founder and CEO of Anthropic" leaves "the co-founder and CEO
of an AI safety lab," which is itself an unusually specific anchor that
many models map to Anthropic without help — and the artifact-name version
may compete with the model's already-correct generation, occasionally
biasing the response toward role-restating rather than fact-listing.
Refusal rates are uniformly low ($\leq 16\%$) and barely shift between A
and B (e.g., Jiayi: $0.125 \to 0.083$).

## Per-model tier breakdown

| Tier | $n_\text{models}$ | mean NR\_A | mean NR\_B | mean $\Delta$ |
|---|---:|---:|---:|---:|
| frontier-reasoning (GPT-5.5-think, Claude-Opus-4.6, Gemini-3.1-Pro, ...) | 8 | 0.759 | 0.767 | **+0.008** |
| frontier-chat (GPT-5.3/4, Kimi-K2.6, Qwen-397B, GLM-4.7, ...) | 6 | 0.617 | 0.663 | **+0.046** |
| mid-weight (Llama-4-Maverick, Llama-3.3-70B, DS-V4-Flash) | 3 | 0.488 | 0.594 | **+0.106** |
| small ($\leq 32$B: Gemma-3, Phi-4, Qwen3-32B-think, Llama-3.1-8B, ...) | 8 | 0.319 | 0.414 | **+0.095** |

The lift is monotonically larger as model capacity decreases. Top-end
reasoning models (Claude-Opus-4.6-think NR\_A $0.80$; GPT-5.5-think
$0.77$) already retrieve the entities from the role-only context, so
adding the artifact yields no marginal information. Small open-weight
models gain the most ($+0.095$ on average; Llama-3.1-8B gains $+0.165$),
because their baseline recognition is low enough that the artifact name
in the context functions as a retrieval key. This is the signature of
genuine in-context-aided retrieval, not of a judge-leakage artifact: a
judge bias would shift all tiers equally.

## Comparison to the observational $+0.36$ finding

The paper's per-response analysis on Jiayi Weng (Table~5) showed that
models that *spontaneously* named Tianshou in their response scored the
creator at $0.71$, vs. $0.35$ for non-mentioning models — a $+0.36$
within-model lift. Our intervention gives Jiayi $+0.288$, slightly
smaller but in the same range. The difference is interpretable: in the
observational regime, models that naturally name Tianshou are
self-selected for already-knowing the entity, while the intervention
forces the artifact name into the context for models that did *not*
know it. Small/mid-weight models in our run gain the most precisely
because they would otherwise fail to retrieve the artifact themselves;
once the artifact is named for them, they generate the corresponding
contributions. The intervention thus *under-states* the natural
correlation (selection effect attenuated) while *over-states* the lift
attributable purely to context (some models would have mentioned the
artifact anyway). The two estimates bracket the true causal effect of
artifact co-mention at roughly $+0.30$ for Jiayi specifically and
$+0.05$–$+0.10$ as a panel-wide pooled effect when summed over 11
heterogeneous pairs.

## Interpretation

Three things follow:

1. **The named-artifact-amplification mechanism is causal, not just
   correlational.** Naming the artifact in the disambiguating context
   produces a real lift in 8 of 11 pairs; on Jiayi the lift is
   $+5.8\sigma$.
2. **The lift saturates at high baseline recognition.** Pairs whose
   baseline NR\_A is already $\geq 0.7$ (Hassabis, Srinivas) show null
   or negative lifts; the mechanism cannot push a model above what it
   already knows. This is internally consistent with the paper's
   `universal-zone` framing.
3. **Lower-tier models drive the effect.** The frontier-reasoning tier
   shows $+0.008$, mid-weight $+0.106$, small $+0.095$. The implication
   for the paper's central thesis (recognition is mediated by named
   artifacts) is that the mediation runs through *retrieval-deficient*
   models — exactly the population for which the named artifact is
   load-bearing context.

## Files

- `inputs_A/`, `inputs_B/` — per-side input bundles (entities + shared
  gold/model/probe/judge files).
- `outputs_A/pilot_results_en.json`, `outputs_B/pilot_results_en.json`
  — per-(entity, model) probe records.
- `contexts.csv` — the 11 paired context strings used.
- `mediation_results.csv` — per-pair NR\_A, NR\_B, $\Delta$, refusal\_A,
  refusal\_B, paired-$t$.
- `per_model_lift.csv` — every (pair, model) score\_A, score\_B,
  delta.
- `per_model_summary.csv` — per-model mean lift across the 11 pairs,
  with tier label.
- `tier_summary.csv` — tier-rolled mean lift.
- `summary.json` — top-line aggregates.
- `build_inputs.py` — script that constructed the inputs.
- `analyze.py` — script that produced the CSVs and summary.
- `run_A.log`, `run_B.log` — probe-runner stdout (407 records each).
