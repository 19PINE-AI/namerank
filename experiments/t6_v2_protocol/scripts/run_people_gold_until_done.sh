#!/usr/bin/env bash
# Auto-resume wrapper for 02a_gold_openalex_people.py.
# The script is resumable (checkpoints every 100 entities). It exits:
#   0  -> completed the full run
#   3  -> OpenAlex daily quota exhausted; retry later (progress checkpointed)
#   other -> hard error; stop and surface it.
# This wrapper retries on exit 3 every RETRY_MIN minutes until completion,
# so the run finishes automatically once the shared daily quota resets.
set -u
SCRIPT="$(dirname "$0")/02a_gold_openalex_people.py"
LOG="$(dirname "$0")/../outputs/people_gold_run.log"
RETRY_MIN="${RETRY_MIN:-30}"
attempt=0
while true; do
  attempt=$((attempt + 1))
  echo "=== attempt $attempt @ $(date -u +%H:%M:%SZ) ===" | tee -a "$LOG"
  python3 "$SCRIPT" >>"$LOG" 2>&1
  code=$?
  if [ "$code" -eq 0 ]; then
    echo "COMPLETE (exit 0) after $attempt attempt(s)" | tee -a "$LOG"
    exit 0
  elif [ "$code" -eq 3 ]; then
    echo "quota exhausted (exit 3); sleeping ${RETRY_MIN}m" | tee -a "$LOG"
    sleep "$((RETRY_MIN * 60))"
  else
    echo "HARD ERROR (exit $code); stopping" | tee -a "$LOG"
    exit "$code"
  fi
done
