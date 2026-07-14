#!/usr/bin/env python3
"""
02b_gold_wikipedia.py — build v2 Wikipedia-intro gold answers.

Cohorts: every mid_tier_* cohort plus ai_startup_or_company, conference,
award, programming_language, database_or_data_system, website_or_service,
ai_hardware, industry_product (~1,851 entities).

Title resolution priority:
  1. entity.wikidata_id -> Wikidata API -> enwiki sitelink   (confidence high)
  2. t1_4 wikipedia_lookup.csv rows with has_wikipedia=1     (confidence high)
  3. MediaWiki search, verified against the entity context   (confidence medium)
Unverified candidates are left unmatched (entity keeps its v1 gold).

Gold = the article's lead section (prop=extracts&exintro&explaintext),
trimmed to ~180 words at a sentence boundary, with reference markers /
pronunciation parentheticals stripped. No added commentary.

Resumable: checkpoints to outputs/checkpoint_wikipedia.json every 100 entities.

Outputs:
  inputs/gold_v2_wikipedia.json
  outputs/match_report_wikipedia.csv
"""

import csv
import json
import os
import re
import sys
import time
import unicodedata
from collections import Counter, OrderedDict

import requests

ROOT = "/home/ubuntu/namerank"
T6 = os.path.join(ROOT, "experiments/t6_v2_protocol")
ENTITIES_PATH = os.path.join(ROOT, "data/inputs/pilot_entities.json")
T14_PATH = os.path.join(ROOT, "experiments/t1_4_wikipedia/wikipedia_lookup.csv")
CHECKPOINT_PATH = os.path.join(T6, "outputs/checkpoint_wikipedia.json")
GOLD_OUT = os.path.join(T6, "inputs/gold_v2_wikipedia.json")
REPORT_OUT = os.path.join(T6, "outputs/match_report_wikipedia.csv")

USER_AGENT = "NameRank-v2-goldbuilder (boj@19pine.ai)"
WIKI_API = "https://en.wikipedia.org/w/api.php"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
MIN_INTERVAL = 0.13  # <10 req/s with headroom
CHECKPOINT_EVERY = 100

EXTRA_COHORTS = {
    "ai_startup_or_company", "conference", "award", "programming_language",
    "database_or_data_system", "website_or_service", "ai_hardware",
    "industry_product",
}

# ---------------------------------------------------------------- HTTP layer

_session = requests.Session()
_session.headers["User-Agent"] = USER_AGENT
_last_req = [0.0]


def api_get(url, params, tries=7):
    for attempt in range(tries):
        wait = MIN_INTERVAL - (time.time() - _last_req[0])
        if wait > 0:
            time.sleep(wait)
        _last_req[0] = time.time()
        try:
            r = _session.get(url, params=params, timeout=30)
        except requests.RequestException:
            if attempt == tries - 1:
                raise
            time.sleep(min(4 * 2 ** attempt, 90))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            retry_after = r.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                time.sleep(min(int(retry_after) + 1, 120))
            else:
                time.sleep(min(4 * 2 ** attempt, 90))
            continue
        r.raise_for_status()
        data = r.json()
        if "error" in data and data["error"].get("code") == "maxlag":
            time.sleep(5)
            continue
        return data
    raise RuntimeError(f"API kept failing: {url} {params}")


# ------------------------------------------------------------- text helpers

_ABBREV_END = re.compile(
    r"\b(?:Dr|Mr|Mrs|Ms|Prof|St|Jr|Sr|Gen|Col|Lt|Sgt|Rev|Fr|Mt|vs|etc|Inc"
    r"|Ltd|Corp|Co|No|Vol|Op|approx|ca|cf|al|Univ|Dept|est|Bros|Capt|Gov"
    r"|Sen|Rep|Hon|Messrs|Mmes|Assn|dist|min|max|[A-Z])\.$"
)
_DOTTED = re.compile(r"\b(?:[A-Za-z]\.){2,}$")  # U.S., Ph.D., a.k.a., J.K.


def split_sentences(text):
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(‘“])", text)
    merged = []
    for p in parts:
        if merged and (_ABBREV_END.search(merged[-1]) or _DOTTED.search(merged[-1])):
            merged[-1] = merged[-1] + " " + p
        else:
            merged.append(p)
    return [s.strip() for s in merged if s.strip()]


def clean_intro(text):
    """Strip reference markers and pronunciation debris; keep dates/facts."""
    t = text
    t = re.sub(r"\[\d+\]|\[citation needed\]|\[note \d+\]", "", t)
    # IPA leftovers and slash-delimited pronunciations
    t = re.sub(r"/[^/\n]{1,80}/[;,]?\s*", "", t)
    # explicit pronunciation segments inside parentheticals
    t = re.sub(r"\b(?:pronounced|pronunciation:?|IPA:?)[^;)]*[;)]",
               lambda m: ")" if m.group(0).endswith(")") else "", t)
    t = re.sub(r"\(?\s*listen\s*\)?[;,]?", "", t)
    # respellings like "dih-RAK" right after an open paren or semicolon
    t = re.sub(r"(?<=[(;])\s*[A-Za-z]+(?:-[A-Za-z]+)*-[A-Z]{2,}[A-Za-z-]*\s*[;,]?", "", t)
    # tidy parenthetical leftovers: "(, 8 August" / "(; born" / "( )"
    for _ in range(3):
        t = re.sub(r"\(\s*[;,]\s*", "(", t)
        t = re.sub(r"[;,]\s*\)", ")", t)
        t = re.sub(r"\(\s*\)", "", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\s+([.,;:!?)])", r"\1", t)
    t = re.sub(r"\(\s+", "(", t)
    return t.strip()


def trim_to_words(text, max_words=180):
    sents = split_sentences(text)
    out, wc = [], 0
    for s in sents:
        w = len(s.split())
        if out and wc + w > max_words:
            break
        out.append(s)
        wc += w
    return " ".join(out)


STOPWORDS = set("""a an the and or of in on at to for with by from as is are was
were be been being this that these those its it's his her their our your my he
she they we you i who whom whose which what when where why how not no nor so
too very s t just don should now known also both more most other some such only
own same than then once during before after above below up down out off over
under again further about against between into through""".split())

BOILER = set("""wikipedia page mid tier level recognition entity person named
notable individual""".split())


def fold(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower()


def squash(s):
    return re.sub(r"[^a-z0-9]", "", fold(s))


def name_tokens(s):
    return [t for t in re.split(r"[^a-z0-9]+", fold(s)) if t]


def clean_entity_name(name):
    """Strip any trailing parenthetical qualifier: 'Linear (product)',
    'Claude (the product)', 'S&P (Oakland)' -> 'Linear', 'Claude', 'S&P'."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()


def name_paren(name):
    """The trailing parenthetical of an entity name, if informative:
    'AI2 (Allen Institute)' -> 'Allen Institute'."""
    m = re.search(r"\(([^)]{3,})\)\s*$", name)
    if not m:
        return None
    p = re.sub(r"^the\s+", "", m.group(1).strip(), flags=re.I)
    if p.lower() in ("product", "company", "service", "band", "writer",
                     "person", "app", "software"):
        return None
    return p


COHORT_KW = {
    "mid_tier_activist": ["activist", "activism", "advocate", "advocacy", "rights", "campaign", "organizer"],
    "mid_tier_actor": ["actor", "actress", "film", "television", "series", "role", "comedian", "star"],
    "mid_tier_architect": ["architect", "architecture", "building", "design", "firm"],
    "mid_tier_artist": ["artist", "art", "paint", "sculpt", "photograph", "installation", "exhibit", "museum", "gallery"],
    "mid_tier_athlete": ["athlete", "player", "football", "basketball", "baseball", "tennis", "soccer", "olympic", "hockey", "golf", "runner", "swimmer", "cricket", "rugby", "racing", "boxer", "wrestl", "gymnast", "cyclist", "skier", "skater", "league", "nba", "nfl", "mlb", "sport", "champion", "team"],
    "mid_tier_book": ["novel", "book", "memoir", "author", "published", "fiction", "bestsell", "essay", "biography", "prize"],
    "mid_tier_chef": ["chef", "restaurant", "culinary", "cook", "michelin", "cuisine", "food"],
    "mid_tier_comedian": ["comedian", "comedy", "stand-up", "standup", "sketch", "actor", "actress", "humor"],
    "mid_tier_filmmaker": ["director", "filmmaker", "film", "screenwriter", "producer", "documentary", "cinema"],
    "mid_tier_founder": ["founder", "co-founder", "cofounder", "entrepreneur", "ceo", "executive", "businessman", "businesswoman", "company", "startup", "founded"],
    "mid_tier_gov_ai_policy": ["policy", "government", "official", "director", "administration", "white house", "advis", "professor", "institute", "regulat", "secretary", "commissioner", "senate", "congress", "agency", "minister", "researcher", "scientist", "technolog"],
    "mid_tier_historical": ["physicist", "scientist", "mathematician", "engineer", "inventor", "philosopher", "historian", "chemist", "biologist", "computer", "economist", "writer", "pioneer", "laureate", "professor", "psychologist", "programmer", "creator", "founder", "author"],
    "mid_tier_journalist": ["journalist", "reporter", "correspondent", "editor", "columnist", "writer", "news", "author", "commentator", "host"],
    "mid_tier_medical": ["physician", "doctor", "medicine", "medical", "surgeon", "epidemiolog", "health", "professor", "hospital", "clinical", "psychiatr"],
    "mid_tier_musician": ["musician", "singer", "songwriter", "band", "album", "music", "composer", "rapper", "guitarist", "pianist", "record", "dj"],
    "mid_tier_online_course": ["course", "university", "stanford", "mit", "lecture", "curriculum", "mooc", "taught", "education", "class"],
    "mid_tier_oss_maintainer": ["software", "developer", "programmer", "open-source", "open source", "engineer", "computer", "python", "javascript", "author", "scientist", "creator", "maintainer"],
    "mid_tier_podcast": ["podcast", "radio", "show", "host", "audio", "episode"],
    "mid_tier_politician": ["politician", "senator", "governor", "representative", "congress", "mayor", "minister", "parliament", "elected", "president", "legislat", "party"],
    "mid_tier_product": ["software", "app", "application", "product", "platform", "tool", "service", "company", "developed", "device", "launched", "web"],
    "mid_tier_religious": ["religious", "church", "pastor", "priest", "bishop", "rabbi", "imam", "theolog", "patriarch", "spiritual", "christian", "buddhis", "minister", "faith", "author", "psychologist"],
    "mid_tier_vc": ["venture", "investor", "capital", "partner", "invest", "firm", "entrepreneur", "businessman", "financier"],
    "mid_tier_writer": ["writer", "novelist", "author", "novel", "book", "poet", "fiction", "essay", "memoir", "journalist"],
    "mid_tier_yc_company": ["company", "startup", "y combinator", "founded", "software", "platform", "app", "service", "technology"],
    "ai_startup_or_company": ["company", "startup", "artificial intelligence", "ai", "lab", "founded", "subsidiary", "division", "institute", "organization", "organisation", "non-profit", "nonprofit"],
    "conference": ["conference", "symposium", "workshop", "meeting", "academic", "research", "annual", "proceedings"],
    "award": ["award", "prize", "fellowship", "medal", "honor", "honour", "grant", "awarded", "recognizes", "recognises"],
    "programming_language": ["programming language", "language", "compiler", "software", "developed", "syntax"],
    "database_or_data_system": ["database", "data", "storage", "query", "software", "open-source", "open source", "distributed", "engine", "format", "system"],
    "website_or_service": ["website", "web", "online", "service", "platform", "internet", "app"],
    "ai_hardware": ["gpu", "chip", "processor", "hardware", "accelerator", "semiconductor", "computing", "graphics", "microarchitecture", "tensor", "nvidia", "designed"],
    "industry_product": ["software", "product", "chatbot", "assistant", "model", "app", "platform", "service", "developed", "language model"],
}


PAREN_OK = set("""company inc corporation startup platform software app
application website ai technology product service journal magazine newsletter
conference band musician singer rapper actor actress writer author novel book
film director filmmaker politician athlete footballer basketball baseball
tennis golfer boxer chef comedian artist painter entrepreneur investor
executive activist podcast language database browser engine video game
character model agent chatbot engineer scientist academic professor physician
historian economist philosopher mathematician producer presenter journalist
broadcaster tool web series programming""".split())

CORP_SUFFIX = {"inc", "ltd", "llc", "corp", "corporation", "co", "company",
               "technologies", "labs", "systems", "software", "group",
               "holdings", "plc",
               # vendor/brand prefixes: "Parquet" -> "Apache Parquet"
               "apache", "amazon", "google", "microsoft", "meta", "ibm",
               "intel", "nvidia", "adobe", "mozilla", "apple", "twilio"}


def context_keywords(entity):
    ctx = fold(entity.get("context", ""))
    ctx = re.sub(r"\(mid-tier level of recognition\)", "", ctx)
    own = set(name_tokens(entity.get("name", "")))
    toks = [t for t in re.split(r"[^a-z0-9-]+", ctx) if len(t) >= 4
            and t not in STOPWORDS and t not in BOILER and t not in own]
    # also keep multiword hints as-is (whole context substring match is too
    # strict; token level is enough)
    return list(OrderedDict.fromkeys(toks))


def kw_hit(kw, text_f):
    """Word-boundary keyword match on folded text. Short keywords (<4 chars)
    must match a whole word ('ai' must not hit 'said'); longer ones may be
    prefixes ('regulat' hits 'regulatory')."""
    pat = r"\b" + re.escape(kw)
    if len(kw) < 4:
        pat += r"\b"
    return bool(re.search(pat, text_f))


def is_namelike_page(title, intro):
    """Surname / given-name index pages ('Bloom is a surname. Notable
    people...') must never be attached to a person."""
    if re.search(r"\((?:surname|given name|name)\)$", title):
        return True
    return bool(re.match(
        r".{0,80}\bis (?:a|an|both a|the)[\w\s,-]{0,30}"
        r"\b(?:surname|given name|family name)\b", intro))


def verify_against_context(entity, title, intro, name_preverified=False):
    """Return (ok, reason). Name must match and context/cohort keywords must
    appear in the intro.

    `name_preverified=True`: the article was reached by fetching the entity's
    own exact name (possibly via a Wikipedia redirect, e.g. "Tenzin Gyatso"
    -> "14th Dalai Lama"); the redirect asserts identity, so only the
    context check applies. Anything found via search or a context-derived
    phrase must match by TITLE — an intro that merely mentions the name (a
    founder's bio for a company entity, a film article for an actor) is not
    the entity's article."""
    if is_namelike_page(title, intro):
        return False, "surname_page"
    intro_f = fold(intro)
    p = intro.find(". ")
    first_sent = intro[:p + 1] if p > 0 else intro[:250]
    name = clean_entity_name(entity["name"])
    # alternate forms: domain-stripped variant ("Distill.pub" -> "Distill"),
    # the entity name's own parenthetical ("AI2 (Allen Institute)")
    forms = [name] + name_variants(name)
    np = name_paren(entity["name"])
    if np:
        forms.append(np)
    title_main = re.sub(r"\s*\([^)]*\)\s*$", "", title)
    tt = set(name_tokens(title_main))
    sqt = squash(title_main)
    nt = set(name_tokens(name))
    sqn = squash(name)
    for f in forms[1:]:
        if squash(f) == sqt:
            nt, sqn = set(name_tokens(f)), squash(f)
            break
    # Wikipedia's sense label must not contradict the entity: a lowercase
    # parenthetical like "(mathematics)" on a startup entity is a namesake.
    # Capitalized parentheticals ("(Canada)", "(Oakland)") are place/person
    # qualifiers and are fine. Skipped for redirects from the exact name.
    tp = re.search(r"\(([^)]+)\)\s*$", title)
    if tp and not name_preverified:
        pwords = [w for w in re.split(r"[^A-Za-z0-9+]+", tp.group(1)) if w]
        if pwords and all(w.islower() for w in pwords):
            allowed = set(PAREN_OK)
            allowed |= set(name_tokens(entity.get("context", "")))
            allowed |= {fold(k) for kws in [COHORT_KW.get(entity["cohort"], [])]
                        for k in kws for k in k.split()}
            allowed |= set(name_tokens(entity["name"]))
            if not any(fold(w) in allowed for w in pwords):
                return False, f"paren_sense_mismatch({tp.group(1)})"
    acronymish = (" " not in name and 3 <= len(name) <= 12
                  and (name.isupper() or sum(c.isupper() for c in name) >= 2))
    # A redirect that lands on a title sharing no token with the name is
    # often a topic merge ("Qdrant" -> "Vector database"): the intro must at
    # least mention the entity, else there is no entity-specific gold there.
    if name_preverified and not (nt & tt):
        isq = squash(intro)
        if not (sqn in isq or any(len(t) >= 5 and kw_hit(t, fold(intro))
                                  for t in nt)):
            return False, "redirect_without_mention"
    if name_preverified or sqn == sqt:
        name_ok = True
    elif acronymish:
        # Acronyms must appear case-sensitively in the title or the FIRST
        # sentence (the canonical "Official Name (ABBR) is ..." pattern).
        # Anywhere-in-intro is unsafe: ICCV's intro mentions CVPR.
        acr = r"(?<![A-Za-z])" + re.escape(name) + r"(?![a-z])"
        name_ok = bool(re.search(acr, title) or re.search(acr, first_sent))
        if not name_ok:
            # or: the title spells out the official name given in the context
            # (CVPR's article never uses the acronym in its intro)
            for phrase in context_phrases(entity):
                pw = {w for w in re.split(r"[^a-z0-9-]+", fold(phrase))
                      if len(w) >= 4 and w not in STOPWORDS}
                if len(pw) >= 2 and pw <= tt:
                    name_ok = True
                    break
    else:
        # acronym of the title's capitalized words ("Tensor Processing Unit"
        # -> "tpu") — lets "Google TPU" match its article by title acronym
        title_acr = fold("".join(w[0] for w in re.findall(r"[A-Za-z]\w*", title_main)
                                 if w[0].isupper()))
        rem = [t for t in nt if t not in tt]  # name tokens absent from title
        ctx_name_f = fold(entity.get("context", "") + " " + entity["name"])
        extras = [t for t in tt if t not in nt]  # title tokens beyond the name
        extras_supported = all(
            t in CORP_SUFFIX or kw_hit(t, ctx_name_f) for t in extras)
        name_ok = (
            (len(nt) >= 2 and len(sqn) >= 5 and nt <= tt)      # name + qualifier in title
            or (nt and len(sqn) >= 5 and nt <= tt and extras_supported)  # "Cassandra" -> "Apache Cassandra"
            or (len(sqt) >= 6 and sqn.startswith(sqt)          # title is head of name...
                and all(kw_hit(t, intro_f) for t in rem))      # ...and the rest is in the intro
            or (len(sqn) >= 6 and len(tt) == 1 and sqt.startswith(sqn))  # name is head of one-word title (Chroma->ChromaDB)
            or (len(title_acr) >= 3 and title_acr in nt
                and all(kw_hit(t, intro_f) for t in nt if t != title_acr))
        )
    if not name_ok:
        return False, "name_mismatch"
    # Abbreviation-like names are ambiguous even through redirects ("S&P"
    # redirects to the credit-rating agency, not the IEEE symposium). If the
    # context spells out an official name, most of its content words must
    # appear in the intro (rejects same-acronym namesakes like "Union
    # Académique Internationale" for the UAI conference).
    if acronymish:
        for phrase in context_phrases(entity)[:1]:
            words = [w for w in re.split(r"[^a-z0-9-]+", fold(phrase))
                     if len(w) >= 4 and w not in STOPWORDS]
            if words:
                hits = sum(kw_hit(w, intro_f) for w in words)
                if hits * 2 < len(words):
                    return False, (f"acronym_official_name_mismatch"
                                   f"({hits}/{len(words)})")
    ctx_kws = context_keywords(entity)
    ctx_hits = [k for k in ctx_kws if kw_hit(k, intro_f)]
    cohort_hits = [k for k in COHORT_KW.get(entity["cohort"], [])
                   if kw_hit(k, intro_f)]
    if not ctx_hits and not cohort_hits:
        return False, "context_unverified"
    # Batch-P26-era YC startups virtually never have articles; any hit on a
    # generic name ("Kinect", "Cohesion") is a namesake unless the intro
    # itself ties the subject to Y Combinator.
    if entity["cohort"] == "mid_tier_yc_company" and not kw_hit("combinator", intro_f):
        return False, "yc_namesake_guard"
    return True, f"ctx={','.join(ctx_hits[:4])};cohort={','.join(cohort_hits[:3])}"


def is_disambig(intro, title):
    if "(disambiguation)" in title:
        return True
    head = intro[:300].lower()
    return bool(re.search(r"may (also )?refer to", head)) and len(intro.split()) < 80


def count_facts(text, entity_name):
    """Rough count of entity-specific facts: distinct years + proper nouns
    not in the entity's own name."""
    years = set(re.findall(r"\b(?:1[5-9]\d\d|20[0-2]\d)\b", text))
    name_toks = set(name_tokens(entity_name))
    caps = set()
    for m in re.finditer(r"(?<![.!?]\s)(?<!^)\b([A-Z][a-zA-Z]{2,})\b", text):
        w = m.group(1)
        if fold(w) not in name_toks and fold(w) not in STOPWORDS:
            caps.add(w)
    return len(years) + len(caps)


def build_gold(entity, title, intro):
    cleaned = clean_intro(intro)
    trimmed = trim_to_words(cleaned, 180)
    wc = len(trimmed.split())
    thin = wc < 40 or (wc < 60 and count_facts(trimmed, entity["name"]) < 3)
    return trimmed, thin, wc


# ------------------------------------------------------------ API operations

def wikidata_sitelinks(qids):
    """qid -> enwiki title (missing if none)."""
    out = {}
    qids = list(qids)
    for i in range(0, len(qids), 50):
        batch = qids[i:i + 50]
        data = api_get(WIKIDATA_API, {
            "action": "wbgetentities", "ids": "|".join(batch),
            "props": "sitelinks", "sitefilter": "enwiki",
            "format": "json"})
        for qid, ent in data.get("entities", {}).items():
            link = ent.get("sitelinks", {}).get("enwiki")
            if link:
                out[qid] = link["title"]
    return out


def fetch_intros(titles):
    """titles -> {requested_title: (final_title, intro)}; missing pages absent.
    Batches of 20 (exintro allows multi-page extracts)."""
    result = {}
    titles = list(OrderedDict.fromkeys(titles))
    for i in range(0, len(titles), 20):
        batch = titles[i:i + 20]
        data = api_get(WIKI_API, {
            "action": "query", "prop": "extracts", "exintro": 1,
            "explaintext": 1, "exlimit": "max", "redirects": 1,
            "titles": "|".join(batch), "format": "json",
            "formatversion": 2, "maxlag": 5})
        q = data.get("query", {})
        fwd = {}  # requested -> final
        for t in batch:
            fwd[t] = t
        for n in q.get("normalized", []):
            for k, v in list(fwd.items()):
                if v == n["from"]:
                    fwd[k] = n["to"]
        for rd in q.get("redirects", []):
            for k, v in list(fwd.items()):
                if v == rd["from"]:
                    fwd[k] = rd["to"]
        pages = {p["title"]: p for p in q.get("pages", [])}
        missing_extract = []
        for req, fin in fwd.items():
            p = pages.get(fin)
            if p and not p.get("missing") and p.get("extract"):
                result[req] = (fin, p["extract"])
            elif p and not p.get("missing"):
                missing_extract.append((req, fin))
        # fallback: single-title fetch for pages whose extract was dropped
        for req, fin in missing_extract:
            data1 = api_get(WIKI_API, {
                "action": "query", "prop": "extracts", "exintro": 1,
                "explaintext": 1, "redirects": 1, "titles": fin,
                "format": "json", "formatversion": 2, "maxlag": 5})
            for p in data1.get("query", {}).get("pages", []):
                if not p.get("missing") and p.get("extract"):
                    result[req] = (p["title"], p["extract"])
    return result


def search_candidates(query, limit=8):
    data = api_get(WIKI_API, {
        "action": "query", "list": "search", "srsearch": query,
        "srlimit": limit, "format": "json", "formatversion": 2,
        "maxlag": 5})
    titles = [h["title"] for h in data.get("query", {}).get("search", [])]
    return [t for t in titles
            if "(disambiguation)" not in t
            and not t.startswith(("List of", "Lists of", "Index of",
                                  "Glossary of", "Outline of"))]


def context_phrases(entity):
    """Capitalized multiword phrases from the context, e.g. the official
    'International Symposium on Microarchitecture' hiding in a conference
    context — good direct-title candidates."""
    ctx = entity.get("context", "")
    pat = re.compile(
        r"\b(?:[A-Z][\w&.'-]*|[A-Z]{2,})"
        r"(?:\s+(?:of|on|and|for|in|the|at|de|[A-Z][\w&.'-]*|[A-Z]{2,})){1,9}")
    out = []
    for m in pat.finditer(ctx):
        p = m.group(0).strip()
        p = re.sub(r"\s+(?:of|on|and|for|in|the|at|de)$", "", p)
        if len(p.split()) >= 2 and squash(p) != squash(entity["name"]):
            out.append(p)
    return out


# For ambiguous bare names, Wikipedia's sense-labelled title is the precise
# target: "Sketch (software)" not SketchUp, "Revolutions (podcast)" not the
# Revolution concept article. Tried before the bare name in the direct round.
SENSE_TITLES = {
    "mid_tier_product": ["software", "app"],
    "mid_tier_podcast": ["podcast"],
    "mid_tier_musician": ["band", "musician"],
    "mid_tier_actor": ["actor", "actress"],
    "mid_tier_book": ["novel", "book"],
    "mid_tier_writer": ["writer", "author", "novel"],
    "mid_tier_comedian": ["comedian"],
    "mid_tier_filmmaker": ["director", "filmmaker"],
    "mid_tier_journalist": ["journalist"],
    "ai_startup_or_company": ["company"],
    "mid_tier_yc_company": ["company"],
    "database_or_data_system": ["database", "software"],
    "website_or_service": ["website"],
    "industry_product": ["software", "chatbot"],
}


def name_variants(name):
    """Alternate lookup forms: strip web-domain suffixes ('Distill.pub' ->
    'Distill', 'lilianweng.github.io' -> 'lilianweng')."""
    out = []
    m = re.match(r"(.+?)(?:\.github\.io|\.(?:com|org|net|io|ai|pub|online|co|app|dev|me))$",
                 name, re.I)
    if m and len(m.group(1)) >= 3:
        out.append(m.group(1))
    return out


def resolve_by_search(entity):
    """Return (title, intro, reason) or (None, None, reason)."""
    name = clean_entity_name(entity["name"])
    variants = name_variants(name)
    sense = [f"{name} ({lbl})" for lbl in SENSE_TITLES.get(entity["cohort"], [])]
    # requests whose redirect asserts identity: the exact name, and the
    # cohort-sense-labelled name ("Revolutions (podcast)" names exactly our
    # entity even when it redirects to "Mike Duncan (podcaster)").
    # Domain-stripped variants are weaker and excluded.
    own_names = {name} | set(sense)
    tried = set()

    def try_titles(titles, tag):
        titles = [t for t in titles if t not in tried][:6]
        for t in titles:
            tried.add(t)
        if not titles:
            return None
        intros = fetch_intros(titles)
        for t in titles:
            got = intros.get(t)
            if not got:
                continue
            fin, intro = got
            if is_disambig(intro, fin):
                continue
            ok, why = verify_against_context(
                entity, fin, intro, name_preverified=(t in own_names))
            if ok:
                return fin, intro, f"{tag}:{why}"
        return None

    # 0) direct titles: cohort sense-labelled titles first ("X (podcast)"),
    #    then the entity name (catches redirects like "NVIDIA H100"), plus
    #    official-name phrases from the context
    hit = try_titles(sense + [name] + variants + context_phrases(entity), "direct")
    if hit:
        return hit
    # 1) plain name search
    hit = try_titles(search_candidates(name), "search")
    if hit:
        return hit
    # 2) name + context keywords (also with domain-stripped variant)
    kws = context_keywords(entity)[:3]
    if kws:
        for nm in [name] + variants:
            hit = try_titles(search_candidates(nm + " " + " ".join(kws)),
                             "search+ctx")
            if hit:
                return hit
    # 3) search on the context's official-name phrase
    for p in context_phrases(entity)[:2]:
        hit = try_titles(search_candidates(p), "search+phrase")
        if hit:
            return hit
    reason = "no_candidate" if not tried else "unverified_candidates"
    return None, None, reason


# --------------------------------------------------------------------- main

def load_checkpoint():
    if os.path.exists(CHECKPOINT_PATH):
        with open(CHECKPOINT_PATH) as f:
            return json.load(f)
    return {}


def save_checkpoint(ck):
    tmp = CHECKPOINT_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(ck, f, ensure_ascii=False)
    os.replace(tmp, CHECKPOINT_PATH)


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    with open(ENTITIES_PATH) as f:
        all_entities = json.load(f)
    targets = [e for e in all_entities
               if e["cohort"].startswith("mid_tier_")
               or e["cohort"] in EXTRA_COHORTS]
    if limit:
        targets = targets[:limit]
    print(f"target entities: {len(targets)}")

    t14 = {}
    with open(T14_PATH) as f:
        for r in csv.DictReader(f):
            if r["has_wikipedia"] == "1" and r["title_matched"]:
                t14[r["entity_id"]] = r["title_matched"]

    ck = load_checkpoint()
    print(f"checkpoint: {len(ck)} entities already done")

    # ---- phase 1: resolve titles via wikidata / t1_4
    pending = [e for e in targets if e["id"] not in ck]
    qids = {e["wikidata_id"] for e in pending if e.get("wikidata_id")}
    qid2title = wikidata_sitelinks(qids) if qids else {}
    print(f"wikidata: resolved {len(qid2title)}/{len(qids)} QIDs to enwiki")

    resolved = {}   # entity_id -> (title, method)
    need_search = []
    for e in pending:
        qid = e.get("wikidata_id")
        if qid and qid in qid2title:
            resolved[e["id"]] = (qid2title[qid], "wikidata")
        elif e["id"] in t14:
            resolved[e["id"]] = (t14[e["id"]], "t1_4")
        else:
            need_search.append(e)
    print(f"resolved by id/t1_4: {len(resolved)}; need search: {len(need_search)}")

    ents_by_id = {e["id"]: e for e in targets}
    done_since_save = 0

    def record(eid, rec):
        nonlocal done_since_save
        ck[eid] = rec
        done_since_save += 1
        if done_since_save >= CHECKPOINT_EVERY:
            save_checkpoint(ck)
            done_since_save = 0
            print(f"  checkpoint saved ({len(ck)} done)")

    # ---- phase 2: fetch intros for id/t1_4-resolved titles in batches of 20
    # Wikidata sitelinks are trusted (stored ID). t1_4 titles are re-verified
    # against the entity context; failures fall through to the search path
    # (t1_4 has occasional wrong matches, e.g. MICRO -> "Micro-conference").
    ids = list(resolved)
    demoted = {}  # entity_id -> note for search fallback
    for i in range(0, len(ids), 20):
        chunk = ids[i:i + 20]
        title_map = {resolved[eid][0]: None for eid in chunk}
        intros = fetch_intros(list(title_map))
        for eid in chunk:
            e = ents_by_id[eid]
            title, method = resolved[eid]
            got = intros.get(title)
            if not got:
                if method == "t1_4":
                    demoted[eid] = f"t1_4_title_missing:{title}"
                else:
                    record(eid, {"matched": 0, "confidence": "", "title": title,
                                 "method": method,
                                 "reason": "page_missing_or_no_extract",
                                 "gold": "", "thin_gold": False})
                continue
            fin, intro = got
            if is_disambig(intro, fin):
                if method == "t1_4":
                    demoted[eid] = f"t1_4_disambig:{fin}"
                else:
                    record(eid, {"matched": 0, "confidence": "", "title": fin,
                                 "method": method, "reason": "disambiguation_page",
                                 "gold": "", "thin_gold": False})
                continue
            ok, why = verify_against_context(e, fin, intro)
            if method == "t1_4" and not ok:
                demoted[eid] = f"t1_4_reverify_failed({why}):{fin}"
                continue
            gold, thin, wc = build_gold(e, fin, intro)
            record(eid, {"matched": 1, "confidence": "high", "title": fin,
                         "method": method,
                         "reason": f"resolved_{method};verify={'ok' if ok else why};words={wc}",
                         "gold": gold, "thin_gold": thin})
        if (i // 20) % 10 == 0:
            print(f"  intros: {min(i+20, len(ids))}/{len(ids)}")

    for eid, note in demoted.items():
        need_search.append(ents_by_id[eid])
    demote_note = demoted
    print(f"t1_4 demoted to search: {len(demoted)}")

    # ---- phase 3: search + verify
    for j, e in enumerate(need_search):
        note = demote_note.get(e["id"])
        title, intro, reason = resolve_by_search(e)
        if note:
            reason = f"{note};{reason}"
        if title:
            gold, thin, wc = build_gold(e, title, intro)
            record(e["id"], {"matched": 1, "confidence": "medium",
                             "title": title, "method": "search",
                             "reason": f"{reason};words={wc}",
                             "gold": gold, "thin_gold": thin})
        else:
            record(e["id"], {"matched": 0, "confidence": "", "title": "",
                             "method": "search", "reason": reason,
                             "gold": "", "thin_gold": False})
        if (j + 1) % 25 == 0:
            print(f"  search: {j+1}/{len(need_search)}")

    save_checkpoint(ck)

    # ---- outputs
    gold_out = {}
    os.makedirs(os.path.dirname(GOLD_OUT), exist_ok=True)
    with open(REPORT_OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["entity_id", "cohort", "matched", "confidence", "title",
                    "method", "reason"])
        for e in targets:
            rec = ck.get(e["id"])
            if rec is None:
                continue
            w.writerow([e["id"], e["cohort"], rec["matched"], rec["confidence"],
                        rec["title"], rec["method"], rec["reason"]])
            if rec["matched"]:
                gold_out[e["id"]] = {
                    "gold": rec["gold"], "source": "wikipedia",
                    "source_ref": rec["title"],
                    "confidence": rec["confidence"],
                    "thin_gold": rec["thin_gold"],
                }
    with open(GOLD_OUT, "w") as f:
        json.dump(gold_out, f, ensure_ascii=False, indent=1)

    # ---- summary
    by_cohort = Counter()
    matched_cohort = Counter()
    thin = 0
    for e in targets:
        rec = ck.get(e["id"])
        if rec is None:
            continue
        by_cohort[e["cohort"]] += 1
        if rec["matched"]:
            matched_cohort[e["cohort"]] += 1
            thin += rec["thin_gold"]
    print(f"\nmatched {sum(matched_cohort.values())}/{sum(by_cohort.values())}; "
          f"thin_gold={thin}")
    for c in sorted(by_cohort):
        print(f"  {c:32s} {matched_cohort[c]:4d}/{by_cohort[c]:4d} "
              f"({matched_cohort[c]/by_cohort[c]*100:5.1f}%)")


if __name__ == "__main__":
    main()
