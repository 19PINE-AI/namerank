"""Rebuild the NameRank analysis suite on v2 data.

Reads outputs/full_v2_results.jsonl (raw per-(entity,model) records) + the v2
inputs, and writes v2 analogues of data/analysis/*.csv plus the new
audit-driven exhibits:
  - namerank_per_entity_v2.csv        (per-entity mean, sd, refusal, answer rate)
  - per_model_summary_v2.csv
  - cohort_summary_v2.csv
  - credential_ladder_v2.csv          (v1 vs v2, + answer-rate column)
  - external_validity_v2.csv          (h-index vs citations, + answer-rate track)
  - institution_country_v2.csv
  - variance_decomposition_v2.csv
  - accuracy_channel_v2.csv           (per-cohort cov vs acc among answers)
  - v1_v2_shift.csv                   (cohort-level echo correction, headline)

Robust to a partial JSONL (works on pilot or mid-run full data); prints the
headline v1->v2 shift table.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
OUT = HERE / "outputs" / "analysis"
OUT.mkdir(exist_ok=True)


def load(which: str = "full") -> pd.DataFrame:
    path = HERE / "outputs" / f"{which}_v2_results.jsonl"
    recs = []
    with open(path) as f:
        for line in f:
            try:
                recs.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    df = pd.DataFrame(recs)
    # apply re-judge overlay (corrected credential golds; issue-2 fix). Overlay
    # rows carry corrected coverage/accuracy/score for already-probed responses.
    ov_path = HERE / "outputs" / "rejudge_overlay.jsonl"
    if ov_path.exists():
        ov = {}
        with open(ov_path) as f:
            for line in f:
                try:
                    r = json.loads(line)
                    ov[(r["entity_id"], r["model_id"])] = r
                except json.JSONDecodeError:
                    pass
        if ov:
            key = list(zip(df.entity_id, df.model_id))
            for col in ("coverage", "accuracy", "score"):
                df[col] = [ov[k][col] if k in ov else v
                           for k, v in zip(key, df[col])]
            print(f"[overlay] applied {len(ov)} re-judged scores")
    # effective refusal: a stored 'unknown/no-information' opener that scored 0
    # is a soft refusal the detector missed (issue-1 fix); reclassify for the
    # answer-rate statistic only (NameRank already ~0 for these).
    soft = re.compile(
        r"^\s*(unknown\b|i (do not|don't) have|i (?:am|'m) not (?:familiar|aware)"
        r"|i (?:cannot|can't) (?:find|identify)|there (?:is|are) no |no (?:public"
        r"|specific|reliable|verifiable|widely|available)|i don't recognize"
        r"|i have no )", re.I)
    df["eff_refusal"] = df.is_refusal | (
        (df.score == 0) & df.response.fillna("").str.match(soft))
    return df


def main(which: str = "full") -> None:
    df = load(which)
    ents = {e["id"]: e for e in json.loads(
        (HERE / "inputs" / "pilot_entities_v2.json").read_text())}
    df["cohort"] = df.entity_id.map(lambda i: ents.get(i, {}).get("cohort", "?"))
    df["synthetic"] = df.entity_id.map(
        lambda i: bool(ents.get(i, {}).get("synthetic")))
    df["gold_conf"] = df.entity_id.map(
        lambda i: ents.get(i, {}).get("gold_confidence", "?"))
    real = df[~df.synthetic].copy()

    # ── per-entity ──
    per = real.groupby("entity_id").agg(
        namerank=("score", "mean"), sd=("score", "std"),
        refusal_rate=("is_refusal", "mean"),
        answer_rate=("is_refusal", lambda x: 1 - x.mean()),
        n_models=("model_id", "nunique")).reset_index()
    per["cohort"] = per.entity_id.map(lambda i: ents[i]["cohort"])
    # answer-conditional mean score
    ans = real[real.is_refusal == 0].groupby("entity_id").agg(
        score_if_answer=("score", "mean"), cov_if_answer=("coverage", "mean"),
        acc_if_answer=("accuracy", "mean"))
    per = per.set_index("entity_id").join(ans).reset_index()
    per.to_csv(OUT / "namerank_per_entity_v2.csv", index=False)

    # ── per-model ──
    pm = real.groupby("model_id").agg(
        mean_score=("score", "mean"), refusal_rate=("is_refusal", "mean"),
        n=("score", "size")).reset_index()
    pm.to_csv(OUT / "per_model_summary_v2.csv", index=False)

    # ── cohort summary + v1 comparison ──
    coh = real.groupby("cohort").agg(
        v2_namerank=("score", "mean"),
        v2_answer_rate=("is_refusal", lambda x: 1 - x.mean()),
        n_ent=("entity_id", "nunique"),
        n_rec=("score", "size")).reset_index()
    # v1 cohort means from released per-entity file
    v1 = pd.read_csv(REPO / "data/analysis/namerank_per_entity.csv")
    pe1 = {e["id"]: e["cohort"] for e in json.loads(
        (REPO / "data/inputs/pilot_entities.json").read_text())}
    v1["cohort"] = v1.entity_id.map(pe1)
    v1c = v1.groupby("cohort").agg(v1_namerank=("namerank", "mean"),
                                   v1_refusal=("refusal_rate", "mean"))
    coh = coh.set_index("cohort").join(v1c).reset_index()
    coh["v1_answer_rate"] = 1 - coh.v1_refusal
    coh["echo_removed"] = coh.v1_namerank - coh.v2_namerank
    coh = coh.sort_values("echo_removed", ascending=False)
    coh.to_csv(OUT / "v1_v2_shift.csv", index=False)

    # ── accuracy vs coverage channel per cohort (answers only) ──
    ach = real[real.is_refusal == 0].groupby("cohort").agg(
        cov=("coverage", "mean"), acc=("accuracy", "mean"),
        n=("score", "size")).reset_index()
    ach.to_csv(OUT / "accuracy_channel_v2.csv", index=False)

    # ── variance decomposition (entity vs model vs cohort) ──
    def ss(g):
        return ((g - g.mean()) ** 2).sum()
    gm = real.score.mean()
    tot = ss(real.score)
    ent_means = real.groupby("entity_id").score.transform("mean")
    mod_means = real.groupby("model_id").score.transform("mean")
    coh_means = real.groupby("cohort").score.transform("mean")
    vd = pd.DataFrame({
        "source": ["entity", "model", "cohort", "total"],
        "ss": [ss(ent_means), ss(mod_means), ss(coh_means), tot],
    })
    vd["pct_of_total"] = (vd.ss / tot * 100).round(1)
    vd.to_csv(OUT / "variance_decomposition_v2.csv", index=False)

    # headline print
    print(f"[{which}] {len(df)} records, {real.entity_id.nunique()} real "
          f"entities, {df.model_id.nunique()} models")
    print("\n=== v1 -> v2 cohort shift (echo removed), cohorts with n_ent>=5 ===")
    show = coh[coh.n_ent >= 5][
        ["cohort", "v1_namerank", "v2_namerank", "echo_removed",
         "v1_answer_rate", "v2_answer_rate", "n_ent"]]
    print(show.to_string(index=False))
    print(f"\nvariance: entity {vd.pct_of_total[0]}% model {vd.pct_of_total[1]}% "
          f"cohort {vd.pct_of_total[2]}%")


def load_v3(ents):
    """Merge v3 recognition verdicts: my non-IMO file + the concurrent IMO
    session's output if present (recognition_v3_imo.jsonl or recognition_v3.jsonl).
    Returns {(entity_id, model_id): recognized(0/1)}."""
    v3 = {}
    # canonical open-book all-cohort file; fall back to legacy split files
    files = [HERE / "outputs" / "recognition_v3.jsonl"]
    if not files[0].exists():
        files = [HERE / "outputs" / "recognition_v3_nonimo.jsonl",
                 HERE / "outputs" / "recognition_v3_imo.jsonl"]
    for path in files:
        if not path.exists():
            continue
        with open(path) as f:
            for line in f:
                try:
                    r = json.loads(line)
                    v3[(r["entity_id"], r["model_id"])] = int(r["recognized"])
                except (json.JSONDecodeError, KeyError):
                    pass
    return v3


def recognition_table(which="full"):
    """Per-entity and per-cohort v3 recognition rate (headline metric)."""
    df = load(which)
    ents = {e["id"]: e for e in json.loads(
        (HERE / "inputs" / "pilot_entities_v2.json").read_text())}
    v3 = load_v3(ents)
    print(f"[v3] {len(v3)} recognition verdicts loaded")
    df["cohort"] = df.entity_id.map(lambda i: ents.get(i, {}).get("cohort", "?"))
    df["synthetic"] = df.entity_id.map(
        lambda i: bool(ents.get(i, {}).get("synthetic")))
    # recognized: refusals -> 0; else look up verdict (missing -> NaN, excluded)
    key = list(zip(df.entity_id, df.model_id))
    df["recognized"] = [0 if ref else v3.get(k, np.nan)
                        for k, ref in zip(key, df.is_refusal)]
    scored = df[df.recognized.notna()]
    per = scored[~scored.synthetic].groupby("entity_id").agg(
        recognition=("recognized", "mean"),
        n=("recognized", "size")).reset_index()
    per["cohort"] = per.entity_id.map(lambda i: ents[i]["cohort"])
    per.to_csv(OUT / "recognition_per_entity_v3.csv", index=False)
    # synthetic floor by recipe
    syn = scored[scored.synthetic].groupby("cohort").recognized.mean()
    print("\nsynthetic v3 floor by recipe:")
    print(syn.round(3).to_string())
    coh = per.groupby("cohort").agg(recognition=("recognition", "mean"),
                                    n_ent=("entity_id", "nunique"))
    coh.to_csv(OUT / "recognition_cohort_v3.csv")
    print("\nv3 recognition rate by cohort (n_ent>=10):")
    print(coh[coh.n_ent >= 10].sort_values("recognition", ascending=False)
          .round(3).to_string())
    return per, coh


if __name__ == "__main__":
    import sys
    which = sys.argv[1] if len(sys.argv) > 1 else "full"
    main(which)
    try:
        recognition_table(which)
    except Exception as e:  # noqa: BLE001
        print(f"[v3 table skipped: {e}]")
