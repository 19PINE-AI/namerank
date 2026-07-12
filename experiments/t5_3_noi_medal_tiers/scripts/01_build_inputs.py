"""Build probe inputs for the NOI 2009 medal-tier run.

The main run probed only NOI *gold* medalists.  This experiment probes the
complete NOI 2009 medal roster — 20 gold, 34 silver, 49 bronze (103 total) —
to test whether medal tier predicts NameRank, or whether (as the credential
treadmill predicts) the tier signal is swamped by post-medal career track.

Roster source: OIerDb raw data (github.com/OIerDb-ng/OIer, model/data.txt),
cross-validated line-by-line against the official CCF list at
https://www.noi.cn/hjmd/mdgs/2009/2009-09-18/710218.shtml (identical names,
schools, scores; official tiers 一等奖/二等奖/三等奖 = gold/silver/bronze).

Entities:
- 20 NOI 2009 golds: copied VERBATIM from the main run (ids, names, contexts,
  golds unchanged) so the gold arm doubles as the anchor to the released run.
- 83 new silver/bronze entities.  Names follow the main run's probe
  convention "Pinyin (汉字)" (e.g. "Lyu Weicong (吕伟聪)"); contexts follow
  the credential-cohort recipe (medal + year + school, never contributions);
  golds follow the same boilerplate recipe as the main-run NOI golds with the
  tier band adapted, so gold length/density is matched across tiers and the
  ~0.20 short-boilerplate synthetic-null floor applies equally to all three.
- In-run controls (golds/contexts verbatim from the main run): the 9
  non-2009 NOI golds (2012/2013), 30 OpenAlex long-tail researchers,
  tuixue.online + nanoGPT reference artifacts, and the diagnostic-reference
  Bojie Li entity (the NOI 2009 bronze medalist 李博杰 also enters via the
  roster with the boilerplate gold; the reference entity keeps its dense
  gold, giving a within-person gold-recipe contrast).

Romanization: pypinyin with fixes — lü→lyu / nü→nyu (passport convention,
matches main run), surname 缪→Miao, and special cases flagged
pinyin_uncertain: 阿拉法特 (Uyghur name, no surname split), 胡张广达
(combined double surname), 梁錦鴻 (Macau; used name is likely Cantonese),
黄偲 (偲 polyphonic Cai/Si).  Every probe name carries the 汉字, and every
context carries year+school, so common-pinyin collisions stay disambiguated.

Writes inputs/tier_entities.json and inputs/tier_gold.json.
"""
from __future__ import annotations

import csv
import json
import random
from pathlib import Path

from pypinyin import lazy_pinyin

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
INP = HERE / "inputs"

MEDAL_EN = {"金牌": "gold", "银牌": "silver", "铜牌": "bronze"}

# Same sentence skeleton as the main-run NOI gold boilerplate; only the tier
# band differs, so gold density is matched across tiers.
TIER_BOILER = {
    "silver": ("NOI silver medalists rank roughly 21st to 55th nationally among "
               "Chinese high-school competitive programmers each year, with most "
               "going on to elite Chinese universities (Tsinghua University, "
               "Peking University, Fudan University, Shanghai Jiao Tong "
               "University) for undergraduate computer science, often continuing "
               "to careers in technology research, AI, software engineering, or "
               "competitive programming infrastructure."),
    "bronze": ("NOI bronze medalists rank roughly 56th to 105th nationally among "
               "Chinese high-school competitive programmers each year, with most "
               "going on to strong Chinese universities for undergraduate "
               "computer science, often continuing to careers in technology "
               "research, AI, software engineering, or competitive programming "
               "infrastructure."),
}

PINYIN_FIX = {"缪": "miao"}          # surname readings pypinyin gets wrong
UNCERTAIN = {"阿拉法特", "胡张广达", "梁錦鴻", "黄偲"}
NO_SPLIT = {"阿拉法特"}              # non-Han name: romanize whole, no surname split
DOUBLE_SURNAMES = ("欧阳", "司马", "上官", "诸葛", "东方", "皇甫")


def romanize(hanzi: str) -> str:
    def syl(chars: str) -> str:
        out = []
        for ch in chars:
            p = PINYIN_FIX.get(ch) or lazy_pinyin(ch)[0]
            out.append(p.replace("lv", "lyu").replace("nv", "nyu"))
        return "".join(out)

    if hanzi in NO_SPLIT:
        return syl(hanzi).capitalize()
    n = 2 if hanzi[:2] in DOUBLE_SURNAMES else 1
    return f"{syl(hanzi[:n]).capitalize()} {syl(hanzi[n:]).capitalize()}"


def main() -> None:
    roster = list(csv.DictReader(open(INP / "noi2009_roster.csv", encoding="utf-8")))
    main_ents = json.loads((REPO / "data" / "inputs" / "pilot_entities.json").read_text())
    main_gold = json.loads((REPO / "data" / "inputs" / "gold_answers.json").read_text())
    by_id = {e["id"]: e for e in main_ents}

    # map 汉字 -> main-run entity for the 20 golds (main names are "Pinyin (汉字)")
    noi_main = {e["name"].split("(")[1].rstrip(")"): e
                for e in main_ents if e["cohort"] == "noi_china_gold"}

    entities, gold = [], {}
    for r in roster:
        tier = MEDAL_EN[r["medal"]]
        meta = {
            "tier": tier, "noi_score": int(r["score"]), "noi_rank": int(r["rank"]),
            "grade": r["grade"], "province": r["province"], "gender": r["gender"],
            "control": False,
        }
        if tier == "gold":
            e = dict(noi_main[r["name"]])          # verbatim main-run entity
            assert e.get("credential_year") == 2009
            e.update(meta)
            entities.append(e)
            gold[e["id"]] = main_gold[e["id"]]
            continue
        pin = romanize(r["name"])
        slugname = pin.lower().replace(" ", "_")
        eid = f"noi_{tier[0]}_{slugname}_2009"
        name = f"{pin} ({r['name']})"
        ctx = (f"a 2009 NOI (China National Olympiad in Informatics) {tier} "
               f"medalist from {r['school']}")
        g = (f"{name} was a {tier} medalist at the 2009 NOI "
             f"(中国全国信息学奥林匹克竞赛, China National Olympiad in "
             f"Informatics, the 26th edition), representing {r['school']}. "
             f"{TIER_BOILER[tier]}")
        entities.append({
            "id": eid, "name": name, "context": ctx,
            "cohort": f"noi_china_{tier}",
            "credential_year": 2009, "credential_country": "China",
            "credential_school": r["school"],
            "pinyin_uncertain": r["name"] in UNCERTAIN,
            **meta,
        })
        gold[eid] = g

    # in-run controls, golds/contexts verbatim from the main run
    controls = [e for e in main_ents if e["cohort"] == "noi_china_gold"
                and e.get("credential_year") != 2009]           # 9 golds 2012/2013
    rng = random.Random(42)
    oa_pool = [e for e in main_ents if e["cohort"] == "long_tail_researcher_openalex"]
    controls += rng.sample(oa_pool, 30)
    controls += [by_id[i] for i in ("tuixue_online", "nanogpt") if i in by_id]
    ref_bojie = [e for e in main_ents
                 if "bojie" in e["id"].lower() or "李博杰" in e.get("name", "")]
    controls += ref_bojie
    for e in controls:
        e = dict(e)
        e["control"] = True
        e["tier"] = None
        entities.append(e)
        gold[e["id"]] = main_gold[e["id"]]

    (INP / "tier_entities.json").write_text(
        json.dumps(entities, indent=1, ensure_ascii=False))
    (INP / "tier_gold.json").write_text(
        json.dumps(gold, indent=1, ensure_ascii=False))

    from collections import Counter
    print(Counter(e["cohort"] for e in entities))
    print(f"total {len(entities)} entities; "
          f"{sum(1 for e in entities if e.get('pinyin_uncertain'))} pinyin-uncertain; "
          f"controls {sum(1 for e in entities if e['control'])}")
    lens = {t: [len(gold[e['id']].split()) for e in entities
                if e.get('tier') == t] for t in ('gold', 'silver', 'bronze')}
    for t, v in lens.items():
        print(f"gold-answer words [{t}]: mean {sum(v)/len(v):.0f} "
              f"range {min(v)}-{max(v)}")


if __name__ == "__main__":
    main()
