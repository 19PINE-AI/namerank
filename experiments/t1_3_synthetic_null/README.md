# T1.3 — Synthetic-null floor for NameRank

## Goal
Construct 30 entirely fictional entities, run them through the full NameRank
pipeline, and use the resulting distribution as a **floor** — the score a
"name that does not exist in any pretraining corpus" should receive. Any
nonzero NameRank measured on a real cohort that is also produced by these
synthetics is, by definition, context-prior leakage rather than corpus
recognition.

## Construction methodology

The 30 synthetic entities span the same archetypes the paper measures:

| Sub-cohort                    | n  | Example                              |
|-------------------------------|----|--------------------------------------|
| `synthetic_cs_faculty`        | 10 | "Yorel Heskenwald" at ETH Zurich     |
| `synthetic_founder`           |  6 | "Brendel Quanzhong" AI infra CEO     |
| `synthetic_imo_gold`          |  6 | "Aslan Shyngyssov" IMO 2014 KAZ      |
| `synthetic_oss_project`       |  4 | "Spindleflow" workflow library       |
| `synthetic_mid_tier_*`        |  4 | musician / chef / journalist / pod   |

**Name discipline.** Names were constructed to be plausible-sounding within
each cohort's ethnic-distribution profile but **deliberately ungoogleable**:
unusual surname / given-name pairings, sometimes blending elements from
different traditions, and always verified via web search to confirm that no
notable real person with that name turns up in the top results. Examples:
"Yorel Heskenwald", "Tarvik Olshanski", "Halvar Mendigutia", "Wenslin
Kraborsky", "Iskander Vrolijk". The IMO sub-cohort uses real-sounding
country-appropriate names from the 2014 vintage (the actual IMO 2014 gold
medalists are a different list), specifically to test whether the pipeline
catches the fact that the named people did not in fact appear.

**Context fields** mirror the real cohort exactly. The CS faculty contexts
say things like *"a computer science faculty member at ETH Zurich working on
programming language theory"* — verbatim format from `cs_faculty` in the
released `pilot_entities.json`. The IMO contexts use the canonical
*"a gold medalist at the International Mathematical Olympiad (IMO) 2014
representing X"* phrasing. OSS artifact contexts include a GitHub URL just
like the real `oss_project` cohort.

**Gold answers** are 100–200 word Wikipedia-style paragraphs (or, for the IMO
sub-cohort, the same short generic boilerplate the real cohort uses) that
describe what each entity *would* have done if real, consistent with the
disambiguating context. This is the standard the judge will compare model
responses against.

## Run

```
python code/run_probe.py \
  --inputs-dir experiments/t1_3_synthetic_null/inputs \
  --outputs-dir experiments/t1_3_synthetic_null/outputs \
  --parallel 24
```

30 entities × 37-model panel = **1,110 probes** + 1,110 judge calls. Wall
time was a few minutes under load; per-record cost similar to the main
pipeline.

## Headline diagnostics

| Metric                                | Synthetic-null | Real `gpt5_system_card` baseline |
|---------------------------------------|---------------:|---------------------------------:|
| Mean record-level NameRank            | **0.072**      | (main run anchor ≈ 0.04)         |
| Mean per-entity NameRank              | **0.072**      | 0.042                            |
| Mean refusal rate                     | **38%**        | 58%                              |
| Fraction of entities with NameRank ≥ 0.10 | 6 / 30 (20%)  | n/a                              |
| Records with score ≥ 0.20 (flagged)   | 156 / 1110 (14%) | n/a                            |
| Records with score ≥ 0.50             | 69 / 1110      | n/a                              |
| Mean embedding similarity (BGE)       | 0.586          | n/a                              |

**Split by sub-cohort:**

| Sub-cohort                        | n  | mean NameRank | refusal |
|-----------------------------------|----|--------------:|--------:|
| `synthetic_imo_gold`              |  6 | **0.199**     | 21%     |
| `synthetic_mid_tier_chef`         |  1 | 0.123         | 27%     |
| `synthetic_mid_tier_journalist`   |  1 | 0.092         | 27%     |
| `synthetic_mid_tier_podcast`      |  1 | 0.075         | 32%     |
| `synthetic_oss_project`           |  4 | 0.065         | 39%     |
| `synthetic_mid_tier_musician`     |  1 | 0.057         | 41%     |
| `synthetic_cs_faculty`            | 10 | **0.027**     | 45%     |
| `synthetic_founder`               |  6 | **0.012**     | 47%     |

**Split by IMO vs. non-IMO:** the IMO sub-cohort drives most of the
context-leakage. Stripping it out, the remaining 24 synthetics have a mean
NameRank of **0.040** with a 42% refusal rate — almost identical to the
real `gpt5_system_card_author` baseline.

## What is going on?

The pipeline's NameRank is **not zero** on entities that demonstrably cannot
exist in the pretraining corpus. The mechanism, visible in
`flagged_responses.md`, is straightforward:

1. The probe gives the model the **disambiguating context** ("X, who is a
   gold medalist at IMO 2014 representing Kazakhstan").
2. Models do not robustly distinguish "I have a stored memory of this
   person" from "the prompt asserts this person did Y". They accept the
   context and produce a confident bio.
3. The judge gold-answer for short-context cohorts (e.g. IMO) is itself
   mostly a re-statement of the disambiguating context plus generic cohort
   boilerplate. So the model's regurgitation of the context scores **full
   coverage and full accuracy** even when no real entity exists.

The CS-faculty and founder cohorts, whose gold answers contain dense
*specific* facts (named PhD institutions, named venues, specific
contributions), give much smaller false-positive scores: mean 0.027 and
0.012 respectively. The judge correctly notices that the response did not
cover those specifics.

## Which models hallucinate confidently?

`per_model_breakdown.csv` shows a clean stratification:

| Model                       | Mean NameRank | Refusal | Frac ≥ 0.20 |
|-----------------------------|--------------:|--------:|------------:|
| gemma-3-4b                  | **0.293**     | 0%      | 63%         |
| gemma-3-12b                 | **0.287**     | 10%     | 70%         |
| llama-4-maverick            | **0.259**     | 0%      | 63%         |
| llama-3.3-70b               | 0.178         | 30%     | 40%         |
| gemma-4-31b                 | 0.147         | 67%     | 30%         |
| claude-opus-4.6-think       | 0.143         | 83%     | 17%         |
| phi-4                       | 0.141         | 0%      | 30%         |
| deepseek-v4-pro-think       | 0.140         | 73%     | 20%         |
| gpt-5.4                     | 0.113         | 83%     | 17%         |
| …                           | …             | …       | …           |
| **15 models score 0.000**   | 0.000         | 0–100%  | 0%          |

The 15 zero-scoring models — including gpt-5.3, grok-4, mistral-large,
qwen3-235b, ernie-4.5, gemini-3.1-pro, kimi-k2 — refuse or otherwise produce
no creditable content for every single synthetic. This is the **target
behaviour** under the null. Small open-weights models (gemma-3 family,
llama-4-maverick, llama-3.3-70b) and a subset of mid-tier reasoning models
fail it.

## Implications for the paper

1. **NameRank is not literally a corpus-recognition score.** A floor of
   ~0.04 on the non-IMO synthetic cohort, comparable to the
   `gpt5_system_card_author` headline number reported in the paper, means
   that low-end NameRank values are dominated by **context-prior leakage**,
   not stored knowledge. The paper's comparative claims (e.g. "GPT-5 system
   card authors recognised at NameRank X vs. DeepSeek-V3 authors at Y")
   should be interpreted relative to this floor, not relative to zero.
2. **Short generic gold answers inflate the floor.** The IMO sub-cohort's
   0.199 score is a methodological warning: cohorts whose gold answer is
   mostly cohort-boilerplate (year + country + medal + generic outcome
   sentence) admit a much larger context-leakage band than cohorts whose
   gold answers contain dense, specific named facts. The
   `cs_faculty`/`founder` cohorts are robust; the `imo_gold` /
   `putnam_fellow` style cohorts are sensitive.
3. **Per-model breakdown matters.** When comparing the per-model panel
   distribution across cohorts, small open-weights models contribute
   most of the floor. Conclusions that rely on agreement among **frontier
   reasoning models** (gpt-5.3, grok-4, claude-opus-4.6, gemini-3.1-pro,
   …) are largely unaffected: these models score 0 across the synthetic
   null.
4. **Recommended use of this experiment in the paper.** Cite the non-IMO
   floor of ~0.04 as the empirical noise level for NameRank, and the IMO
   floor of ~0.20 as the noise level for short-gold-answer cohorts.
   Differences observed in the main experiment that are smaller than this
   floor should not be treated as evidence of corpus recognition.

## Files

- `inputs/pilot_entities.json` — 30 synthetic entities
- `inputs/gold_answers.json` — matching 100–200 word gold paragraphs
- `inputs/probe_template_en.txt`, `inputs/judge_prompt.txt`,
  `inputs/model_set.json` — verbatim copies from the main pipeline
- `outputs/pilot_results_en.json` — 1,110 raw probe+judge records
- `pilot_summary_en.csv` — record-level CSV (copy of the file the runner
  writes under `data/raw/`; the canonical run was moved out of that
  directory so it does not pollute the main pipeline)
- `synthetic_namerank_per_entity.csv` — 30 rows, one per entity
- `per_model_breakdown.csv` — 37 rows, one per panel model
- `flagged_responses.md` — every record with score ≥ 0.20 (156 records),
  with judge rationale and full response text for human audit
- `analyze.py` — script that produces the three CSV / MD outputs
- `run.log` — runner stdout
