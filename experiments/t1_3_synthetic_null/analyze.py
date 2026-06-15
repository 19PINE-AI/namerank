"""Analyze the synthetic-null probe results.

Reads:
  outputs/pilot_results_en.json
  inputs/pilot_entities.json

Writes (to the experiment root):
  synthetic_namerank_per_entity.csv
  per_model_breakdown.csv
  flagged_responses.md
"""
from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "outputs" / "pilot_results_en.json"
ENTITIES = ROOT / "inputs" / "pilot_entities.json"


def main() -> None:
    recs = json.loads(RESULTS.read_text())
    ents = {e["id"]: e for e in json.loads(ENTITIES.read_text())}

    # ----- per-entity NameRank -----
    per_ent_scores: dict[str, list[float]] = defaultdict(list)
    per_ent_refusals: dict[str, int] = defaultdict(int)
    per_ent_emb: dict[str, list[float]] = defaultdict(list)

    for r in recs:
        eid = r["entity_id"]
        per_ent_scores[eid].append(float(r.get("score") or 0.0))
        if r.get("is_refusal"):
            per_ent_refusals[eid] += 1
        es = r.get("embedding_sim")
        if es is not None:
            per_ent_emb[eid].append(float(es))

    rows = []
    for eid, scores in per_ent_scores.items():
        e = ents.get(eid, {})
        n = len(scores)
        mean = sum(scores) / n if n else 0.0
        sd = statistics.stdev(scores) if n > 1 else 0.0
        emb_mean = (sum(per_ent_emb[eid]) / len(per_ent_emb[eid])) if per_ent_emb[eid] else 0.0
        rows.append({
            "entity_id": eid,
            "entity_name": e.get("name", ""),
            "cohort": e.get("cohort", "?"),
            "n_models": n,
            "namerank": round(mean, 4),
            "namerank_sd": round(sd, 4),
            "refusal_rate": round(per_ent_refusals[eid] / n if n else 0.0, 3),
            "embedding_sim_mean": round(emb_mean, 4),
        })

    rows.sort(key=lambda r: -r["namerank"])
    out_csv = ROOT / "synthetic_namerank_per_entity.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} entities -> {out_csv}")

    # ----- per-model breakdown -----
    per_mod_scores: dict[str, list[float]] = defaultdict(list)
    per_mod_refusals: dict[str, int] = defaultdict(int)
    per_mod_n: dict[str, int] = defaultdict(int)
    per_mod_high: dict[str, int] = defaultdict(int)
    for r in recs:
        m = r["model_id"]
        s = float(r.get("score") or 0.0)
        per_mod_scores[m].append(s)
        per_mod_n[m] += 1
        if r.get("is_refusal"):
            per_mod_refusals[m] += 1
        if s >= 0.20:
            per_mod_high[m] += 1

    mod_rows = []
    for m, scores in per_mod_scores.items():
        n = len(scores)
        mod_rows.append({
            "model_id": m,
            "n": n,
            "mean_namerank": round(sum(scores) / n if n else 0.0, 4),
            "refusal_rate": round(per_mod_refusals[m] / n if n else 0.0, 3),
            "n_records_ge_020": per_mod_high[m],
            "fraction_ge_020": round(per_mod_high[m] / n if n else 0.0, 3),
        })
    mod_rows.sort(key=lambda r: -r["mean_namerank"])
    mod_csv = ROOT / "per_model_breakdown.csv"
    with open(mod_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(mod_rows[0].keys()))
        w.writeheader()
        w.writerows(mod_rows)
    print(f"Wrote {len(mod_rows)} models -> {mod_csv}")

    # ----- flagged responses (score >= 0.20) -----
    flagged = [r for r in recs if float(r.get("score") or 0.0) >= 0.20]
    flagged.sort(key=lambda r: -float(r.get("score") or 0.0))
    md = ROOT / "flagged_responses.md"
    with open(md, "w", encoding="utf-8") as f:
        f.write(f"# Flagged synthetic responses (NameRank >= 0.20)\n\n")
        f.write(f"Total flagged: {len(flagged)} of {len(recs)} records "
                f"({100*len(flagged)/len(recs):.2f}%).\n\n")
        if not flagged:
            f.write("(none — no record cleared the 0.20 audit threshold)\n")
        for r in flagged:
            f.write(f"## {r['entity_name']} ({r['entity_id']}) — model `{r['model_id']}`\n")
            f.write(f"- coverage={r['coverage']:.2f}, accuracy={r['accuracy']:.2f}, "
                    f"score={r['score']:.2f}, refusal={r['is_refusal']}, "
                    f"emb_sim={r['embedding_sim']:.3f}\n")
            f.write(f"- judge rationale: {r['rationale']}\n\n")
            f.write("**Response:**\n\n")
            f.write("```\n" + (r.get("response") or "") + "\n```\n\n")
    print(f"Wrote {len(flagged)} flagged records -> {md}")

    # ----- summary diagnostics -----
    all_scores = [float(r.get("score") or 0.0) for r in recs]
    all_refusals = sum(1 for r in recs if r.get("is_refusal"))
    n_records = len(recs)
    per_ent_mean = [r["namerank"] for r in rows]
    per_ent_refrate = [r["refusal_rate"] for r in rows]

    print()
    print("=== HEADLINE DIAGNOSTICS ===")
    print(f"Total records: {n_records:,}")
    print(f"Record-level mean NameRank: {sum(all_scores)/n_records:.4f}")
    print(f"Record-level refusal rate: {all_refusals/n_records:.3f}")
    print(f"Per-entity mean NameRank: {sum(per_ent_mean)/len(per_ent_mean):.4f}")
    print(f"Per-entity median NameRank: {statistics.median(per_ent_mean):.4f}")
    print(f"Per-entity mean refusal rate: {sum(per_ent_refrate)/len(per_ent_refrate):.3f}")
    print(f"# entities with NameRank >= 0.10: {sum(1 for v in per_ent_mean if v >= 0.10)} / {len(per_ent_mean)}")
    print(f"# entities with NameRank >= 0.05: {sum(1 for v in per_ent_mean if v >= 0.05)} / {len(per_ent_mean)}")
    print(f"# records with score >= 0.20: {sum(1 for s in all_scores if s >= 0.20)} / {n_records} "
          f"({100*sum(1 for s in all_scores if s >= 0.20)/n_records:.2f}%)")
    print(f"# records with score >= 0.50: {sum(1 for s in all_scores if s >= 0.50)} / {n_records}")
    print()
    print("=== Per-cohort means ===")
    cohort_scores: dict[str, list[float]] = defaultdict(list)
    cohort_refrate: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        cohort_scores[r["cohort"]].append(r["namerank"])
        cohort_refrate[r["cohort"]].append(r["refusal_rate"])
    for c in sorted(cohort_scores):
        ss = cohort_scores[c]
        rs = cohort_refrate[c]
        print(f"  {c:>34s}: n={len(ss):>2d}  nr={sum(ss)/len(ss):.4f}  ref={sum(rs)/len(rs):.3f}")


if __name__ == "__main__":
    main()
