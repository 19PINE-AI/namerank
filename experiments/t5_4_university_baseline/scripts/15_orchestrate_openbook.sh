#!/usr/bin/env bash
# Drive the t5_4 open-book-judge takeover to completion, unattended.
#   1. wait for the univ_v2 probe to finish (25,272 records)
#   2. open-book judge all stored responses (13_judge_detect.py)
#   3. top-up probe + judge the 190 S2-unmatched entities (12_topup_probe_v3.py)
#   4. recompute the ladder (14_analyze_final.py)
# Parallelism kept modest (judge 6) — Gemini is shared with the t6 full pass.
set -u
cd /home/ubuntu/namerank/experiments/t5_4_university_baseline
LOG=outputs/orchestrate_openbook.log
say() { echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$LOG"; }

say "waiting for univ_v2 probe to finish"
while pgrep -f "06_run_probe_v2.py" >/dev/null; do sleep 30; done
say "probe done: $(wc -l < outputs/univ_v2_results.jsonl) records"

say "open-book judging stored responses (resumable)"
prev=-1
while true; do
  python3 -u scripts/13_judge_detect.py --parallel 6 >> outputs/judge_openbook.log 2>&1
  cur=$(wc -l < outputs/univ_v3judge_results.jsonl 2>/dev/null || echo 0)
  say "judged=$cur"
  [ "$cur" = "$prev" ] && break
  prev=$cur; sleep 10
done

say "top-up probe + judge the 190 S2-unmatched entities"
python3 -u scripts/12_topup_probe_v3.py --parallel 12 >> outputs/topup.log 2>&1
say "topup done: $(wc -l < outputs/univ_v3judge_topup.jsonl 2>/dev/null || echo 0) records"

say "recomputing ladder"
python3 -u scripts/14_analyze_final.py >> outputs/analyze_final.log 2>&1
say "T5_4 OPEN-BOOK COMPLETE"
touch outputs/T5_4_DONE
