# Full Cohort Specification

The main recognition run covers **4,685 real entities across 54 defined
cohorts** (plus 45 synthetic-null controls). This table lists the **53 cohorts
scored on the full 36-model panel with v2 gold answers** — the same population
the paper's cohort means are computed over (4,578 entities) — sorted by mean
NameRank. `n` is that gold-answer entity count per cohort, `Mean NR` its mean
recognition rate, and `Refusal` the fraction of panel responses returning
"unknown"/refusal. (`mid_tier_yc_company`, 25 entities, carries no v2 gold and
is not scored here.) Rows are keyed by the cohort identifiers used in the
released dataset (`data/inputs/pilot_entities.json`,
`data/analysis/cohort_summary.csv`); the paper refers to the same cohorts by
readable names (mapping in `paper/figures/_style.py`, `COHORT_NAMES`).

| Cohort | n | Mean NR | Refusal | Inclusion criteria |
|---|---:|---:|---:|---|
| mid_tier_online_course | 3 | 1.000 | 0% | Notable online courses (CS50, MIT 6.006, etc.) |
| ai_hardware | 6 | 0.986 | 1% | AI accelerator products (H100, TPU v5, etc.) |
| mid_tier_historical | 102 | 0.981 | 0% | Pre-1980 historical figures, less-canonical |
| mid_tier_artist | 45 | 0.976 | 0% | Contemporary visual artists with major museum representation |
| database_or_data_system | 26 | 0.976 | 2% | Open-source databases (Postgres, ClickHouse, etc.) |
| programming_language | 29 | 0.966 | 3% | Languages with >1M users (Python, Rust, Go, etc.) |
| conference | 24 | 0.957 | 1% | CS / ML conferences (NeurIPS, ICML, etc.) |
| dataset | 14 | 0.956 | 1% | ML datasets (COCO, ImageNet, etc.) |
| mid_tier_filmmaker | 38 | 0.950 | 0% | Independent directors with multiple festival features |
| website_or_service | 2 | 0.944 | 1% | Public-utility websites/services |
| mid_tier_politician | 103 | 0.938 | 1% | Mid-tier elected officials globally |
| mid_tier_musician | 64 | 0.934 | 0% | Working musicians with mid-tier commercial success |
| mid_tier_religious | 28 | 0.927 | 1% | Notable religious leaders |
| named_method | 60 | 0.919 | 1% | Named ML methods (Adam, BatchNorm, Transformer, etc.) |
| award | 13 | 0.917 | 1% | Major academic / industry awards (Turing, Nobel CS-relevant) |
| mid_tier_chef | 43 | 0.917 | 2% | Michelin-starred chefs not at the absolute top |
| mid_tier_podcast | 43 | 0.903 | 1% | Notable podcasts |
| industry_product | 6 | 0.898 | 5% | Industry products (Cursor, ChatGPT product, etc.) |
| mid_tier_medical | 35 | 0.891 | 2% | Mid-career physicians and medical researchers |
| mid_tier_founder | 29 | 0.890 | 3% | Mid-tier startup founders |
| mid_tier_journalist | 68 | 0.888 | 1% | Working journalists at major outlets |
| oss_project | 167 | 0.872 | 4% | OSS projects with >10K GitHub stars |
| mid_tier_book | 110 | 0.848 | 6% | Notable books (literary + non-fiction) |
| mid_tier_comedian | 45 | 0.839 | 2% | Comedians with Netflix specials but not headliners |
| mid_tier_oss_maintainer | 22 | 0.833 | 8% | OSS project maintainers |
| ai_startup_or_company | 59 | 0.825 | 6% | AI startups Series B+ founded post-2018 |
| mid_tier_activist | 2 | 0.819 | 13% | Working-level activists (n=2, placeholder; excluded from cohort-level claims) |
| mid_tier_gov_ai_policy | 25 | 0.804 | 5% | US/UK/EU AI-policy government working-level officials |
| mid_tier_vc | 9 | 0.781 | 3% | Mid-tier VCs at top firms |
| mid_tier_writer | 192 | 0.751 | 12% | Working authors with multiple published books |
| benchmark | 20 | 0.744 | 12% | ML benchmarks (MMLU, GPQA, HellaSwag, etc.) |
| mid_tier_actor | 123 | 0.734 | 11% | Working actors with multiple credits |
| foundation_model | 64 | 0.725 | 12% | Released foundation models 2020–2026 |
| mid_tier_athlete | 134 | 0.721 | 12% | Working professional athletes |
| mid_tier_product | 46 | 0.672 | 1% | Consumer products with mid-tier adoption |
| reference_pilot | 37 | 0.627 | 17% | Hand-curated diagnostic reference set |
| cs_faculty | 448 | 0.552 | 20% | CS faculty from CS Rankings ≥1 paper |
| mid_tier_architect | 36 | 0.542 | 24% | Working architects without star status |
| long_tail_researcher_openalex | 603 | 0.396 | 32% | OpenAlex researchers 500–30,000 citations |
| putnam_fellow | 35 | 0.343 | 39% | Putnam Mathematical Competition top-25 2005–2015 |
| icpc_world_finals_gold | 18 | 0.338 | 29% | ICPC World Finals gold-medal team members 2005–2015 |
| research_paper | 162 | 0.247 | 7% | Highly-cited papers (>10K citations) |
| long_tail_paper | 491 | 0.238 | 33% | Long-tail academic papers 50–500 citations |
| msra_phd_fellowship | 237 | 0.182 | 52% | MSRA PhD Fellowship 2005–2024 |
| ioi_gold | 68 | 0.154 | 39% | IOI gold medalists 2005–2015 |
| rhodes_scholar | 36 | 0.152 | 59% | Rhodes Scholarship recipients 2016–2017 |
| imo_gold | 197 | 0.120 | 40% | IMO gold medalists 2005–2015 |
| long_tail_researcher_ikp | 159 | 0.110 | 53% | Researcher subset from IKP §5.7 |
| deepseek_v3_author | 22 | 0.098 | 50% | DeepSeek-V3 paper author list |
| gpt5_system_card_author | 20 | 0.089 | 61% | GPT-5 system card author list |
| noi_china_gold | 29 | 0.086 | 59% | National Olympiad in Informatics China gold 2005–2015 |
| cmo_china_gold | 131 | 0.032 | 66% | China Math Olympiad gold 2005–2012 |
| cpho_china_first_prize | 50 | 0.028 | 68% | China Physics Olympiad first prize 2009 |
