#!/usr/bin/env python3
"""NameRank — measure how recognizable a named entity is to a panel of LLMs.

NameRank asks a *panel* of language models one open-ended question about a
named entity ("Tell me what you know about {name}, who is {context}") and
counts how many of them genuinely RECOGNIZE the entity. The score is a single
number in [0, 1]:

    NameRank = (# panel models that recognize the entity) / (panel size)

Recognition is decided by an *open-book* judge (the canonical NameRank v3
"tightened" recognition rubric): a model recognizes the entity only if its
response states at least one specific, non-guessable, beyond-the-context fact
that is true of *this* entity (verified against the gold answer or the judge's
own knowledge). Restating the probe context, generic praise, plausible-sounding
hallucination, and refusals all score as NOT recognized.

The gold answer (the reference the judge disambiguates and anchors against) is
either supplied by you (--gold / --gold-file) or generated on the fly by a
web-search LLM agent (Gemini + Google Search, or an OpenRouter :online model).

Like the IKP tool, this is a single self-contained script: it prints every
model's raw response and verdict, then the NameRank. Point --api-base/--api-key
at any OpenAI-compatible endpoint; the default is OpenRouter.

Examples
--------
  # One entity, auto-generated gold, full 37-model panel (needs OPENROUTER_API_KEY)
  python namerank.py --name "Bojie Li" \
      --context "a computer scientist and AI researcher"

  # Supply your own gold answer
  python namerank.py --name "Ada Lovelace" --context "a 19th-century mathematician" \
      --gold "English mathematician; wrote the first algorithm intended for Babbage's Analytical Engine; daughter of Lord Byron."

  # Fast pass on a small sub-panel, show every response
  python namerank.py --name "Tri Dao" --context "a machine learning researcher" \
      --sample 8 --inspect

  # Batch: a JSON list of {name, context, [gold]}
  python namerank.py --entities people.json -o results.json

  # Just generate and print the gold answer, probe nothing
  python namerank.py --name "Tri Dao" --context "an ML researcher" --gold-only

  # Look at the panel / probe / judge without spending tokens
  python namerank.py --show-panel
  python namerank.py --show-probe
"""

import argparse
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

import httpx

# ── Baked-in protocol constants ─────────────────────────────────────────────
# The open-ended probe. {name} and {context} are filled per entity. The context
# is a short disambiguation ("who is ..."); the judge gives ZERO credit for
# merely restating it, so it cannot inflate the score.
PROBE_TEMPLATE = (
    'Tell me what you know about {name}, who is {context}. '
    'If you do not recognize this entity, respond with "unknown". '
    'Limit your response to about 150 words.'
)

# Canonical open-book "recognition" judge (v3, tightened / anti-confabulation).
# Fields: {name}, {context}, {gold_answer}, {response}. Returns strict JSON.
JUDGE_PROMPT = """ENTITY: {name}

PROBE CONTEXT (already given to the model in the question; repeating it earns nothing):
{context}

GOLD ANSWER (reference facts that IDENTIFY which specific entity this is -- use it to disambiguate the person/thing and as a correctness anchor):
{gold_answer}

MODEL RESPONSE (to be graded):
{response}

Judge whether the model genuinely RECOGNIZES this specific entity.

RECOGNIZED = true only if the response states at least one SPECIFIC, NON-GUESSABLE fact that is:
  (a) TRUE of THIS entity, established by EITHER (i) the gold answer, OR (ii) your own independent knowledge -- meaning you actually recognize this fact as true of this specific entity, not merely that it sounds plausible; and
  (b) not derivable from the probe context; and
  (c) about the SAME entity the gold identifies (same person/thing), not a different entity that shares the name.

CRITICAL ASYMMETRY between crediting and refuting:
  - To CREDIT a fact not in the gold, you must POSITIVELY know it is true of this entity. If you do not already know this entity, you CANNOT verify novel claims about it -- a plausible-sounding but unverified specific is exactly what a model hallucinates about obscure or non-existent people, and it scores FALSE. When you do not know the entity, ignore your own knowledge and grade STRICTLY against the gold answer only.
  - To REFUTE, use all of your knowledge freely: if you know the response describes a same-name DIFFERENT entity, or states something false about this entity, do not credit it.

ANTI-CONFABULATION RULE (important -- you do NOT have reliable per-individual memory of most competition participants, fellowship recipients, or minor-paper authors):
  - For an entity who is a COMPETITION PARTICIPANT (olympiad/contest medalist), a FELLOWSHIP/AWARD recipient, or the author/subject of a NON-FAMOUS paper: do NOT credit fine-grained biographical minutiae via "your own knowledge" -- e.g. other-year participations, secondary-competition medals, exact scores or ranks, specific host-city trivia, or co-author names of minor works. You cannot reliably recall these for individuals, and asserting you "verified them against official records" is confabulation. For such entities, credit ONLY facts that are present in the GOLD ANSWER, or a MAJOR, widely-documented public achievement you are highly confident about (a well-known company they founded, a famous theorem/tool bearing their name, a professorship at a named university you actually recognize them for).
  - The credential OUTCOME itself is guessable and does NOT count on its own: given a probe saying someone "participated in" a competition, asserting they "won a gold medal / a prize / the fellowship" is a low-entropy guess and is NOT recognition unless accompanied by a genuinely-known, non-guessable specific about THIS person.

Further guards (RECOGNIZED = false):
  - Wrong entity: specifics consistent with a different same-name person/thing.
  - Hallucination / fabrication-dominated response. (One genuinely-verified correct specific still counts even if a minor detail is off; a response that is mostly wrong does not.)
  - Guessable/generic: broad field, nationality, an employer/school implied by the context or inferable from the name, generic praise, restating the context. For a PAPER, naming its journal/venue alone does NOT count (inferable from topic); a real author name, specific result, or exact contribution does -- but only if you actually know the paper.
  - Refusal / "I don't have information" / hedged non-answer.
  - When genuinely unsure whether a fact is specific-and-verified-true, default to false.

Also output coverage and accuracy in [0,1] for diagnostics.

Output ONLY JSON: {{"recognized": <true|false>, "coverage": <0.0-1.0>, "accuracy": <0.0-1.0>, "rationale": "<one sentence: name the qualifying fact and how it was verified (gold or your knowledge), or why none qualifies>"}}"""

# Web-search gold-generation agent instruction (length-disciplined, namesake-guarded).
GOLD_INSTR = """You write reference profiles for a recognition benchmark. You are given an entity NAME and a DISAMBIGUATION (a short description that identifies WHICH entity is meant -- its purpose is to pin identity against namesakes).

Search the web, then write ONE factual profile of this specific entity.

NAMESAKE GUARD (most important rule): Many names are shared by multiple people. Include a fact about the entity's education, career, or later life ONLY IF a source explicitly ties that fact to THIS SAME individual through a matching identifier -- the same school, the same competition/olympiad record, a consistent graduation year, or an explicit statement. A person who merely shares the name but has no sourced connection to the DISAMBIGUATION is a DIFFERENT person; exclude them entirely.

LENGTH DISCIPLINE (important for fair measurement): Write AT MOST {maxwords} words, and select the entity's MOST DISTINCTIVE, IDENTIFYING facts to fill that budget -- the specific named achievements, works, roles, or affiliations a knowledgeable person would name first. Do NOT try to be exhaustive: a famous person is summarized to their top few facts, not given a longer profile than an obscure one. Prefer specific named facts over generic description. Do NOT restate the disambiguation to fill space.

RULES:
1. State only facts verifiable from search results tied to THIS individual. Never invent, guess, or speculate.
2. Prioritize source-linked facts that go BEYOND the disambiguation (named works, roles, companies, achievements, affiliations) -- these are what the benchmark scores.
3. If you cannot verify any beyond-disambiguation facts with explicit source-linkage, write ONLY the facts the disambiguation itself guarantees. A one-sentence profile is the CORRECT, honest answer for a genuinely low-profile entity -- do not pad, do not generalize about their cohort, do not invent a plausible career.
4. If you cannot confidently distinguish this entity from namesakes, restrict to what the disambiguation guarantees.
5. Neutral third person, no hedging ("appears to be", "likely").

Output only the profile text."""

# The canonical NameRank panel (paper's 37-model panel). openrouter_id is the
# slug for OpenRouter; on other OpenAI-compatible endpoints, override with
# --models or --panel. thinking=True passes reasoning:{effort:medium}.
DEFAULT_PANEL = [
    {"id": "gpt-5.5-think",            "openrouter_id": "openai/gpt-5.5",                          "thinking": True},
    {"id": "gpt-5.4",                  "openrouter_id": "openai/gpt-5.4",                          "thinking": False},
    {"id": "gpt-5.3",                  "openrouter_id": "openai/gpt-5.3-chat",                     "thinking": False},
    {"id": "claude-opus-4.6-think",    "openrouter_id": "anthropic/claude-opus-4.6",              "thinking": True},
    {"id": "claude-sonnet-4.6-think",  "openrouter_id": "anthropic/claude-sonnet-4.6",            "thinking": True},
    {"id": "gemini-3.1-pro",           "openrouter_id": "google/gemini-3.1-pro-preview",           "thinking": False},
    {"id": "gemini-3-flash-think",     "openrouter_id": "google/gemini-3-flash-preview",           "thinking": True},
    {"id": "gemini-2.5-pro-think",     "openrouter_id": "google/gemini-2.5-pro",                   "thinking": True},
    {"id": "grok-4.20-think",          "openrouter_id": "x-ai/grok-4.20",                          "thinking": True},
    {"id": "grok-4",                   "openrouter_id": "x-ai/grok-4",                             "thinking": False},
    {"id": "deepseek-v4-pro-think",    "openrouter_id": "deepseek/deepseek-v4-pro",               "thinking": True},
    {"id": "deepseek-v3.2-think",      "openrouter_id": "deepseek/deepseek-v3.2",                 "thinking": True},
    {"id": "qwen3.5-397b-a17b-think",  "openrouter_id": "qwen/qwen3.5-397b-a17b",                 "thinking": True},
    {"id": "kimi-k2.6-think",          "openrouter_id": "moonshotai/kimi-k2.6",                   "thinking": True},
    {"id": "kimi-k2",                  "openrouter_id": "moonshotai/kimi-k2",                     "thinking": False},
    {"id": "glm-5.1-think",            "openrouter_id": "z-ai/glm-5.1",                           "thinking": True},
    {"id": "glm-4.7-think",            "openrouter_id": "z-ai/glm-4.7",                           "thinking": True},
    {"id": "llama-4-maverick",         "openrouter_id": "meta-llama/llama-4-maverick",             "thinking": False},
    {"id": "mistral-large",            "openrouter_id": "mistralai/mistral-large-2411",            "thinking": False},
    {"id": "deepseek-v4-flash-think",  "openrouter_id": "deepseek/deepseek-v4-flash",             "thinking": True},
    {"id": "qwen3-235b-a22b-think",    "openrouter_id": "qwen/qwen3-235b-a22b",                   "thinking": True},
    {"id": "qwen3-32b-think",          "openrouter_id": "qwen/qwen3-32b",                         "thinking": True},
    {"id": "glm-4-32b",                "openrouter_id": "z-ai/glm-4-32b",                         "thinking": False},
    {"id": "llama-3.3-70b",            "openrouter_id": "meta-llama/llama-3.3-70b-instruct",       "thinking": False},
    {"id": "mistral-medium-3.1",       "openrouter_id": "mistralai/mistral-medium-3.1",            "thinking": False},
    {"id": "gemma-4-31b",              "openrouter_id": "google/gemma-4-31b-it",                   "thinking": False},
    {"id": "ernie-4.5-300b-a47b",      "openrouter_id": "baidu/ernie-4.5-300b-a47b",              "thinking": False},
    {"id": "minimax-m2.7-think",       "openrouter_id": "minimax/minimax-m2.7",                   "thinking": True},
    {"id": "qwen3-8b-think",           "openrouter_id": "qwen/qwen3-8b",                          "thinking": True},
    {"id": "phi-4",                    "openrouter_id": "microsoft/phi-4",                        "thinking": False},
    {"id": "gemma-3-12b",              "openrouter_id": "google/gemma-3-12b-it",                   "thinking": False},
    {"id": "llama-3.1-8b",             "openrouter_id": "meta-llama/llama-3.1-8b-instruct",        "thinking": False},
    {"id": "mistral-small-24b",        "openrouter_id": "mistralai/mistral-small-24b-instruct-2501","thinking": False},
    {"id": "gpt-oss-20b-think",        "openrouter_id": "openai/gpt-oss-20b",                     "thinking": True},
    {"id": "llama-3.2-1b",             "openrouter_id": "meta-llama/llama-3.2-1b-instruct",        "thinking": False},
    {"id": "gemma-3-4b",               "openrouter_id": "google/gemma-3-4b-it",                   "thinking": False},
    {"id": "ministral-3b",             "openrouter_id": "mistralai/ministral-3b-2512",             "thinking": False},
]

DEFAULT_JUDGE_MODEL = "google/gemini-3-flash-preview"
DEFAULT_GOLD_MODEL = "google/gemini-3-flash-preview"
GOLD_MAXWORDS = 55

REFUSAL_PATTERNS = [
    "i don't know", "i'm not sure", "i am not sure", "i don't recognize",
    "i'm not familiar", "not familiar with", "no information",
    "i cannot find", "cannot identify", "i have no information",
    "未知", "我不知道", "我不认识", "不熟悉", "没有相关信息",
]

# ── Terminal styling ────────────────────────────────────────────────────────
GREEN, RED, YELLOW, DIM, RESET = "\033[92m", "\033[91m", "\033[93m", "\033[90m", "\033[0m"


# ── Helpers ─────────────────────────────────────────────────────────────────
def strip_thinking(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    if cleaned.startswith("<think>"):
        end = cleaned.find("</think>")
        cleaned = cleaned[end + 8:].strip() if end >= 0 else ""
    return cleaned or text


def is_refusal(text: str) -> bool:
    if not text or len(text.strip()) < 5:
        return True
    t = text.strip().lower()
    if t in ("unknown", "unknown.", "未知", "未知。"):
        return True
    if len(t) < 80:
        return any(pat in t for pat in REFUSAL_PATTERNS)
    return False


def extract_json(text: str):
    """Best-effort parse of a JSON object out of a model's text."""
    if not text:
        return None
    # Strip a ```json … ``` (or bare ```) code fence if the model wrapped its output.
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if fenced:
        text = fenced.group(1)
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


def salvage_judge_json(raw: str):
    """Recover the judge's verdict fields from a truncated / malformed JSON string
    (e.g. a length-capped completion that cut off mid-object). Returns a dict with
    at least `recognized`, or None if even that cannot be found. This keeps a
    truncated-but-decisive judge response from silently scoring as NOT recognized."""
    if not raw:
        return None
    m = re.search(r'"recognized"\s*:\s*(true|false)', raw, flags=re.IGNORECASE)
    if not m:
        return None
    out = {"recognized": m.group(1).lower() == "true"}
    for key in ("coverage", "accuracy"):
        km = re.search(rf'"{key}"\s*:\s*(-?[0-9]*\.?[0-9]+)', raw)
        out[key] = float(km.group(1)) if km else 0.0
    rm = re.search(r'"rationale"\s*:\s*"((?:[^"\\]|\\.)*)"', raw)
    out["rationale"] = rm.group(1) if rm else "[recovered from truncated judge output]"
    return out


def truncate_words(text: str, n: int) -> str:
    words = (text or "").split()
    return " ".join(words[:n]) if len(words) > n else (text or "")


def slugify(text: str, maxlen: int = 48) -> str:
    """Filesystem-friendly slug from an entity name (keeps unicode letters)."""
    s = re.sub(r"\s+", "-", (text or "").strip().lower())
    s = re.sub(r"[^\w\-]", "", s, flags=re.UNICODE).strip("-_")
    return (s[:maxlen].strip("-_") or "entity")


def save_entity_dump(entity_out: dict, args) -> str:
    """Write one entity's full run (every model response + every judge response)
    to a descriptively-named JSON file in the cwd. Returns the path written."""
    slug = slugify(entity_out["name"])
    path = Path.cwd() / f"namerank_{slug}.json"
    dump = {
        "name": entity_out["name"],
        "context": entity_out["context"],
        "gold": entity_out["gold"],
        "gold_meta": entity_out["gold_meta"],
        "probe": PROBE_TEMPLATE.format(name=entity_out["name"], context=entity_out["context"]),
        "judge_prompt_template": JUDGE_PROMPT,
        "judge_model": args.judge_model,
        "namerank": entity_out["namerank"],
        "depth": entity_out["depth"],
        "n_recognized": entity_out["n_recognized"],
        "panel_size": entity_out["panel_size"],
        # each record carries the model's raw response AND the judge's raw response
        "records": entity_out["records"],
    }
    path.write_text(json.dumps(dump, indent=2, ensure_ascii=False))
    return str(path)


# ── Chat completion (OpenAI-compatible) ─────────────────────────────────────
def chat(api_base: str, api_key: str, model: str, messages: list,
         thinking: bool = False, temperature: float = 0.0,
         json_mode: bool = False, plugins=None, timeout: int = 120,
         max_tokens: int = None) -> str:
    payload = {"model": model, "messages": messages, "temperature": temperature}
    if thinking:
        payload["reasoning"] = {"effort": "medium"}
    if max_tokens:
        payload["max_tokens"] = max_tokens
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    if plugins:
        payload["plugins"] = plugins
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    with httpx.Client(timeout=timeout) as http:
        for attempt in range(4):
            try:
                r = http.post(f"{api_base.rstrip('/')}/chat/completions",
                              headers=headers, json=payload)
                if r.status_code == 200:
                    data = r.json()
                    if "choices" not in data:
                        return ""
                    msg = data["choices"][0]["message"]
                    content = msg.get("content") or ""
                    if not content and msg.get("reasoning"):
                        content = msg["reasoning"]
                    return content
                if r.status_code in (429, 502, 503, 504):
                    time.sleep(2 ** (attempt + 1))
                    continue
                return ""
            except httpx.TimeoutException:
                # Honor the timeout budget: retry once for a transient stall,
                # then give up rather than hang for 4×timeout.
                if attempt >= 1:
                    return ""
                continue
            except Exception:
                time.sleep(2 * (attempt + 1))
    return ""


# ── Gold generation (web-search agent) ──────────────────────────────────────
def generate_gold_gemini(name: str, context: str, model: str, maxwords: int) -> dict:
    """Canonical gold: Gemini + native Google Search grounding (needs google-genai)."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    resp = client.models.generate_content(
        model=model,
        contents=f"NAME: {name}\nDISAMBIGUATION: {context}\n\nWrite the profile.",
        config=types.GenerateContentConfig(
            system_instruction=GOLD_INSTR.format(maxwords=maxwords),
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.0,
        ),
    )
    text = (resp.text or "").strip()
    gm = resp.candidates[0].grounding_metadata
    n_src = len(gm.grounding_chunks) if gm and gm.grounding_chunks else 0
    return {"gold": text, "n_sources": n_src, "backend": f"gemini:{model}"}


def generate_gold_openrouter(name: str, context: str, api_base: str, api_key: str,
                             model: str, maxwords: int) -> dict:
    """Fallback gold: an OpenRouter :online model (web plugin) via one API key."""
    online = model if model.endswith(":online") else f"{model}:online"
    text = chat(
        api_base, api_key, online,
        messages=[
            {"role": "system", "content": GOLD_INSTR.format(maxwords=maxwords)},
            {"role": "user", "content": f"NAME: {name}\nDISAMBIGUATION: {context}\n\nWrite the profile."},
        ],
        temperature=0.0, timeout=180,
        plugins=[{"id": "web", "max_results": 5}],
    ).strip()
    return {"gold": text, "n_sources": None, "backend": f"openrouter-online:{model}"}


def make_gold(name, context, backend, gold_model, api_base, api_key, maxwords):
    """backend in {auto, gemini, openrouter}."""
    if backend == "auto":
        backend = "gemini" if (os.environ.get("GEMINI_API_KEY") and _has_genai()) else "openrouter"
    if backend == "gemini":
        return generate_gold_gemini(name, context, gold_model.split("/")[-1].replace(":online", ""),
                                    maxwords)
    return generate_gold_openrouter(name, context, api_base, api_key, gold_model, maxwords)


def _has_genai() -> bool:
    try:
        import google.genai  # noqa: F401
        return True
    except Exception:
        return False


# ── Judge (open-book recognition) ───────────────────────────────────────────
def judge_recognition(api_base, api_key, judge_model, name, context, gold, response,
                      timeout: int = 60) -> dict:
    if is_refusal(response):
        return {"recognized": False, "coverage": 0.0, "accuracy": 0.0,
                "rationale": "refusal / non-answer", "judge_raw": None}
    prompt = JUDGE_PROMPT.format(name=name, context=context, gold_answer=gold, response=response)
    # Two attempts: judge JSON is occasionally cut off (a length-capped completion,
    # e.g. when the judge model spends output budget on reasoning tokens). An explicit
    # generous max_tokens keeps the ~70-token verdict well inside any provider cap;
    # salvage_judge_json recovers a decisive verdict from a partial object; and a
    # retry covers a transient truncation. Only after all of that do we give up.
    raw = ""
    for attempt in range(2):
        raw = chat(api_base, api_key, judge_model,
                   messages=[{"role": "user", "content": prompt}],
                   thinking=False, temperature=0.0, json_mode=True,
                   timeout=timeout, max_tokens=1500)
        p = extract_json(raw)
        if not p or "recognized" not in p:
            p = salvage_judge_json(raw)
        if p and "recognized" in p:
            return {
                "recognized": bool(p.get("recognized")),
                "coverage": float(p.get("coverage", 0.0) or 0.0),
                "accuracy": float(p.get("accuracy", 0.0) or 0.0),
                "rationale": str(p.get("rationale", "")),
                "judge_raw": raw,
            }
    return {"recognized": False, "coverage": 0.0, "accuracy": 0.0,
            "rationale": f"[JUDGE-PARSE-ERROR] {raw[:120]}", "judge_raw": raw}


# ── Panel resolution ────────────────────────────────────────────────────────
def resolve_panel(args) -> list:
    if args.panel:
        panel = json.loads(Path(args.panel).read_text())
    else:
        panel = [dict(m) for m in DEFAULT_PANEL]
    if args.models:
        wanted = [s.strip() for s in args.models.split(",") if s.strip()]
        # match against id OR openrouter_id; if not found in default panel, treat
        # the raw string as a bare model id (for a custom endpoint).
        by_key = {}
        for m in panel:
            by_key[m["id"]] = m
            by_key[m.get("openrouter_id", m["id"])] = m
        picked = []
        for w in wanted:
            if w in by_key:
                picked.append(by_key[w])
            else:
                picked.append({"id": w, "openrouter_id": w, "thinking": args.thinking})
        panel = picked
    if args.sample and args.sample < len(panel):
        # deterministic stratified-ish sample: keep a spread across the panel order
        step = len(panel) / args.sample
        panel = [panel[int(i * step)] for i in range(args.sample)]
    return panel


# ── Display ─────────────────────────────────────────────────────────────────
def display_entity(name, context, gold, gold_meta, records, inspect):
    n = len(records)
    n_rec = sum(1 for r in records if r["recognized"])
    namerank = n_rec / n if n else 0.0
    mean_depth = sum(r["coverage"] * r["accuracy"] for r in records) / n if n else 0.0
    n_refuse = sum(1 for r in records if r["is_refusal"])

    print()
    print("  ╔══════════════════════════════════════════════════════════╗")
    print("  ║  NameRank Result                                         ║")
    print("  ╠══════════════════════════════════════════════════════════╣")
    print(f"  ║  Entity:    {name[:42]:42s}  ║")
    print(f"  ║  NameRank:  {namerank:.3f}  ({n_rec}/{n} models recognize){' ' * (24 - len(str(n_rec)) - len(str(n)))}║")
    print(f"  ║  Depth:     {mean_depth:.3f}  (mean coverage×accuracy){' ' * 15}║")
    print("  ╚══════════════════════════════════════════════════════════╝")

    print(f"\n  {DIM}Context:{RESET} {context}")
    src = gold_meta.get("n_sources")
    src_s = f", {src} web sources" if src is not None else ""
    print(f"  {DIM}Gold ({gold_meta.get('backend','user-supplied')}{src_s}):{RESET} {gold}")

    print(f"\n  {'':2}{'Model':30s} {'Recognized':>11} {'Cov':>5} {'Acc':>5}")
    print(f"  {'─' * 68}")
    for r in sorted(records, key=lambda x: (not x["recognized"], -x["coverage"] * x["accuracy"])):
        if r["recognized"]:
            mark, col = "✓ yes", GREEN
        elif r["is_refusal"]:
            mark, col = "· refuse", YELLOW
        else:
            mark, col = "✗ no", RED
        print(f"  {col}{'●'}{RESET} {r['model_id']:30s} {col}{mark:>9}{RESET} "
              f"{r['coverage']:>5.2f} {r['accuracy']:>5.2f}")

    if n_refuse:
        print(f"\n  {DIM}{n_refuse}/{n} responded 'unknown' / refused.{RESET}")

    if inspect:
        print(f"\n  {'─' * 90}\n  RESPONSES\n  {'─' * 90}")
        for r in sorted(records, key=lambda x: (not x["recognized"])):
            col = GREEN if r["recognized"] else (YELLOW if r["is_refusal"] else RED)
            tag = "RECOGNIZED" if r["recognized"] else ("REFUSAL" if r["is_refusal"] else "not recognized")
            print(f"\n  {col}[{tag}]{RESET} {r['model_id']}")
            print(f"    {DIM}response:{RESET} {r['response']}")
            print(f"    {DIM}judge:{RESET} {r['rationale']}")
    print()
    return namerank, mean_depth


def display_batch(entity_results):
    print(f"\n  {'Entity':32s} {'NameRank':>9} {'Recog':>7} {'Depth':>7}")
    print(f"  {'─' * 60}")
    for e in sorted(entity_results, key=lambda x: -x["namerank"]):
        print(f"  {e['name'][:32]:32s} {e['namerank']:>9.3f} "
              f"{e['n_recognized']}/{e['panel_size']:<5} {e['depth']:>7.3f}")
    print()


# ── Main ────────────────────────────────────────────────────────────────────
def build_arg_parser():
    p = argparse.ArgumentParser(
        description="NameRank — measure how recognizable a named entity is to a panel of LLMs.",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)

    ent = p.add_argument_group("Entity (choose --name/--context OR --entities)")
    ent.add_argument("--name", help="Entity name to probe")
    ent.add_argument("--context", help="Short disambiguation ('who is ...'): pins identity, not scored")
    ent.add_argument("--entities", metavar="FILE",
                     help="JSON list of {name, context, [gold]} for a batch run")

    gold = p.add_argument_group("Gold answer")
    gold.add_argument("--gold", metavar="TEXT", help="Supply the gold answer directly")
    gold.add_argument("--gold-file", metavar="FILE", help="Read the gold answer from a text file")
    gold.add_argument("--gold-backend", choices=["auto", "gemini", "openrouter"], default="auto",
                      help="Web-search agent for auto gold (default: auto — gemini if GEMINI_API_KEY else openrouter)")
    gold.add_argument("--gold-model", default=DEFAULT_GOLD_MODEL,
                      help=f"Model for gold generation (default: {DEFAULT_GOLD_MODEL})")
    gold.add_argument("--gold-maxwords", type=int, default=GOLD_MAXWORDS,
                      help=f"Length cap for generated golds (default: {GOLD_MAXWORDS})")
    gold.add_argument("--gold-only", action="store_true",
                      help="Generate/print the gold answer and exit (no probing)")

    api = p.add_argument_group("Panel API (OpenAI-compatible; default OpenRouter)")
    api.add_argument("--api-base", default="https://openrouter.ai/api/v1", metavar="URL")
    api.add_argument("--api-key", metavar="KEY", help="Default: $OPENROUTER_API_KEY")
    api.add_argument("--models", metavar="LIST",
                     help="Comma-separated subset of the panel (ids or model slugs)")
    api.add_argument("--panel", metavar="FILE", help="Custom panel JSON (list of {id, openrouter_id, thinking})")
    api.add_argument("--thinking", action="store_true",
                     help="Force reasoning mode for models given via --models on a custom endpoint")

    judge = p.add_argument_group("Judge")
    judge.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL,
                       help=f"Open-book recognition judge (default: {DEFAULT_JUDGE_MODEL})")
    judge.add_argument("--judge-api-base", metavar="URL",
                       help="Judge endpoint (default: same as --api-base)")
    judge.add_argument("--judge-api-key", metavar="KEY", help="Judge key (default: --api-key)")

    ev = p.add_argument_group("Evaluation / output")
    ev.add_argument("--sample", "-n", type=int, metavar="N", help="Probe only N models from the panel")
    ev.add_argument("--workers", "-w", type=int, default=12, help="Parallel workers (default: 12)")
    ev.add_argument("--timeout", type=int, default=60, metavar="SEC",
                    help="Per-request timeout in seconds for panel + judge calls (default: 60)")
    ev.add_argument("--output", "-o", metavar="FILE",
                    help="Save the combined run to this JSON path (default: auto-named file(s) in the cwd)")
    ev.add_argument("--no-save", action="store_true",
                    help="Disable the automatic per-entity response dumps")
    ev.add_argument("--inspect", action="store_true", help="Print every model's full response + judge rationale")

    info = p.add_argument_group("Info (no tokens spent)")
    info.add_argument("--show-panel", action="store_true", help="Print the default panel and exit")
    info.add_argument("--show-probe", action="store_true", help="Print the probe + judge prompt and exit")
    return p


def run_entity(name, context, gold, gold_meta, panel, args,
               api_base, api_key, judge_base, judge_key):
    probe = PROBE_TEMPLATE.format(name=name, context=context)
    total = len(panel)
    lock = threading.Lock()
    state = {"done": 0, "recognized": 0}
    records = []

    # Header for this entity's live stream. Show the probe/gold the panel sees,
    # then print each model's verdict on its own line as it returns — no
    # carriage-return overwriting, so nothing is clobbered in the scrollback.
    src = gold_meta.get("n_sources")
    src_s = f", {src} web sources" if src is not None else ""
    print(f"\n  {DIM}Entity:{RESET} {name}  {DIM}—{RESET} {context}")
    print(f"  {DIM}Gold ({gold_meta.get('backend', 'user-supplied')}{src_s}):{RESET} {gold}")
    print(f"  {DIM}Probing {total} models (judge: {args.judge_model}, "
          f"timeout: {args.timeout}s)…{RESET}")
    print(f"  {'─' * 74}")

    def emit(rec):
        """Print one model's verdict line. Suppressed once the panel is closed so
        a late straggler thread can't scribble past the printed summary."""
        with lock:
            if state.get("closed"):
                return
            state["done"] += 1
            if rec["recognized"]:
                state["recognized"] += 1
                mark, col = "✓ yes    ", GREEN
            elif rec["is_refusal"]:
                mark, col = "· refuse ", YELLOW
            else:
                mark, col = "✗ no     ", RED
            note = (rec.get("rationale", "") or "")
            note = (note[:60] + "…") if len(note) > 61 else note
            print(f"  [{state['done']:>2}/{total}] {col}{mark}{RESET} "
                  f"{rec['model_id']:28s} {DIM}{note}{RESET}")

    def work(m):
        # A worker must never propagate: one model erroring or timing out cannot be
        # allowed to sink the whole panel's results. Any failure becomes a non-answer.
        try:
            resp = truncate_words(
                chat(api_base, api_key, m["openrouter_id"],
                     messages=[{"role": "user", "content": probe}],
                     thinking=m.get("thinking", False), timeout=args.timeout),
                200)
            verdict = judge_recognition(judge_base, judge_key, args.judge_model,
                                        name, context, gold, resp, timeout=args.timeout)
            rec = {"model_id": m["id"], "openrouter_id": m["openrouter_id"],
                   "response": resp, "is_refusal": is_refusal(resp), **verdict}
        except Exception as e:
            rec = {"model_id": m["id"], "openrouter_id": m["openrouter_id"],
                   "response": "", "is_refusal": True, "recognized": False,
                   "coverage": 0.0, "accuracy": 0.0,
                   "rationale": f"error: {type(e).__name__}: {e}", "judge_raw": None}
        emit(rec)
        return rec

    # Collect results as they arrive, but never block indefinitely on a hung tail:
    # as long as at least one model keeps reporting within `quiet` seconds we keep
    # waiting; once the panel goes silent that long, the stragglers are counted as
    # timeouts and the score is printed immediately. `quiet` allows one full retry
    # cycle of a genuinely-slow model before it's cut.
    quiet = args.timeout * 2 + 15
    ex = ThreadPoolExecutor(max_workers=args.workers)
    fut_to_m = {ex.submit(work, m): m for m in panel}
    pending = set(fut_to_m)
    try:
        while pending:
            done, pending = wait(pending, timeout=quiet, return_when=FIRST_COMPLETED)
            if not done:
                break  # no completion in `quiet`s → treat the rest as hung
            for f in done:
                records.append(f.result())
    finally:
        with lock:
            state["closed"] = True
        ex.shutdown(wait=False, cancel_futures=True)

    # Account for any models that never returned so the panel size stays honest.
    for f, m in fut_to_m.items():
        if f in pending:
            records.append({"model_id": m["id"], "openrouter_id": m["openrouter_id"],
                            "response": "", "is_refusal": True, "recognized": False,
                            "coverage": 0.0, "accuracy": 0.0,
                            "rationale": "timed out — no response within panel deadline",
                            "judge_raw": None})
            n_timeout = len(records)
            print(f"  [{n_timeout:>2}/{total}] {YELLOW}· timeout {RESET} "
                  f"{m['id']:28s} {DIM}no response within deadline{RESET}")

    n_rec = sum(1 for r in records if r["recognized"])
    print(f"  {'─' * 74}")
    print(f"  {DIM}Done: {n_rec}/{total} recognized.{RESET}")
    return records


def resolve_gold(name, context, entity_gold, args, api_base, api_key):
    if entity_gold:
        return entity_gold, {"backend": "user-supplied", "n_sources": None}
    if args.gold:
        return args.gold, {"backend": "user-supplied", "n_sources": None}
    if args.gold_file:
        return Path(args.gold_file).read_text().strip(), {"backend": "user-supplied", "n_sources": None}
    g = make_gold(name, context, args.gold_backend, args.gold_model,
                  api_base, api_key, args.gold_maxwords)
    return g["gold"], {"backend": g["backend"], "n_sources": g["n_sources"]}


def main():
    args = build_arg_parser().parse_args()

    if args.show_panel:
        print(f"\n  NameRank panel: {len(DEFAULT_PANEL)} models\n  {'─' * 60}")
        for m in DEFAULT_PANEL:
            t = " (thinking)" if m["thinking"] else ""
            print(f"    {m['id']:30s} {m['openrouter_id']}{t}")
        print()
        return
    if args.show_probe:
        print("\n  PROBE TEMPLATE\n  " + "─" * 60)
        print("  " + PROBE_TEMPLATE.replace("\n", "\n  "))
        print("\n  RECOGNITION JUDGE PROMPT\n  " + "─" * 60)
        print("  " + JUDGE_PROMPT.replace("\n", "\n  "))
        print()
        return

    api_base = args.api_base
    api_key = args.api_key or os.environ.get("OPENROUTER_API_KEY", "")
    judge_base = args.judge_api_base or api_base
    judge_key = args.judge_api_key or api_key

    if "openrouter" in api_base and not api_key:
        sys.exit("Error: OPENROUTER_API_KEY not set. Use --api-key or export it.")

    # Assemble the entity work-list
    if args.entities:
        entities = json.loads(Path(args.entities).read_text())
    elif args.name and args.context:
        entities = [{"name": args.name, "context": args.context, "gold": None}]
    else:
        build_arg_parser().print_help()
        return

    # gold-only shortcut
    if args.gold_only:
        for e in entities:
            gold, meta = resolve_gold(e["name"], e["context"], e.get("gold"), args, api_base, api_key)
            print(f"\n  {e['name']}  {DIM}({meta['backend']}"
                  f"{', ' + str(meta['n_sources']) + ' sources' if meta['n_sources'] is not None else ''}){RESET}")
            print(f"  {gold}")
        print()
        return

    panel = resolve_panel(args)
    print(f"\n  Probing {len(panel)} models on {len(entities)} entit"
          f"{'y' if len(entities) == 1 else 'ies'} (judge: {args.judge_model})")

    all_out = []
    entity_summ = []
    saved_paths = []
    for e in entities:
        name, context = e["name"], e["context"]
        gold, gold_meta = resolve_gold(name, context, e.get("gold"), args, api_base, api_key)
        if not gold:
            print(f"  {YELLOW}skip {name}: empty gold{RESET}")
            continue
        records = run_entity(name, context, gold, gold_meta, panel, args,
                             api_base, api_key, judge_base, judge_key)
        if len(entities) == 1:
            namerank, depth = display_entity(name, context, gold, gold_meta, records, args.inspect)
        else:
            n_rec = sum(1 for r in records if r["recognized"])
            namerank = n_rec / len(records) if records else 0.0
            depth = sum(r["coverage"] * r["accuracy"] for r in records) / len(records) if records else 0.0
        n_rec = sum(1 for r in records if r["recognized"])
        entity_summ.append({"name": name, "namerank": namerank, "depth": depth,
                            "n_recognized": n_rec, "panel_size": len(records)})
        entity_out = {"name": name, "context": context, "gold": gold, "gold_meta": gold_meta,
                      "namerank": namerank, "depth": depth, "n_recognized": n_rec,
                      "panel_size": len(records), "records": records}
        all_out.append(entity_out)

        # Auto-save every entity's full responses + judge responses for inspection.
        if not args.no_save:
            saved_paths.append(save_entity_dump(entity_out, args))

    if len(entities) > 1:
        display_batch(entity_summ)

    # Explicit --output: the combined run; otherwise the per-entity dumps above.
    if args.output:
        Path(args.output).write_text(json.dumps({
            "probe_template": PROBE_TEMPLATE,
            "judge_model": args.judge_model,
            "panel_size": len(panel),
            "entities": all_out,
        }, indent=2, ensure_ascii=False))
        print(f"  Combined results saved to {args.output}")

    if saved_paths:
        print(f"  {DIM}Saved per-entity responses + judge verdicts for inspection:{RESET}")
        for pth in saved_paths:
            print(f"    {pth}")
    print()


if __name__ == "__main__":
    main()
