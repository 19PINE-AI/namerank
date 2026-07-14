"""v2 golds for credential cohorts, from official records + conservative enrichment.

Cohorts: imo_gold, ioi_gold, noi_china_gold, cmo_china_gold,
cpho_china_first_prize, putnam_fellow, icpc_world_finals_gold, rhodes_scholar,
msra_phd_fellowship.

Sources:
- imo-official.org embedded JSON (scores, ranks, medals, multi-year via
  contestantId + name).
- stats.ioinformatics.org year tables.
- t5_3 NOI 2009 roster (school, score, rank, province) + v1 entity metadata
  (credential_school/score/province/university) that previously leaked into
  contexts and now becomes gold content.
- Enrichment: t1_4 Wikipedia matches (intro sentences) and conservative
  OpenAlex author matches (exact-name + field + dominance rule; MSRA also
  institution-filtered).

Style guide: experiments/t6_v2_protocol/README.md. No cohort-generic text,
no bibliometric aggregates; >=3 beyond-context facts else thin_gold.
"""
from __future__ import annotations

import csv
import json
import os
import re
import time
import unicodedata
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
UA = {"User-Agent": "NameRank-v2-goldbuilder (boj@19pine.ai)"}
OA_KEY = os.environ.get("OPENALEX_API_KEY", "")

CRED_COHORTS = ["imo_gold", "ioi_gold", "noi_china_gold", "cmo_china_gold",
                "cpho_china_first_prize", "putnam_fellow",
                "icpc_world_finals_gold", "rhodes_scholar",
                "msra_phd_fellowship"]

COUNTRY3 = {"China": "CHN", "USA": "USA", "United States": "USA",
            "Russia": "RUS", "South Korea": "KOR", "Korea": "KOR",
            "Japan": "JPN", "Vietnam": "VNM", "Iran": "IRN",
            "Thailand": "THA", "Singapore": "SGP", "Taiwan": "TWN",
            "Ukraine": "UKR", "Germany": "GER", "Romania": "ROU",
            "Hungary": "HUN", "Poland": "POL", "Canada": "CAN",
            "UK": "UNK", "United Kingdom": "UNK", "France": "FRA",
            "Italy": "ITA", "Belarus": "BLR", "Kazakhstan": "KAZ",
            "India": "IND", "Australia": "AUS", "Brazil": "BRA",
            "Turkey": "TUR", "Israel": "ISR", "Serbia": "SRB",
            "Bulgaria": "BGR", "North Korea": "PRK", "Peru": "PER",
            "Croatia": "HRV", "Hong Kong": "HKG", "Mexico": "MEX",
            "Indonesia": "IDN", "Slovakia": "SVK", "Czech Republic": "CZE",
            "Netherlands": "NLD", "Moldova": "MDA", "Georgia": "GEO",
            "Armenia": "ARM", "Azerbaijan": "AZE", "Mongolia": "MNG",
            "Malaysia": "MYS", "Philippines": "PHL", "Bangladesh": "BGD",
            "Sweden": "SWE", "Norway": "NOR", "Switzerland": "SUI",
            "Austria": "AUT", "Argentina": "ARG", "Colombia": "COL",
            "Saudi Arabia": "SAU", "Syria": "SYR"}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z ]", "", s.lower()).strip()


def name_keys(full: str) -> set[str]:
    toks = norm(full).split()
    keys = {" ".join(toks)}
    if len(toks) >= 2:
        keys.add(" ".join(toks[::-1]))
        keys.add(" ".join([toks[-1]] + toks[:-1]))
        keys.add(" ".join(toks[1:] + [toks[0]]))
    return keys


def ordinal(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1:'st',2:'nd',3:'rd'}.get(n % 10, 'th')}"


# ── IMO ────────────────────────────────────────────────────────
def fetch_imo(years: list[int]) -> dict:
    """Return {year: [contestant dicts]}."""
    out = {}
    for y in years:
        url = f"https://www.imo-official.org/results/individual/year/{y}/"
        try:
            h = requests.get(url, headers=UA, timeout=30).text
        except Exception as e:  # noqa: BLE001
            print(f"  IMO {y}: fetch failed {e}")
            continue
        objs = re.findall(r'\{"participationId".*?\}', h)
        rows = []
        for o in objs:
            try:
                rows.append(json.loads(o))
            except json.JSONDecodeError:
                pass
        out[y] = rows
        print(f"  IMO {y}: {len(rows)} contestants")
        time.sleep(1.0)
    return out


# ── IOI ────────────────────────────────────────────────────────
def fetch_ioi(years: list[int]) -> dict:
    out = {}
    for y in years:
        url = f"https://stats.ioinformatics.org/results/{y}"
        try:
            h = requests.get(url, headers=UA, timeout=30).text
        except Exception as e:  # noqa: BLE001
            print(f"  IOI {y}: fetch failed {e}")
            continue
        rows = []
        for r in re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S):
            cells = [re.sub(r"<[^>]+>", "", c).strip()
                     for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
            if len(cells) >= 6 and cells and cells[0].isdigit():
                medal = cells[-1] if cells[-1] in ("Gold", "Silver", "Bronze") else ""
                rows.append({"rank": int(cells[0]), "name": cells[1],
                             "country": cells[2], "total": cells[-3],
                             "pct": cells[-2], "medal": medal})
        out[y] = rows
        print(f"  IOI {y}: {len(rows)} contestants")
        time.sleep(1.0)
    return out


# ── OpenAlex conservative author match ─────────────────────────
def oa_get(url: str, params: dict) -> dict | None:
    params = dict(params, mailto="boj@19pine.ai")
    if OA_KEY:
        params["api_key"] = OA_KEY
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=30)
            if r.status_code == 200:
                return r.json()
            time.sleep(2)
        except Exception:  # noqa: BLE001
            time.sleep(2)
    return None


MATH_CS = re.compile(r"math|computer|algorithm|machine learning|artificial|"
                     r"statistic|informati|software|data", re.I)


def oa_match(name: str, institution: str | None = None) -> dict | None:
    """Exact-name + dominance + field match. Returns enrichment dict or None."""
    j = oa_get("https://api.openalex.org/authors",
               {"search": name, "per_page": 5})
    time.sleep(0.13)
    if not j or not j.get("results"):
        return None
    cands = j["results"]
    keys = name_keys(name)
    exact = [c for c in cands if norm(c["display_name"]) in keys
             or any(norm(a) in keys for a in c.get("display_name_alternatives", []))]
    if institution:
        inst_l = norm(institution)
        exact = [c for c in exact if any(
            inst_l in norm(i.get("display_name", ""))
            for aff in c.get("affiliations", [])
            for i in [aff.get("institution", {})])]
    if not exact:
        return None
    top = exact[0]
    others = [c for c in cands if c["id"] != top["id"]]
    if not institution:  # name-only match needs dominance + field
        if others and top.get("cited_by_count", 0) < 2 * max(
                o.get("cited_by_count", 0) for o in others):
            return None
        topics = " ".join(t.get("display_name", "")
                          for t in top.get("topics", [])[:5])
        if not MATH_CS.search(topics):
            return None
    if top.get("works_count", 0) < 3:
        return None
    aid = top["id"].rsplit("/", 1)[-1]
    w = oa_get("https://api.openalex.org/works",
               {"filter": f"author.id:{aid}", "sort": "cited_by_count:desc",
                "per_page": 3, "select": "title,publication_year,primary_location"})
    time.sleep(0.13)
    works = []
    for it in (w or {}).get("results", []):
        if not it.get("title"):
            continue
        venue = ((it.get("primary_location") or {}).get("source") or {}).get(
            "display_name") or ""
        t = " ".join(it["title"].split()[:12])
        works.append(f"'{t}' ({venue + ', ' if venue else ''}{it.get('publication_year', '')})")
    affs = []
    for aff in top.get("affiliations", [])[:3]:
        i = aff.get("institution", {}).get("display_name")
        yrs = aff.get("years", [])
        if i:
            affs.append(f"{i}" + (f" ({min(yrs)}–{max(yrs)})" if yrs else ""))
    return {"openalex_id": top["id"], "display_name": top["display_name"],
            "works": works, "affiliations": affs,
            "works_count": top.get("works_count", 0)}


def wiki_intro(title: str) -> str | None:
    try:
        r = requests.get(
            "https://en.wikipedia.org/api/rest_v1/page/summary/"
            + requests.utils.quote(title.replace(" ", "_")),
            headers=UA, timeout=20)
        if r.status_code == 200:
            ex = r.json().get("extract", "")
            return " ".join(ex.split())[:700] or None
    except Exception:  # noqa: BLE001
        pass
    return None


def main() -> None:
    pe = json.loads((REPO / "data/inputs/pilot_entities.json").read_text())
    ents = [e for e in pe if e["cohort"] in CRED_COHORTS]
    print(f"{len(ents)} credential entities")

    wl = {}
    with open(REPO / "experiments/t1_4_wikipedia/wikipedia_lookup.csv") as f:
        for row in csv.DictReader(f):
            if row["has_wikipedia"] == "1" and row["title_matched"]:
                wl[row["entity_id"]] = row["title_matched"]

    noi_roster = {}
    with open(REPO / "experiments/t5_3_noi_medal_tiers/inputs/noi2009_roster.csv") as f:
        for row in csv.DictReader(f):
            noi_roster[row["name"]] = row

    imo_years = sorted({e["credential_year"] for e in ents
                        if e["cohort"] == "imo_gold" and e["credential_year"]})
    ioi_years = sorted({e["credential_year"] for e in ents
                        if e["cohort"] == "ioi_gold" and e["credential_year"]})
    span = lambda ys: list(range(min(ys) - 3, max(ys) + 3)) if ys else []
    print("Fetching IMO years", span(imo_years))
    imo = fetch_imo(span(imo_years))
    print("Fetching IOI years", span(ioi_years))
    ioi = fetch_ioi(span(ioi_years))

    # index IMO by (year, country, name-key); and by contestantId for multi-year
    imo_idx, imo_by_cid = {}, {}
    for y, rows in imo.items():
        for c in rows:
            full = f"{c['name']} {c['surname']}".strip()
            for k in name_keys(full):
                imo_idx[(y, c["countryCode"], k)] = c
            imo_by_cid.setdefault(c.get("contestantId"), []).append((y, c))

    ioi_idx = {}
    for y, rows in ioi.items():
        for c in rows:
            for k in name_keys(c["name"]):
                ioi_idx[(y, norm(c["country"]), k)] = c

    gold_out, report = {}, []
    ckpt = HERE / "inputs" / "gold_v2_credentials.json"
    for n_done, e in enumerate(ents):
        eid, name, coh = e["id"], e["name"], e["cohort"]
        year = e.get("credential_year")
        country = e.get("credential_country") or ""
        facts, official, conf = [], False, "medium"
        # strip han characters for pinyin-han combined names
        latin_name = re.sub(r"\s*[（(][^)）]*[)）]", "", name).strip()

        if coh == "imo_gold" and year:
            c3 = COUNTRY3.get(country, "")
            hit = None
            for k in name_keys(latin_name):
                hit = imo_idx.get((year, c3, k))
                if hit:
                    break
            if hit:
                official, conf = True, "high"
                # no edition ordinal: IMO was not held in 1980, so year-based
                # ordinals are off by one after 1980 and a wrong ordinal in
                # the gold would penalize correct responses
                facts.append(
                    f"{name} represented {country} at the International "
                    f"Mathematical Olympiad {year}, winning a "
                    f"gold medal with a total score of {hit['total']}/42 "
                    f"(rank {hit['rank']}).")
                for oy, oc in sorted(imo_by_cid.get(hit.get("contestantId"), [])):
                    if oy != year and oc.get("award"):
                        facts.append(
                            f"They also competed at IMO {oy}, winning a "
                            f"{oc['award']} medal (score {oc['total']}/42).")
        elif coh == "ioi_gold" and year:
            hit = None
            for k in name_keys(latin_name):
                hit = ioi_idx.get((year, norm(country), k))
                if hit:
                    break
            if hit:
                official, conf = True, "high"
                facts.append(
                    f"{name} represented {country} at the International "
                    f"Olympiad in Informatics {year}, winning a gold medal "
                    f"with rank {hit['rank']} and a score of {hit['total']} points.")
        elif coh in ("noi_china_gold", "cmo_china_gold", "cpho_china_first_prize"):
            comp = {"noi_china_gold": "National Olympiad in Informatics (NOI)",
                    "cmo_china_gold": "China Mathematical Olympiad (CMO)",
                    "cpho_china_first_prize":
                        "Chinese Physics Olympiad (CPhO)"}[coh]
            tier = ("first prize" if coh == "cpho_china_first_prize"
                    else "gold medal")
            base = f"{name} won a {tier} at the {year} {comp}"
            school = e.get("credential_school")
            han = re.search(r"[（(]([^)）]*)[)）]", name)
            r = noi_roster.get(han.group(1)) if (han and coh == "noi_china_gold") else None
            if r:
                official, conf = True, "high"
                facts.append(base + f", representing {r['school']} as a "
                             f"{ {'高一':'first-year','高二':'second-year','高三':'third-year'}.get(r['grade'], r['grade']) } "
                             f"high-school student, scoring {r['score']} points "
                             f"(rank {r['rank']} nationally).")
            else:
                if school:
                    base += f", representing {school}"
                if e.get("credential_score"):
                    base += f", scoring {e['credential_score']}"
                if e.get("credential_province"):
                    base += f" ({e['credential_province']} province)"
                facts.append(base + ".")
                conf = "high" if (school or e.get("credential_score")) else "medium"
        elif coh == "putnam_fellow" and year:
            facts.append(
                f"{name} was a Putnam Fellow in {year}: one of the top five "
                f"individual scorers of the William Lowell Putnam Mathematical "
                f"Competition that year.")
            conf = "high"  # roster membership is from the official listing
        elif coh == "icpc_world_finals_gold" and year:
            uni = re.sub(r"^.*winning team from ", "", e.get("context", ""))
            facts.append(
                f"{name} was a member of the team from {uni} that won the "
                f"{year} ICPC World Finals (gold medal), the premier "
                f"collegiate programming championship.")
            conf = "high"
        elif coh == "rhodes_scholar" and year:
            m = re.search(r"from (.+)$", e.get("context", ""))
            inst = m.group(1) if m else ""
            facts.append(
                f"{name} was elected a {year} {country or 'American'} Rhodes "
                f"Scholar{f' from {inst}' if inst else ''}, funding "
                f"postgraduate study at the University of Oxford.")
            conf = "high"
        elif coh == "msra_phd_fellowship" and year:
            uni = e.get("credential_university", "")
            facts.append(
                f"{name} received the {year} Microsoft Research Asia PhD "
                f"Fellowship while a PhD student"
                + (f" at {uni}" if uni else "") + ".")
            conf = "high"

        # enrichment: Wikipedia then OpenAlex
        enrich_src = []
        if eid in wl:
            intro = wiki_intro(wl[eid])
            if intro:
                sents = re.split(r"(?<=[.!?]) ", intro)[:4]
                facts.append(" ".join(sents))
                enrich_src.append(f"wikipedia:{wl[eid]}")
        if len(" ".join(facts).split()) < 90:
            inst_filter = e.get("credential_university") \
                if coh == "msra_phd_fellowship" else None
            m = oa_match(latin_name, inst_filter)
            if m:
                s = f"{name} is a researcher"
                if m["affiliations"]:
                    s += f" affiliated with {m['affiliations'][0]}"
                    if len(m["affiliations"]) > 1:
                        s += f" (previously {m['affiliations'][1]})"
                s += "."
                facts.append(s)
                if m["works"]:
                    facts.append("Their published works include "
                                 + ", ".join(m["works"][:3]) + ".")
                enrich_src.append(f"openalex:{m['openalex_id']}")

        gold = " ".join(facts)
        # an official record (medal + score + rank) is >=3 beyond-context
        # facts even when short; thin means metadata-skeleton only
        thin = (not official and len(gold.split()) < 45) or not facts
        gold_out[eid] = {"gold": gold, "source": "official+enrich",
                         "source_ref": ";".join(
                             (["official"] if official else []) + enrich_src),
                         "confidence": conf, "thin_gold": thin,
                         "official_record": official}
        report.append({"entity_id": eid, "cohort": coh,
                       "matched": int(official or bool(enrich_src)),
                       "confidence": conf,
                       "official": int(official),
                       "enrich": ";".join(enrich_src),
                       "words": len(gold.split())})
        if (n_done + 1) % 50 == 0:
            ckpt.write_text(json.dumps(gold_out, ensure_ascii=False, indent=1))
            print(f"  {n_done+1}/{len(ents)}")

    ckpt.write_text(json.dumps(gold_out, ensure_ascii=False, indent=1))
    with open(HERE / "outputs" / "match_report_credentials.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(report[0].keys()))
        w.writeheader()
        w.writerows(report)
    import collections
    stats = collections.Counter((r["cohort"], r["confidence"]) for r in report)
    for k in sorted(stats):
        print(k, stats[k])
    print("official-record hits:",
          sum(r["official"] for r in report), "/", len(report))
    print("thin golds:", sum(1 for g in gold_out.values() if g["thin_gold"]))


if __name__ == "__main__":
    main()
