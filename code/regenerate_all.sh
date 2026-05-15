#!/usr/bin/env bash
# Regenerate every released CSV from the record-level pilot_summary CSVs in data/raw/.
# Run from anywhere; the scripts resolve repo-relative paths through _paths.py.
set -euo pipefail

cd "$(dirname "$0")"

echo "==> build_namerank.py"
python3 build_namerank.py

echo "==> cohort_summary.py"
python3 cohort_summary.py

echo "==> credential_ladder.py"
python3 credential_ladder.py

echo "==> country_affiliation.py"
python3 country_affiliation.py

echo "==> east_west.py"
python3 east_west.py

echo "==> cross_language.py"
python3 cross_language.py

echo "==> external_validity.py"
python3 external_validity.py

echo "==> variance_decomposition.py"
python3 variance_decomposition.py

echo "==> refusal_patterns.py"
python3 refusal_patterns.py

echo "==> embedding_judge_gap.py"
python3 embedding_judge_gap.py

echo
echo "All analyses regenerated. CSVs in data/analysis/."
