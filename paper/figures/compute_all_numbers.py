"""Compute every number the paper cites, from the final data, and dump as a
flat key->value map (JSON + printed). Used to fill/verify the \\tbd placeholders.
Run after the uniform judging pass completes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
import numpy as np
import pandas as pd
import _data

V = {}


def cohort_means(dataset):
    t = _data.cohort_table(dataset, min_n=1).set_index("cohort")
    return {c: round(float(r.recognition), 3) for c, r in t.iterrows()}


main = cohort_means("main")
for k, c in [("baseline", "long_tail_researcher_openalex"), ("faculty", "cs_faculty"),
             ("imo", "imo_gold"), ("ioi", "ioi_gold"), ("noi", "noi_china_gold"),
             ("cmo", "cmo_china_gold"), ("cpho", "cpho_china_first_prize"),
             ("rhodes", "rhodes_scholar"), ("putnam", "putnam_fellow"),
             ("msra", "msra_phd_fellowship"), ("icpc", "icpc_world_finals_gold"),
             ("methods", "named_method"), ("oss", "oss_project"),
             ("gpt5", "gpt5_system_card_author"), ("deepseek", "deepseek_v3_author"),
             ("foundation_model", "foundation_model"), ("ai_company", "ai_startup_or_company")]:
    if c in main:
        V[f"main.{k}"] = main[c]

for dataset, keys in [("llm", {"llm_method": "llm_method_originator",
                               "llm_bestpaper": "llm_best_paper_author",
                               "llm_foundational": "llm_foundational_author"}),
                      ("awards", {"nobel": "nobel_physics", "turing": "turing_award",
                                  "fields": "fields_medal", "acmprize": "acm_prize_computing",
                                  "godel": "godel_prize", "acmfellow": "acm_fellow",
                                  "macarthur": "macarthur_fellow", "sloan": "sloan_fellow"}),
                      ("univ", {"fac_mit": "univ_fac_mit", "fac_berkeley": "univ_fac_uc_berkeley",
                                "fac_ucsd": "univ_fac_ucsd", "fac_irvine": "univ_fac_uc_irvine",
                                "win_mit": "univ_mit", "win_berkeley": "univ_uc_berkeley",
                                "win_ucsd": "univ_ucsd", "win_irvine": "univ_uc_irvine"})]:
    cm = cohort_means(dataset)
    for k, c in keys.items():
        if c in cm:
            V[f"{dataset}.{k}"] = cm[c]

# floors
fl = _data.floors("main")
V["floor.people"] = round(fl["_people"], 3)
V["floor.papers"] = round(fl["_papers"], 3)

# extra main cohorts cited in the body
for k, c in [("proglang", "programming_language"), ("benchmark", "benchmark"),
             ("dataset", "dataset"), ("oss", "oss_project"),
             ("named_method", "named_method")]:
    if c in main:
        V[f"main.{k}"] = main[c]

# named individual entities (atlas + inversion prose)
pe = _data.per_entity("main")
byname = {r["name"]: round(float(r.recognition), 3) for _, r in pe.iterrows()}
byid = {r.entity_id: round(float(r.recognition), 3) for _, r in pe.iterrows()}
for label, nm in [("lecun", "Yann LeCun"), ("hinton", "Geoffrey Hinton"),
                  ("jiayi_weng", "Jiayi Weng"), ("tianshou", "Tianshou"),
                  ("nanogpt", "nanoGPT"), ("karpathy", "Andrej Karpathy"),
                  ("tri_dao", "Tri Dao"), ("flashattention", "FlashAttention")]:
    if nm in byname:
        V[f"ent.{label}"] = byname[nm]
    elif label in byid:
        V[f"ent.{label}"] = byid[label]

# country breakdown (CS faculty institution -> country)
import importlib.util as _ilu
sys.path.insert(0, str(REPO / "code"))
_meta_inst = {e["id"]: e for e in json.loads(
    (REPO / "data/inputs/pilot_entities.json").read_text())}
_spec = _ilu.spec_from_file_location("ca", REPO / "code" / "country_affiliation.py")
try:
    ca = _ilu.module_from_spec(_spec)
    try:
        _spec.loader.exec_module(ca)
    except Exception:
        pass  # module main may fail on paths; only COUNTRY_KEYWORDS is needed
    def _country(eid):
        inst = (_meta_inst.get(eid, {}).get("institution") or "")
        for country, kws in ca.COUNTRY_KEYWORDS.items():
            if any(kw.lower() in inst.lower() for kw in kws):
                return country
        return None
    fac = pe[~pe.synthetic & (pe.cohort == "cs_faculty")].copy()
    fac["country"] = fac.entity_id.map(_country)
    fac = fac.dropna(subset=["country"])
    gc = fac.groupby("country").recognition
    means, sizes = gc.mean(), gc.size()
    for label, cty in [("usa", "USA"), ("china", "China"), ("india", "India")]:
        if cty in means.index:
            V[f"country.{label}"] = round(float(means[cty]), 3)
            V[f"country.{label}_n"] = int(sizes[cty])
except Exception as e:
    print("country skipped:", e)

# injection lift (causal A/B): arm B injects the creator's named artifact into
# the context, arm A is role-only. lift = recognized(B) - recognized(A), paired
# by (creator, model). Reported as the per-creator mean of the model-mean diff.
inj = _data.T6 / "outputs" / "injection_results.jsonl"
if inj.exists():
    import collections
    arms = collections.defaultdict(dict)  # (creator, model) -> {A,B}
    for line in open(inj):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        eid = r["entity_id"]  # inj_A_<name> / inj_B_<name>
        arm = eid.split("_")[1]
        creator = eid.split("_", 2)[2]
        arms[(creator, r["model_id"])][arm] = r["recognized"]
    per_creator = collections.defaultdict(list)
    for (creator, _m), d in arms.items():
        if "A" in d and "B" in d:
            per_creator[creator].append(d["B"] - d["A"])
    if per_creator:
        creator_means = [np.mean(v) for v in per_creator.values()]
        V["injection.mean_lift"] = round(float(np.mean(creator_means)), 3)
        V["injection.n_creators"] = len(per_creator)

# totals
V["total.entities_main"] = len(pe)

# h-index regression
meta = {e["id"]: e for e in json.loads((REPO / "data/inputs/pilot_entities.json").read_text())}
df = _data.per_entity("main")
df = df[~df.synthetic & (df.cohort == "long_tail_researcher_openalex")].copy()
df["h"] = df.entity_id.map(lambda i: meta.get(i, {}).get("h_index"))
df["c"] = df.entity_id.map(lambda i: meta.get(i, {}).get("cited_by_count"))
df = df.dropna(subset=["h", "c"])
X = np.column_stack([np.log10(df.h), np.log10(df.c.clip(lower=1))])
y = df.recognition.values
import numpy.linalg as la
def r2(Xm):
    Xa = np.column_stack([np.ones(len(y)), Xm])
    b, *_ = la.lstsq(Xa, y, rcond=None)
    return 1 - ((y - Xa @ b) ** 2).sum() / ((y - y.mean()) ** 2).sum()
V["hindex.r2_h"] = round(r2(X[:, [0]]), 3)
V["hindex.r2_cites"] = round(r2(X[:, [1]]), 3)
V["hindex.r2_joint"] = round(r2(X), 3)
V["hindex.n"] = len(df)

# variance decomposition — from the uniform final verdicts (main dataset)
ents = _data.entities("main")
final = _data.T6 / "outputs" / "recognition_final.jsonl"
src = final if final.exists() else (_data.T6 / "outputs" / "recognition_v3.jsonl")
rec = []
for line in open(src):
    try:
        r = json.loads(line)
    except json.JSONDecodeError:
        continue
    if r.get("dataset") not in (None, "main"):
        continue
    e = ents.get(r["entity_id"])
    if e and not e.get("synthetic") and e.get("gold_v2"):
        rec.append((r["entity_id"], r["model_id"], e.get("cohort"), r["recognized"]))
Vd = pd.DataFrame(rec, columns=["e", "m", "c", "y"])
tot = ((Vd.y - Vd.y.mean()) ** 2).sum()
for name, key in [("entity", "e"), ("cohort", "c"), ("model", "m")]:
    mu = Vd.groupby(key).y.transform("mean")
    V[f"var.{name}"] = round(float(((mu - Vd.y.mean()) ** 2).sum() / tot) * 100, 1)

# self-report: aggregate rho + per-model panel-fame vs own-behavior + inter-model
sr = REPO / "experiments/t5_4_self_report/outputs/bt_theta.csv"
if sr.exists():
    import csv as _csv
    from collections import defaultdict as _dd
    from scipy.stats import spearmanr as _sp
    theta = _dd(list)
    pm = _dd(lambda: {"theta": [], "panel": [], "own": []})
    ent_theta_by_model = _dd(dict)
    for r in _csv.DictReader(open(sr)):
        try:
            t = float(r["bt_theta"])
        except (ValueError, KeyError):
            continue
        theta[r["entity_id"]].append(t)
        pm[r["model_id"]]["theta"].append(t)
        pm[r["model_id"]]["panel"].append(float(r["panel_nr"]))
        pm[r["model_id"]]["own"].append(float(r["own_score"]))
        ent_theta_by_model[r["model_id"]][r["entity_id"]] = t
    pei = _data.per_entity("main").set_index("entity_id")
    et = {e: np.mean(v) for e, v in theta.items()}
    common = [e for e in et if e in pei.index and not pei.loc[e, "synthetic"]]
    if common:
        V["selfreport.rho_aggregate"] = round(float(_sp(
            [et[e] for e in common], [pei.loc[e, "recognition"] for e in common]).statistic), 2)
    panel_rhos = [_sp(pm[m]["theta"], pm[m]["panel"]).statistic for m in pm
                  if len(pm[m]["theta"]) > 3]
    own_rhos = [_sp(pm[m]["theta"], pm[m]["own"]).statistic for m in pm
                if len(pm[m]["theta"]) > 3]
    V["selfreport.rho_panel_fame"] = round(float(np.nanmean(panel_rhos)), 2)
    V["selfreport.rho_own_behavior"] = round(float(np.nanmean(own_rhos)), 2)
    # inter-model: mean pairwise spearman of per-entity theta across models
    models = [m for m in ent_theta_by_model if len(ent_theta_by_model[m]) > 10]
    inter = []
    for i in range(len(models)):
        for j in range(i + 1, len(models)):
            shared = set(ent_theta_by_model[models[i]]) & set(ent_theta_by_model[models[j]])
            if len(shared) > 10:
                s = list(shared)
                inter.append(_sp([ent_theta_by_model[models[i]][e] for e in s],
                                 [ent_theta_by_model[models[j]][e] for e in s]).statistic)
    if inter:
        V["selfreport.rho_inter_model"] = round(float(np.nanmean(inter)), 2)

print("data sources:", _data.source_report())
print(json.dumps(V, indent=2))
(HERE / "computed_numbers.json").write_text(json.dumps(V, indent=2))
print(f"\nwrote computed_numbers.json ({len(V)} values)")
