"""Patch pass for golds written before the 02d fixes: strip wrong IMO edition
ordinals and un-thin official records. Idempotent."""
import json, re
from pathlib import Path
p = Path(__file__).resolve().parent.parent / "inputs" / "gold_v2_credentials.json"
g = json.loads(p.read_text())
n_ord = n_thin = 0
for k, v in g.items():
    new = re.sub(r"the \d+(?:st|nd|rd|th) International Mathematical Olympiad \((\d{4})\)",
                 r"the International Mathematical Olympiad \1", v["gold"])
    if new != v["gold"]:
        v["gold"] = new; n_ord += 1
    if v.get("official_record") and v.get("thin_gold"):
        v["thin_gold"] = False; n_thin += 1
p.write_text(json.dumps(g, ensure_ascii=False, indent=1))
print(f"patched ordinals={n_ord}, un-thinned={n_thin} of {len(g)}")
