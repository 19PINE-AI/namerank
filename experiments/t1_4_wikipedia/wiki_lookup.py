"""Bulk Wikipedia / Wikidata / Pageviews lookup for NameRank pilot entities.

For each entity, attempts to identify its English Wikipedia article (if any),
its Wikidata sitelink count, and 30-day pageviews. Disambiguation uses the
entity's `context` field to confirm a candidate page actually describes the
intended entity (e.g. BERT-the-language-model vs. Bert-the-Muppet).

Outputs:
  wikipedia_lookup.json   {entity_id: {has_wikipedia, title_matched, qid,
                                       sitelinks, pageviews_30d, method, notes}}
  wikipedia_lookup.csv    flattened
"""
from __future__ import annotations

import csv
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock

ROOT = Path("/home/ubuntu/namerank")
OUT = ROOT / "experiments" / "t1_4_wikipedia"
OUT.mkdir(parents=True, exist_ok=True)
CACHE = OUT / "wikipedia_lookup.json"

USER_AGENT = "NameRankExperiment/1.0 (academic research; contact: boj@19pine.ai)"
HEADERS = {"User-Agent": USER_AGENT}

PV_END = (datetime.utcnow().date() - timedelta(days=2))
PV_START = PV_END - timedelta(days=29)


STOP = set(
    "a an and the of in on at for to with by from is was as or but not this that these those "
    "his her its their he she they we you who whom which whose what when where why how an "
    "approximately about academic researcher member faculty named gold medal medalist "
    "representing language model artifact entity person".split()
)


def context_tokens(text: str) -> list[str]:
    """Extract content tokens from an entity's context string."""
    if not text:
        return []
    toks = re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", text)
    return [t.lower() for t in toks if t.lower() not in STOP and len(t) > 2]


# Cohort-specific extra confirmation keywords. Required: at least one of these
# (or institution / context-specific tokens) must appear in the candidate's
# extract for confirmation.
COHORT_HINTS: dict[str, list[str]] = {
    "long_tail_researcher_openalex": ["researcher", "scientist", "professor", "academic", "phd"],
    "long_tail_researcher_ikp": ["researcher", "scientist", "professor", "academic"],
    "cs_faculty": ["computer", "professor", "faculty", "associate", "assistant", "researcher"],
    "imo_gold": ["mathematician", "olympiad", "mathematical", "imo", "mathematics"],
    "cmo_china_gold": ["mathematician", "olympiad", "mathematical", "mathematics"],
    "cpho_china_first_prize": ["physicist", "olympiad", "physics"],
    "noi_china_gold": ["informatics", "computer", "olympiad", "programming"],
    "ioi_gold": ["informatics", "computer", "olympiad", "programming"],
    "icpc_world_finals_gold": ["programming", "competitive", "computer", "icpc"],
    "putnam_fellow": ["mathematician", "mathematics", "putnam"],
    "rhodes_scholar": ["rhodes", "scholar", "scholarship", "oxford"],
    "msra_phd_fellowship": ["researcher", "scientist", "phd", "fellow", "microsoft", "computer"],
    "gpt5_system_card_author": ["openai", "researcher", "scientist", "ai"],
    "deepseek_v3_author": ["deepseek", "researcher", "scientist"],
    "foundation_model": ["model", "language", "ai", "artificial", "neural", "openai", "anthropic",
                         "google", "meta", "mistral"],
    "ai_startup_or_company": ["company", "startup", "founded", "ai", "artificial"],
    "ai_hardware": ["chip", "processor", "hardware", "ai", "company"],
    "named_method": ["algorithm", "method", "machine", "learning", "neural"],
    "benchmark": ["benchmark", "evaluation", "dataset", "test"],
    "dataset": ["dataset", "data", "benchmark", "training"],
    "conference": ["conference", "academic", "annual"],
    "database_or_data_system": ["database", "system", "data"],
    "oss_project": ["software", "open", "source", "project", "library"],
    "programming_language": ["programming", "language"],
    "research_paper": ["paper", "research", "article", "published"],
    "long_tail_paper": ["paper", "research", "article", "published"],
    "mid_tier_writer": ["author", "writer", "novelist", "journalist", "book"],
    "mid_tier_book": ["book", "novel", "published", "author"],
    "mid_tier_actor": ["actor", "actress", "film", "television", "movie"],
    "mid_tier_athlete": ["athlete", "sport", "player", "olympic", "champion"],
    "mid_tier_artist": ["artist", "painter", "sculptor", "art"],
    "mid_tier_musician": ["musician", "singer", "band", "album", "song"],
    "mid_tier_filmmaker": ["director", "filmmaker", "film", "movie"],
    "mid_tier_politician": ["politician", "minister", "senator", "elected", "government"],
    "mid_tier_historical": ["born", "died", "century", "history"],
    "mid_tier_journalist": ["journalist", "reporter", "newspaper", "magazine"],
    "mid_tier_chef": ["chef", "cook", "restaurant", "cuisine"],
    "mid_tier_comedian": ["comedian", "comedy", "comic"],
    "mid_tier_architect": ["architect", "architecture", "building", "designed"],
    "mid_tier_vc": ["venture", "investor", "capital", "firm"],
    "mid_tier_founder": ["founder", "co-founder", "founded", "company", "ceo"],
    "mid_tier_yc_company": ["company", "startup", "founded"],
    "mid_tier_podcast": ["podcast", "podcaster", "show"],
    "mid_tier_medical": ["doctor", "physician", "medical", "surgeon"],
    "mid_tier_religious": ["religious", "pastor", "rabbi", "imam", "bishop", "minister"],
    "mid_tier_activist": ["activist", "movement", "advocacy"],
    "mid_tier_oss_maintainer": ["software", "developer", "open", "source", "engineer"],
    "mid_tier_product": ["product", "service", "company"],
    "mid_tier_gov_ai_policy": ["government", "policy", "official"],
    "mid_tier_online_course": ["course", "online", "instructor", "education"],
    "industry_product": ["product", "service", "company"],
    "website_or_service": ["website", "service", "online"],
    "award": ["award", "prize", "honor"],
    "reference_pilot": [],
}


def http_get(url: str, retries: int = 4, timeout: int = 30):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                code = r.getcode()
                body = r.read()
                if code == 200:
                    return json.loads(body)
                last = f"HTTP {code}"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None  # no such page (pageviews returns 404 when no data)
            last = f"HTTPError {e.code}"
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
        time.sleep(0.5 * (2 ** attempt))
    return {"__error__": last}


def fetch_page(title: str) -> dict | None:
    """Get pageid/title/qid/extract for an exact-title lookup. Returns None if missing."""
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "pageprops|info|extracts|categories",
        "redirects": 1,
        "inprop": "url",
        "exintro": 1,
        "explaintext": 1,
        "exsentences": 4,
        "cllimit": 20,
    }
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    data = http_get(url)
    if not data or "__error__" in (data or {}):
        return None
    pages = data.get("query", {}).get("pages", {})
    for pid, p in pages.items():
        if pid == "-1":
            return None
        # Skip disambiguation pages — they don't represent a single entity
        cats = [c.get("title", "") for c in p.get("categories", [])]
        if any("disambiguation" in c.lower() for c in cats):
            return {"__disambig__": True, "title": p.get("title")}
        return {
            "title": p.get("title"),
            "qid": p.get("pageprops", {}).get("wikibase_item"),
            "extract": (p.get("extract") or "")[:1500],
            "shortdesc": p.get("pageprops", {}).get("wikibase-shortdesc", ""),
            "categories": cats,
        }
    return None


def wiki_search(query: str, limit: int = 3) -> list[str]:
    params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": query,
        "srlimit": limit,
        "srprop": "snippet",
    }
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    data = http_get(url)
    if not data or "__error__" in (data or {}):
        return []
    return [h["title"] for h in data.get("query", {}).get("search", [])]


def fetch_sitelinks(qid: str) -> int | None:
    url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
    data = http_get(url)
    if not data or "__error__" in (data or {}):
        return None
    ent = data.get("entities", {}).get(qid, {})
    return len(ent.get("sitelinks", {}))


def fetch_pageviews(title: str) -> int | None:
    enc = urllib.parse.quote(title.replace(" ", "_"), safe="")
    url = (
        f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        f"en.wikipedia/all-access/all-agents/{enc}/daily/"
        f"{PV_START.strftime('%Y%m%d')}/{PV_END.strftime('%Y%m%d')}"
    )
    data = http_get(url)
    if data is None:
        return 0  # 404 = no pageview data
    if "__error__" in (data or {}):
        return None
    return sum(item.get("views", 0) for item in data.get("items", []))


def _ascii_fold(s: str) -> str:
    import unicodedata
    # NFD normalize then drop combining marks; keep base letters
    nfkd = unicodedata.normalize("NFKD", s)
    out = []
    for ch in nfkd:
        if unicodedata.category(ch) == "Mn":
            continue
        # Map common non-ASCII letters that have no NFKD decomp
        out.append(ch)
    s2 = "".join(out)
    # Handle a few extras (Turkish, Polish, etc.)
    repl = {"ı": "i", "İ": "I", "ø": "o", "Ø": "O", "ł": "l", "Ł": "L",
            "ß": "ss", "æ": "ae", "Æ": "AE", "œ": "oe", "Œ": "OE",
            "đ": "d", "Đ": "D", "ð": "d", "Ð": "D", "þ": "th", "Þ": "Th"}
    return "".join(repl.get(c, c) for c in s2)


def name_overlap(name: str, title: str) -> tuple[float, int]:
    """(fraction, count) of name tokens that appear in title (case-insensitive,
    ASCII-folded so diacritic variants match)."""
    name_f = _ascii_fold(name)
    title_f = _ascii_fold(title)
    nt = [t for t in re.findall(r"[A-Za-z][A-Za-z0-9\-]+", name_f) if len(t) >= 2]
    if not nt:
        return 0.0, 0
    tl = title_f.lower()
    hits = sum(1 for t in nt if t.lower() in tl)
    return hits / len(nt), hits


# Person-style cohorts: a Wikipedia page must have a title that contains the
# person's family name (otherwise search frequently returns unrelated articles
# that happen to mention an institution).
PERSON_COHORTS = {
    "imo_gold", "cmo_china_gold", "cpho_china_first_prize", "noi_china_gold", "ioi_gold",
    "icpc_world_finals_gold", "putnam_fellow", "rhodes_scholar", "msra_phd_fellowship",
    "long_tail_researcher_openalex", "long_tail_researcher_ikp", "cs_faculty",
    "gpt5_system_card_author", "deepseek_v3_author", "reference_pilot",
    "mid_tier_writer", "mid_tier_actor", "mid_tier_athlete", "mid_tier_artist",
    "mid_tier_musician", "mid_tier_filmmaker", "mid_tier_politician",
    "mid_tier_historical", "mid_tier_journalist", "mid_tier_chef", "mid_tier_comedian",
    "mid_tier_architect", "mid_tier_vc", "mid_tier_founder", "mid_tier_podcast",
    "mid_tier_medical", "mid_tier_religious", "mid_tier_activist",
    "mid_tier_oss_maintainer", "mid_tier_gov_ai_policy",
}


def confirms(extract: str, shortdesc: str, name: str, ctx: str, cohort: str,
             institution: str = "", title: str = "") -> tuple[bool, str]:
    """Decide if the candidate page describes the intended entity.

    Two-stage check:
      (a) Name-overlap: the page title must contain >=50% of the entity-name
          tokens (catches the BERT-vs-Bert and Fraser-Brown-vs-Alison-Fraser
          cases).  For artifact-style cohorts we relax this — many AI artifacts
          have stylized names that may be a substring of the page title.
      (b) Extract must mention some context hint (institution name, subfield
          token, cohort keyword).
    """
    text = (extract + " " + shortdesc).lower()
    if not text:
        return False, "no_extract"

    # --- (a) name-overlap gate ---
    ov, ov_hits = name_overlap(name, title or "")
    n_name_toks = len([t for t in re.findall(r"[A-Za-z][A-Za-z0-9\-]+", name) if len(t) >= 2])
    # For people: require >=2 matching tokens (so single-surname matches like
    # "Fraser Brown" -> "Alison Fraser" are rejected); single-token names need
    # an exact title match.
    if cohort in PERSON_COHORTS:
        if n_name_toks == 1:
            if (title or "").lower() != name.lower():
                return False, f"name_mismatch:single_tok:title={title!r}"
        else:
            if ov_hits < 2:
                return False, f"name_mismatch:ov={ov:.2f}:hits={ov_hits}:title={title!r}"
    # For artifacts: require the (folded) name be a substring of the (folded)
    # title — generic single-token overlap (e.g. shared "paper", "method") is
    # not enough.
    if cohort not in PERSON_COHORTS:
        name_f = _ascii_fold(name).lower()
        title_f = _ascii_fold(title or "").lower()
        if name_f not in title_f:
            return False, f"artifact_name_mismatch:title={title!r}"

    # --- (b) context confirmation ---
    ctx_toks = set(context_tokens(ctx))
    inst_toks = set(context_tokens(institution)) if institution else set()
    hits_ctx = [t for t in ctx_toks if t in text and len(t) >= 4]
    hits_inst = [t for t in inst_toks if t in text and len(t) >= 4]
    cohort_keys = COHORT_HINTS.get(cohort, [])
    hits_cohort = [k for k in cohort_keys if k in text]

    if hits_inst:
        return True, f"institution_match:{hits_inst[:3]}"
    if len(hits_ctx) >= 2:
        return True, f"context_match:{hits_ctx[:3]}"
    if hits_cohort and hits_ctx:
        return True, f"cohort+context:{hits_cohort[:2]}+{hits_ctx[:2]}"
    if len(hits_cohort) >= 2:
        return True, f"cohort_match:{hits_cohort[:3]}"
    # Single cohort-keyword match is enough for clearly-identifiable artifacts
    if cohort in {"programming_language", "foundation_model", "named_method", "benchmark",
                  "dataset", "oss_project", "conference", "database_or_data_system",
                  "ai_hardware", "research_paper", "long_tail_paper", "industry_product",
                  "website_or_service", "ai_startup_or_company", "award"} and hits_cohort:
        return True, f"cohort_match:{hits_cohort[:2]}"
    # For well-known people whose Wikipedia page title is an exact match of the
    # entity name, a 1-token context hit is enough.
    if cohort in PERSON_COHORTS and ov >= 0.9 and (hits_ctx or hits_cohort):
        return True, f"person_exact:ov={ov:.2f}:{(hits_ctx+hits_cohort)[:2]}"
    return False, f"no_match:ov={ov:.2f}"


def lookup_entity(ent: dict) -> dict:
    name = ent["name"]
    ctx = ent.get("context", "") or ""
    cohort = ent.get("cohort", "") or ""
    institution = ent.get("institution", "") or ""

    # Some entity names include trailing tags ("BERT paper", "...Technical
    # Report") or parenthesized aliases ("Sanmi Koyejo (...)"). Generate
    # cleaned variants for exact-title lookup.
    variants = [name]
    for suffix in (" paper", " Paper", " Technical Report", " technical report"):
        if name.endswith(suffix):
            variants.append(name[: -len(suffix)].strip())
            break
    paren = re.match(r"^([^(]+)\(([^)]+)\)\s*$", name)
    if paren:
        variants.append(paren.group(1).strip())
        variants.append(paren.group(2).strip())

    method = "exact"
    page = None
    name_for_check = name
    for cn in variants:
        page = fetch_page(cn)
        if page and "__disambig__" not in page:
            name_for_check = cn
            break
    candidate = None
    if page and "__disambig__" not in page:
        candidate = page
    # If exact missed or returned disambiguation page, fall back to search
    if candidate is None:
        method = "search"
        # Use a concise search query
        if institution and cohort in {"cs_faculty", "long_tail_researcher_openalex",
                                       "long_tail_researcher_ikp", "msra_phd_fellowship",
                                       "gpt5_system_card_author", "deepseek_v3_author"}:
            q = f"{name} {institution}"
        else:
            # Use cohort hints to constrain
            hints = COHORT_HINTS.get(cohort, [])[:2]
            q = f"{name} " + " ".join(hints) if hints else name
        titles = wiki_search(q, limit=3)
        for t in titles:
            p = fetch_page(t)
            if p and "__disambig__" not in p:
                candidate = p
                break

    if not candidate:
        return {"has_wikipedia": False, "title_matched": None, "qid": None,
                "sitelinks": 0, "pageviews_30d": 0, "method": method, "notes": "no_candidate"}

    confirmed, reason = confirms(
        candidate.get("extract", ""), candidate.get("shortdesc", ""),
        name_for_check, ctx, cohort, institution, title=candidate.get("title", "")
    )
    if not confirmed:
        # One more shot: search with context if we only did exact match
        if method == "exact":
            method = "search_after_exact"
            hints = COHORT_HINTS.get(cohort, [])[:2]
            q = f"{name} " + " ".join(hints) if hints else f"{name} {ctx[:60]}"
            if institution:
                q = f"{name} {institution}"
            titles = wiki_search(q, limit=3)
            for t in titles:
                if t == candidate["title"]:
                    continue
                p = fetch_page(t)
                if p and "__disambig__" not in p:
                    c2, r2 = confirms(p.get("extract",""), p.get("shortdesc",""),
                                       name_for_check, ctx, cohort, institution,
                                       title=p.get("title",""))
                    if c2:
                        candidate = p
                        confirmed, reason = True, r2
                        break
    if not confirmed:
        return {"has_wikipedia": False, "title_matched": candidate.get("title"),
                "qid": candidate.get("qid"), "sitelinks": 0, "pageviews_30d": 0,
                "method": method, "notes": f"unconfirmed:{reason}",
                "shortdesc": candidate.get("shortdesc", "")[:160]}

    title = candidate["title"]
    qid = candidate.get("qid")
    sl = fetch_sitelinks(qid) if qid else None
    pv = fetch_pageviews(title)
    return {
        "has_wikipedia": True, "title_matched": title, "qid": qid,
        "sitelinks": sl if sl is not None else 0,
        "pageviews_30d": pv if pv is not None else 0,
        "method": method, "notes": reason,
        "shortdesc": candidate.get("shortdesc", "")[:160],
    }


def main(workers: int = 4):
    ents = json.loads((ROOT / "data/inputs/pilot_entities.json").read_text())
    cache: dict[str, dict] = {}
    if CACHE.exists():
        try:
            cache = json.loads(CACHE.read_text())
        except Exception:
            cache = {}

    todo = [e for e in ents if e["id"] not in cache]
    print(f"Loaded {len(ents)} entities; cache has {len(cache)}; todo={len(todo)}", flush=True)

    lock = Lock()
    done = 0
    t0 = time.time()
    SAVE_EVERY = 100

    def work(ent):
        try:
            r = lookup_entity(ent)
        except Exception as e:
            r = {"has_wikipedia": False, "title_matched": None, "qid": None,
                 "sitelinks": 0, "pageviews_30d": 0, "method": "error",
                 "notes": f"exc:{type(e).__name__}:{e}"}
        return ent["id"], r

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(work, e) for e in todo]
        for fut in as_completed(futures):
            eid, r = fut.result()
            with lock:
                cache[eid] = r
                done += 1
                if done % 50 == 0 or done == len(todo):
                    rate = done / (time.time() - t0 + 0.001)
                    eta = (len(todo) - done) / rate if rate > 0 else 0
                    print(f"[{done}/{len(todo)}] rate={rate:.1f}/s eta={eta/60:.1f}min "
                          f"hits={sum(1 for v in cache.values() if v.get('has_wikipedia'))}",
                          flush=True)
                if done % SAVE_EVERY == 0:
                    CACHE.write_text(json.dumps(cache, indent=1))
    CACHE.write_text(json.dumps(cache, indent=1))
    print("Done. Total cached:", len(cache))

    # Flatten to CSV
    csv_path = OUT / "wikipedia_lookup.csv"
    ents_by_id = {e["id"]: e for e in ents}
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["entity_id", "entity_name", "cohort", "has_wikipedia",
                    "title_matched", "qid", "sitelinks", "pageviews_30d",
                    "method", "notes"])
        for eid, r in cache.items():
            e = ents_by_id.get(eid, {})
            w.writerow([eid, e.get("name", ""), e.get("cohort", ""),
                        int(bool(r.get("has_wikipedia"))),
                        r.get("title_matched") or "", r.get("qid") or "",
                        r.get("sitelinks") or 0, r.get("pageviews_30d") or 0,
                        r.get("method") or "", r.get("notes") or ""])
    print(f"Wrote {csv_path}")


if __name__ == "__main__":
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    main(workers=workers)
