#!/usr/bin/env bash
# Orchestrate the remaining v2 probing once the S2 gold builder and full-run
# pass 1 finish. Idempotent-ish: each probe run is resumable (JSONL skip).
set -u
cd /home/ubuntu/namerank
D=experiments/t6_v2_protocol
LOG=$D/outputs/orchestrate.log
say() { echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$LOG"; }

S2_PID="${1:?need S2 pid}"
PASS1_PID="${2:?need pass1 pid}"

say "waiting for S2 gold builder (pid $S2_PID)"
while kill -0 "$S2_PID" 2>/dev/null; do sleep 30; done
say "S2 done: $(python3 -c "import json;print(len(json.load(open('$D/inputs/gold_v2_researchers_s2.json'))),'researcher/faculty golds')")"

say "re-assembling v2 inputs (adds researcher/faculty golds)"
python3 $D/scripts/03c_assemble_v2_inputs.py 2>&1 | tail -6 | tee -a "$LOG"

say "waiting for full-run pass 1 (pid $PASS1_PID)"
while kill -0 "$PASS1_PID" 2>/dev/null; do sleep 60; done
say "pass 1 done: $(wc -l < $D/outputs/full_v2_results.jsonl) records"

say "launching full-run pass 2 (resumes; adds newly-golded entities)"
python3 -u $D/scripts/04_run_probe_v2.py --parallel 40 >> $D/outputs/full_run_pass2.log 2>&1
say "pass 2 done: $(wc -l < $D/outputs/full_v2_results.jsonl) records"

say "ALL PROBING COMPLETE"
touch $D/outputs/PROBING_DONE
