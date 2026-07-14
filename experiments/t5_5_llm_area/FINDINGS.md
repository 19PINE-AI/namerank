# LLM-area cohorts — findings (2026-07-13)

8,856 records, 0 judge errors, 36-model panel, open-book recognition judge.
Synthetic-null floor 0.009 (fictional ML researchers, works-list recipe) — all
rates below are real recognition.

## Recognition rate by cohort
| cohort | n | recognition |
|---|---|---|
| llm_method_originator | 84 | **0.654** ± 0.049 |
| llm_best_paper_author | 65 | **0.532** ± 0.073 |
| llm_foundational_author | 85 | **0.459** ± 0.061 |
| synthetic (floor) | 12 | 0.009 |

All three cohorts sit at/above the working-researcher baseline (0.410) — LLM-area
technical figures are recognized substantially more than the average
citation-tracked researcher, and far above olympiad credential holders
(IMO 0.238, etc.). Method originators lead: naming a widely-used method
propagates the creator's name.

Top method originators saturate (Sutskever, Hinton, Goodfellow, Schulman = 1.00);
bottom are recent/niche (Hao Liu/Ring Attention 0.00, Juho Lee/Set Transformer
0.00, Shih-Yang Liu/DoRA 0.11) — recognition tracks how widely the method
propagated, not recency alone.

## Method-vs-creator (nuanced — differs from the reference-set inversion)
On 53 method↔artifact pairs (fuzzy name match to main-run named_method/paper
artifacts; NOISY, treat as indicative): 26/53 (49%) the method out-ranks its
creator; mean creator 0.704 vs method 0.516. Unlike the reference-set
independent-creator inversion (Weng<Tianshou), method *originators* are
themselves well-known (cohort 0.654), so the artifact does NOT uniformly
out-rank them — the inversion holds for obscure independent creators, not for
the already-famous method originators. This is consistent with the paper's
stated exception (senior/famous creators out-rank their artifacts). Clean
inversion measurement needs the methods probed as artifacts in the same run
(future: add method-artifact entities to the main cohort).

## Paper use
A new "LLM-area figures" cohort group: three rows (method originator / best-paper
/ foundational author) placed on the recognition ladder between the
working-researcher baseline and the universal zone — modern technical
recognition. Data: outputs/llm_area_results.jsonl.
