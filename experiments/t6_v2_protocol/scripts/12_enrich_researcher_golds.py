"""Widen the researcher/faculty v3 verification pool (fix for narrow-gold false
negatives found 2026-07-12). The top-3-paper gold rejects a model that
genuinely recognizes the researcher via their research areas, OTHER papers, or
collaborators. This re-fetches each already-matched S2 author (authorId stored
in the existing gold's source_ref) and rebuilds the gold with:
  - up to 6 notable works (was 3),
  - up to 5 distinctive frequent collaborators (non-guessable, strong
    recognition signal; a same-name namesake will not share them),
  - a research-areas phrase derived from the papers' fields/venues.

Only widens the answer key; does NOT relax correctness. A wrong-person
(namesake) response still matches none of the real papers/collaborators.

Writes inputs/gold_v2_researchers_s2_rich.json (same schema). Resumable.
"""
from __future__ import annotations

import json
import re
import time
import urllib.request
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
UA = {"User-Agent": "NameRank-v2 (mailto:boj@19pine.ai)"}
S2 = "https://api.semanticscholar.org/graph/v1"
OUT = HERE / "inputs" / "gold_v2_researchers_s2_rich.json"


def s2_get(path):
    for a in range(6):
        try:
            req = urllib.request.Request(S2 + path, headers=UA)
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


def main():
    ents = {e["id"]: e for e in json.loads(
        (HERE / "inputs" / "pilot_entities_v2.json").read_text())}
    old = json.loads((HERE / "inputs" / "gold_v2_researchers_s2.json").read_text())
    rich = json.loads(OUT.read_text()) if OUT.exists() else {}
    todo = [(eid, v) for eid, v in old.items()
            if v.get("source_ref") and eid not in rich]
    print(f"{len(old)} S2 golds, {len(rich)} enriched, {len(todo)} to fetch")

    def field_of(e):
        m = re.search(r"researcher in (.+?)(?: at |$)", e["context"])
        return m.group(1).strip() if m else ""

    def inst_of(e):
        if e["cohort"] == "cs_faculty":
            return e.get("institution") or ""
        m = re.search(r" at (.+)$", e["context"])
        return m.group(1).strip() if m else ""

    n = 0
    for eid, v in todo:
        e = ents.get(eid)
        if not e:
            continue
        aid = v["source_ref"]
        pr = s2_get(f"/author/{aid}/papers?fields=title,year,venue,"
                    "citationCount,fieldsOfStudy,authors&limit=100")
        papers = (pr or {}).get("data", []) if pr else []
        if not papers:
            rich[eid] = v  # keep the old gold if refetch fails
            n += 1
            continue
        papers.sort(key=lambda x: -(x.get("citationCount") or 0))
        name = e["name"]
        # notable works (up to 6)
        works = []
        for p in papers[:6]:
            t = " ".join((p.get("title") or "").split()[:14])
            if not t:
                continue
            ven, yr = (p.get("venue") or "").strip(), p.get("year")
            tag = t + (f" ({ven}, {yr})" if ven and yr else (f" ({yr})" if yr else ""))
            works.append(f"“{tag}”")
        # distinctive collaborators (frequent coauthors, excluding self)
        self_last = re.sub(r"[^a-z]", "", name.lower().split()[-1])
        co = Counter()
        for p in papers[:25]:
            for a in (p.get("authors") or []):
                an = a.get("name", "")
                if re.sub(r"[^a-z]", "", an.lower().split()[-1] if an.split() else "") == self_last:
                    continue
                co[an] += 1
        collabs = [a for a, c in co.most_common(8) if c >= 2][:5]
        # research areas from fieldsOfStudy (specific-ish); fall back to none
        fos = Counter()
        for p in papers[:15]:
            for f in (p.get("fieldsOfStudy") or []):
                if f not in ("Computer Science",):  # too generic (== context often)
                    fos[f] += 1
        areas = [f for f, _ in fos.most_common(3)]

        field, inst = field_of(e), inst_of(e)
        s = f"{name} is a researcher"
        if field:
            s += f" in {field}"
        if inst:
            s += f" at {inst}"
        s += "."
        if works:
            s += " Their notable works include " + ", ".join(works) + "."
        if collabs:
            s += " Frequent collaborators include " + ", ".join(collabs) + "."
        if areas:
            s += " Their publications also span " + ", ".join(areas) + "."
        rich[eid] = {"gold": s, "source": "semantic_scholar",
                     "source_ref": aid, "confidence": v.get("confidence", "medium"),
                     "thin_gold": len(works) < 2 and not collabs}
        n += 1
        if n % 50 == 0:
            OUT.write_text(json.dumps(rich, ensure_ascii=False, indent=1))
            print(f"  {n}/{len(todo)}", flush=True)

    OUT.write_text(json.dumps(rich, ensure_ascii=False, indent=1))
    print(f"done: {len(rich)} enriched golds")
    # sample
    for eid in list(rich)[:2]:
        print(" e.g.", rich[eid]["gold"][:240])


if __name__ == "__main__":
    main()
