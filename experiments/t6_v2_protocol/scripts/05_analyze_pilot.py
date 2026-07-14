"""Pilot v2 validation gates.

Gate 1  Synthetic floors: every synthetic recipe family panel-mean < 0.10,
        except credential recipes where the medal-tier guess is partially
        creditable (report the measured guessing floor; require < 0.25).
Gate 2  Echo collapse: gemma-3-4b / phi-4 on real long-tail researchers
        score < 0.15 mean (v1: gemma median 0.80).
Gate 3  Recognition preserved: reference_pilot ordering vs v1 NameRank
        Spearman > 0.7; universally-known entities stay well above floor.
Gate 4  Judge health: <1% JUDGE-ERROR records; refusal detector unchanged.
Gate 5  Cohort sanity: per-cohort means finite, silent cohorts near zero.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent

recs = [json.loads(l) for l in open(HERE / "outputs" / "pilot_v2_results.jsonl")]
df = pd.DataFrame(recs)
ents = {e["id"]: e for e in json.loads(
    (HERE / "inputs" / "pilot_entities_v2.json").read_text())}
df["cohort"] = df.entity_id.map(lambda i: ents[i]["cohort"])
df["synthetic"] = df.entity_id.map(lambda i: bool(ents[i].get("synthetic")))

print(f"{len(df)} records, {df.entity_id.nunique()} entities, "
      f"{df.model_id.nunique()} models\n")

print("── Gate 1: synthetic floors (panel mean by recipe) ──")
syn = df[df.synthetic].groupby("cohort").agg(
    floor=("score", "mean"), ref=("is_refusal", "mean"), n=("score", "size"))
print(syn.round(3).to_string())
cred = {"synthetic_imo_gold_v2", "synthetic_noi_v2"}
g1 = all((v < 0.25 if c in cred else v < 0.10)
         for c, v in syn.floor.items())
print("GATE 1:", "PASS" if g1 else "FAIL", "\n")

print("── Gate 2: echo collapse on real long-tail researchers ──")
echo = df[(~df.synthetic)
          & df.cohort.isin(["long_tail_researcher_openalex", "cs_faculty"])
          & df.model_id.isin(["gemma-3-4b", "phi-4"])]
if len(echo):
    m = echo.groupby("model_id").score.mean()
    print(m.round(3).to_string())
    g2 = (m < 0.15).all()
else:
    g2 = None
print("GATE 2:", "PASS" if g2 else ("no data" if g2 is None else "FAIL"), "\n")

print("── Gate 3: reference-set ordering vs v1 ──")
v1 = pd.read_csv(REPO / "data/analysis/namerank_per_entity.csv").set_index("entity_id")
ref = df[(df.cohort == "reference_pilot")].groupby("entity_id").score.mean()
both = pd.DataFrame({"v2": ref}).join(v1[["namerank"]]).dropna()
if len(both) >= 5:
    rho = spearmanr(both.v2, both.namerank).statistic
    print(both.round(3).to_string(), f"\nSpearman rho = {rho:.3f}")
    g3 = rho > 0.7
else:
    g3 = None
print("GATE 3:", "PASS" if g3 else ("insufficient" if g3 is None else "FAIL"), "\n")

print("── Gate 4: judge health ──")
err = df.rationale.str.contains("JUDGE-ERROR", na=False).mean()
print(f"judge-error rate: {err:.4f}")
print("GATE 4:", "PASS" if err < 0.01 else "FAIL", "\n")

print("── Gate 5: per-cohort v2 means (real entities) ──")
real = df[~df.synthetic].groupby("cohort").agg(
    v2=("score", "mean"), p_ans=("is_refusal", lambda x: 1 - x.mean()),
    n_ent=("entity_id", "nunique"))
# v1 comparison at cohort level
v1coh = pd.read_csv(REPO / "data/analysis/cohort_summary.csv")
v1map = dict(zip(v1coh[v1coh.columns[0]], v1coh["mean_namerank"])) \
    if "mean_namerank" in v1coh.columns else {}
real["v1"] = [v1map.get(c, np.nan) for c in real.index]
print(real.round(3).to_string())
