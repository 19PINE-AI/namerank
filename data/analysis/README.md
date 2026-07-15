# `data/analysis/` — derived NameRank tables

Every file here reports the **recognition-verdict** metric over the **36-model**
panel — the single metric the paper uses. The aggregate tables are regenerated
from the record-level recognition run by
[`code/build_release_tables.py`](../../code/build_release_tables.py), which
cross-checks its output against the paper's own figure numbers
([`paper/figures/computed_numbers.json`](../../paper/figures/computed_numbers.json))
and refuses to write a table that drifts.

Record-level source of truth:
`experiments/t6_v2_protocol/outputs/recognition_final.jsonl`
(one binary `recognized` verdict per entity × model, from the open-book
anti-confabulation judge).

| File | Contents |
|---|---|
| `namerank_per_entity.csv` | Per-entity recognition score (`namerank`), panel size, refusal rate, embedding similarity. |
| `namerank_matrix.json` | Per-entity → per-model `recognized` (0/1) matrix, main run (4,730 × 36). |
| `per_model_summary.csv` | Per-model recognition and refusal rates; vendor and Western/Chinese class. |
| `cohort_summary.csv` | Per-cohort recognition distribution (mean/median/sd/percentiles, `frac_recognized`, refusal). |
| `credential_ladder.csv` | The credential-treadmill table (IMO/IOI/ICPC/Putnam/CMO/NOI/CPhO/Rhodes/MSRA/DeepSeek/GPT-5 authors). |
| `cs_faculty_by_country.csv` | CS-faculty recognition by institution country (the country gradient). |
| `cross_language_per_entity.csv` | EN vs ZH recognition on the 240-entity Chinese-prompt sub-run, with Western/Chinese model splits. |
| `attribution_pairs_v2.csv` | Creator vs artifact recognition for the verified inversion pairs. |
| `model_cutoffs.json` | Per-model knowledge-cutoff metadata (metric-independent). |

Cohort-level tables (`cohort_summary`, `credential_ladder`, `cs_faculty_by_country`)
report the paper's cohort-mean population: real (non-synthetic) entities with a
v2 gold answer, judged by the full panel — matching
`paper/figures/_data.cohort_table`. `namerank_per_entity.csv` lists every probed
entity without that filter.

To regenerate: `python3 code/build_release_tables.py`.
