"""Build probe inputs for the award-ladder run.

Entities = 8 award cohorts (from 01/02) + in-run controls resampled from the
main run (60 OpenAlex long-tail researchers, 40 IMO golds, tuixue.online,
nanoGPT — golds and contexts copied verbatim) + 2 new USTC website entities.

Contexts follow the main run's credential-cohort convention (award + year,
never contributions).  Golds: en-Wikipedia intro trimmed to ~200 words where
available; otherwise the boilerplate recipe used for MSRA/IMO golds (award
fact + 2-3 sentences about the award), so gold density mirrors the credential
cohorts it will be compared against.

Writes inputs/award_entities.json and inputs/award_gold.json.
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
OUT = HERE / "outputs"
INP = HERE / "inputs"

CONTEXT = {
    "turing_award": "a computer scientist who received the ACM A.M. Turing Award{yr}",
    "fields_medal": "a mathematician who received the Fields Medal{yr}",
    "nobel_physics": "a physicist who received the Nobel Prize in Physics{yr}",
    "godel_prize": "a theoretical computer scientist who received the Gödel Prize{yr}",
    "acm_prize_computing": "a computer scientist who received the ACM Prize in Computing{yr}",
    "macarthur_fellow": "a recipient of the MacArthur Fellowship{yr}",
    "acm_fellow": "a computer scientist elected a Fellow of the ACM{yr}",
    "sloan_fellow": "a researcher who received a Sloan Research Fellowship{yr}",
}

BOILER = {
    "turing_award": ("The ACM A.M. Turing Award is generally regarded as the highest "
                     "distinction in computer science, given annually by the Association "
                     "for Computing Machinery for contributions of lasting and major "
                     "technical importance to the field."),
    "fields_medal": ("The Fields Medal is awarded every four years by the International "
                     "Mathematical Union to mathematicians under forty, and is widely "
                     "regarded as one of the highest honors in mathematics."),
    "nobel_physics": ("The Nobel Prize in Physics is awarded annually by the Royal "
                      "Swedish Academy of Sciences and is regarded as the most "
                      "prestigious recognition in physics."),
    "godel_prize": ("The Gödel Prize is awarded jointly by EATCS and ACM SIGACT for "
                    "outstanding papers in theoretical computer science."),
    "acm_prize_computing": ("The ACM Prize in Computing recognizes early-to-mid-career "
                            "computer scientists for fundamental, innovative contributions "
                            "in computing."),
    "macarthur_fellow": ("The MacArthur Fellowship (the 'genius grant') is a no-strings "
                         "five-year award given annually by the MacArthur Foundation to "
                         "roughly two dozen exceptionally creative individuals across all "
                         "fields."),
    "acm_fellow": ("ACM Fellow is the highest membership grade of the Association for "
                   "Computing Machinery, recognizing the top 1% of members for "
                   "accomplishments in computing."),
    "sloan_fellow": ("The Sloan Research Fellowship is a prestigious early-career award "
                     "given annually by the Alfred P. Sloan Foundation to outstanding "
                     "young researchers in the sciences."),
}

WEBSITES = [
    {
        "id": "artifact_icourse_club",
        "name": "icourse.club",
        "context": ("a Chinese-language course-review website for students of the "
                    "University of Science and Technology of China (USTC)"),
        "cohort": "website_or_service",
        "gold": ("icourse.club (USTC评课社区, the USTC Course-Review "
                 "Community) is a Chinese-language course-review website serving "
                 "students of the University of Science and Technology of China. "
                 "Launched in May 2015, it lets students rate and review courses and "
                 "instructors to inform course selection; as of 2026 it hosts over "
                 "48,000 reviews covering more than 5,500 courses, contributed by more "
                 "than 22,000 registered users. The site was built by USTC students: "
                 "product and frontend by Jingning Zhang (jenny42), backend by Bojie Li "
                 "(boj) and Zhen Chang (Aaron1992). Its code is open source under the "
                 "GNU AGPL v3 license in the USTC-iCourse/ustc-course repository on "
                 "GitHub. It combines official course information with "
                 "student-contributed evaluations and has become the de facto course "
                 "information platform at USTC."),
    },
    {
        "id": "artifact_ustc_hackergame",
        "name": "Hackergame",
        "context": ("an annual online capture-the-flag (CTF) security competition "
                    "organized by the Linux User Group of the University of Science and "
                    "Technology of China (USTC)"),
        "cohort": "website_or_service",
        "gold": ("Hackergame is an annual online capture-the-flag (CTF) security "
                 "competition organized by the Linux User Group (LUG) of the University "
                 "of Science and Technology of China (USTC), formally titled the USTC "
                 "Information Security Competition "
                 "(中国科学技术大学信息安"
                 "全大赛). Growing out of a campus contest first held in "
                 "2014, it later adopted the Hackergame name and an open-to-the-public "
                 "online format, reaching its eleventh edition in 2024. The competition "
                 "runs for one week each autumn on the platform hack.lug.ustc.edu.cn "
                 "and features dozens of original challenges spanning web security, "
                 "binary exploitation, cryptography, and general computer-science "
                 "puzzles, known for a beginner-friendly and playful problem design. It "
                 "attracts thousands of participants from universities across China "
                 "each year, and complete official and community write-ups are "
                 "published on GitHub under the USTC-Hackergame organization after each "
                 "edition."),
    },
]


def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return s or "x"


def trim_words(text: str, max_words: int = 200) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    cut = " ".join(words[:max_words])
    # end at the last sentence boundary inside the cut
    m = re.search(r"^(.+[.!?])\s[^.!?]*$", cut, re.S)
    return m.group(1) if m else cut + "..."


def main() -> None:
    cohorts = json.loads((OUT / "award_candidates.json").read_text())
    bios = json.loads((OUT / "bios.json").read_text())
    entities, gold = [], {}

    for cid, c in cohorts.items():
        for m in c["members"]:
            b = bios.get(m["wikidata"], {})
            yr = m.get("award_year")
            ctx = CONTEXT[cid].format(yr=f" in {yr}" if yr else "")
            wiki = (b.get("wiki") or {})
            # probe with the common name (Wikipedia title), not the Wikidata
            # label ("Shafi Goldwasser", not "Shafrira Goldwasser")
            if wiki.get("title"):
                m["name"] = wiki["title"]
            eid = f"{cid}_{slug(m['name'])}"
            extract = (wiki.get("extract") or "").strip()
            if len(extract.split()) >= 40:
                g = trim_words(extract)
                gold_src = "wikipedia"
            else:
                award_fact = ctx[0].upper() + ctx[1:]
                g = f"{m['name']} is {ctx}. {BOILER[cid]}"
                del award_fact
                gold_src = "boilerplate"
            oa = b.get("openalex") or {}
            confident = bool(oa) and (oa.get("name_similarity") or 0) >= 0.85
            entities.append({
                "id": eid, "name": m["name"], "context": ctx, "cohort": cid,
                "career_stage": m["career_stage"], "award_year": yr,
                "wikidata": m["wikidata"], "gold_source": gold_src,
                "complete_roster": c["complete_roster"],
                "h_index": oa.get("h_index") if confident else None,
                "cited_by_count": oa.get("cited_by_count") if confident else None,
                "control": False,
            })
            gold[eid] = g

    # in-run controls from the main run, golds/contexts verbatim
    main_ents = json.loads((REPO / "data" / "inputs" / "pilot_entities.json").read_text())
    main_gold = json.loads((REPO / "data" / "inputs" / "gold_answers.json").read_text())
    rng = random.Random(42)
    oa_pool = [e for e in main_ents if e["cohort"] == "long_tail_researcher_openalex"]
    imo_pool = [e for e in main_ents if e["cohort"] == "imo_gold"]
    refs = [e for e in main_ents if e["id"] in ("tuixue_online", "nanogpt")]
    for e in rng.sample(oa_pool, 60) + rng.sample(imo_pool, 40) + refs:
        e = dict(e)
        e["control"] = True
        e["career_stage"] = None
        entities.append(e)
        gold[e["id"]] = main_gold[e["id"]]

    for w in WEBSITES:
        gold[w["id"]] = w.pop("gold")
        w.update({"control": False, "career_stage": None})
        entities.append(w)

    INP.mkdir(exist_ok=True)
    (INP / "award_entities.json").write_text(json.dumps(entities, indent=1, ensure_ascii=False))
    (INP / "award_gold.json").write_text(json.dumps(gold, indent=1, ensure_ascii=False))
    from collections import Counter
    print(Counter(e["cohort"] for e in entities))
    n_wiki = sum(1 for e in entities if e.get("gold_source") == "wikipedia")
    n_boil = sum(1 for e in entities if e.get("gold_source") == "boilerplate")
    n_h = sum(1 for e in entities if e.get("h_index"))
    print(f"total {len(entities)}; golds wiki {n_wiki} / boilerplate {n_boil}; "
          f"confident h-index {n_h}")


if __name__ == "__main__":
    main()
