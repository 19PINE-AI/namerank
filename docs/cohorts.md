# Full Cohort Specification

All 54 cohorts (5,719 entities), sorted by mean NameRank. "Refusal" is the
fraction of the 37-model panel's responses that returned "unknown" or refusal
phrasing. Rows are keyed by the cohort identifiers used in the released
dataset (`data/inputs/pilot_entities.json`,
`data/analysis/namerank_per_entity.csv`); the paper refers to the same cohorts
by readable names (mapping in `paper/figures/_style.py`, `COHORT_NAMES`).

| Cohort | n | Mean NR | Refusal | Inclusion criteria |
|---|---:|---:|---:|---|
| mid_tier_gov_ai_policy | 42 | 0.803 | 6% | US/UK/EU AI-policy government working-level officials |
| mid_tier_filmmaker | 38 | 0.786 | 0% | Independent directors with multiple festival features |
| programming_language | 29 | 0.779 | 1% | Languages with >1M users (Python, Rust, Go, etc.) |
| mid_tier_artist | 45 | 0.774 | 0% | Contemporary visual artists with major museum representation |
| database_or_data_system | 30 | 0.773 | 0% | Open-source databases (Postgres, ClickHouse, etc.) |
| award | 15 | 0.772 | 1% | Major academic / industry awards (Turing, Nobel CS-relevant) |
| benchmark | 47 | 0.747 | 4% | ML benchmarks (MMLU, GPQA, HellaSwag, etc.) |
| ai_hardware | 20 | 0.730 | 3% | AI accelerator products (H100, TPU v5, etc.) |
| dataset | 45 | 0.725 | 3% | ML datasets (COCO, ImageNet, etc.) |
| mid_tier_musician | 64 | 0.692 | 1% | Working musicians with mid-tier commercial success |
| mid_tier_chef | 47 | 0.645 | 1% | Michelin-starred chefs not at the absolute top |
| ai_startup_or_company | 102 | 0.638 | 5% | AI startups Series B+ founded post-2018 |
| mid_tier_comedian | 46 | 0.632 | 2% | Comedians with Netflix specials but not headliners |
| research_paper | 298 | 0.625 | 3% | Highly-cited papers (>10K citations) |
| mid_tier_historical | 105 | 0.622 | 0% | Pre-1980 historical figures, less-canonical |
| conference | 30 | 0.610 | 0% | CS / ML conferences (NeurIPS, ICML, etc.) |
| icpc_world_finals_gold | 18 | 0.610 | 16% | ICPC World Finals gold-medal team members 2005–2015 |
| putnam_fellow | 35 | 0.608 | 12% | Putnam Mathematical Competition top-25 2005–2015 |
| mid_tier_medical | 44 | 0.603 | 3% | Mid-career physicians and medical researchers |
| mid_tier_product | 88 | 0.603 | 1% | Consumer products with mid-tier adoption |
| industry_product | 9 | 0.590 | 4% | Industry products (Cursor, ChatGPT product, etc.) |
| named_method | 73 | 0.557 | 1% | Named ML methods (Adam, BatchNorm, Transformer, etc.) |
| mid_tier_actor | 123 | 0.536 | 8% | Working actors with multiple credits |
| mid_tier_founder | 48 | 0.526 | 4% | Mid-tier startup founders |
| mid_tier_oss_maintainer | 51 | 0.525 | 5% | OSS project maintainers |
| mid_tier_writer | 194 | 0.519 | 10% | Working authors with multiple published books |
| oss_project | 184 | 0.519 | 3% | OSS projects with >10K GitHub stars |
| foundation_model | 107 | 0.518 | 10% | Released foundation models 2020–2026 |
| mid_tier_journalist | 84 | 0.512 | 2% | Working journalists at major outlets |
| mid_tier_religious | 30 | 0.486 | 1% | Notable religious leaders |
| mid_tier_athlete | 134 | 0.477 | 10% | Working professional athletes |
| **long_tail_researcher_openalex** | **771** | **0.464** | 24% | OpenAlex researchers 500–30,000 citations |
| reference_pilot | 37 | 0.452 | 15% | Hand-curated diagnostic reference set |
| website_or_service | 9 | 0.437 | 10% | Public-utility websites/services |
| mid_tier_online_course | 40 | 0.434 | 0% | Notable online courses (CS50, MIT 6.006, etc.) |
| mid_tier_podcast | 57 | 0.427 | 2% | Notable podcasts |
| **cs_faculty** | **698** | **0.417** | 22% | CS faculty from CS Rankings ≥1 paper |
| mid_tier_vc | 31 | 0.402 | 12% | Mid-tier VCs at top firms |
| **long_tail_paper** | **499** | **0.368** | 24% | Long-tail academic papers 50–500 citations |
| noi_china_gold | 29 | 0.368 | 37% | National Olympiad in Informatics China gold 2005–2015 |
| mid_tier_book | 130 | 0.363 | 3% | Notable books (literary + non-fiction) |
| **imo_gold** | **197** | **0.362** | 28% | IMO gold medalists 2005–2015 |
| mid_tier_politician | 103 | 0.356 | 1% | Mid-tier elected officials globally |
| msra_phd_fellowship | 237 | 0.343 | 29% | MSRA PhD Fellowship 2005–2024 |
| ioi_gold | 68 | 0.341 | 24% | IOI gold medalists 2005–2015 |
| rhodes_scholar | 36 | 0.315 | 27% | Rhodes Scholarship recipients 2016–2017 |
| cmo_china_gold | 131 | 0.302 | 38% | China Math Olympiad gold 2005–2012 |
| mid_tier_architect | 36 | 0.255 | 18% | Working architects without star status |
| cpho_china_first_prize | 50 | 0.182 | 53% | China Physics Olympiad first prize 2009 |
| deepseek_v3_author | 69 | 0.178 | 42% | DeepSeek-V3 paper author list |
| long_tail_researcher_ikp | 159 | 0.158 | 47% | Researcher subset from IKP §5.7 |
| mid_tier_activist | 2 | 0.111 | 15% | Working-level activists (n=2, placeholder; excluded from cohort-level claims) |
| mid_tier_yc_company | 25 | 0.101 | 57% | YC company sample from older batches (W19–S22) |
| gpt5_system_card_author | 80 | 0.042 | 58% | GPT-5 system card author list |
