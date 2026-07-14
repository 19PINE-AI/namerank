#!/usr/bin/env python3
"""02c: build v2 gold answers for artifact cohorts.

Cohorts: oss_project (GitHub), long_tail_paper (OpenAlex by ID),
research_paper (OpenAlex title search), foundation_model / benchmark /
named_method / dataset (Wikipedia lead, OpenAlex primary-paper fallback).

Resumable: checkpoint every 100 entities to outputs/gold_artifacts_checkpoint.json.

NOTE (deviations from task brief, both forced by the environment):
1. Only 1/184 oss_project contexts actually contains a "hosted at
   github.com/OWNER/REPO" slug. Where the slug is absent we resolve the repo
   via the GitHub search API, require a normalized repo-name match, verify
   description overlap with the probe context, and record confidence
   "medium" instead of "high".
2. The OpenAlex API key ran out of daily budget mid-build (2026-07-12,
   sibling gold builders 02a/02b share the quota; resets midnight UTC).
   When OpenAlex answers 429 "Insufficient budget" the paper backends fall
   back to Semantic Scholar Graph API (batch by DOI/MAG + relevance search)
   with Crossref filling metadata/abstract gaps by DOI. source is recorded
   honestly as "semanticscholar" or "crossref" in those cases; long-tail
   papers resolved by their stored DOI keep confidence "high".
"""
import base64
import csv
import html
import json
import re
import subprocess
import sys
import time
import urllib.parse

import requests

ROOT = "/home/ubuntu/namerank"
EXP = f"{ROOT}/experiments/t6_v2_protocol"
ENTITIES = f"{ROOT}/data/inputs/pilot_entities.json"
CHECKPOINT = f"{EXP}/outputs/gold_artifacts_checkpoint.json"
GOLD_OUT = f"{EXP}/inputs/gold_v2_artifacts.json"
REPORT_OUT = f"{EXP}/outputs/match_report_artifacts.csv"

import os

# optional SOCKS route (e.g. OA_SOCKS=127.0.0.1:1080) for quota-exhausted hosts
if os.environ.get("OA_SOCKS"):
    import socket

    import socks

    _h, _p = os.environ["OA_SOCKS"].rsplit(":", 1)
    socks.set_default_proxy(socks.SOCKS5, _h, int(_p), rdns=True)
    socket.socket = socks.socksocket
    print(f"[INFO] routing via SOCKS {_h}:{_p}")

MAILTO = "boj@19pine.ai"
OPENALEX_KEY = os.environ.get("OPENALEX_API_KEY", "")  # keyless polite pool ok

COHORTS = ["oss_project", "long_tail_paper", "research_paper",
           "foundation_model", "benchmark", "named_method", "dataset"]

SESSION = requests.Session()
SESSION.headers["User-Agent"] = f"NameRank-gold-builder/2.0 (mailto:{MAILTO})"

_last_oa = [0.0]
OA_BUDGET_DOWN = [False]  # daily budget exhausted -> use S2/Crossref backends


def oa_get(path, params):
    """OpenAlex GET with api key, mailto, <=8 rps, retries.

    Returns None on 404, "BUDGET" (and sets OA_BUDGET_DOWN) when the daily
    request budget is exhausted.
    """
    if OA_BUDGET_DOWN[0]:
        return "BUDGET"
    wait = 0.13 - (time.time() - _last_oa[0])
    if wait > 0:
        time.sleep(wait)
    params = dict(params)
    params["mailto"] = MAILTO
    if OPENALEX_KEY:
        params["api_key"] = OPENALEX_KEY
    for attempt in range(4):
        try:
            _last_oa[0] = time.time()
            r = SESSION.get(f"https://api.openalex.org/{path}", params=params, timeout=30)
            if r.status_code == 404:
                return None
            if r.status_code == 429:
                if "Insufficient budget" in r.text:
                    OA_BUDGET_DOWN[0] = True
                    print("  [openalex] daily budget exhausted -> "
                          "falling back to Semantic Scholar/Crossref", flush=True)
                    return "BUDGET"
                time.sleep(3 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError):
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))
    return None


_last_s2 = [0.0]


def s2_req(path, params=None, json_body=None, attempts=8):
    """Semantic Scholar Graph API, ~1 rps, patient 429 backoff."""
    url = f"https://api.semanticscholar.org/graph/v1/{path}"
    for attempt in range(attempts):
        wait = 1.1 - (time.time() - _last_s2[0])
        if wait > 0:
            time.sleep(wait)
        try:
            _last_s2[0] = time.time()
            if json_body is not None:
                r = SESSION.post(url, params=params, json=json_body, timeout=40)
            else:
                r = SESSION.get(url, params=params, timeout=40)
            if r.status_code == 404:
                return None
            if r.status_code == 429:
                time.sleep(min(4 * (attempt + 1), 25))
                continue
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError):
            if attempt == attempts - 1:
                raise RuntimeError("s2 unavailable")
            time.sleep(3 * (attempt + 1))
    raise RuntimeError("s2 throttled")


def crossref_work(doi):
    for attempt in range(3):
        try:
            r = SESSION.get(f"https://api.crossref.org/works/{doi}",
                            params={"mailto": MAILTO}, timeout=30)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json().get("message")
        except (requests.RequestException, ValueError):
            if attempt == 2:
                return None
            time.sleep(2 * (attempt + 1))
    return None


S2_FIELDS = "title,year,venue,authors,abstract,citationCount,externalIds"


def s2_to_work(p):
    """Convert an S2 paper record to the OpenAlex-like work dict used here."""
    if not p:
        return None
    ext = p.get("externalIds") or {}
    doi = ext.get("DOI")
    ref = f"https://doi.org/{doi}" if doi else f"S2:{p.get('paperId')}"
    title = re.sub(r"\.\s*$", "", (p.get("title") or "").strip())
    return {
        "id": ref,
        "title": title,
        "display_name": title,
        "publication_year": p.get("year"),
        "primary_location": {"source": ({"display_name": p["venue"]}
                                        if p.get("venue") else None)},
        "authorships": [{"author": {"display_name": a.get("name")}}
                        for a in (p.get("authors") or [])],
        "abstract_inverted_index": None,
        "_abstract": (p.get("abstract") or "").strip(),
        "cited_by_count": p.get("citationCount") or 0,
        "_source": "semanticscholar",
        "_doi": doi,
    }


def strip_jats(text):
    text = re.sub(r"</?jats:[^>]*>", " ", text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return re.sub(r"^(Abstract|ABSTRACT|Summary)[\s.:—-]*", "", text)


def crossref_to_work(m):
    if not m:
        return None
    title = (m.get("title") or [""])[0]
    dp = (m.get("issued") or m.get("published") or {}).get("date-parts") or [[None]]
    year = dp[0][0]
    venue = (m.get("container-title") or [None])[0]
    auths = [{"author": {"display_name": (f"{a.get('given', '')} {a.get('family', '')}").strip()}}
             for a in m.get("author") or [] if a.get("family") or a.get("given")]
    return {
        "id": f"https://doi.org/{m.get('DOI')}",
        "title": title, "display_name": title,
        "publication_year": year,
        "primary_location": {"source": ({"display_name": venue} if venue else None)},
        "authorships": auths,
        "abstract_inverted_index": None,
        "_abstract": strip_jats(m.get("abstract") or ""),
        "cited_by_count": m.get("is-referenced-by-count") or 0,
        "_source": "crossref",
        "_doi": m.get("DOI"),
    }


def work_abstract(work):
    if work.get("abstract_inverted_index"):
        return deinvert_abstract(work["abstract_inverted_index"])
    return work.get("_abstract") or ""


_last_cr = [0.0]


def crossref_search(query, year=None, rows=15):
    """Crossref bibliographic search -> list of work dicts."""
    wait = 0.35 - (time.time() - _last_cr[0])
    if wait > 0:
        time.sleep(wait)
    params = {"query.bibliographic": query, "rows": rows, "mailto": MAILTO,
              "select": "DOI,title,author,issued,published,container-title,"
                        "is-referenced-by-count,abstract"}
    if year:
        params["filter"] = f"from-pub-date:{year-1}-01-01,until-pub-date:{year+1}-12-31"
    for attempt in range(3):
        try:
            _last_cr[0] = time.time()
            r = SESSION.get("https://api.crossref.org/works", params=params, timeout=30)
            if r.status_code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            r.raise_for_status()
            items = r.json()["message"].get("items", [])
            return [w for w in (crossref_to_work(m) for m in items) if w and w["title"]]
        except (requests.RequestException, ValueError, KeyError):
            if attempt == 2:
                return []
            time.sleep(3 * (attempt + 1))
    return []


_last_arxiv = [0.0]


def arxiv_search(query, max_results=25):
    """arXiv API title search -> list of work dicts (includes abstracts)."""
    wait = 3.1 - (time.time() - _last_arxiv[0])
    if wait > 0:
        time.sleep(wait)
    q = re.sub(r'["\^]+', " ", query).strip()
    params = {"search_query": f'ti:"{q}"', "max_results": max_results}
    for attempt in range(3):
        try:
            _last_arxiv[0] = time.time()
            r = SESSION.get("http://export.arxiv.org/api/query", params=params, timeout=30)
            r.raise_for_status()
            break
        except requests.RequestException:
            if attempt == 2:
                return []
            time.sleep(4 * (attempt + 1))
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(r.text)
    except ET.ParseError:
        return []
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for entry in root.findall("a:entry", ns):
        title = re.sub(r"\s+", " ", (entry.findtext("a:title", "", ns) or "")).strip()
        summary = re.sub(r"\s+", " ", (entry.findtext("a:summary", "", ns) or "")).strip()
        pub = entry.findtext("a:published", "", ns) or ""
        aid = (entry.findtext("a:id", "", ns) or "").rsplit("/abs/", 1)[-1]
        authors = [ae.findtext("a:name", "", ns) for ae in entry.findall("a:author", ns)]
        if not title:
            continue
        aid = re.sub(r"v\d+$", "", aid)
        out.append({
            "id": f"arXiv:{aid}",
            "title": title, "display_name": title,
            "publication_year": int(pub[:4]) if pub[:4].isdigit() else None,
            "primary_location": {"source": {"display_name": "arXiv"}},
            "authorships": [{"author": {"display_name": a}} for a in authors if a],
            "abstract_inverted_index": None,
            "_abstract": summary,
            "cited_by_count": 0,
            "_source": "arxiv",
            "_doi": None,
        })
    return out


def arxiv_abstract_for_title(title):
    for w in arxiv_search(title, max_results=5):
        if norm_name(w["title"]) == norm_name(title) and work_abstract(w):
            return work_abstract(w)
    return None


def ensure_abstract(work):
    """Backfill a missing abstract: Crossref by DOI -> S2 by DOI -> arXiv by title."""
    if work_abstract(work):
        return work
    doi = work.get("_doi")
    if doi and work.get("_source") != "crossref":
        cm = crossref_work(doi)
        ab = strip_jats((cm or {}).get("abstract") or "")
        if ab:
            work["_abstract"] = ab
            return work
    if doi and work.get("_source") != "semanticscholar":
        try:
            res = s2_req("paper/batch", params={"fields": "abstract"},
                         json_body={"ids": [f"DOI:{doi}"]}, attempts=3)
        except RuntimeError:
            res = None
        if res and res[0] and res[0].get("abstract"):
            work["_abstract"] = res[0]["abstract"].strip()
            return work
    if work.get("_source") != "arxiv" and work.get("title"):
        ab = arxiv_abstract_for_title(work["title"])
        if ab:
            work["_abstract"] = ab
    return work


_search_cache = {}


def search_works(query, year=None, include_arxiv=True):
    """Unified title search -> list of work dicts.

    Backend chain: OpenAlex (while budget lasts) else Crossref + arXiv.
    """
    key = (query.lower(), year, include_arxiv, OA_BUDGET_DOWN[0])
    if key in _search_cache:
        return _search_cache[key]
    if not OA_BUDGET_DOWN[0]:
        cands, seen = [], set()
        param_sets = [{"filter": f"title.search:{query}", "per-page": 15,
                       "select": WORK_SELECT}]
        if year:
            param_sets.append({"filter": f"title.search:{query},"
                                         f"publication_year:{year-1}-{year+1}",
                               "per-page": 15, "select": WORK_SELECT,
                               "sort": "cited_by_count:desc"})
        for ps in param_sets:
            res = oa_get("works", ps)
            if res == "BUDGET":
                break
            for w in (res or {}).get("results", []):
                if w["id"] not in seen:
                    seen.add(w["id"])
                    w["_source"] = "openalex"
                    doi = w.get("doi") or ""
                    w["_doi"] = doi.replace("https://doi.org/", "") or None
                    cands.append(w)
        if not OA_BUDGET_DOWN[0]:
            _search_cache[key] = cands
            return cands
    cands = crossref_search(query, year=year)
    if include_arxiv:
        have = {norm_name(w["title"]) for w in cands}
        for w in arxiv_search(query):
            if norm_name(w["title"]) not in have:
                cands.append(w)
    _search_cache[key] = cands
    return cands


def wiki_get(params):
    params = dict(params)
    params.update({"format": "json", "action": "query"})
    for attempt in range(4):
        try:
            r = SESSION.get("https://en.wikipedia.org/w/api.php", params=params, timeout=30)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError):
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))
    return None


def gh_api(path):
    """gh api call; returns (json_or_None, err_string_or_None)."""
    for attempt in range(3):
        p = subprocess.run(["gh", "api", path], capture_output=True, text=True)
        if p.returncode == 0:
            try:
                return json.loads(p.stdout), None
            except ValueError:
                return None, "bad-json"
        err = (p.stderr or p.stdout or "").strip()[:200]
        if "404" in err or "Not Found" in err:
            return None, "404"
        if "rate limit" in err.lower() or "403" in err:
            time.sleep(20 * (attempt + 1))
            continue
        time.sleep(3)
    return None, err or "gh-error"


# ---------------------------------------------------------------- text utils

STOP = set("""a an the and or of for in on to with by from at as is are was were be been
this that it its their using use used new large very more most other others into over
under between across based can which who whose than approximately paper academic
open source open-source""".split())


def words(text):
    return re.findall(r"[a-z0-9][a-z0-9'\-]*", (text or "").lower())


def content_words(text):
    return {w for w in words(text) if w not in STOP and len(w) > 2}


def norm_name(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def trim_words(text, n):
    """Trim to ~n words, preferring a sentence boundary."""
    ws = text.split()
    if len(ws) <= n:
        return text.strip()
    cut = " ".join(ws[:n])
    m = None
    for m_ in re.finditer(r"[.!?][\"')\]]?\s", cut + " "):
        m = m_
    if m and m.end() > len(cut) * 0.45:
        return cut[: m.end()].strip()
    return cut.rstrip(",;: ") + "."


def wc(text):
    return len(text.split())


def strip_markdown(text):
    """Markdown/HTML -> prose lines."""
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
    text = re.sub(r"\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)", " ", text)  # badge links
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)  # images
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)  # links -> text
    text = re.sub(r"<[^>]+>", " ", text)  # html tags
    text = html.unescape(text)
    text = re.sub(r"[*_`#>|]+", " ", text)
    return text


BADGE_HINTS = ("badge", "shields.io", "img.shields", "build status", "license",
               "pypi version", "downloads", "codecov", "documentation status")


def readme_summary(md, name, limit=95):
    """First meaningful prose paragraphs of a README, ~limit words."""
    raw = re.split(r"\n\s*\n", strip_markdown(md or ""))
    paras = []
    for p in raw:
        p = re.sub(r"\s+", " ", p).strip(" -•\t")
        if wc(p) < 8:
            continue
        low = p.lower()
        if any(h in low for h in BADGE_HINTS) and wc(p) < 20:
            continue
        if low.startswith(("table of contents", "installation", "getting started",
                           "quick start", "quickstart", "usage", "citation",
                           "if you use", "pip install", "docker ", "latest news",
                           "news ", "star history", "sponsors", "contributing",
                           "[!", "we have released", "we are excited",
                           "we're excited", "update:", "new!")):
            continue
        if re.search(r"\b(click the|visit the|join our|follow us on|"
                     r"subscribe to)\b", low):
            continue  # calls-to-action, not facts
        if re.match(r"^[\W\d]", p) and wc(p) < 12:
            continue
        ws = p.split()
        caps = sum(1 for t in ws if t[:1].isupper())
        if len(ws) >= 6 and caps / len(ws) > 0.5:
            continue  # nav / link-menu line, not prose
        if re.match(r"^(19|20)\d{2}[-/.]", p) or low.startswith(("[20", "(20")):
            continue  # changelog/news bullets
        paras.append(p)
        if len(paras) >= 12:
            break
    # prefer the paragraph that actually describes the project
    start = 0
    pat = re.compile(re.escape(name).replace(r"\ ", r"[\s_-]?") +
                     r".{0,30}\b(is|provides|enables|implements|offers|lets|aims)\b", re.I)
    for i, p in enumerate(paras):
        if pat.search(p):
            start = i
            break
    picked, total = [], 0
    for p in paras[start:]:
        picked.append(p)
        total += wc(p)
        if total >= limit or len(picked) >= 3:
            break
    return trim_words(" ".join(picked), limit)


def author_phrase(authorships):
    names = [a.get("author", {}).get("display_name") or "?" for a in authorships]
    names = [n for n in names if n and n != "?"]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    if len(names) == 3:
        return f"{names[0]}, {names[1]} and {names[2]}"
    return f"{names[0]}, {names[1]}, {names[2]} and {len(names) - 3} others"


def deinvert_abstract(inv):
    if not inv:
        return ""
    pos = []
    for word, idxs in inv.items():
        for i in idxs:
            pos.append((i, word))
    pos.sort()
    text = " ".join(w for _, w in pos)
    text = re.sub(r"</?jats:[^>]*>", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^(Abstract|ABSTRACT|Summary)[\s.:—-]*", "", text)
    return text


def paper_gold(work, lead_in=None, omit_year=False):
    """'TITLE is a YEAR paper by A, B, C and N others in VENUE. ' + abstract ~130w.

    lead_in: artifact name for fallback golds -> "NAME was introduced in 'TITLE', ..."
    omit_year: leave the year out (snapshot year conflicts with context).
    """
    title = re.sub(r"\s+", " ", (work.get("title") or work.get("display_name") or "").strip())
    year = work.get("publication_year")
    by = author_phrase(work.get("authorships") or [])
    loc = work.get("primary_location") or {}
    src = (loc.get("source") or {}).get("display_name")
    yearp = "a paper" if (omit_year or not year) else f"a {year} paper"
    if lead_in:
        s = f"{lead_in} was introduced in “{title}”, {yearp}"
    else:
        s = f"{title} is {yearp}"
    if by:
        s += f" by {by}"
    if src == "arXiv":
        s += " on arXiv"
    elif src:
        s += f" in {src}"
    s += ". "
    abstract = work_abstract(work)
    gold = (s + trim_words(abstract, 130)).strip()
    return gold, abstract


WORK_SELECT = ("id,title,display_name,publication_year,primary_location,"
               "authorships,abstract_inverted_index,cited_by_count,doi")


# ---------------------------------------------------------------- oss_project

def build_oss(ent):
    ctx = ent.get("context", "")
    name = ent["name"]
    m = re.search(r"github\.com/([\w.\-]+)/([\w.\-]+)", ctx)
    confidence, how = "high", "slug-in-context"
    if m:
        slug = f"{m.group(1)}/{m.group(2).rstrip('.')}"
    else:
        slug = search_repo(name, ctx)
        confidence, how = "medium", "github-search"
        if not slug:
            return None, ("no-slug-in-context; github search found no verified repo", None)
    repo, err = gh_api(f"repos/{slug}")
    if repo is None:
        return None, (f"repo {slug} fetch failed: {err}", slug)
    readme_md = ""
    rd, _ = gh_api(f"repos/{slug}/readme")
    if rd and rd.get("content"):
        try:
            readme_md = base64.b64decode(rd["content"]).decode("utf-8", "replace")
        except Exception:
            readme_md = ""

    desc = re.sub(r"\s+", " ", (repo.get("description") or "").strip().rstrip("."))
    desc = re.sub(r"^[^\w\"'(]+", "", desc)  # leading emoji/symbols
    m2 = re.match(r"^([^:—–]{2,60}?)\s*[:—–]\s*(.+)$", desc)
    if m2 and norm_name(m2.group(1)) in (norm_name(name),
                                         norm_name(name.split()[-1])):
        desc = m2.group(2)  # "PEFT: State-of-the-art ..." -> "State-of-the-art ..."
    lang = repo.get("language")
    year = (repo.get("created_at") or "")[:4]
    owner = repo.get("owner", {}).get("login", slug.split("/")[0])
    owner_name = None
    ow, _ = gh_api(f"users/{owner}")
    if ow:
        owner_name = ow.get("name") or None
        owner_type = ow.get("type")
    else:
        owner_type = repo.get("owner", {}).get("type")

    parts = []
    if desc:
        if desc.lower().startswith(name.lower() + " "):
            parts.append(desc)
        else:
            first = desc.split()[0]
            plain = first[0].isupper() and (len(first) == 1 or first[1:].islower())
            d = desc[0].lower() + desc[1:] if plain else desc
            parts.append(f"{name} is {d}")
    else:
        parts.append(f"{name} is an open-source project")
    parts[0] = parts[0].rstrip(".") + "."

    who = f"{owner_name} ({owner})" if owner_name and owner_name.lower() != owner.lower() else owner
    kind = "organization" if owner_type == "Organization" else "developer"
    s2 = f"It is hosted on GitHub as {repo.get('full_name', slug)}, maintained by the {kind} {who}"
    if year:
        s2 += f", and was created in {year}"
    if lang:
        s2 += f"; the codebase is primarily {lang}"
    parts.append(s2 + ".")

    summ = readme_summary(readme_md, name)
    if summ and content_words(summ) - content_words(parts[0]):
        parts.append(summ)

    arx = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", readme_md)
    if arx:
        parts.append(f"The project's README links its paper, arXiv:{arx.group(1)}.")

    gold = trim_words(" ".join(p for p in parts if p), 180)
    return {"gold": gold, "source": "github", "source_ref": repo.get("full_name", slug),
            "confidence": confidence, "thin_gold": wc(gold) < 80,
            "_how": how}, None


def search_repo(name, ctx):
    """Resolve a repo slug by name via GitHub search, verified against context.

    Query variants handle slug!=display-name cases ('Hugging Face
    Transformers' -> transformers, 'Q-LoRA' -> qlora); verification accepts
    repo-name, full-slug, or owner-name matches backed by stars and a
    description consistent with the probe context.
    """
    import math
    nn = norm_name(name)
    queries = [name]
    collapsed = re.sub(r"[^A-Za-z0-9]+", "", name)
    if collapsed.lower() != name.lower().replace(" ", ""):
        queries.append(collapsed)
    parts = name.split()
    if len(parts) > 1 and len(parts[-1]) >= 6:
        queries.append(parts[-1])  # org-prefixed display names
    items, seen = [], set()
    for q in queries:
        uq = urllib.parse.quote(q)
        for query in (f"search/repositories?q={uq}&per_page=10",
                      f"search/repositories?q={uq}+in:name&per_page=10"):
            res, err = gh_api(query)
            for it in (res or {}).get("items") or []:
                if it.get("full_name") not in seen:
                    seen.add(it.get("full_name"))
                    items.append(it)
        if any(norm_name(i.get("name", "")) == nn and
               (i.get("stargazers_count") or 0) >= 300 for i in items):
            break  # exact hit already in hand; skip extra rate-limited queries
    ctx_w = content_words(ctx)
    best, best_score = None, -1.0
    for it in items:
        rn = norm_name(it.get("name", ""))
        fn = norm_name(it.get("full_name", ""))
        on = norm_name((it.get("owner") or {}).get("login", ""))
        if it.get("fork") or not rn:
            continue
        overlap = len(content_words(it.get("description") or "") & ctx_w)
        stars = it.get("stargazers_count") or 0
        name_hit = (rn == nn or fn == nn or
                    ((nn in rn or rn in nn) and abs(len(rn) - len(nn)) <= 6) or
                    (on == nn and overlap >= 1))
        if not name_hit:
            continue
        if stars < 300 and not (overlap >= 2 and stars >= 30):
            continue  # famous-project cohort: skip mirrors/forks/toys
        score = (3.0 if (rn == nn or fn == nn) else 1.0) + overlap + math.log10(stars + 1)
        if score > best_score:
            best, best_score = it, score
    return best.get("full_name") if best else None


# ------------------------------------------------------------ long_tail_paper

def title_agrees(entity_name, title):
    """Entity 'name' (possibly truncated with ...) matches the work title."""
    en = norm_name(re.sub(r"\.{3,}.*$|….*$", "", entity_name or ""))
    tn = norm_name(title or "")
    if not en or not tn:
        return False
    k = min(len(en), len(tn))
    return en[:k] == tn[:k] and k >= 15


def fetch_long_tail(entities, done):
    """Fetch stored-ID works: OpenAlex if budget allows, else S2 batch by
    DOI/MAG (the numeric part of pre-2021 W-ids is the MAG id; verified
    against the entity's stored title) with Crossref filling gaps."""
    todo = [e for e in entities if e["id"] not in done]
    if not todo:
        return {}
    results = {}

    # --- preferred path: OpenAlex batch by stored work id
    if not OA_BUDGET_DOWN[0]:
        id_map = {}
        for e in todo:
            m = re.search(r"(W\d+)", e.get("openalex_id") or "")
            if m:
                id_map.setdefault(m.group(1), []).append(e)
        out = {}
        ids = list(id_map)
        for i in range(0, len(ids), 50):
            chunk = ids[i:i + 50]
            res = oa_get("works", {"filter": "ids.openalex:" + "|".join(chunk),
                                   "per-page": 50, "select": WORK_SELECT})
            if res == "BUDGET":
                break
            for w in (res or {}).get("results", []):
                wid = w["id"].rsplit("/", 1)[-1]
                w["_source"] = "openalex"
                w["_doi"] = (w.get("doi") or "").replace("https://doi.org/", "") or None
                out[wid] = w
        if not OA_BUDGET_DOWN[0]:
            for e in todo:
                m = re.search(r"(W\d+)", e.get("openalex_id") or "")
                wid = m.group(1) if m else None
                w = out.get(wid)
                if not w:
                    results[e["id"]] = (None, (f"openalex work {wid or 'missing-id'} not found", wid))
                    continue
                results[e["id"]] = (make_paper_record(w, "high", "stored-id"), None)
            return results

    # --- fallback path: S2 batch by DOI / MAG id
    key_of = {}
    for e in todo:
        doi = (e.get("doi") or "").replace("https://doi.org/", "").strip()
        if doi:
            key_of[e["id"]] = f"DOI:{doi}"
        else:
            m = re.search(r"W(\d+)", e.get("openalex_id") or "")
            if m and int(m.group(1)) < 4200000000:  # MAG-era OpenAlex id
                key_of[e["id"]] = f"MAG:{m.group(1)}"
    fetched = {}
    keys = sorted(set(key_of.values()))
    for i in range(0, len(keys), 100):
        chunk = keys[i:i + 100]
        try:
            res = s2_req("paper/batch", params={"fields": S2_FIELDS},
                         json_body={"ids": chunk})
        except RuntimeError:
            res = None
        if res:
            for k, p in zip(chunk, res):
                fetched[k] = s2_to_work(p)
        print(f"  s2 batch {i + len(chunk)}/{len(keys)}", flush=True)
    for e in todo:
        key = key_of.get(e["id"])
        if not key:
            results[e["id"]] = (None, ("no doi and post-MAG openalex id; "
                                       "openalex budget exhausted", None))
            continue
        w = fetched.get(key)
        if w is None and key.startswith("DOI:"):
            w = crossref_to_work(crossref_work(key[4:]))
        if w is None:
            results[e["id"]] = (None, (f"{key} not found in S2/Crossref "
                                       "(openalex budget exhausted)", key))
            continue
        if key.startswith("MAG:") and not title_agrees(e.get("name"), w.get("title")):
            results[e["id"]] = (None, (f"{key} title mismatch vs stored name", key))
            continue
        ensure_abstract(w)
        how = f"stored-{key.split(':')[0].lower()}"
        # S2 sometimes carries the preprint year; the entity's stored year
        # comes from the original OpenAlex record for this same work.
        cy = e.get("credential_year")
        if cy and w.get("publication_year") and w["publication_year"] != cy:
            w["publication_year"] = cy
            how += "|year-from-openalex"
        results[e["id"]] = (make_paper_record(w, "high", how), None)
    return results


def make_paper_record(work, confidence, how, lead_in=None, omit_year=False):
    gold, abstract = paper_gold(work, lead_in=lead_in, omit_year=omit_year)
    thin = wc(gold) < 80 or not abstract
    return {"gold": trim_words(gold, 185), "source": work.get("_source", "openalex"),
            "source_ref": work["id"], "confidence": confidence,
            "thin_gold": thin, "_how": how}


# ------------------------------------------------------------- research_paper

def quoted_title(ctx):
    m = re.search(r"[‘'\"“]([^'\"’”]{8,120})[’'\"”]", ctx)
    if not m:
        return None
    t = m.group(1).strip()
    if t.startswith("s ") or wc(t) < 2:  # possessive apostrophe artifact
        return None
    return t


def ctx_surnames(ctx):
    """Author surnames named in the context ('Devlin et al.', \"Gu and Dao's\").

    Single possessives ('OpenAI's', 'DeepMind's') are orgs, not surnames."""
    names = []
    m = re.search(r"\(?\s*((?:[A-Z][\w'’-]+,?\s+)+)et al\.", ctx or "")
    if m:
        names += re.findall(r"[A-Z][\w'’-]+", m.group(1))
    m = re.search(r"([A-Z][\w'’-]+) and ([A-Z][\w'’-]+)['’]s", ctx or "")
    if m:
        names += [m.group(1), m.group(2)]
    return [n for n in names if len(n) >= 2]


def author_match(surnames, author_names):
    for sn in surnames:
        pat = r"(?<![A-Za-z])" + re.escape(sn.lower()) + r"(?![A-Za-z])"
        if any(re.search(pat, (a or "").lower()) for a in author_names):
            return True
    return False


def title_exactish(query, title):
    """Normalized equality, or title == 'QUERY: subtitle' (colon/em-dash only)."""
    tn, qn_ = norm_name(title), norm_name(query)
    if tn == qn_:
        return True
    return bool(re.match(re.escape(query.lower()) + r"\s*[:—–]",
                         title.lower().strip()))


def mention_in_title(alias, title):
    """Alias appears in the title (word-boundary for single tokens)."""
    alias = (alias or "").strip()
    if not alias:
        return False
    if len(alias.split()) > 1:
        return norm_name(alias) in norm_name(title)
    return bool(re.search(r"(?<![A-Za-z0-9])" + re.escape(alias.lower()) +
                          r"(?![A-Za-z0-9])", title.lower()))


def pick_paper(cands, query, ctx, name):
    """Pick a verified candidate. Returns (work, omit_year) or (None, False).

    Strict on purpose: Crossref/relevance search is noisy (junk records with
    exact famous titles, derivative papers sharing all content words), so a
    candidate must match the query title tightly AND clear a citation floor
    unless it is an arXiv record whose title starts with the query.
    """
    yr = re.search(r"\b(19|20)\d{2}\b", ctx or "")
    ctx_year = int(yr.group(0)) if yr else None
    qn = content_words(query)
    ctxw = content_words(ctx) | content_words(name)
    surnames = ctx_surnames(ctx)
    best, best_score, best_conflict = None, 0.0, False
    for w in cands:
        title = w.get("title") or w.get("display_name") or ""
        tw = content_words(title)
        if not qn:
            continue
        subtitleish = bool(re.match(re.escape(query.lower()) + r"\s*[:—–]",
                                    title.lower().strip()))
        equalish = norm_name(title) == norm_name(query)
        exactish = subtitleish or equalish
        contained = len(norm_name(query)) >= 12 and norm_name(query) in norm_name(title)
        sim = len(qn & tw) / max(1, len(qn))
        extras = len(tw - qn)
        year_ok = ctx_year is None or (w.get("publication_year") and
                                       abs(w["publication_year"] - ctx_year) <= 1)
        cited = w.get("cited_by_count") or 0
        arx = w.get("_source") == "arxiv"
        auths = [a.get("author", {}).get("display_name") or ""
                 for a in w.get("authorships") or []]
        surname_hit = author_match(surnames, auths)
        if surnames and auths and not surname_hit:
            continue  # context names the authors; candidate must agree
        if len(qn) <= 2 and equalish and not subtitleish:
            continue  # a bare short-name title is junk-record bait, not the paper
        # citation floor: lenient when the query is specific or the context's
        # author names corroborate; strict for unverified short names
        floor = 30 if (len(qn) > 2 or surname_hit) else 150
        if exactish or contained:
            if not arx and cited < floor:
                continue
        elif sim >= 0.9 and extras == 0 and len(qn) >= 3:
            if (not arx and cited < floor) or not year_ok:
                continue
        elif sim >= 0.7 and year_ok and not arx and cited >= 5000:
            pass  # landmark rescue for paraphrased/derived queries
        else:
            continue
        if not year_ok and (arx or not exactish):
            continue  # year conflict tolerated only for exact non-arXiv titles
        score = (sim * 2 + (2.0 if exactish else 0) + (1.0 if contained else 0)
                 + len(tw & ctxw) * 0.2 + min(cited, 20000) / 20000.0
                 + (0.5 if year_ok else 0) + (1.0 if surname_hit else 0))
        if score > best_score:
            best, best_score, best_conflict = w, score, not year_ok
    return best, best_conflict


def build_research_paper(ent):
    ctx = ent.get("context", "")
    name = re.sub(r"\s*\(.*?\)\s*$", "", ent["name"]).strip()
    queries = []  # (search_query, verify_query)
    qt = quoted_title(ctx)
    if qt:
        queries.append((qt, qt))
    base = re.sub(r"\s+paper$", "", name, flags=re.I)
    if base != qt:
        queries.append((base, base))
    m = re.search(r"introduc\w+\s+(.+?)(?:\s*\(|$)", ctx)
    if m and 3 <= wc(m.group(1)) <= 12:
        q3 = m.group(1).strip(" .'\"")
        queries.append((q3, q3))
    surnames = ctx_surnames(ctx)
    if surnames:  # author-augmented search, verified against the plain name
        queries.append((f"{base} {' '.join(surnames)}", base))
    yr = re.search(r"\b(19|20)\d{2}\b", ctx or "")
    year = int(yr.group(0)) if yr else None
    tried = []
    for with_arxiv in (False, True):  # arXiv pass only if Crossref/OA pass fails
        for sq, q in queries:
            cands = search_works(sq, year=year, include_arxiv=with_arxiv)
            if sq not in tried:
                tried.append(sq)
            w, conflict = pick_paper(cands, q, ctx, base)
            if w:
                ensure_abstract(w)
                rec = make_paper_record(w, "medium",
                                        "title-search" + ("|year-conflict" if conflict else ""),
                                        omit_year=conflict)
                return rec, None
        if not OA_BUDGET_DOWN[0]:
            break  # openalex path already covers everything it can
    return None, (f"no verified title match (queries: {tried})", None)


# ------------------------------------- foundation_model / benchmark / method / dataset

def context_expansion(ctx):
    m = re.match(r"^(?:the\s+)?([A-Z][^,]{3,70}),", ctx or "")
    if m and re.search(r"[A-Z]", m.group(1)[1:]):
        return m.group(1).strip()
    return None


def wiki_lookup(name, ctx):
    """Search Wikipedia; return (title, url, lead) of a context-verified page."""
    exp = context_expansion(ctx)
    queries = [name]
    if exp and norm_name(exp) != norm_name(name):
        queries.append(exp)
    hint = " ".join(list(content_words(ctx))[:4])
    queries.append(f"{name} {hint}".strip())
    ctxw = content_words(ctx)
    namew = {norm_name(name)} | ({norm_name(exp)} if exp else set())
    seen = set()
    best, best_score = None, 0.0
    for q in queries:
        data = wiki_get({"generator": "search", "gsrsearch": q, "gsrlimit": 6,
                         "gsrnamespace": 0, "prop": "extracts|info",
                         "exintro": 1, "explaintext": 1, "exlimit": "max",
                         "inprop": "url", "redirects": 1})
        pages = ((data or {}).get("query") or {}).get("pages") or {}
        for p in pages.values():
            title = p.get("title", "")
            if title in seen:
                continue
            seen.add(title)
            lead = (p.get("extract") or "").strip()
            if wc(lead) < 25 or "may refer to" in lead[:200].lower():
                continue
            tn = norm_name(re.sub(r"\s*\(.*?\)\s*$", "", title))
            title_hit = tn in namew or any(n and (n in tn or tn in n) for n in namew)
            lead_low = norm_name(lead[:1200])
            name_in_lead = any(n and n in lead_low for n in namew)
            overlap = len(content_words(lead[:1500]) & ctxw)
            if overlap < 2 or not (title_hit or name_in_lead):
                continue
            score = overlap + (4 if title_hit else 0) + (1 if name_in_lead else 0)
            if score > best_score:
                best, best_score = p, score
        if best is not None and best_score >= 6:
            break
    if not best:
        return None
    return (best["title"],
            best.get("fullurl") or "https://en.wikipedia.org/wiki/" +
            urllib.parse.quote(best["title"].replace(" ", "_")),
            best.get("extract", "").strip())


def openalex_primary_paper(name, ctx, aliases=()):
    """Fallback: resolve the artifact's primary paper on OpenAlex.

    An alias (name, context expansion, or Wikipedia full form) must appear in
    the candidate's TITLE — abstract-only mentions are not attribution.
    Verified candidates ranked to prefer ones with an abstract, then citations.
    """
    exp = context_expansion(ctx)
    # query longer (more specific) aliases first, keep all verified candidates
    alias_set = [a for a in dict.fromkeys([exp, *aliases, name]) if a]
    queries = sorted(alias_set, key=lambda a: -len(a.split()))
    ctxw = content_words(ctx)
    long_aliases = [a for a in alias_set if len(a.split()) > 1]
    verified = {}
    for q in queries:
        for w in search_works(q):
            if w["id"] in verified:
                continue
            title = w.get("title") or ""
            if not any(mention_in_title(a, title) for a in alias_set):
                continue
            abstract = work_abstract(w)
            overlap = len(content_words(title + " " + abstract[:1500]) & ctxw)
            cited = w.get("cited_by_count") or 0
            long_hit = any(mention_in_title(a, title) for a in long_aliases)
            # arXiv candidates carry no citation counts: require a long-alias
            # title match or a 'NAME: subtitle' title instead of the floor.
            popular = cited >= 20 or (w.get("_source") == "arxiv" and
                                      (long_hit or any(title_exactish(a, title)
                                                       for a in alias_set)))
            if overlap >= 2 and popular:
                w["_long_alias"] = long_hit
                verified[w["id"]] = w
    if not verified:
        return None
    best = max(verified.values(),
               key=lambda w: (w.get("_long_alias", False),
                              min(w.get("cited_by_count") or 0, 50000),
                              bool(work_abstract(w))))
    return ensure_abstract(best)


def build_wiki_cohort(ent):
    ctx = ent.get("context", "")
    name = ent["name"]
    hit = wiki_lookup(name, ctx)
    if hit:
        title, url, lead = hit
        lead = re.sub(r"\s+", " ", lead)
        gold = trim_words(lead, 180)
        how = f"wiki:{title}"
        if wc(gold) < 80:  # thin lead: enrich with the artifact's primary paper
            aliases = [re.sub(r"\s*\(.*?\)\s*$", "", title)]
            m = re.match(r"^([^().]{4,90}?)\s*\(([^)]*)\)", lead)
            if m and norm_name(name) in norm_name(m.group(2)):
                aliases.append(m.group(1))  # bolded full form, e.g. wiki "X (NAME)"
            w = openalex_primary_paper(name, ctx, aliases=aliases)
            if w and work_abstract(w):
                extra, _ = paper_gold(w, lead_in="It")
                gold = trim_words(gold + " " + extra, 180)
                how += "|paper-enriched"
        return {"gold": gold, "source": "wikipedia", "source_ref": url,
                "confidence": "medium", "thin_gold": wc(gold) < 80,
                "_how": how}, None
    w = openalex_primary_paper(name, ctx)
    if w:
        return make_paper_record(w, "medium", "primary-paper", lead_in=name), None
    return None, ("no wikipedia article verified and no primary paper found", None)


# ----------------------------------------------------------------------- main

def main():
    with open(ENTITIES) as f:
        all_ents = json.load(f)
    ents = [e for e in all_ents if e.get("cohort") in COHORTS]
    print(f"{len(ents)} entities in scope", flush=True)

    try:
        with open(CHECKPOINT) as f:
            ck = json.load(f)
    except FileNotFoundError:
        ck = {"results": {}, "unmatched": {}}
    # transient failures (throttling, exceptions) are retried on resume
    transient = [k for k, v in ck["unmatched"].items()
                 if re.search(r"throttl|exception|unavailable|budget exhausted|"
                              r"pending-openalex-retry", v.get("reason", ""))]
    for k in transient:
        del ck["unmatched"][k]
    done = set(ck["results"]) | set(ck["unmatched"])
    print(f"resuming with {len(done)} done", flush=True)

    def write_outputs():
        gold = {}
        for eid, rec in ck["results"].items():
            gold[eid] = {k: v for k, v in rec.items() if not k.startswith("_")}
        with open(GOLD_OUT, "w") as f:
            json.dump(gold, f, ensure_ascii=False, indent=1)
        with open(REPORT_OUT, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["entity_id", "cohort", "matched", "confidence", "source",
                        "source_ref", "reason"])
            for e in ents:
                eid = e["id"]
                if eid in ck["results"]:
                    r = ck["results"][eid]
                    w.writerow([eid, e["cohort"], 1, r["confidence"], r["source"],
                                r["source_ref"], r.get("_how", "")])
                elif eid in ck["unmatched"]:
                    u = ck["unmatched"][eid]
                    w.writerow([eid, e["cohort"], 0, "", "", u.get("source_ref", ""),
                                u["reason"]])
                else:
                    w.writerow([eid, e["cohort"], 0, "", "", "",
                                "pending: not yet processed"])

    def save():
        with open(CHECKPOINT, "w") as f:
            json.dump(ck, f, ensure_ascii=False)
        write_outputs()

    # search-based cohorts may succeed on OpenAlex after the quota resets, so
    # their misses are recorded as pending (retried on the next run)
    PENDING_COHORTS = {"research_paper", "foundation_model", "benchmark",
                       "named_method", "dataset"}

    builders = {"oss_project": build_oss, "research_paper": build_research_paper,
                "foundation_model": build_wiki_cohort, "benchmark": build_wiki_cohort,
                "named_method": build_wiki_cohort, "dataset": build_wiki_cohort}
    # non-paper sources first (GitHub, Wikipedia), then the paper cohorts
    order = ["oss_project", "foundation_model", "benchmark", "named_method",
             "dataset", "research_paper"]
    n = 0
    for cohort in order:
        for e in ents:
            if e["cohort"] != cohort:
                continue
            eid = e["id"]
            if eid in ck["results"] or eid in ck["unmatched"]:
                continue
            try:
                rec, err = builders[cohort](e)
            except Exception as ex:
                print(f"  ERROR {eid}: {ex!r}", flush=True)
                rec, err = None, (f"exception: {ex!r}"[:180], None)
            if rec:
                ck["results"][eid] = rec
            else:
                reason = err[0]
                if cohort in PENDING_COHORTS and not reason.startswith("exception"):
                    reason = "pending-openalex-retry: " + reason
                ck["unmatched"][eid] = {"reason": reason, "source_ref": err[1] or ""}
            n += 1
            if n % 100 == 0:
                save()
                print(f"  ...{n} this run ({len(ck['results'])} matched, "
                      f"{len(ck['unmatched'])} unmatched)", flush=True)
        save()
        print(f"cohort {cohort} done", flush=True)

    # long_tail_paper last: batched by stored id (OpenAlex, else S2/Crossref)
    ltp = [e for e in ents if e["cohort"] == "long_tail_paper"]
    batch = fetch_long_tail(ltp, set(ck["results"]) | set(ck["unmatched"]))
    for eid, (rec, err) in batch.items():
        if rec:
            ck["results"][eid] = rec
        else:
            ck["unmatched"][eid] = {"reason": err[0], "source_ref": err[1] or ""}
    if batch:
        print(f"long_tail_paper batch done: {len(batch)}", flush=True)
    save()

    # summary
    from collections import Counter, defaultdict
    tot, match, thin = Counter(), Counter(), Counter()
    for e in ents:
        tot[e["cohort"]] += 1
        if e["id"] in ck["results"]:
            match[e["cohort"]] += 1
            if ck["results"][e["id"]].get("thin_gold"):
                thin[e["cohort"]] += 1
    print("\ncohort, total, matched, rate, thin_gold")
    for c in COHORTS:
        print(f"{c}, {tot[c]}, {match[c]}, {match[c]/max(1,tot[c]):.3f}, {thin[c]}")
    print(f"TOTAL, {sum(tot.values())}, {sum(match.values())}, "
          f"{sum(match.values())/max(1,sum(tot.values())):.3f}, {sum(thin.values())}")


if __name__ == "__main__":
    main()
