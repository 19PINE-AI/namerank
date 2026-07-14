"""Single data provider for all paper figures.

Every figure script loads recognition data through this module, so the whole
figure set refreshes mechanically by re-running the make_*.py scripts.

Source selection: prefers the uniform final judging pass
(experiments/t6_v2_protocol/outputs/recognition_final.jsonl, all datasets, one
judge rubric) for the datasets it has finished; falls back to the per-dataset
verdict files for anything the pass has not yet covered. `source_report()`
says which source each dataset came from — figure scripts print it so a stale
fallback is visible at build time.
"""
from __future__ import annotations

import json
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent.parent
T6 = REPO / "experiments" / "t6_v2_protocol"
FINAL = T6 / "outputs" / "recognition_final.jsonl"

# fallback per-dataset verdict files (pre-uniform-pass)
FALLBACK = {
    "main": T6 / "outputs" / "recognition_v3.jsonl",
    "llm": REPO / "experiments/t5_5_llm_area/outputs/llm_area_results.jsonl",
    "univ": REPO / "experiments/t5_4_university_baseline/outputs/univ_v3judge_results.jsonl",
    # events/awards have no recognition-metric fallback (cov*acc only) — they
    # appear only once the uniform pass reaches them.
}

# entity metadata per dataset
ENTITY_FILES = {
    "main": T6 / "inputs" / "pilot_entities_v2.json",
    "events": REPO / "experiments/t4_1_news_events/inputs/event_entities.json",
    "awards": REPO / "experiments/t5_1_award_ladder/inputs/award_entities.json",
    "llm": REPO / "experiments/t5_5_llm_area/inputs/probe_entities.json",
    "univ": REPO / "experiments/t5_4_university_baseline/inputs/univ_entities_v2.json",
}

# expected record counts per dataset in the final file (completeness gate)
EXPECTED_MIN = {"main": 165_000, "events": 9_000, "awards": 20_000,
                "llm": 8_700, "univ": 24_000}

_source_used: dict[str, str] = {}


@lru_cache(maxsize=1)
def _final_by_dataset():
    out = defaultdict(dict)
    if FINAL.exists():
        with open(FINAL) as f:
            for line in f:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                out[r["dataset"]][(r["entity_id"], r["model_id"])] = r["recognized"]
    return out


@lru_cache(maxsize=8)
def entities(dataset: str = "main") -> dict:
    return {e["id"]: e for e in json.loads(ENTITY_FILES[dataset].read_text())}


def _verdicts(dataset: str) -> dict:
    fin = _final_by_dataset().get(dataset, {})
    if len(fin) >= EXPECTED_MIN.get(dataset, 1):
        _source_used[dataset] = "final(uniform)"
        return fin
    fb = FALLBACK.get(dataset)
    if fb and fb.exists():
        _source_used[dataset] = f"FALLBACK({fb.name})"
        out = {}
        with open(fb) as f:
            for line in f:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "recognized" in r:
                    out[(r["entity_id"], r["model_id"])] = r["recognized"]
        return out
    _source_used[dataset] = "UNAVAILABLE"
    return {}


@lru_cache(maxsize=8)
def per_entity(dataset: str = "main") -> pd.DataFrame:
    """entity_id, name, cohort, synthetic, recognition, n_models"""
    ents = entities(dataset)
    v = _verdicts(dataset)
    agg = defaultdict(list)
    for (eid, _m), rec in v.items():
        agg[eid].append(rec)
    rows = []
    for eid, votes in agg.items():
        e = ents.get(eid)
        if not e:
            continue
        rows.append({"entity_id": eid, "name": e.get("name", eid),
                     "cohort": e.get("cohort", "?"),
                     "synthetic": bool(e.get("synthetic")),
                     "gold_v2": bool(e.get("gold_v2", True)),
                     "recognition": float(np.mean(votes)),
                     "n_models": len(votes)})
    return pd.DataFrame(rows)


def cohort_table(dataset: str = "main", min_n: int = 10,
                 full_panel_only: bool = True) -> pd.DataFrame:
    """cohort, recognition, ci95, n_ent — real entities with v2 golds."""
    df = per_entity(dataset)
    df = df[~df.synthetic & df.gold_v2]
    if full_panel_only:
        df = df[df.n_models >= 30]
    g = df.groupby("cohort").recognition
    out = pd.DataFrame({"recognition": g.mean(),
                        "ci95": 1.96 * g.std() / np.sqrt(g.size()),
                        "n_ent": g.size()}).reset_index()
    return out[out.n_ent >= min_n].sort_values("recognition")


def floors(dataset: str = "main") -> dict:
    """synthetic-null recognition floor per recipe family + convenience keys."""
    df = per_entity(dataset)
    syn = df[df.synthetic]
    per = syn.groupby("cohort").recognition.mean().to_dict()
    people = syn[~syn.cohort.str.contains("paper")].recognition
    papers = syn[syn.cohort.str.contains("paper")].recognition
    per["_people"] = float(people.mean()) if len(people) else 0.0
    per["_papers"] = float(papers.mean()) if len(papers) else 0.0
    return per


def source_report() -> str:
    return "; ".join(f"{k}:{v}" for k, v in sorted(_source_used.items())) or "none loaded"
