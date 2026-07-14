"""v2 golds for paper cohorts via Crossref (free, uncapped) — OpenAlex is
credit-metered and exhausted. Cohorts: long_tail_paper (have DOI + first_authors
+ subfield + openalex_id), research_paper (title only).

Gold recipe: "TITLE is a YEAR paper by A, B, C and N others, published in VENUE.
[Subject areas / abstract sentence.]" — >=3 facts beyond the v2 context
("a YEAR academic paper in SUBFIELD"): author names, venue, and specific
subjects/findings.

Resumable; checkpoints every 100.
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
OUT_GOLD = HERE / "inputs" / "gold_v2_papers.json"
OUT_REPORT = HERE / "outputs" / "match_report_papers.csv"
UA = {"User-Agent": "NameRank-v2-goldbuilder (mailto:boj@19pine.ai)"}


def cr_get(url: str):
    for a in range(4):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503):
                time.sleep(2 * (a + 1))
                continue
            return None
        except Exception:
            time.sleep(1.5)
    return None


def strip_jats(txt: str) -> str:
    txt = re.sub(r"<[^>]+>", " ", txt or "")
    return re.sub(r"\s+", " ", txt).strip()


def compose(msg: dict, subfield: str, year_hint) -> tuple[str, bool]:
    title = (msg.get("title") or [""])[0].strip()
    venue = (msg.get("container-title") or [""])[0].strip()
    yr = None
    for k in ("published-print", "published-online", "issued"):
        p = msg.get(k, {}).get("date-parts", [[None]])
        if p and p[0] and p[0][0]:
            yr = p[0][0]
            break
    yr = yr or year_hint
    authors = msg.get("author", []) or []
    anames = [f"{a.get('given','').strip()} {a.get('family','').strip()}".strip()
              for a in authors if a.get("family")]
    subjects = [s for s in (msg.get("subject") or []) if s][:3]
    abstract = strip_jats(msg.get("abstract", ""))

    facts = []
    lead = f"“{title}” is"
    if yr:
        lead += f" a {yr}"
    else:
        lead += " a"
    lead += " research paper"
    if anames:
        if len(anames) <= 3:
            lead += " by " + ", ".join(anames)
        else:
            lead += " by " + ", ".join(anames[:3]) + f" and {len(anames)-3} others"
    if venue:
        lead += f", published in {venue}"
    lead += "."
    facts.append(lead)
    if abstract:
        sents = re.split(r"(?<=[.!?]) ", abstract)
        facts.append(" ".join(sents[:3])[:600])
    elif subjects:
        facts.append("It falls under " + ", ".join(subjects) + ".")
    gold = " ".join(facts)
    # beyond-context facts: authors + venue (subfield is in context). Thin if
    # neither venue nor authors resolved.
    thin = not (venue or anames)
    return gold, thin


def main() -> None:
    pe = json.loads((REPO / "data/inputs/pilot_entities.json").read_text())
    papers = [e for e in pe if e["cohort"] in ("long_tail_paper", "research_paper")]
    gold = json.loads(OUT_GOLD.read_text()) if OUT_GOLD.exists() else {}
    todo = [e for e in papers if e["id"] not in gold]
    print(f"{len(papers)} papers, {len(gold)} done, {len(todo)} to fetch")

    report_rows = []

    def work(e):
        eid = e["id"]
        subfield = e.get("subfield", "")
        yr = e.get("credential_year")
        doi = e.get("doi")
        msg = None
        method = ""
        if doi:
            d = cr_get("https://api.crossref.org/works/" + urllib.parse.quote(doi))
            if d:
                msg, method = d.get("message"), "doi"
        if msg is None:
            # title search
            q = urllib.parse.urlencode({"query.bibliographic": e["name"][:200],
                                        "rows": 3, "mailto": "boj@19pine.ai"})
            d = cr_get("https://api.crossref.org/works?" + q)
            items = (d or {}).get("message", {}).get("items", [])
            # verify: title token overlap
            want = set(re.findall(r"\w+", e["name"].lower()))
            for it in items:
                cand = set(re.findall(r"\w+", (it.get("title", [""])[0]).lower()))
                if want and len(want & cand) / len(want) >= 0.6:
                    msg, method = it, "title"
                    break
        if msg is None:
            return eid, None, {"matched": 0, "method": "none", "reason": "no crossref hit"}
        g, thin = compose(msg, subfield, yr)
        return eid, {"gold": g, "source": "crossref", "source_ref": method,
                     "confidence": "high" if method == "doi" else "medium",
                     "thin_gold": thin}, {"matched": 1, "method": method}

    done_since_ckpt = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(work, e): e for e in todo}
        for i, fut in enumerate(as_completed(futs)):
            eid, rec, rep = fut.result()
            e = futs[fut]
            if rec:
                gold[eid] = rec
            report_rows.append({"entity_id": eid, "cohort": e["cohort"], **rep})
            done_since_ckpt += 1
            if done_since_ckpt >= 100:
                OUT_GOLD.write_text(json.dumps(gold, ensure_ascii=False, indent=1))
                done_since_ckpt = 0
                print(f"  checkpoint {i+1}/{len(todo)}", flush=True)

    OUT_GOLD.write_text(json.dumps(gold, ensure_ascii=False, indent=1))
    import csv
    with open(OUT_REPORT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["entity_id", "cohort", "matched",
                                          "method", "reason"])
        w.writeheader()
        for r in report_rows:
            w.writerow({k: r.get(k, "") for k in
                        ["entity_id", "cohort", "matched", "method", "reason"]})
    matched = sum(1 for v in gold.values() if v.get("gold"))
    thin = sum(1 for v in gold.values() if v.get("thin_gold"))
    print(f"done: {matched} golds, {thin} thin")


if __name__ == "__main__":
    main()
