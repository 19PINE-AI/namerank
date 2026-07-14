"""Repair pass for credential golds:
1. Empty golds (IMO/IOI table misses): retry with country-agnostic and
   token-subset name matching against refetched year tables; if still no hit,
   fall back to the v1 roster fact (medal + year + country), thin=True.
2. CMO/CPhO metadata golds with school AND score have >=3 beyond-context
   facts (prize tier, school, score): thin=False.
Idempotent.
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent

spec = importlib.util.spec_from_file_location(
    "c", HERE / "scripts" / "02d_gold_credentials.py")
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c) if False else None
# import helpers without running main
import sys
sys.path.insert(0, str(HERE / "scripts"))
import importlib
mod = importlib.import_module("02d_gold_credentials") if False else None

# reimplement the small helpers to avoid module-name issues
exec((HERE / "scripts" / "02d_gold_credentials.py").read_text()
     .split("def main()")[0])  # noqa: S102 — trusted local file

gp = HERE / "inputs" / "gold_v2_credentials.json"
g = json.loads(gp.read_text())
pe = {e["id"]: e for e in json.loads(
    (REPO / "data/inputs/pilot_entities.json").read_text())}

empty = [k for k, v in g.items() if len(v["gold"].split()) < 5]
print(f"{len(empty)} empty golds to repair")

years_needed_imo = sorted({pe[k]["credential_year"] for k in empty
                           if k.startswith("imo_") and pe[k].get("credential_year")})
years_needed_ioi = sorted({pe[k]["credential_year"] for k in empty
                           if k.startswith("ioi_") and pe[k].get("credential_year")})
imo = fetch_imo(years_needed_imo) if years_needed_imo else {}
ioi = fetch_ioi(years_needed_ioi) if years_needed_ioi else {}


def loose_match(latin, rows, name_of):
    """country-agnostic: exact key match, then token-multiset, then subset."""
    want = name_keys(latin)
    toks_want = sorted(norm(latin).split())
    cands = []
    for r in rows:
        full = name_of(r)
        if name_keys(full) & want:
            return r
        if sorted(norm(full).split()) == toks_want:
            cands.append(r)
    if len(cands) == 1:
        return cands[0]
    # subset: all tokens of one side contained in the other (handles middle
    # names like "Xiaolin Danny Shi" vs "Xiaolin Shi")
    subs = []
    for r in rows:
        a, b = set(norm(name_of(r)).split()), set(toks_want)
        if a and (a <= b or b <= a):
            subs.append(r)
    return subs[0] if len(subs) == 1 else None


n_fixed = n_fallback = 0
for k in empty:
    e = pe[k]
    latin = re.sub(r"\s*[（(][^)）]*[)）]", "", e["name"]).strip()
    year, country = e.get("credential_year"), e.get("credential_country") or ""
    hit = None
    if k.startswith("imo_") and year in imo:
        hit = loose_match(latin, imo[year],
                          lambda r: f"{r['name']} {r['surname']}")
        if hit:
            g[k]["gold"] = (
                f"{e['name']} represented {country} at the International "
                f"Mathematical Olympiad {year}, winning a gold medal with a "
                f"total score of {hit['total']}/42 (rank {hit['rank']}).")
    elif k.startswith("ioi_") and year in ioi:
        hit = loose_match(latin, ioi[year], lambda r: r["name"])
        if hit:
            g[k]["gold"] = (
                f"{e['name']} represented {country} at the International "
                f"Olympiad in Informatics {year}, winning a gold medal with "
                f"rank {hit['rank']} and a score of {hit['total']} points.")
    if hit:
        g[k].update(confidence="high", thin_gold=False, official_record=True)
        n_fixed += 1
    else:
        comp = ("International Mathematical Olympiad" if k.startswith("imo_")
                else "International Olympiad in Informatics")
        g[k]["gold"] = (f"{e['name']} won a gold medal at the {comp} "
                        f"{year}, representing {country}.")
        g[k].update(confidence="medium", thin_gold=True, official_record=False)
        n_fallback += 1

n_unthin = 0
for k, v in g.items():
    if (k.startswith("cmo_") or k.startswith("cpho_")) and v["thin_gold"]:
        if ("representing" in v["gold"] and
                re.search(r"scoring \d+", v["gold"])):
            v["thin_gold"] = False
            n_unthin += 1

gp.write_text(json.dumps(g, ensure_ascii=False, indent=1))
still_empty = [k for k, v in g.items() if len(v["gold"].split()) < 5]
thin = sum(1 for v in g.values() if v["thin_gold"])
print(f"repaired via loose match: {n_fixed}, metadata fallback: {n_fallback}, "
      f"cmo/cpho un-thinned: {n_unthin}")
print(f"still empty: {len(still_empty)}; thin now: {thin}/{len(g)}")
