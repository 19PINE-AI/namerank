"""Collect candidate 2021-2023 news events from English Wikipedia year pages.

Sources:
  - Global year pages: "2021", "2022", "2023" (Events sections)
  - Country year pages: "<year> in <country>" for a region-balanced country list

Output: outputs/candidates.json — one record per (link, source line), deduped
by link target, with the source line text and any leading date retained.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "outputs"
OUT.mkdir(exist_ok=True)

API = "https://en.wikipedia.org/w/api.php"
UA = {"User-Agent": "NameRankResearch/1.0 (bojieli@gmail.com) requests"}

YEARS = [2021, 2022, 2023]
COUNTRIES = [
    "India", "China", "Japan", "Indonesia", "Pakistan", "Bangladesh",
    "the Philippines", "Vietnam", "South Korea",
    "Nigeria", "Kenya", "South Africa", "Egypt", "Ethiopia",
    "Brazil", "Mexico", "Argentina", "Colombia", "Peru", "Chile",
    "France", "Germany", "Italy", "Spain", "Poland", "the United Kingdom",
    "Russia", "Ukraine", "Turkey",
    "the United States", "Canada", "Australia",
]

MONTHS = ("January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December")

# Heuristic: keep a link if the target looks like a discrete-event article.
EVENT_WORDS = re.compile(
    r"(earthquake|flood|cyclone|hurricane|typhoon|storm|tornado|wildfire|"
    r"eruption|landslide|drought|heat wave|blizzard|tsunami|"
    r"crash|collision|derailment|disaster|explosion|fire|sinking|collapse|"
    r"stampede|crush|spill|blackout|outage|"
    r"election|referendum|coup|protest|riot|unrest|uprising|crisis|"
    r"invasion|offensive|battle|siege|war|conflict|insurgency|clashes|"
    r"attack|bombing|shooting|massacre|hostage|assassination|kidnapping|"
    r"trial|verdict|scandal|impeachment|inauguration|summit|agreement|"
    r"strike|shutdown|bankruptcy|acquisition|merger|launch|mission|"
    r"pandemic|outbreak|epidemic|"
    r"olympics|world cup|championship|final|games|super bowl|grand prix|"
    r"funeral|coronation|wedding|jubilee|census|expo|convention)",
    re.IGNORECASE)
YEAR_PREFIX = re.compile(r"^20(21|22|23)[ –-]")

SKIP_TARGETS = re.compile(
    r"^(January|February|March|April|May|June|July|August|September|October|"
    r"November|December)( \d+)?$|^\d{4}$|^COVID-19 pandemic$|^List of|"
    r"^Timeline of|^Category:|^File:|^Portal:|^Wikipedia:", re.IGNORECASE)

LINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")


def get_wikitext(title: str) -> str | None:
    r = requests.get(API, params={
        "action": "query", "prop": "revisions", "rvprop": "content",
        "rvslots": "main", "titles": title, "format": "json",
        "formatversion": "2", "redirects": "1",
    }, headers=UA, timeout=30)
    r.raise_for_status()
    pages = r.json()["query"]["pages"]
    if not pages or "missing" in pages[0]:
        return None
    try:
        return pages[0]["revisions"][0]["slots"]["main"]["content"]
    except (KeyError, IndexError):
        return None


def events_section(wikitext: str) -> str:
    """Slice out the Events section(s) of a year page."""
    lines = wikitext.split("\n")
    keep, active = [], False
    for ln in lines:
        m = re.match(r"^(=+)\s*(.*?)\s*=+\s*$", ln)
        if m:
            depth, head = len(m.group(1)), m.group(2).strip()
            if depth == 2:
                active = head.lower().startswith("event")
            # month sub-heads (=== January ===) stay within Events
            continue
        if active:
            keep.append(ln)
    return "\n".join(keep)


def parse_events(section: str, source: str) -> list[dict]:
    out = []
    for ln in section.split("\n"):
        if not ln.strip().startswith("*"):
            continue
        text = ln.lstrip("* ").strip()
        # leading date like [[March 23]] or March 23 –
        date = None
        dm = re.match(r"^\[?\[?(%s) (\d{1,2})\]?\]?" % "|".join(MONTHS), text)
        if dm:
            date = f"{dm.group(1)} {dm.group(2)}"
        for target in LINK.findall(ln):
            t = target.strip()
            if SKIP_TARGETS.match(t):
                continue
            if not (EVENT_WORDS.search(t) or YEAR_PREFIX.match(t)):
                continue
            out.append({"target": t, "line_date": date, "line": text[:300],
                        "source": source})
    return out


def main() -> None:
    pages = [str(y) for y in YEARS]
    pages += [f"{y} in {c}" for y in YEARS for c in COUNTRIES]

    cands: list[dict] = []
    for i, page in enumerate(pages):
        try:
            wt = get_wikitext(page)
        except Exception as e:  # noqa: BLE001
            print(f"  [WARN] {page}: {e}")
            continue
        if not wt:
            print(f"  [MISS] {page}")
            continue
        sec = events_section(wt)
        got = parse_events(sec, page)
        cands.extend(got)
        print(f"  {page}: {len(got)} candidate links")
        time.sleep(0.3)

    # dedupe by target, keep first occurrence (global pages come first)
    seen, dedup = set(), []
    for c in cands:
        key = c["target"].lower()
        if key in seen:
            continue
        seen.add(key)
        dedup.append(c)

    (OUT / "candidates.json").write_text(
        json.dumps(dedup, indent=1, ensure_ascii=False))
    print(f"\nTotal: {len(cands)} raw, {len(dedup)} unique targets "
          f"-> {OUT/'candidates.json'}")


if __name__ == "__main__":
    main()
