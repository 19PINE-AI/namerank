"""Recompute main-run cohort means on the event run's 29-model sub-panel.

8 of the 37 main-run models are no longer routable (see 06_run_probe.py), so
the event cohort is scored by a 29-model panel. Any placement of event scores
against main-run cohorts must use main-run NameRank recomputed on the same 29
models. This script derives those baselines from the released per-record file
data/raw/pilot_summary_en.csv.gz and reports how little the sub-panel moves
the main-run numbers (per-entity correlation, cohort-mean shifts).

Output: outputs/subpanel_baseline.json
"""
from __future__ import annotations

import csv
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE / "scripts"))

DEAD_MODELS = {
    "ernie-4.5-300b-a47b", "mistral-large", "mistral-medium-3.1",
    "ministral-3b", "kimi-k2", "grok-4", "glm-4-32b", "llama-3.2-1b",
}


def main() -> None:
    ents = {e["id"]: e for e in json.loads(
        (REPO / "data/inputs/pilot_entities.json").read_text())}

    full: dict[str, list] = defaultdict(list)
    sub: dict[str, list] = defaultdict(list)
    with gzip.open(REPO / "data/raw/pilot_summary_en.csv.gz", "rt") as f:
        for row in csv.DictReader(f):
            s = float(row["score"])
            full[row["entity_id"]].append(s)
            if row["model_id"] not in DEAD_MODELS:
                sub[row["entity_id"]].append(s)

    per_full = {e: float(np.mean(v)) for e, v in full.items() if len(v) >= 30}
    per_sub = {e: float(np.mean(v)) for e, v in sub.items() if e in per_full}

    common = sorted(per_full)
    xf = np.array([per_full[e] for e in common])
    xs = np.array([per_sub[e] for e in common])
    r = float(np.corrcoef(xf, xs)[0, 1])
    mean_shift = float(np.mean(xs - xf))
    max_shift = float(np.max(np.abs(xs - xf)))
    print(f"n={len(common)} entities; per-entity corr full-vs-29 = {r:.5f}")
    print(f"mean shift = {mean_shift:+.4f}, max |shift| = {max_shift:.3f}")

    coh_full: dict[str, list] = defaultdict(list)
    coh_sub: dict[str, list] = defaultdict(list)
    for e in common:
        c = ents.get(e, {}).get("cohort")
        if c:
            coh_full[c].append(per_full[e])
            coh_sub[c].append(per_sub[e])
    cohorts = {c: {"n": len(v), "full": round(float(np.mean(v)), 3),
                   "sub29": round(float(np.mean(coh_sub[c])), 3)}
               for c, v in coh_full.items() if len(v) >= 10}
    for c in sorted(cohorts, key=lambda c: -cohorts[c]["sub29"])[:12]:
        d = cohorts[c]
        print(f"  {c:34s} n={d['n']:<5} full={d['full']:.3f} sub29={d['sub29']:.3f}")

    out = {"per_entity_corr": round(r, 5), "mean_shift": round(mean_shift, 4),
           "max_abs_shift": round(max_shift, 4), "cohorts": cohorts,
           "reference": {e: round(per_sub[e], 3) for e in (
               "nanogpt", "flashattention", "sam_altman", "tianshou",
               "geoffrey_hinton", "langchain", "vllm") if e in per_sub}}
    (HERE / "outputs/subpanel_baseline.json").write_text(json.dumps(out, indent=1))
    print("Wrote outputs/subpanel_baseline.json")


if __name__ == "__main__":
    main()
