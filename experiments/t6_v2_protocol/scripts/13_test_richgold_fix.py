"""Focused A/B test: does WIDER gold alone fix the researcher/faculty false
negatives under the CURRENT v3 judge (no shared judge-prompt change)?

For researcher/faculty records that were substantive-but-recognized=0, re-judge
each response under both the OLD 3-paper gold and a RICH gold (6 papers +
collaborators + areas, fetched inline), using the unchanged judge_prompt_v3.
Reports flips and, crucially, confirms namesake/hallucination cases STAY
recognized=0.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from collections import Counter
from pathlib import Path

from google import genai
from google.genai import types as genai_types

HERE = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "NameRank-v2 (mailto:boj@19pine.ai)"}
S2 = "https://api.semanticscholar.org/graph/v1"
TPL = (HERE / "inputs" / "judge_prompt_v3.txt").read_text()
SCHEMA = {"type": "object", "properties": {
    "recognized": {"type": "boolean"}, "coverage": {"type": "number"},
    "accuracy": {"type": "number"}, "rationale": {"type": "string"}},
    "required": ["recognized", "coverage", "accuracy", "rationale"]}
SYS = ("You are an objective grader judging whether a language model genuinely "
       "recognizes a named entity. You grade only the response against the gold "
       "answer, giving no credit for restating the probe context or for "
       "guessable generic facts.")
gc = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def s2_get(path):
    for a in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(S2 + path, headers=UA),
                                        timeout=25) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2.5 * (a + 1)); continue
            return None
        except Exception:
            time.sleep(1.5)
    return None


def rich_gold(name, field, inst, aid):
    pr = s2_get(f"/author/{aid}/papers?fields=title,year,venue,citationCount,"
                "fieldsOfStudy,authors&limit=100")
    papers = sorted((pr or {}).get("data", []),
                    key=lambda x: -(x.get("citationCount") or 0))
    if not papers:
        return None
    works = []
    for p in papers[:6]:
        t = " ".join((p.get("title") or "").split()[:14])
        if t:
            ven, yr = (p.get("venue") or "").strip(), p.get("year")
            works.append(f"“{t}" + (f" ({ven}, {yr})" if ven and yr else
                                     (f" ({yr})" if yr else "")) + "”")
    sl = re.sub(r"[^a-z]", "", name.lower().split()[-1])
    co = Counter()
    for p in papers[:25]:
        for a in (p.get("authors") or []):
            an = a.get("name", "")
            if an and re.sub(r"[^a-z]", "", an.lower().split()[-1]) != sl:
                co[an] += 1
    collabs = [a for a, c in co.most_common(8) if c >= 2][:5]
    fos = Counter()
    for p in papers[:15]:
        for f in (p.get("fieldsOfStudy") or []):
            if f != "Computer Science":
                fos[f] += 1
    areas = [f for f, _ in fos.most_common(3)]
    s = f"{name} is a researcher" + (f" in {field}" if field else "") + \
        (f" at {inst}" if inst else "") + "."
    if works:
        s += " Their notable works include " + ", ".join(works) + "."
    if collabs:
        s += " Frequent collaborators include " + ", ".join(collabs) + "."
    if areas:
        s += " Their publications also span " + ", ".join(areas) + "."
    return s


def judge(name, ctx, gold, resp):
    for a in range(3):
        try:
            r = gc.models.generate_content(
                model="gemini-3-flash-preview",
                contents=TPL.format(name=name, context=ctx, gold_answer=gold,
                                    response=resp),
                config=genai_types.GenerateContentConfig(
                    system_instruction=SYS, temperature=0.0,
                    response_mime_type="application/json", response_schema=SCHEMA))
            p = json.loads(r.text)
            return bool(p["recognized"]), p["rationale"]
        except Exception:
            if a == 2:
                return None, "ERR"
            time.sleep(2 * (a + 1))


def main():
    ents = {e["id"]: e for e in json.loads(
        (HERE / "inputs" / "pilot_entities_v2.json").read_text())}
    oldg = json.loads((HERE / "inputs" / "gold_v2_researchers_s2.json").read_text())
    v3 = {}
    for line in open(HERE / "outputs" / "recognition_v3_nonimo.jsonl"):
        try:
            r = json.loads(line); v3[(r["entity_id"], r["model_id"])] = r
        except json.JSONDecodeError:
            pass
    resp = {}
    for line in open(HERE / "outputs" / "full_v2_results.jsonl"):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (r["entity_id"], r["model_id"]) in v3:
            resp[(r["entity_id"], r["model_id"])] = r

    TARGET = {"cs_faculty", "long_tail_researcher_openalex",
              "long_tail_researcher_ikp"}
    # substantive-but-rejected records
    cases = []
    for k, vr in v3.items():
        e = ents.get(vr["entity_id"], {})
        if e.get("cohort") not in TARGET or vr["recognized"] == 1 or vr.get("is_refusal"):
            continue
        rr = resp.get(k)
        if not rr or rr["is_refusal"] or len(rr.get("response") or "") < 180:
            continue
        if vr["entity_id"] not in oldg or not oldg[vr["entity_id"]].get("source_ref"):
            continue
        cases.append((k, vr, rr, e))
    cases = cases[:24]
    print(f"testing {len(cases)} substantive-but-rejected researcher/faculty records\n")

    gold_cache = {}
    flips = stay = 0
    for k, vr, rr, e in cases:
        eid = vr["entity_id"]
        if eid not in gold_cache:
            m = re.search(r"researcher in (.+?)(?: at |$)", e["context"])
            field = m.group(1).strip() if m else ""
            inst = e.get("institution") if e["cohort"] == "cs_faculty" else ""
            gold_cache[eid] = rich_gold(e["name"], field, inst,
                                        oldg[eid]["source_ref"]) or oldg[eid]["gold"]
        rg = gold_cache[eid]
        rec_new, rat = judge(e["name"], e["context"], rg, rr["response"])
        if rec_new is None:
            continue
        flag = "FLIP→recognized" if rec_new else "stays rejected"
        if rec_new:
            flips += 1
        else:
            stay += 1
        print(f"[{flag}] {e['name']} [{rr['model_id']}] {e['cohort']}")
        print(f"   resp: {(rr['response'] or '')[:150].strip()}")
        print(f"   rich-gold verdict: {rat[:150]}")
    print(f"\nflips to recognized: {flips}/{len(cases)}; stayed rejected: {stay}")
    print("Manually confirm flips are genuine recognition and stays are "
          "namesakes/hallucinations/soft-refusals.")


if __name__ == "__main__":
    main()
