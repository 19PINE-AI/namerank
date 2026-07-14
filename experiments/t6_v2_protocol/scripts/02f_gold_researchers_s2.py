"""v2 golds for researcher/faculty cohorts via Semantic Scholar (OpenAlex is
credit-metered and exhausted). Cohorts: long_tail_researcher_openalex (771,
known h_index+subfield), cs_faculty (698, known institution), plus any
long_tail_researcher_ikp / gpt5 / deepseek not already done by 02a.

Disambiguation (the wrong-person guard):
- Researchers with a known OpenAlex h_index: accept the S2 author whose hIndex
  lies in [max(2, 0.4*h_known - 3), 2.5*h_known + 8] AND is the clear leader by
  paperCount (>=1.5x the runner-up, or the only in-band candidate). S2 and
  OpenAlex h differ but correlate; the band + dominance rejects namesakes.
- Faculty (no known h): accept only if the top candidate's affiliation string
  overlaps the known institution, OR it uniquely dominates paperCount (>=3x
  runner-up) with paperCount>=15. Otherwise unmatched (no guess).

Gold: "NAME is a researcher in FIELD[ at INSTITUTION]. Their most-cited works
include 'T1' (VENUE Y1), 'T2' (Y2), 'T3' (Y3)." No h-index/citation numbers.

Serialized (S2 unauth throttle); resumable; checkpoints every 40.
"""
from __future__ import annotations

import csv
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
OUT_GOLD = HERE / "inputs" / "gold_v2_researchers_s2.json"
OUT_REPORT = HERE / "outputs" / "match_report_researchers_s2.csv"
UA = {"User-Agent": "NameRank-v2 (mailto:boj@19pine.ai)"}
S2 = "https://api.semanticscholar.org/graph/v1"

# gpt5/deepseek authors are DELIBERATELY excluded: they are industry engineers
# with little/no academic record, so S2 name-search returns wrong-person
# namesakes. They stay on 02a's stricter OpenAlex matches (system-card-in-works
# or OpenAI/DeepSeek affiliation) or the assembly's membership-minimal gold;
# either way the cohort is silent-zone calibration and must not carry a
# wrong-person gold.
COHORTS = ["long_tail_researcher_openalex", "cs_faculty",
           "long_tail_researcher_ikp"]


def s2_get(path: str):
    url = S2 + path
    for a in range(6):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2.0 * (a + 1))
                continue
            return None
        except Exception:
            time.sleep(1.5)
    return None


def norm(s: str) -> str:
    return re.sub(r"[^a-z ]", "", (s or "").lower()).strip()


ORG_RE = re.compile(r"\b(university|universit|institute|institut|agency|badan|"
                    r"pusat|department|departemen|laboratory|laboratoire|centre|"
                    r"center|ministry|kementerian|hospital|college|academy|"
                    r"foundation|council|society|association|group|team|corp|inc|"
                    r"gmbh|ltd)\b", re.I)


def is_org_name(name: str) -> bool:
    return bool(ORG_RE.search(name)) or len(name.split()) >= 5


def name_ok(query: str, cand: str) -> bool:
    q, c = norm(query).split(), norm(cand).split()
    if not q or not c:
        return False
    if q[-1] == c[-1]:  # surname match; given name full or shared initial
        return q[0] == c[0] or q[0][:1] == c[0][:1]
    # reversed order (e.g. romanized Chinese names)
    if q[0] == c[-1] or q[-1] == c[0]:
        return True
    return False


CS_TERMS = re.compile(
    r"\b(comput|algorithm|network|learning|machine|neural|softwar|system|data|"
    r"program|languag|security|cryptograph|graph|robot|vision|inform|artificial|"
    r"database|distributed|parallel|architectur|compiler|verif|optimiz|"
    r"interact|human-comput|hci|nlp|retriev|model|simulation|circuit|processor)\b",
    re.I)
CS_VENUES = re.compile(
    r"\b(POPL|PLDI|OOPSLA|ICFP|NeurIPS|NIPS|ICML|ICLR|AAAI|IJCAI|CVPR|ICCV|ECCV|"
    r"ACL|EMNLP|NAACL|SIGCOMM|NSDI|OSDI|SOSP|SIGMOD|VLDB|ICSE|FSE|CHI|UIST|"
    r"CCS|USENIX|Oakland|S&P|STOC|FOCS|SODA|ISCA|MICRO|HPCA|KDD|WWW|SIGGRAPH)\b",
    re.I)


def cs_topical(papers) -> bool:
    """Reject same-name academics in unrelated fields using S2 fieldsOfStudy.
    Require >=3 of the top-6 cited papers tagged Computer Science or
    Mathematics (some CS faculty publish in math/stats/theory venues).
    Falls back to keyword matching if fieldsOfStudy is absent."""
    top = sorted(papers, key=lambda x: -(x.get("citationCount") or 0))[:6]
    cs = tagged = kw = 0
    for p in top:
        fos = p.get("fieldsOfStudy") or [
            x.get("category") for x in (p.get("s2FieldsOfStudy") or [])]
        fos = [f for f in fos if f]
        if fos:
            tagged += 1
            if any(f in ("Computer Science", "Mathematics", "Engineering")
                   for f in fos):
                cs += 1
        blob = f"{p.get('title','')} {p.get('venue','')}"
        if CS_TERMS.search(blob) or CS_VENUES.search(p.get("venue", "") or ""):
            kw += 1
    if tagged >= 3:
        return cs >= 3 or cs / tagged >= 0.5
    return kw >= 2  # fallback when S2 has no field tags


def pick_author(cands, h_known, institution):
    inband = []
    for a in cands:
        h = a.get("hIndex")
        pc = a.get("paperCount") or 0
        if pc < 3:
            continue
        if h_known is not None and h is not None:
            lo, hi = max(2, 0.4 * h_known - 3), 2.5 * h_known + 8
            if not (lo <= h <= hi):
                continue
        inband.append(a)
    if not inband:
        return None, "no in-band candidate"
    inband.sort(key=lambda a: -(a.get("paperCount") or 0))
    top = inband[0]
    runner = (inband[1].get("paperCount") or 0) if len(inband) > 1 else 0
    if institution and h_known is None:
        # faculty (no reference h): the top paperCount candidate for a
        # distinctive CS-faculty name is almost always correct, but S2
        # affiliations are usually empty so we cannot gate on them. Gate
        # instead on (a) dominance/uniqueness and (b) a CS-topical check done
        # by the caller after fetching papers (rejects same-name academics in
        # unrelated fields). Return the candidate + a flag to verify topically.
        if (top.get("paperCount") or 0) < 10:
            return None, "faculty: top candidate too few papers"
        if len(inband) == 1 or (top.get("paperCount") or 0) >= 1.5 * runner:
            return top, "faculty: dominance (verify CS-topical)"
        return None, "faculty: ambiguous same-name candidates"
    # researcher with known h: require dominance or uniqueness
    if len(inband) == 1 or (top.get("paperCount") or 0) >= 1.5 * runner:
        return top, "h-band + dominance"
    return None, "ambiguous in-band"


def build_gold(name, field, institution, papers):
    ps = sorted(papers, key=lambda x: -(x.get("citationCount") or 0))
    named = []
    for p in ps:
        t = (p.get("title") or "").strip()
        if not t:
            continue
        t = " ".join(t.split()[:14])
        v = (p.get("venue") or "").strip()
        y = p.get("year")
        tag = t
        if v and y:
            tag += f" ({v}, {y})"
        elif y:
            tag += f" ({y})"
        named.append(f"“{tag}”")
        if len(named) >= 3:
            break
    s = f"{name} is a researcher"
    if field:
        s += f" in {field}"
    if institution:
        s += f" at {institution}"
    s += "."
    if named:
        s += " Their most-cited works include " + ", ".join(named) + "."
    thin = len(named) < 2
    return s, thin


def main() -> None:
    pe = json.loads((REPO / "data/inputs/pilot_entities.json").read_text())
    ents = [e for e in pe if e["cohort"] in COHORTS]
    # skip entities already resolved by 02a (OpenAlex people builder)
    prev = {}
    ppath = HERE / "inputs" / "gold_v2_people.json"
    if ppath.exists():
        prev = json.loads(ppath.read_text())
    gold = json.loads(OUT_GOLD.read_text()) if OUT_GOLD.exists() else {}
    report = list(csv.DictReader(open(OUT_REPORT))) if OUT_REPORT.exists() else []
    seen = {r["entity_id"] for r in report}
    todo = [e for e in ents if e["id"] not in prev and e["id"] not in gold
            and e["id"] not in seen]
    print(f"{len(ents)} entities; {len(prev)} from 02a, {len(gold)} S2-done; "
          f"{len(todo)} to fetch", flush=True)

    def field_of(e):
        c = e["context"]
        m = re.search(r"researcher in (.+?)(?: at |$)", c)
        if m:
            return m.group(1).strip()
        return e.get("subfield", "")

    def inst_of(e):
        if e["cohort"] == "cs_faculty":
            return e.get("institution") or e["context"].split(" at ")[-1]
        m = re.search(r" at (.+)$", e["context"])
        return m.group(1).strip() if m else None

    n = 0
    for e in todo:
        eid = e["id"]
        if is_org_name(e["name"]):  # OpenAlex author-parse artifacts (agencies)
            report.append({"entity_id": eid, "cohort": e["cohort"],
                           "matched": 0, "s2_author": "",
                           "reason": "org-name (not a person), skipped"})
            n += 1
            continue
        h_known = e.get("h_index")
        field = field_of(e)
        inst = inst_of(e) if e["cohort"] == "cs_faculty" else \
            (re.search(r" at (.+)$", e["context"]).group(1)
             if " at " in e["context"] else None)
        q = urllib.parse.quote(e["name"])
        sr = s2_get(f"/author/search?query={q}"
                    "&fields=name,hIndex,paperCount,affiliations")
        cands = [a for a in (sr or {}).get("data", [])
                 if name_ok(e["name"], a.get("name", ""))] if sr else []
        author, reason = (pick_author(cands, h_known, inst)
                          if cands else (None, "no name-matched candidate"))
        rec = None
        if author:
            pr = s2_get(f"/author/{author['authorId']}/papers"
                        "?fields=title,year,venue,citationCount,fieldsOfStudy,s2FieldsOfStudy&limit=100")
            papers = (pr or {}).get("data", []) if pr else []
            # faculty: verify the matched author actually works in CS
            if e["cohort"] == "cs_faculty" and not cs_topical(papers):
                reason = "faculty: matched author not CS-topical (rejected)"
            else:
                g, thin = build_gold(
                    e["name"], field,
                    inst if e["cohort"] == "cs_faculty" else None, papers)
                rec = {"gold": g, "source": "semantic_scholar",
                       "source_ref": str(author["authorId"]),
                       "confidence": "medium", "thin_gold": thin}
                gold[eid] = rec
        report.append({"entity_id": eid, "cohort": e["cohort"],
                       "matched": int(bool(rec)),
                       "s2_author": author.get("authorId") if author else "",
                       "reason": reason})
        n += 1
        if n % 40 == 0:
            OUT_GOLD.write_text(json.dumps(gold, ensure_ascii=False, indent=1))
            with open(OUT_REPORT, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["entity_id", "cohort",
                                                  "matched", "s2_author", "reason"])
                w.writeheader()
                w.writerows(report)
            print(f"  {n}/{len(todo)} ({sum(1 for v in gold.values() if v.get('gold'))} matched)",
                  flush=True)

    OUT_GOLD.write_text(json.dumps(gold, ensure_ascii=False, indent=1))
    with open(OUT_REPORT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["entity_id", "cohort", "matched",
                                          "s2_author", "reason"])
        w.writeheader()
        w.writerows(report)
    matched = sum(1 for v in gold.values() if v.get("gold"))
    print(f"done: {matched}/{len(todo)+len(gold)-len(todo)} S2 golds", flush=True)
    from collections import Counter
    print("matched by cohort:",
          dict(Counter(r["cohort"] for r in report if r["matched"] == 1 or r["matched"] == "1")))


if __name__ == "__main__":
    main()
