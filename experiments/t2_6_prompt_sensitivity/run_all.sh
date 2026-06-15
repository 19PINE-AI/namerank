#!/bin/bash
set -e
cd /home/ubuntu/namerank/experiments/t2_6_prompt_sensitivity
echo "=== Starting T1 at $(date) ==="
python -u run_probe_template.py --inputs-dir inputs --outputs-dir outputs_T1 --template T1 --parallel 24 2>&1 | tee log_T1.txt
echo "=== Starting T2 at $(date) ==="
python -u run_probe_template.py --inputs-dir inputs --outputs-dir outputs_T2 --template T2 --parallel 24 2>&1 | tee log_T2.txt
echo "=== Starting T3 at $(date) ==="
python -u run_probe_template.py --inputs-dir inputs --outputs-dir outputs_T3 --template T3 --parallel 24 2>&1 | tee log_T3.txt
echo "=== All done at $(date) ==="
