"""T5.4 input builder: stratified entity subsample + pairwise comparison list.

Selects 400 real entities stratified by panel NameRank band (cohort-capped)
plus all 30 T1.3 fictional entities, then generates one shared pair list used
verbatim by all three self-report models:

  within-R   : both panel NR >= 0.15 -- 1,100 close-gap (|dNR| < 0.15)
               + 1,100 random pairs (graded-introspection region)
  cross      : one NR >= 0.30, one NR < 0.05 -- 500 pairs (binary
               self-knowledge; also anchors the BT scale across clusters)
  within-L   : both NR < 0.15 -- 250 pairs (abstention behavior)
  trap       : fictional x real (12 partners each, spread over bands) = 360
               + 40 fictional-fictional pairs
  reversed   : 10% of unique pairs re-presented in swapped order
               (position-bias probe)

A/B presentation order is randomized once per pair (seed 42) and shared
across models so per-model differences are not confounded by ordering.
"""
from __future__ import annotations

import json
import random
from itertools import combinations
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
REPO = HERE.parent.parent
SEED = 42

MODELS = ["gpt-5.5-think", "claude-opus-4.6-think", "gemini-3.1-pro"]

BANDS = [(0.00, 0.05, 40), (0.05, 0.15, 40), (0.15, 0.30, 70),
         (0.30, 0.50, 90), (0.50, 0.70, 90), (0.70, 1.01, 70)]
COHORT_CAP = 12


def main() -> None:
    rng = random.Random(SEED)

    per_ent = pd.read_csv(REPO / "data/analysis/namerank_per_entity.csv")
    raw = pd.read_csv(REPO / "data/raw/pilot_summary_en.csv.gz")
    raw = raw[raw.model_id.isin(MODELS)]
    ents = {e["id"]: e for e in json.loads(
        (REPO / "data/inputs/pilot_entities.json").read_text())}
    fict = json.loads((REPO / "experiments/t1_3_synthetic_null/inputs/"
                       "pilot_entities.json").read_text())

    # per-model behavioral score/refusal lookup
    mscore = {(r.entity_id, r.model_id): (r.score, int(r.is_refusal))
              for r in raw.itertuples()}

    # ---- stratified real-entity sample ----
    nr = dict(zip(per_ent.entity_id, per_ent.namerank))
    sampled: list[dict] = []
    for lo, hi, quota in BANDS:
        pool = [eid for eid, v in nr.items()
                if lo <= v < hi and eid in ents]
        rng.shuffle(pool)
        counts: dict[str, int] = {}
        take = []
        for eid in pool:
            c = ents[eid]["cohort"]
            if counts.get(c, 0) >= COHORT_CAP:
                continue
            counts[c] = counts.get(c, 0) + 1
            take.append(eid)
            if len(take) == quota:
                break
        assert len(take) == quota, f"band {lo}-{hi}: only {len(take)}"
        for eid in take:
            e = ents[eid]
            rec = {"id": eid, "name": e["name"], "context": e["context"],
                   "cohort": e["cohort"], "kind": "real",
                   "panel_nr": round(nr[eid], 4)}
            for m in MODELS:
                s, rf = mscore[(eid, m)]
                rec[f"score__{m}"] = round(float(s), 3)
                rec[f"refusal__{m}"] = rf
            sampled.append(rec)

    for e in fict:
        sampled.append({"id": e["id"], "name": e["name"],
                        "context": e["context"], "cohort": e["cohort"],
                        "kind": "fictional", "panel_nr": None})

    by_id = {e["id"]: e for e in sampled}
    real = [e for e in sampled if e["kind"] == "real"]
    fic = [e for e in sampled if e["kind"] == "fictional"]
    R = [e["id"] for e in real if e["panel_nr"] >= 0.15]
    L = [e["id"] for e in real if e["panel_nr"] < 0.15]
    HI = [e["id"] for e in real if e["panel_nr"] >= 0.30]
    LO = [e["id"] for e in real if e["panel_nr"] < 0.05]

    pairs: list[dict] = []
    seen: set[frozenset] = set()

    def add(a: str, b: str, stratum: str) -> bool:
        key = frozenset((a, b))
        if a == b or key in seen:
            return False
        seen.add(key)
        if rng.random() < 0.5:
            a, b = b, a
        pairs.append({"pair_id": f"p{len(pairs):05d}", "a": a, "b": b,
                      "stratum": stratum, "rev_of": None})
        return True

    # within-R close-gap: enumerate candidates, sample
    close = [(x, y) for x, y in combinations(R, 2)
             if abs(by_id[x]["panel_nr"] - by_id[y]["panel_nr"]) < 0.15]
    rng.shuffle(close)
    n = 0
    for x, y in close:
        if add(x, y, "withinR_close"):
            n += 1
        if n == 1100:
            break

    n = 0
    while n < 1100:
        if add(rng.choice(R), rng.choice(R), "withinR_random"):
            n += 1

    n = 0
    while n < 500:
        if add(rng.choice(HI), rng.choice(LO), "cross_boundary"):
            n += 1

    n = 0
    while n < 250:
        if add(rng.choice(L), rng.choice(L), "withinL"):
            n += 1

    # traps: each fictional vs 12 real partners spread across bands
    for f in fic:
        partners = []
        for lo, hi, _ in BANDS:
            band = [e["id"] for e in real if lo <= e["panel_nr"] < hi]
            partners += rng.sample(band, 2)
        for p in partners:
            add(f["id"], p, "trap_real")
    n = 0
    while n < 40:
        if add(rng.choice(fic)["id"], rng.choice(fic)["id"], "trap_fict"):
            n += 1

    # reversed-duplicate position-bias probe: 10% of unique pairs
    rev_src = rng.sample(pairs, k=round(0.10 * len(pairs)))
    for p in rev_src:
        pairs.append({"pair_id": f"p{len(pairs):05d}", "a": p["b"],
                      "b": p["a"], "stratum": p["stratum"],
                      "rev_of": p["pair_id"]})

    (HERE / "inputs/entities.json").write_text(
        json.dumps(sampled, indent=1, ensure_ascii=False))
    (HERE / "inputs/pairs.json").write_text(
        json.dumps(pairs, indent=1, ensure_ascii=False))

    from collections import Counter
    print(f"{len(sampled)} entities ({len(real)} real + {len(fic)} fictional)")
    print(f"{len(pairs)} presentations/model; {len(pairs)*len(MODELS)} calls total")
    print(Counter(p["stratum"] for p in pairs))
    deg = Counter()
    for p in pairs:
        deg[p["a"]] += 1
        deg[p["b"]] += 1
    print("degree: min", min(deg.values()), "median",
          sorted(deg.values())[len(deg)//2], "max", max(deg.values()))


if __name__ == "__main__":
    main()
