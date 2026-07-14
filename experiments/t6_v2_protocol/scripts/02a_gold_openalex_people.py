#!/usr/bin/env python3
"""
02a — Build v2 gold answers for person cohorts from OpenAlex.

Cohorts handled (from data/inputs/pilot_entities.json):
  - long_tail_researcher_openalex (openalex_id present -> direct fetch, high)
  - long_tail_researcher_ikp      (openalex_id present -> direct fetch, high)
  - cs_faculty                    (name + institution -> filtered author search, medium)
  - gpt5_system_card_author       (matched against the OpenAI GPT-5 System Card
                                   authorship list W7119523234; fallback search
                                   requires an OpenAI affiliation, medium)
  - deepseek_v3_author            (matched against DeepSeek-V3 Technical Report
                                   authorship list W4405903187; fallback search
                                   requires a DeepSeek affiliation, medium)

Golds are composed mechanically (f-strings, no LLM) per the v2 style guide:
80-180 words, >=3 entity-specific facts, named works/venues/years/affiliations,
NO citation counts / h-index. Titles truncated at ~12 words.

Resumable: raw fetch results are checkpointed to outputs/_cache_people.json
every 100 entities; outputs are rewritten at each checkpoint.

Outputs:
  inputs/gold_v2_people.json         (matched entities only, high/medium)
  outputs/match_report_people.csv    (all entities in these cohorts)
"""

import csv
import difflib
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # t6_v2_protocol
REPO = os.path.dirname(os.path.dirname(BASE))                        # namerank
ENTITIES_PATH = os.path.join(REPO, "data", "inputs", "pilot_entities.json")
CACHE_PATH = os.path.join(BASE, "outputs", "_cache_people.json")
GOLD_PATH = os.path.join(BASE, "inputs", "gold_v2_people.json")
REPORT_PATH = os.path.join(BASE, "outputs", "match_report_people.csv")

API = "https://api.openalex.org"
API_KEY = os.environ.get("OPENALEX_API_KEY", "")

# optional SOCKS route (e.g. OA_SOCKS=127.0.0.1:1080) for quota-exhausted hosts
if os.environ.get("OA_SOCKS"):
    import socket

    import socks

    _h, _p = os.environ["OA_SOCKS"].rsplit(":", 1)
    socks.set_default_proxy(socks.SOCKS5, _h, int(_p), rdns=True)
    socket.socket = socks.socksocket
    print(f"[INFO] routing via SOCKS {_h}:{_p}")
MAILTO = "boj@19pine.ai"
MIN_INTERVAL = 0.20  # ~5 req/s, comfortably under the 10 rps cap

COHORTS = [
    "long_tail_researcher_openalex",
    "long_tail_researcher_ikp",
    "cs_faculty",
    "gpt5_system_card_author",
    "deepseek_v3_author",
]

REPORT_WORKS = {
    "gpt5_system_card_author": "W7119523234",   # OpenAI GPT-5 System Card (2025)
    "deepseek_v3_author": "W4405903187",        # DeepSeek-V3 Technical Report (2024)
}
# Normalized title fragments to exclude from golds (the probe context already
# names the report); catches duplicate OpenAlex copies with different work IDs.
REPORT_TITLE_FRAG = {
    "gpt5_system_card_author": "gpt 5 system card",
    "deepseek_v3_author": "deepseek v3 technical report",
}
COMPANY_KEYWORD = {
    "gpt5_system_card_author": "openai",
    "deepseek_v3_author": "deepseek",
}

# ---------------------------------------------------------------- HTTP client

_last_req = [0.0]
# A Retry-After longer than this means the daily quota is exhausted, not a
# transient burst limit — no point spinning; checkpoint and let a resume finish.
QUOTA_ABORT_S = 300.0


class QuotaExhausted(Exception):
    """Raised when OpenAlex signals a long (daily-quota) cooldown."""


def api_get(path_and_query, ok404=False):
    """Rate-limited GET with retries. Returns parsed JSON, or None on 404.

    Raises QuotaExhausted on a long Retry-After (daily cap) so the caller can
    checkpoint and exit cleanly for a later resume, instead of hanging ~21h.
    """
    sep = "&" if "?" in path_and_query else "?"
    url = f"{API}{path_and_query}{sep}mailto={MAILTO}"
    if API_KEY:
        url += f"&api_key={API_KEY}"
    attempts = 6
    for attempt in range(attempts):
        wait = _last_req[0] + MIN_INTERVAL - time.time()
        if wait > 0:
            time.sleep(wait)
        _last_req[0] = time.time()
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                if ok404:
                    return None
                raise
            if e.code in (429, 500, 502, 503):
                ra = e.headers.get("Retry-After") if e.headers else None
                try:
                    ra_s = float(ra)
                except (TypeError, ValueError):
                    ra_s = None
                if ra_s is not None and ra_s > QUOTA_ABORT_S:
                    raise QuotaExhausted(f"Retry-After={ra_s:.0f}s on {url}")
                if attempt < attempts - 1:
                    delay = ra_s if ra_s is not None else min(90.0, 3.0 * (2 ** attempt))
                    time.sleep(min(delay, 90.0))
                    continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt < attempts - 1:
                time.sleep(min(90.0, 3.0 * (2 ** attempt)))
                continue
            raise
    raise RuntimeError(f"unreachable: {url}")


# ------------------------------------------------------------- name matching

def norm_tokens(name):
    if "," in name:  # "Pan, Zizheng" -> "Zizheng Pan"
        last, first = name.split(",", 1)
        name = first + " " + last
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("-", " ").replace(".", " ").replace("'", "")
    return [t for t in re.split(r"[^a-z]+", s) if t]


def name_sim(a, b):
    ta, tb = norm_tokens(a), norm_tokens(b)
    if not ta or not tb:
        return 0.0
    if ta == tb or ta == tb[::-1]:
        return 1.0
    if set(ta) == set(tb):
        return 0.98
    if ta[-1] == tb[-1] and ta[0] == tb[0]:
        return 0.95  # middle names / initials differ
    if ta[-1] == tb[0] and ta[0] == tb[-1]:
        return 0.90  # name-order flip with extras
    if ta[-1] == tb[-1] and ta[0][0] == tb[0][0] and (len(ta[0]) == 1 or len(tb[0]) == 1):
        return 0.85  # first name vs initial
    return difflib.SequenceMatcher(None, " ".join(ta), " ".join(tb)).ratio() * 0.9


ORG_WORDS = {
    "institute", "institut", "instituto", "institution", "university",
    "universitas", "universidad", "universidade", "universiti", "department",
    "dept", "center", "centre", "centro", "laboratory", "laboratories",
    "laboratoire", "ministry", "agency", "committee", "commission",
    "association", "hospital", "school", "college", "foundation", "badan",
    "penelitian", "pengembangan", "consortium", "collaboration", "society",
    "council", "bureau", "organization", "organisation", "corporation",
    "network", "academy", "akademi", "faculty", "division", "gmbh", "inc",
    "ltd", "llc", "group", "team", "clinic", "bank", "office",
}


def looks_like_org(name):
    return any(t in ORG_WORDS for t in norm_tokens(name))


def short_id(openalex_url):
    return openalex_url.rsplit("/", 1)[-1] if openalex_url else ""


def norm_inst(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"\((united states|china|uk|united kingdom|germany|france)\)", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def inst_match(a, b):
    na, nb = norm_inst(a), norm_inst(b)
    if not na or not nb:
        return False
    return na == nb or na in nb or nb in na


# ------------------------------------------------------------- author slims

def slim_author(a):
    if not a:
        return None
    return {
        "id": a["id"],
        "display_name": a.get("display_name"),
        "works_count": a.get("works_count", 0),
        "affiliations": [
            {
                "name": (aff.get("institution") or {}).get("display_name"),
                "country": (aff.get("institution") or {}).get("country_code"),
                "years": sorted(aff.get("years") or []),
            }
            for aff in (a.get("affiliations") or [])
            if (aff.get("institution") or {}).get("display_name")
        ],
        "last_known": [
            i.get("display_name") for i in (a.get("last_known_institutions") or [])
        ],
        "topics": [
            {
                "name": t.get("display_name"),
                "field": ((t.get("field") or {}).get("display_name")),
            }
            for t in (a.get("topics") or [])
        ],
        "recent_years": [
            c["year"] for c in (a.get("counts_by_year") or []) if c.get("works_count")
        ],
    }


CS_FIELDS = {"Computer Science", "Mathematics"}
CS_TOPIC_RE = re.compile(
    r"neural|language model|machine learning|deep learning|artificial intelligence"
    r"|reinforcement|transformer|natural language|computer vision|speech"
    r"|software|computing|data mining|algorithm|robot|semiconductor|circuit",
    re.I,
)


def primary_cs(author_slim):
    """True if the author's PRIMARY (top) topic is CS/Math or CS-regex.

    Deliberately strict: guards the industry cohorts against common-name
    mis-attribution to unrelated (chemistry/biology/etc.) OpenAlex clusters.
    """
    topics = author_slim.get("topics", [])
    if not topics:
        return False
    top = topics[0]
    if top.get("field") in CS_FIELDS:
        return True
    return bool(top.get("name") and CS_TOPIC_RE.search(top["name"]))


def author_has_company(author_slim, keyword):
    for aff in author_slim.get("affiliations", []):
        if keyword in (aff.get("name") or "").lower():
            return True
    return any(keyword in (n or "").lower() for n in author_slim.get("last_known", []))


# ---------------------------------------------------------------- works fetch

WORK_SELECT = "id,title,publication_year,cited_by_count,primary_location,authorships"


def fetch_works(author_id, per_page):
    aid = short_id(author_id)
    top = api_get(
        f"/works?filter=author.id:{aid}&sort=cited_by_count:desc"
        f"&per_page={per_page}&select={WORK_SELECT}"
    )
    first = api_get(
        f"/works?filter=author.id:{aid}&sort=publication_date:asc"
        f"&per_page=1&select=publication_year"
    )
    works = []
    for w in top.get("results", []):
        auths = w.get("authorships") or []
        pos, n_auth = None, len(auths)
        for x in auths:
            if short_id((x.get("author") or {}).get("id", "")) == aid:
                pos = x.get("author_position")
                break
        src = (w.get("primary_location") or {}).get("source") or {}
        works.append(
            {
                "wid": short_id(w.get("id", "")),
                "title": w.get("title"),
                "year": w.get("publication_year"),
                "venue": src.get("display_name"),
                "cited": w.get("cited_by_count", 0),
                "position": pos,
                "n_authors": n_auth,
            }
        )
    fy = None
    fr = first.get("results", [])
    if fr:
        fy = fr[0].get("publication_year")
    return {"top": works, "first_year": fy}


# ---------------------------------------------------------------- composing

TAG_RE = re.compile(r"<[^>]+>")


def clean_title(t, max_words=12):
    t = TAG_RE.sub("", t or "").strip()
    t = re.sub(r"\s+", " ", t)
    words = t.split()
    if len(words) > max_words:
        t = " ".join(words[:max_words]).rstrip(",;:") + "…"
    return t


def fmt_years(years):
    if not years:
        return None
    lo, hi = min(years), max(years)
    return str(lo) if lo == hi else f"{lo}–{hi}"


def aff_phrase(aff):
    yr = fmt_years(aff["years"])
    return f"{aff['name']} ({yr})" if yr else aff["name"]


def join_list(items):
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _title_norm(t):
    return re.sub(r"[^a-z0-9]+", " ", TAG_RE.sub("", (t or "")).lower()).strip()


def compose_gold(name, author, works_info, exclude_wids=(),
                 exclude_title_frag=None, fallback_field=None):
    """Mechanical composition. Returns (text, n_facts, usable_facts)."""
    topics = [t["name"] for t in author.get("topics", []) if t.get("name")]
    field = topics[0] if topics else (fallback_field or "their field")

    # Filter out the report work (by id and by title fragment) and dedupe
    # remaining works by normalized title, keeping the highest-cited copy.
    works = []
    seen_titles = set()
    for w in works_info.get("top", []):
        if not w.get("title") or w["wid"] in exclude_wids:
            continue
        tn = _title_norm(w["title"])
        if exclude_title_frag and exclude_title_frag in tn:
            continue
        if tn in seen_titles:
            continue
        seen_titles.add(tn)
        works.append(w)
    affs = sorted(
        author.get("affiliations", []),
        key=lambda a: max(a["years"]) if a["years"] else 0,
        reverse=True,
    )
    # dedupe affiliations by name, keep order
    seen, affs_d = set(), []
    for a in affs:
        if a["name"] not in seen:
            seen.add(a["name"])
            affs_d.append(a)
    first_year = works_info.get("first_year")
    works_count = author.get("works_count", 0)

    def render(n_works, n_affs, pad):
        sents = [f"{name} is a researcher in {field}."]
        used_affs = affs_d[:n_affs]
        if used_affs:
            sents.append(
                "They have been affiliated with "
                + join_list([aff_phrase(a) for a in used_affs]) + "."
            )
        listed = works[:n_works]
        if listed:
            parts = []
            for i, w in enumerate(listed):
                t = clean_title(w["title"])
                if i < 2 and w.get("venue"):
                    parts.append(f"'{t}' ({clean_title(w['venue'], 8)}, {w['year']})")
                else:
                    parts.append(f"'{t}' ({w['year']})")
            label = "works include" if len(listed) > 1 else "work is"
            sents.append(f"Their most-cited {label} {join_list(parts)}.")
        fa = next((w for w in works[:5] if w.get("position") == "first"), None)
        if fa is not None:
            n_co = max(0, (fa.get("n_authors") or 1) - 1)
            co = "which they wrote alone" if n_co == 0 else (
                f"which they wrote with {n_co} coauthor" + ("s" if n_co > 1 else "")
            )
            if fa in listed:
                if len(listed) == 1:
                    sents.append(f"They are the first author of this work, {co}.")
                else:
                    sents.append(
                        f"Of these, '{clean_title(fa['title'], 6)}' is first-authored, {co}."
                    )
            else:
                sents.append(
                    f"They are the first author of '{clean_title(fa['title'])}'"
                    f" ({fa['year']}), {co}."
                )
        if pad:
            extra = works[n_works:5]
            if extra:
                parts = [f"'{clean_title(w['title'])}' ({w['year']})" for w in extra]
                sents.append(f"Other works include {join_list(parts)}.")
            elif len(topics) > 1:
                sents.append(
                    f"Their research also covers {join_list(topics[1:3])}."
                )
        if works_count and first_year:
            sents.append(
                f"They have published {works_count} works since {first_year}."
            )
        text = " ".join(sents)
        n_facts = len(listed) + len(used_affs) + (1 if first_year else 0)
        if fa is not None:
            n_facts += 1
        return text, n_facts

    usable_facts = len(works) + len(affs_d)  # verifiable, entity-specific
    text, n_facts = render(3, 3, pad=False)
    wc = len(text.split())
    if wc < 80:
        text, n_facts = render(3, 3, pad=True)
        wc = len(text.split())
    if wc > 180:
        text, n_facts = render(2, 2, pad=False)
    return text, n_facts, usable_facts


# ---------------------------------------------------------------- cache I/O

def load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            return json.load(f)
    return {"authors": {}, "works": {}, "matches": {}, "inst_ids": {},
            "report_authorships": {}}


def save_cache(cache):
    tmp = CACHE_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cache, f)
    os.replace(tmp, CACHE_PATH)


# ---------------------------------------------------------------- matching

def batch_fetch_authors(ids, cache):
    """Batch-fetch author records by OpenAlex ID into cache['authors']."""
    todo = [i for i in ids if i not in cache["authors"]]
    for i in range(0, len(todo), 50):
        chunk = todo[i:i + 50]
        r = api_get("/authors?filter=ids.openalex:" + "|".join(chunk) + "&per_page=50")
        got = {short_id(a["id"]): a for a in r.get("results", [])}
        for aid in chunk:
            if aid in got:
                cache["authors"][aid] = slim_author(got[aid])
        # individually fetch missing (merged/redirected IDs)
        for aid in chunk:
            if aid not in cache["authors"]:
                a = api_get(f"/authors/{aid}", ok404=True)
                cache["authors"][aid] = slim_author(a)  # None if 404
        print(f"  batch authors: {min(i + 50, len(todo))}/{len(todo)}", flush=True)


def get_report_authorships(cohort, cache):
    wid = REPORT_WORKS[cohort]
    if wid not in cache["report_authorships"]:
        w = api_get(f"/works/{wid}")
        cache["report_authorships"][wid] = [
            {
                "author_id": short_id((a.get("author") or {}).get("id", "")),
                "name": (a.get("author") or {}).get("display_name", ""),
            }
            for a in (w.get("authorships") or [])
        ]
    return cache["report_authorships"][wid]


def match_report_author(name, authorships):
    best, best_sim = None, 0.0
    ties = 0
    for a in authorships:
        s = name_sim(name, a["name"])
        if s > best_sim:
            best, best_sim, ties = a, s, 1
        elif s == best_sim and s > 0:
            ties += 1
    if best_sim >= 0.90 and ties == 1:
        return best, best_sim
    if best_sim >= 0.98:  # exact-ish even if tie (same person listed twice)
        return best, best_sim
    return None, best_sim


def resolve_institution(inst, cache):
    key = norm_inst(inst)
    if key not in cache["inst_ids"]:
        r = api_get("/institutions?search=" + urllib.parse.quote(inst) + "&per_page=2")
        res = r.get("results", [])
        cache["inst_ids"][key] = {
            "id": short_id(res[0]["id"]) if res else None,
            "name": res[0]["display_name"] if res else None,
        }
    return cache["inst_ids"][key]


def match_cs_faculty(name, inst, cache):
    """Returns (author_slim, reason) or (None, reason)."""
    inst_rec = resolve_institution(inst, cache) if inst else {"id": None}
    if inst_rec.get("id"):
        r = api_get(
            f"/authors?filter=affiliations.institution.id:{inst_rec['id']}"
            "&search=" + urllib.parse.quote(name) + "&per_page=10"
        )
        cands = [(slim_author(a), name_sim(name, a.get("display_name", "")))
                 for a in r.get("results", [])]
        cands = [(a, s) for a, s in cands if s >= 0.85]
        cands.sort(key=lambda x: (-x[1], -x[0]["works_count"]))
        if cands:
            top_sim = cands[0][1]
            tied = [c for c in cands if c[1] == top_sim]
            if len(tied) > 1:
                # Break ties only when exactly one tied cluster is substantive
                # (>=5 works) and the rest are stubs (<=2) — distinguishes the
                # real author from duplicate thin clusters, not two real people.
                subst = [c for c in tied if c[0]["works_count"] >= 5]
                stubs = [c for c in tied if c[0]["works_count"] <= 2]
                if len(subst) == 1 and len(stubs) == len(tied) - 1:
                    a, s = subst[0]
                    return a, (f"inst-filtered hit '{a['display_name']}' sim={s:.2f} "
                               f"@ {inst_rec['name']} (dominant cluster over "
                               f"{len(tied) - 1} stubs)")
                return None, f"ambiguous: {len(tied)} candidates at {inst} sim={top_sim:.2f}"
            a, s = cands[0]
            return a, (f"inst-filtered search hit '{a['display_name']}' sim={s:.2f} "
                       f"@ {inst_rec['name']}")
    # fallback: plain search, require the institution among affiliations
    r = api_get("/authors?search=" + urllib.parse.quote(name) + "&per_page=10")
    cands = []
    for a in r.get("results", []):
        sa = slim_author(a)
        s = name_sim(name, sa["display_name"] or "")
        if s >= 0.90 and any(inst_match(inst, aff["name"]) for aff in sa["affiliations"]):
            cands.append((sa, s))
    cands.sort(key=lambda x: (-x[1], -x[0]["works_count"]))
    if len(cands) == 1 or (len(cands) > 1 and cands[0][1] > cands[1][1]):
        a, s = cands[0]
        return a, f"plain search + affiliation string match sim={s:.2f}"
    if len(cands) > 1:
        return None, f"ambiguous: {len(cands)} plain-search candidates"
    return None, "no candidate with matching affiliation and name sim>=0.85"


def match_industry(name, cohort, cache):
    """gpt5/deepseek cohorts. Returns (author_slim, reason) or (None, reason)."""
    authorships = get_report_authorships(cohort, cache)
    hit, sim = match_report_author(name, authorships)
    if hit is not None:
        aid = hit["author_id"]
        if not aid:
            return None, (f"report authorship '{hit['name']}' has no linked "
                          "OpenAlex author cluster")
        if aid not in cache["authors"]:
            a = api_get(f"/authors/{aid}", ok404=True)
            cache["authors"][aid] = slim_author(a)
        sa = cache["authors"][aid]
        if sa is None:
            return None, "report authorship resolved but author record 404"
        kw = COMPANY_KEYWORD[cohort]
        has_company = author_has_company(sa, kw)
        # A cluster with >3 works must look like an ML/CS researcher (or carry
        # the company affiliation) — otherwise it is likely a common-name
        # mis-attribution to an unrelated OpenAlex cluster.
        if sa["works_count"] > 3 and not has_company and not primary_cs(sa):
            return None, (f"report authorship '{hit['name']}' resolved to "
                          f"non-CS cluster {aid} (primary topic "
                          f"'{(sa['topics'][0]['name'] if sa['topics'] else '?')}')"
                          " — likely common-name mis-attribution")
        tag = " (+company aff)" if has_company else ""
        return sa, f"matched report authorship '{hit['name']}' sim={sim:.2f}{tag}"
    # fallback: plain search, require company affiliation
    kw = COMPANY_KEYWORD[cohort]
    r = api_get("/authors?search=" + urllib.parse.quote(name) + "&per_page=10")
    cands = []
    for a in r.get("results", []):
        sa = slim_author(a)
        s = name_sim(name, sa["display_name"] or "")
        if s >= 0.85 and author_has_company(sa, kw):
            cands.append((sa, s))
    cands.sort(key=lambda x: (-x[1], -x[0]["works_count"]))
    if cands:
        a, s = cands[0]
        return a, f"search + {kw} affiliation sim={s:.2f}"
    return None, f"not in report authorship list (best sim={sim:.2f}), no {kw}-affiliated candidate"


# ---------------------------------------------------------------- main loop

def write_outputs(cache, entities):
    gold, rows = {}, []
    for e in entities:
        m = cache["matches"].get(e["id"])
        if m is None:
            continue
        rows.append([e["id"], e["cohort"], m["matched"], m["confidence"],
                     m.get("openalex_id", ""), m["reason"]])
        if m["matched"] and m["confidence"] in ("high", "medium"):
            rec = {
                "gold": m["gold"],
                "source": "openalex",
                "source_ref": m["openalex_id"],
                "confidence": m["confidence"],
                "thin_gold": m["thin_gold"],
            }
            if m.get("not_a_person"):
                rec["not_a_person"] = True
            gold[e["id"]] = rec
    os.makedirs(os.path.dirname(GOLD_PATH), exist_ok=True)
    with open(GOLD_PATH + ".tmp", "w") as f:
        json.dump(gold, f, indent=1, ensure_ascii=False)
    os.replace(GOLD_PATH + ".tmp", GOLD_PATH)
    with open(REPORT_PATH + ".tmp", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["entity_id", "cohort", "matched", "confidence",
                    "openalex_id", "reason"])
        w.writerows(rows)
    os.replace(REPORT_PATH + ".tmp", REPORT_PATH)
    return gold


def main():
    if not API_KEY:
        print("[INFO] OPENALEX_API_KEY not set; using keyless polite pool")
    with open(ENTITIES_PATH) as f:
        all_entities = json.load(f)
    entities = [e for e in all_entities if e["cohort"] in COHORTS]
    print(f"{len(entities)} entities across {len(COHORTS)} cohorts", flush=True)

    cache = load_cache()
    done = sum(1 for e in entities if e["id"] in cache["matches"])
    print(f"resuming: {done} already in cache", flush=True)

    # Prefetch: batch author records for direct-ID cohorts not yet matched.
    direct_ids = [
        short_id(e["openalex_id"]) for e in entities
        if e.get("openalex_id") and e["id"] not in cache["matches"]
    ]
    if direct_ids:
        print(f"prefetching {len(direct_ids)} direct-ID author records...", flush=True)
        try:
            batch_fetch_authors(direct_ids, cache)
        except QuotaExhausted:
            save_cache(cache)
            write_outputs(cache, entities)
            print("\nQUOTA_EXHAUSTED during prefetch; checkpointed. "
                  "Re-run to resume when quota resets.", flush=True)
            sys.exit(3)
        save_cache(cache)

    t0 = time.time()
    for n, e in enumerate(entities, 1):
        if e["id"] in cache["matches"]:
            continue
        cohort, name = e["cohort"], e["name"]
        author, confidence, reason = None, "low", ""
        try:
            if cohort in ("long_tail_researcher_openalex", "long_tail_researcher_ikp"):
                aid = short_id(e["openalex_id"])
                author = cache["authors"].get(aid)
                if author is None:
                    reason = f"openalex id {aid} not found (404/deleted)"
                else:
                    confidence, reason = "high", f"direct fetch of stored id {aid}"
            elif cohort == "cs_faculty":
                author, reason = match_cs_faculty(name, e.get("institution", ""), cache)
                if author is not None:
                    confidence = "medium"
            else:
                author, reason = match_industry(name, cohort, cache)
                if author is not None:
                    confidence = "medium"

            if author is not None:
                aid = short_id(author["id"])
                if aid not in cache["works"]:
                    per_page = 7 if cohort in REPORT_WORKS else 5
                    cache["works"][aid] = fetch_works(author["id"], per_page)
                fallback = e.get("subfield") or (
                    "computer science" if cohort == "cs_faculty" else None)
                gold_text, n_facts, usable = compose_gold(
                    name, author, cache["works"][aid],
                    exclude_wids=(REPORT_WORKS.get(cohort, ""),),
                    exclude_title_frag=REPORT_TITLE_FRAG.get(cohort),
                    fallback_field=fallback,
                )
                wc = len(gold_text.split())
                if usable == 0:
                    # No verifiable fact beyond the report/context -> not usable.
                    cache["matches"][e["id"]] = {
                        "matched": 0, "confidence": "low", "openalex_id": "",
                        "reason": (f"{reason}; but cluster has no usable facts "
                                   "(no affiliation, no work besides the report)"),
                    }
                else:
                    m = {
                        "matched": 1,
                        "confidence": confidence,
                        "openalex_id": author["id"],
                        "reason": reason,
                        "gold": gold_text,
                        "thin_gold": bool(usable < 3 or wc < 80),
                        "n_facts": n_facts,
                        "word_count": wc,
                    }
                    if looks_like_org(name) or looks_like_org(author["display_name"] or ""):
                        m["not_a_person"] = True
                    cache["matches"][e["id"]] = m
            else:
                cache["matches"][e["id"]] = {
                    "matched": 0, "confidence": "low",
                    "openalex_id": "", "reason": reason or "no match",
                }
        except QuotaExhausted:
            save_cache(cache)
            write_outputs(cache, entities)
            print(f"\nQUOTA_EXHAUSTED at {done} done; checkpointed. "
                  "Re-run to resume when quota resets.", flush=True)
            sys.exit(3)
        except Exception as ex:  # record and continue; rerun will retry
            print(f"  ERROR {e['id']}: {ex}", flush=True)
            cache["matches"][e["id"]] = {
                "matched": 0, "confidence": "low",
                "openalex_id": "", "reason": f"error: {ex}",
            }

        done += 1
        if done % 100 == 0:
            save_cache(cache)
            write_outputs(cache, entities)
            rate = done / max(1e-9, time.time() - t0)
            print(f"checkpoint: {done}/{len(entities)} "
                  f"({rate:.1f} entities/s)", flush=True)

    save_cache(cache)
    gold = write_outputs(cache, entities)

    # summary
    from collections import Counter, defaultdict
    per = defaultdict(Counter)
    for e in entities:
        m = cache["matches"][e["id"]]
        c = per[e["cohort"]]
        c["total"] += 1
        c["matched"] += m["matched"]
        c["thin"] += 1 if m.get("thin_gold") else 0
        c["not_a_person"] += 1 if m.get("not_a_person") else 0
    print("\ncohort, total, matched, match_rate, thin_gold, not_a_person")
    for c in COHORTS:
        s = per[c]
        print(f"{c}, {s['total']}, {s['matched']}, "
              f"{s['matched'] / max(1, s['total']):.3f}, {s['thin']}, {s['not_a_person']}")
    print(f"\ngold entries written: {len(gold)} -> {GOLD_PATH}")
    print(f"match report -> {REPORT_PATH}")


if __name__ == "__main__":
    main()
