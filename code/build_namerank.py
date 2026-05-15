"""Compute per-entity NameRank from record-level probe results.

Reads:  data/raw/pilot_summary_en.csv(.gz)  — one row per (entity, model)
        data/inputs/pilot_entities.json     — entity metadata (cohort, name, ...)

Writes: data/analysis/namerank_per_entity.csv
        data/analysis/namerank_matrix.json  — {entity_id: {model_id: score}}

NameRank(e) = mean over the M=37 model panel of cov(e,m) * acc(e,m),
where the multiplication happens upstream when the judge assigns coverage and
accuracy scores; in the record-level CSV, this is already the `score` column.
"""
from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict

from _paths import ANALYSIS, INPUTS, open_text, raw_records_path


def main() -> None:
    ents = {e["id"]: e for e in json.loads((INPUTS / "pilot_entities.json").read_text())}

    per_ent_scores: dict[str, list[float]] = defaultdict(list)
    per_ent_model: dict[str, dict[str, float]] = defaultdict(dict)
    per_ent_refusals: dict[str, int] = defaultdict(int)
    per_ent_emb: dict[str, list[float]] = defaultdict(list)

    with open_text(raw_records_path("en")) as fh:
        for r in csv.DictReader(fh):
            eid = r["entity_id"]
            m = r["model_id"]
            score = float(r.get("score") or 0.0)
            per_ent_scores[eid].append(score)
            per_ent_model[eid][m] = score
            if r.get("is_refusal") in ("1", "true", "True"):
                per_ent_refusals[eid] += 1
            es = r.get("embedding_sim")
            if es not in (None, ""):
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

    ANALYSIS.mkdir(parents=True, exist_ok=True)
    out_csv = ANALYSIS / "namerank_per_entity.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} entities -> {out_csv}")

    out_matrix = ANALYSIS / "namerank_matrix.json"
    with open(out_matrix, "w", encoding="utf-8") as f:
        json.dump({eid: per_ent_model[eid] for eid in per_ent_model}, f)
    print(f"Wrote per-entity-per-model matrix -> {out_matrix}")


if __name__ == "__main__":
    main()
