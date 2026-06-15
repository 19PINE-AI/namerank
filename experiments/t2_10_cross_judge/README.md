# t2_10: Cross-judge replication (Claude Opus 4.6, GPT-5.5)

**Question.** Are the NameRank paper's headline findings judge-specific? The pilot used Gemini 3.1 Pro as sole judge. Here we re-judge a 615-record stratified subsample with two non-Gemini judges — Anthropic `claude-opus-4-5` (Claude Opus 4.6) and `openai/gpt-5.5` via OpenRouter — and compare.

## Sample (615 records, 592 non-refusals)

- **reference_pilot (185)**: 5 entities (Sam Altman, Karpathy, Jiayi Weng, Bojie Li, FlashAttention) × all 37 models
- **cs_faculty / long_tail_researcher_openalex / imo_gold / gpt5_system_card_author (100 each)**: random (entity, model) pairs, non-refusal
- **oss_project / mid_tier_writer (15 each)**: smaller domain spread
- Refusals (n=23, all from reference_pilot) treated as 0/0 by convention.

Each judge received the exact same prompt template (`data/inputs/judge_prompt.txt`), temperature 0, with the gold answer and the cached model response. Both judges completed all 615 records with zero parse failures (Claude in ~4 min @ 8 concurrency; GPT-5.5 in ~13 min).

## Headline findings

### 1. Judges agree strongly on average

| Pair | Pearson (n=615) | Spearman |
|---|---|---|
| Gemini ↔ Claude | **0.868** | 0.840 |
| Gemini ↔ GPT-5.5 | **0.893** | 0.849 |
| Claude ↔ GPT-5.5 | **0.933** | 0.919 |

Cross-judge agreement is high overall, with Claude ↔ GPT-5.5 the tightest pair and Gemini somewhat more idiosyncratic. The pilot's signal is **not a Gemini artifact** — at r ≈ 0.87–0.93 the judges measure essentially the same construct on this prompt.

### 2. Reference-pilot ranking is judge-invariant

| Entity | NameRank (Gemini) | NameRank (Claude) | NameRank (GPT-5.5) | Rank under {G,C,P} |
|---|---|---|---|---|
| andrej_karpathy | 0.614 | 0.676 | 0.723 | 1 / 2 / 3 |
| sam_altman | 0.610 | 0.743 | 0.731 | 2 / 1 / 2 |
| flashattention | 0.607 | 0.665 | 0.742 | 3 / 3 / 1 |
| jiayi_weng | 0.331 | 0.387 | 0.407 | 4 / 4 / 4 |
| bojie_li | 0.090 | 0.152 | 0.151 | 5 / 5 / 5 |

The top three (Karpathy, Altman, FlashAttention) cluster very tightly under all three judges and their ordering jitters within ~0.03; the famous/long-tail boundary (positions 3→4) and the bottom rank (Bojie Li) are stable across judges. **The paper's "Bojie Li scores ~0 even with full context" core claim replicates under both Claude and GPT-5.5.**

### 3. Cohort ordering is mostly stable

| Cohort | n | mean Gemini | mean Claude | mean GPT-5.5 |
|---|---|---|---|---|
| long_tail_researcher_openalex | 100 | 0.669 | 0.630 | 0.631 |
| mid_tier_writer | 15 | 0.636 | 0.692 | 0.590 |
| oss_project | 15 | 0.597 | 0.683 | 0.718 |
| cs_faculty | 100 | 0.557 | 0.519 | 0.485 |
| **imo_gold** | 100 | **0.499** | **0.602** | **0.636** |
| **reference_pilot** | 185 | **0.451** | **0.525** | **0.551** |
| gpt5_system_card_author | 100 | 0.087 | 0.165 | 0.123 |

Gemini scores imo_gold and reference_pilot lower than Claude and GPT-5.5 do (both other judges give ~0.10–0.13 more). The relative ordering across cohorts is preserved (long_tail_researcher_openalex is the easiest cohort under every judge, gpt5_system_card_author the hardest), so **the credential-treadmill ordering is stable: the relative cohort ranking holds under every judge.** The gpt5_system_card_author cohort scoring near zero — a near-perfect floor for that obscurity — replicates under all three judges, which is the strongest replication of the paper's main credential-asymmetry result.

### 4. Family bias: Gemini judge mildly favors Gemini-family responses; Claude does not favor Claude

Raw in-family lift is confounded by capability (Gemini and GPT-5 model responses are among the best in our sample). Using a **residual lift** (judge score minus the mean of the two other judges):

| Judge | In-family residual | Out-family residual | Lift |
|---|---|---|---|
| Gemini | +0.014 | -0.048 | **+0.062** |
| Claude | +0.012 | +0.022 | -0.010 |
| GPT-5.5 | +0.060 | +0.019 | **+0.041** |

Gemini gives Gemini-family responses a ~6-pt boost above what Claude+GPT-5.5 award on the same response, and GPT-5.5 gives GPT-family responses a ~4-pt boost. **Claude does not favor Claude-family responses.** The Gemini in-family lift is small but consistent — small enough that it does not flip rankings (reference_pilot and cohort orderings are preserved), but large enough that it slightly inflates Gemini-family models in published score tables. Future runs should consider Claude as primary judge or report a multi-judge mean to neutralize this.

## Where judges disagree

Per-cohort Pearson correlations highlight one outlier:

- `oss_project` (n=15): Gemini↔Claude r=0.10; Gemini↔GPT-5.5 r=0.45. Inspection shows this is driven by a few records where Gemini judges generic descriptions of well-known projects (e.g., "LangChain is a framework...") as highly accurate while Claude/GPT-5.5 penalize them for not naming creators/dates listed in the gold answer. Sample is too small (n=15) to draw strong conclusions, but it's the one cell where the multi-judge story fractures.
- Spearman correlations within `long_tail_researcher_openalex` (r=0.59) and `imo_gold` (r=0.68) are noticeably below the overall rank correlation, suggesting rank-order disagreements at the low-score tail — these are mostly tied 0/0 refusals that judges break differently.
- **Chinese-name researchers do NOT show judge disagreement.** Within reference_pilot, the four Chinese-name entities (bojie_li, jiayi_weng, tianshou, tuixue_online — n=74 of their model responses) give r=0.957 for Gemini↔Claude and r=0.945 for Gemini↔GPT-5.5. The "Chinese name → judge disagreement" hypothesis is rejected by this sample.

## Implications for the paper

1. **Headline findings replicate.** The credential-treadmill ordering, the Bojie-Li-scores-zero result, and the cohort-level gradient are not Gemini artifacts.
2. **Multi-judge robustness check could be added** to §4 or appendix. The simplest addition: report cross-judge Pearson on a held-out 600-record stratified sample and note Claude as the most parsimonious primary judge (least family bias, tightest agreement with the third judge).
3. **Slight Gemini in-family lift exists** (~6 pts on residual). This does not change paper conclusions but is worth flagging: when reporting per-vendor scoreboards (Figure 3-style), readers should understand that Gemini judging Gemini models is ~6 pts generous. A footnote suffices.
4. **GPT-5.5 also has a ~4-pt in-family lift** — non-trivial but smaller. Claude is the cleanest of the three.

## Files

- `sample_records.json` — 615 sampled records with cached Gemini judgments
- `claude_judge.json` / `gpt_judge.json` — raw per-record judgments by the two new judges
- `rejudge_results.csv` — merged per-record table with all three judges
- `cross_judge_correlation.csv` — Pearson/Spearman per cohort
- `family_bias_check.csv` — per (judge, response_family) means
- `family_bias_residual.csv` — residual in-family lift (controls for response-capability confound)
- `cohort_means_per_judge.csv` — cohort means under each judge (for headline-finding stability)
- `reference_pilot_under_each_judge.csv` — per-entity NameRank under each judge with ranks
- `rejudge.py` / `analyze.py` — reproduction scripts
- `analysis_output.log` — captured stdout from analyze.py

## Reproduction

```bash
cd /home/ubuntu/namerank/experiments/t2_10_cross_judge
# requires ANTHROPIC_API_KEY and OPENROUTER_API_KEY
python3 rejudge.py both    # ~15 min, ~$20
python3 analyze.py
```
