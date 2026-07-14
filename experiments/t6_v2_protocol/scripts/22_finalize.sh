#!/usr/bin/env bash
# Autonomous finalization: waits for uniform judging pass + zh probe, then
# rebuilds analysis, regenerates all figures, and compiles the paper.
set -u
cd /home/ubuntu/namerank
D=experiments/t6_v2_protocol
LOG=$D/outputs/finalize.log
say(){ echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$LOG"; }

say "waiting for uniform judging pass (FINAL_JUDGE_DONE)"
while [ ! -f $D/outputs/FINAL_JUDGE_DONE ]; do sleep 120; done
say "uniform pass done: $(wc -l < $D/outputs/recognition_final.jsonl) verdicts"

say "waiting for zh probe"
while pgrep -f "20_probe_judge_generic.py --job zh" >/dev/null; do sleep 60; done
say "zh done: $(wc -l < $D/outputs/zh_results.jsonl 2>/dev/null || echo 0) records"

say "computing final numbers"
python3 paper/figures/compute_all_numbers.py > $D/outputs/final_numbers.log 2>&1
say "regenerating figures"
cd paper/figures
for f in make_fig1_atlas make_fig_calibration make_fig_axis_strip make_fig9_career_arc \
         make_fig_inversion make_fig_hindex make_fig_universities make_fig_country \
         make_fig_events; do
  python3 $f.py >> ../../$D/outputs/finalize.log 2>&1 && echo "  ok $f" | tee -a ../../$D/outputs/finalize.log
done
cd ../..
say "compiling paper"
cd paper && pdflatex -interaction=nonstopmode main.tex > /tmp/finalize_build.log 2>&1
grep -oE "Output written on main.pdf \([0-9]+ pages" /tmp/finalize_build.log | tee -a ../$D/outputs/finalize.log
cd ..
say "FINALIZE STAGE COMPLETE — numbers computed, figures regenerated, paper compiled. Manual \\tbd fill still required."
touch $D/outputs/FINALIZE_DONE
