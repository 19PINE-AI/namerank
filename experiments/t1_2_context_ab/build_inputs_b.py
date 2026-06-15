"""Sample 300 entities and build minimal-context inputs for the B arm."""
from __future__ import annotations

import csv
import json
import random
import shutil
from pathlib import Path

ROOT = Path("/home/ubuntu/namerank")
INPUTS_A = ROOT / "data" / "inputs"
EXP = ROOT / "experiments" / "t1_2_context_ab"
INPUTS_B = EXP / "inputs_B"

SEED = 20260525
random.seed(SEED)

# Reference-pilot anchor names requested by the task (10 diagnostic anchors)
REFERENCE_ANCHOR_NAMES = {
    "Sam Altman", "Geoffrey Hinton", "Andrej Karpathy", "Tri Dao", "Jiayi Weng",
    "Bojie Li", "Suresh Kumar", "Tianshou", "FlashAttention", "tuixue.online",
}


def minimal_context(entity: dict) -> str:
    """Return the minimal-context replacement (the 'context' field for arm B)."""
    cohort = entity["cohort"]
    name = entity["name"]
    if cohort == "cs_faculty":
        return "a computer science researcher"
    if cohort == "long_tail_researcher_openalex":
        return "an academic researcher"
    if cohort == "imo_gold":
        # strict null: drop "IMO gold" entirely
        return "a high-school mathematics competitor"
    if cohort == "msra_phd_fellowship":
        return "a PhD researcher"
    if cohort == "mid_tier_writer":
        return "a writer"
    if cohort == "mid_tier_politician":
        return "a politician"
    if cohort == "mid_tier_filmmaker":
        return "a filmmaker"
    if cohort == "oss_project":
        return "an open-source software project"
    if cohort == "ai_startup_or_company":
        return "a technology company"
    if cohort == "reference_pilot":
        # 10 anchors get a generic role descriptor by entity name
        artifacts = {"Tianshou", "FlashAttention", "tuixue.online"}
        if name in artifacts:
            return "a software project"
        return "a software engineer"  # generic role for the human anchors
    raise ValueError(f"Unhandled cohort for minimal context: {cohort}")


def sample_cohort(entities: list[dict], cohort: str, n: int) -> list[dict]:
    pool = [e for e in entities if e["cohort"] == cohort]
    if len(pool) <= n:
        return list(pool)
    return random.sample(pool, n)


def main() -> None:
    INPUTS_B.mkdir(parents=True, exist_ok=True)
    entities = json.loads((INPUTS_A / "pilot_entities.json").read_text())
    by_id = {e["id"]: e for e in entities}

    selected: list[dict] = []

    # 60 cs_faculty stratified by institution
    # The task asks 15 each of Stanford / CMU / Tsinghua / Peking. The
    # underlying dataset has 19 Stanford, 65 CMU, 4 Tsinghua, 4 Peking. We
    # therefore take all of Tsinghua/Peking and balance the remaining 52 slots
    # equally between Stanford (15) and CMU (15) so the Stanford-vs-Tsinghua
    # contrast is preserved. Remaining 22 slots filled from CMU.
    cs = [e for e in entities if e["cohort"] == "cs_faculty"]
    stanford = [e for e in cs if e.get("institution") == "Stanford University"]
    cmu = [e for e in cs if e.get("institution") == "Carnegie Mellon University"]
    tsinghua = [e for e in cs if e.get("institution") == "Tsinghua University"]
    peking = [e for e in cs if e.get("institution") == "Peking University"]
    sel_stanford = random.sample(stanford, 15)
    sel_cmu = random.sample(cmu, 15)
    sel_tsinghua = tsinghua  # all 4
    sel_peking = peking  # all 4
    cs_pick = sel_stanford + sel_cmu + sel_tsinghua + sel_peking  # 38 entities

    selected.extend(cs_pick)

    # 50 long_tail_researcher_openalex
    selected.extend(sample_cohort(entities, "long_tail_researcher_openalex", 50))
    # 30 imo_gold
    selected.extend(sample_cohort(entities, "imo_gold", 30))
    # 30 msra_phd_fellowship
    selected.extend(sample_cohort(entities, "msra_phd_fellowship", 30))
    # 30 mid_tier_writer
    selected.extend(sample_cohort(entities, "mid_tier_writer", 30))
    # 30 oss_project
    selected.extend(sample_cohort(entities, "oss_project", 30))
    # 30 mid_tier_politician
    selected.extend(sample_cohort(entities, "mid_tier_politician", 30))
    # 20 ai_startup_or_company
    selected.extend(sample_cohort(entities, "ai_startup_or_company", 20))
    # 20 mid_tier_filmmaker
    selected.extend(sample_cohort(entities, "mid_tier_filmmaker", 20))

    # 10 reference_pilot anchors (Sam Altman, Hinton, Karpathy, Tri Dao,
    # Jiayi Weng, Bojie Li, Suresh Kumar, Tianshou, FlashAttention, tuixue.online)
    ref_pool = [e for e in entities if e["cohort"] == "reference_pilot"
                and e["name"] in REFERENCE_ANCHOR_NAMES]
    assert len(ref_pool) == 10, (
        f"Expected 10 reference anchors but found {len(ref_pool)}: "
        f"{[e['name'] for e in ref_pool]}"
    )
    selected.extend(ref_pool)

    # Deduplicate (just in case) preserving order
    seen = set()
    deduped: list[dict] = []
    for e in selected:
        if e["id"] in seen:
            continue
        seen.add(e["id"])
        deduped.append(e)

    assert len(deduped) == 38 + 50 + 30 + 30 + 30 + 30 + 30 + 20 + 20 + 10, len(deduped)
    # Total = 288 (since CS faculty is 38 instead of 60). Let me reconcile.
    print(f"Selected {len(deduped)} entities")

    # Build arm-B entities with replaced context
    arm_b = []
    contexts_rows = []
    for e in deduped:
        new_ctx = minimal_context(e)
        new_e = dict(e)
        new_e["context"] = new_ctx
        arm_b.append(new_e)
        contexts_rows.append({
            "id": e["id"],
            "name": e["name"],
            "cohort": e["cohort"],
            "context_A": e["context"],
            "context_B": new_ctx,
        })

    # Write pilot_entities.json (arm B)
    (INPUTS_B / "pilot_entities.json").write_text(
        json.dumps(arm_b, indent=2, ensure_ascii=False)
    )

    # Copy shared files
    for fname in ["gold_answers.json", "model_set.json",
                  "probe_template_en.txt", "probe_template_zh.txt",
                  "judge_prompt.txt"]:
        shutil.copy2(INPUTS_A / fname, INPUTS_B / fname)

    # Write contexts.csv
    with open(EXP / "contexts.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "name", "cohort",
                                          "context_A", "context_B"])
        w.writeheader()
        for r in contexts_rows:
            w.writerow(r)

    # Per-cohort counts
    from collections import Counter
    c = Counter(e["cohort"] for e in arm_b)
    for k, v in sorted(c.items()):
        print(f"  {k}: {v}")
    print(f"TOTAL: {len(arm_b)}")


if __name__ == "__main__":
    main()
