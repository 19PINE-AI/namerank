"""Build the stratified 200-entity sample for the prompt-sensitivity probe.

Strata (seed=42, deterministic):
  30 gpt5_system_card_author   (silent zone)
  30 imo_gold                  (low-discriminative)
  30 long_tail_researcher_openalex (mid)
  30 cs_faculty                (mid, spans range)
  30 mid_tier_writer           (mid-high)
  30 oss_project               (high)
  20 from research_paper OR mid_tier_filmmaker (universal zone)
"""
from __future__ import annotations

import json
import random
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SRC = REPO / "data" / "inputs" / "pilot_entities.json"
GOLD = REPO / "data" / "inputs" / "gold_answers.json"
OUT_DIR = Path(__file__).resolve().parent / "inputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

STRATA = [
    ("gpt5_system_card_author", 30),
    ("imo_gold", 30),
    ("long_tail_researcher_openalex", 30),
    ("cs_faculty", 30),
    ("mid_tier_writer", 30),
    ("oss_project", 30),
]
UNIVERSAL = ("research_paper", "mid_tier_filmmaker", 20)


def main() -> None:
    entities = json.loads(SRC.read_text())
    gold = json.loads(GOLD.read_text())
    by_cohort: dict[str, list] = {}
    for e in entities:
        by_cohort.setdefault(e.get("cohort", "?"), []).append(e)

    rng = random.Random(42)
    picked = []
    for cohort, n in STRATA:
        pool = sorted(by_cohort[cohort], key=lambda x: x["id"])
        rng2 = random.Random(42)  # one rng per stratum
        sample = rng2.sample(pool, n)
        picked.extend(sample)
        print(f"  {cohort:35s} sampled {n} from pool of {len(pool)}")

    # Universal: 20 split across two cohorts (10+10), or all from the larger
    pool_a = sorted(by_cohort[UNIVERSAL[0]], key=lambda x: x["id"])
    pool_b = sorted(by_cohort[UNIVERSAL[1]], key=lambda x: x["id"])
    rng_a = random.Random(42)
    rng_b = random.Random(42)
    n_a = 10
    n_b = 20 - n_a
    sa = rng_a.sample(pool_a, n_a)
    sb = rng_b.sample(pool_b, n_b)
    picked.extend(sa + sb)
    print(f"  research_paper                      sampled {n_a} from pool of {len(pool_a)}")
    print(f"  mid_tier_filmmaker                  sampled {n_b} from pool of {len(pool_b)}")

    # Ensure unique ids
    ids = [e["id"] for e in picked]
    assert len(ids) == len(set(ids)), "duplicate ids in picked set"
    assert len(picked) == 200, f"expected 200, got {len(picked)}"

    # Make sure each has gold answer
    missing_gold = [e["id"] for e in picked if e["id"] not in gold]
    if missing_gold:
        print(f"WARNING: {len(missing_gold)} entities missing gold answers:")
        for mid in missing_gold[:5]:
            print(f"    {mid}")

    sub_gold = {e["id"]: gold[e["id"]] for e in picked if e["id"] in gold}

    (OUT_DIR / "pilot_entities.json").write_text(
        json.dumps(picked, indent=2, ensure_ascii=False)
    )
    (OUT_DIR / "gold_answers.json").write_text(
        json.dumps(sub_gold, indent=2, ensure_ascii=False)
    )
    print(f"Wrote {len(picked)} entities and {len(sub_gold)} gold answers")


if __name__ == "__main__":
    main()
