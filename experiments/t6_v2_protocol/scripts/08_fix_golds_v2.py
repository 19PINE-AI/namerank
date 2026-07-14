"""Post-audit gold fixes (2026-07-12), applied to the source gold files so
pass 2 and any re-judge use corrected golds. Does NOT touch the running JSONL.

Issue 2 — credential golds over-hard: raw competition score/rank ("42/42,
rank 1", "scoring 577 points, rank 1 nationally") are database facts that do
not propagate as prose, so they suppress the achievable ceiling and make
IMO/IOI/NOI/CMO/CPhO gold density incomparable to the Putnam/Rhodes/researcher
golds. Strip the numeric score/rank; KEEP medal/tier + year + country +
additional-participation-years + Wikipedia enrichment. This equalizes gold
density across the credential ladder.

Issue 3 — membership-minimal echo: for author-list contributors we could not
match to a real bio, the gold ("listed as a contributor on the DeepSeek-V3 /
GPT-5 report") merely restates the probe context, so capable models echo it
(gemini-3-flash 0.87, gemma-3-4b 0.21 — the v1 echo signature). Drop these
golds; the author cohorts are measured in v2 only on their real-bio-matched
members, plus a separate full-cohort refusal-rate silence statistic.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

# ── Issue 2: strip score/rank from credential golds ──
cg_path = HERE / "inputs" / "gold_v2_credentials.json"
cg = json.loads(cg_path.read_text())
patterns = [
    r",?\s*with a total score of \d+/\d+\s*\(rank \d+\)",   # IMO
    r",?\s*with rank \d+ and a score of \d+ points",         # IOI
    r",?\s*scoring \d+ points \(rank \d+ nationally\)",       # NOI roster
    r",?\s*scoring \d+(?:/\d+)?",                             # CMO/CPhO "scoring 126"
    r"\s*\(perfect score \d+/\d+\)",
    r",?\s*\(\d+(?:st|nd|rd|th) place nationwide[^)]*\)",
]
n2 = 0
for k, v in cg.items():
    g0 = v["gold"]
    g = g0
    for p in patterns:
        g = re.sub(p, "", g)
    g = re.sub(r"\s+([.,])", r"\1", g)
    g = re.sub(r"\s{2,}", " ", g).strip()
    # ensure the medal sentence still ends cleanly
    g = g.replace("gold medal .", "gold medal.").replace(" .", ".")
    if g != g0:
        v["gold"] = g
        n2 += 1
cg_path.write_text(json.dumps(cg, ensure_ascii=False, indent=1))
print(f"Issue 2: stripped score/rank from {n2} credential golds")
# show a sample
for k, v in cg.items():
    if k.startswith("imo_") and "gold medal" in v["gold"]:
        print("  e.g.", v["gold"][:150])
        break

# ── Issue 3: mark membership-minimal author golds for exclusion ──
# handled in the assembler (03c) via a drop-list written here
drop = {"reason": "membership-minimal gold restates context (echo); excluded "
        "from v2 headline, cohort measured by refusal-rate silence"}
(HERE / "inputs" / "_drop_membership_minimal.json").write_text(json.dumps(drop))
print("Issue 3: flagged membership-minimal for assembler exclusion")
