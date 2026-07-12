"""Build probe inputs for the NOI gold/silver boundary RD.

t5_3 found a gold-vs-non-gold cliff on NOI 2009 and a suggestive jump at the
gold/silver cut (last-6 golds vs first-6 silvers). This experiment stacks
that boundary across years to power it: for each clean NOI year in OIerDb
(2010, 2011, 2012, 2013, 2015 -- 2005-2008 are absent from OIerDb, 2014's
medal line does not follow score order and is excluded), take the 6 lowest-
scoring golds and 6 highest-scoring silvers. People this close to the cut
were near-identical on contest day; a recognition gap at the cut is the
treatment effect of gold (roster documentation + national-training-team
status + elite-admission channel, bundled).

The 12-person 2009 boundary re-enters verbatim from t5_3 as a run-to-run
anchor (re-probed here; its t5_3 scores give the equivalence check).

Golds are year-neutral variants of the t5_3 tier boilerplates (gold counts
changed from ~20 to ~50 across 2011+, so the "top ~20" phrasing of the 2009
text would be wrong for later years); gold and silver texts are structure-
and length-matched, so the short-gold synthetic floor applies equally to
both sides of the cut. Romanization identical to t5_3.

Writes inputs/rd_entities.json and inputs/rd_gold.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
T53 = REPO / "experiments" / "t5_3_noi_medal_tiers"
sys.path.insert(0, str(T53 / "scripts"))
from importlib import import_module

build = import_module("01_build_inputs".replace(".py", "")) if False else None
# romanize() lives in t5_3's build script (module name starts with a digit,
# so import it via SourceFileLoader instead of the import system)
from importlib.machinery import SourceFileLoader
t53_build = SourceFileLoader("t53_build", str(T53 / "scripts" / "01_build_inputs.py")).load_module()
t53_build.PINYIN_FIX["曾"] = "zeng"        # surname reading (Ceng -> Zeng)
romanize = t53_build.romanize
# 曾進智: Hong Kong contestant (保良局百周年李兆忠紀念中學) — his used
# romanization is likely Cantonese (Tsang), not pinyin
UNCERTAIN = set(t53_build.UNCERTAIN) | {"曾進智"}

DATA_TXT = Path("/tmp/claude-1000/-home-ubuntu-namerank/41c553c2-8a40-4021-9031-37736d980b2b/scratchpad/oierdb_data.txt")
YEARS = [2010, 2011, 2012, 2013, 2015]
BANDWIDTH = 6

BOILER = {
    "gold": ("NOI gold medalists are the top-ranked high-school competitive "
             "programmers in China each year and enter the national training "
             "team, with most going on to elite Chinese universities (Tsinghua "
             "University, Peking University) for undergraduate computer "
             "science, often continuing to careers in technology research, AI, "
             "software engineering, or competitive programming infrastructure."),
    "silver": ("NOI silver medalists rank just below the gold tier nationally "
               "among Chinese high-school competitive programmers each year, "
               "with most going on to elite Chinese universities for "
               "undergraduate computer science, often continuing to careers in "
               "technology research, AI, software engineering, or competitive "
               "programming infrastructure."),
}
MEDAL_EN = {"金牌": "gold", "银牌": "silver"}


def main() -> None:
    by_year = {y: [] for y in YEARS}
    for line in DATA_TXT.read_text().splitlines():
        for y in YEARS:
            if line.startswith(f"NOI{y},"):
                p = line.rstrip(",").split(",")
                by_year[y].append(dict(
                    medal=p[1], name=p[2], grade=p[3], school=p[4],
                    score=int(p[5]), province=p[6],
                    gender=p[7] if len(p) > 7 else ""))

    entities, gold = [], {}
    for y in YEARS:
        rows = by_year[y]
        golds = sorted([r for r in rows if r["medal"] == "金牌"],
                       key=lambda r: r["score"])
        silvers = sorted([r for r in rows if r["medal"] == "银牌"],
                         key=lambda r: -r["score"])
        cut = (golds[0]["score"] + silvers[0]["score"]) / 2
        window = ([dict(r, tier="gold", side=+1) for r in golds[:BANDWIDTH]] +
                  [dict(r, tier="silver", side=-1) for r in silvers[:BANDWIDTH]])
        edition_num = y - 1983
        for r in window:
            tier = r["tier"]
            pin = romanize(r["name"])
            eid = f"noird_{tier[0]}_{pin.lower().replace(' ', '_')}_{y}"
            name = f"{pin} ({r['name']})"
            ctx = (f"a {y} NOI (China National Olympiad in Informatics) {tier} "
                   f"medalist from {r['school']}")
            g = (f"{name} was a {tier} medalist at the {y} NOI "
                 f"(中国全国信息学奥林匹克竞赛, China National Olympiad in "
                 f"Informatics, the {edition_num}th edition), representing "
                 f"{r['school']}. {BOILER[tier]}")
            entities.append({
                "id": eid, "name": name, "context": ctx,
                "cohort": f"noird_{tier}",
                "credential_year": y, "credential_country": "China",
                "credential_school": r["school"],
                "tier": tier, "noi_score": r["score"],
                "dist_to_cut": r["score"] - cut,
                "grade": r["grade"], "province": r["province"],
                "gender": r["gender"],
                "pinyin_uncertain": r["name"] in UNCERTAIN,
                "anchor": False,
            })
            gold[eid] = g

    # 2009 boundary anchors: entities + golds verbatim from t5_3
    t53_ents = {e["id"]: e for e in json.loads(
        (T53 / "inputs" / "tier_entities.json").read_text())}
    t53_gold = json.loads((T53 / "inputs" / "tier_gold.json").read_text())
    boundary09 = [e for e in t53_ents.values()
                  if e.get("tier") in ("gold", "silver") and not e["control"]]
    boundary09 = (sorted([e for e in boundary09 if e["tier"] == "gold"],
                         key=lambda e: e["noi_score"])[:BANDWIDTH] +
                  sorted([e for e in boundary09 if e["tier"] == "silver"],
                         key=lambda e: -e["noi_score"])[:BANDWIDTH])
    for e in boundary09:
        e = dict(e)
        e["anchor"] = True
        e["dist_to_cut"] = e["noi_score"] - (366 + 352) / 2
        entities.append(e)
        gold[e["id"]] = t53_gold[e["id"]]

    inp = HERE / "inputs"
    inp.mkdir(exist_ok=True)
    (inp / "rd_entities.json").write_text(
        json.dumps(entities, indent=1, ensure_ascii=False))
    (inp / "rd_gold.json").write_text(
        json.dumps(gold, indent=1, ensure_ascii=False))

    from collections import Counter
    print(Counter((e["credential_year"], e["tier"]) for e in entities))
    print(f"total {len(entities)} entities "
          f"({sum(1 for e in entities if e['anchor'])} anchors); "
          f"{sum(1 for e in entities if e.get('pinyin_uncertain'))} pinyin-uncertain")
    for e in entities[:3] + entities[-3:]:
        print(" ", e["id"], "|", e["name"], "|", e["noi_score"], e["tier"])


if __name__ == "__main__":
    main()
