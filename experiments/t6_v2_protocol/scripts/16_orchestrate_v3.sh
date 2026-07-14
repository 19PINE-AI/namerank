#!/usr/bin/env bash
# Orchestrate the canonical open-book v3 rollout across ALL cohorts.
# 1. wait for researcher/faculty gold enrichment
# 2. re-assemble v2 inputs (folds enriched golds into gold_answers_v2.json)
# 3. loop: run the all-cohort open-book v3 judge (resumable) until the probe
#    run is done AND every probed record has a verdict.
set -u
cd /home/ubuntu/namerank
D=experiments/t6_v2_protocol
LOG=$D/outputs/orchestrate_v3.log
say() { echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$LOG"; }

ENRICH_PID="${1:?need enrich pid}"
TARGET_RICH="${2:-1036}"   # expected final count of enriched golds

say "waiting for gold enrichment (pid $ENRICH_PID, target $TARGET_RICH)"
# Robust wait: enrichment process must be gone AND the rich-gold file complete.
while true; do
  alive=1; kill -0 "$ENRICH_PID" 2>/dev/null || alive=0
  cnt=$(python3 -c "import json;print(len(json.load(open('$D/inputs/gold_v2_researchers_s2_rich.json'))))" 2>/dev/null || echo 0)
  [ "$alive" = 0 ] && [ "$cnt" -ge "$TARGET_RICH" ] && break
  # also proceed if the process died and the count stopped growing (fetch failures)
  if [ "$alive" = 0 ]; then
    sleep 20
    cnt2=$(python3 -c "import json;print(len(json.load(open('$D/inputs/gold_v2_researchers_s2_rich.json'))))" 2>/dev/null || echo 0)
    [ "$cnt2" = "$cnt" ] && { say "enrichment process ended at $cnt (<$TARGET_RICH); proceeding"; break; }
  fi
  sleep 30
done
say "enrichment done: $(python3 -c "import json;print(len(json.load(open('$D/inputs/gold_v2_researchers_s2_rich.json'))))") rich researcher golds"

say "re-assembling v2 inputs with enriched golds"
python3 $D/scripts/03c_assemble_v2_inputs.py 2>&1 | tail -4 | tee -a "$LOG"

# loop the resumable v3 judge until it converges (probe run may still be adding
# records; each pass judges whatever new responses exist).
prev=-1
while true; do
  python3 -u $D/scripts/15_recognition_v3_all.py --parallel 8 >> $D/outputs/v3_all.log 2>&1
  cur=$(wc -l < $D/outputs/recognition_v3.jsonl)
  probed=$(wc -l < $D/outputs/full_v2_results.jsonl)
  say "v3 verdicts=$cur, probed records=$probed"
  # done when no probe run active and verdicts stopped growing
  if ! pgrep -f "04_run_probe_v2" >/dev/null && [ "$cur" = "$prev" ]; then
    say "V3 COMPLETE (probe run finished, verdicts converged)"
    touch $D/outputs/V3_DONE
    break
  fi
  prev=$cur
  sleep 120
done
