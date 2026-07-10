"""Flag recurring-series instances vs singular events (name-uniqueness axis).

An event is a *series instance* if its title is a year-templated name whose
base recurs as another year's Wikipedia article (e.g. "2022 Malaysian general
election" <-> "2018 Malaysian general election"). Such names are templates,
not unique names: the corpus contains many near-identical strings that differ
only in the year slot. The main study's predecessor (IKP) identified *name
uniqueness* as a propagation mechanism for researchers; this flag tests the
event-domain analogue objectively.

Detection: for titles carrying a leading "20XX " (or "20XX–YY ") year prefix,
probe the REST summary endpoint for the same base title under nearby years
(y-4..y+2, skipping y). Any standard-article hit => recurring. Titles without
a year affix are checked for Roman-numeral edition markers (e.g. Super Bowl
LVI); otherwise singular.

Output: outputs/recurring_flags.json  {id: {"recurring": bool, "evidence": str}}
"""
from __future__ import annotations

import csv
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote

import requests

HERE = Path(__file__).resolve().parent.parent
INP, OUT = HERE / "inputs", HERE / "outputs"
UA = {"User-Agent": "NameRankResearch/1.0 (bojieli@gmail.com) requests"}

ROMAN = re.compile(r"\b([IVXL]{1,7})\b")
ROMAN_MAP = {"I": 1, "V": 5, "X": 10, "L": 50}


def roman_to_int(s: str) -> int:
    total, prev = 0, 0
    for ch in reversed(s):
        v = ROMAN_MAP[ch]
        total = total - v if v < prev else total + v
        prev = max(prev, v)
    return total


def int_to_roman(n: int) -> str:
    vals = [(50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"),
            (4, "IV"), (1, "I")]
    out = ""
    for v, sym in vals:
        while n >= v:
            out += sym
            n -= v
    return out


def exists(title: str) -> bool:
    url = ("https://en.wikipedia.org/api/rest_v1/page/summary/"
           + quote(title.replace(" ", "_"), safe=""))
    for _ in range(2):
        try:
            r = requests.get(url, headers=UA, timeout=15,
                             params={"redirect": "true"})
            if r.status_code == 404:
                return False
            r.raise_for_status()
            return r.json().get("type") == "standard"
        except Exception:  # noqa: BLE001
            time.sleep(1)
    return False


def check(title: str) -> dict:
    # Any 4-digit year token in the title: substitute nearby years.
    # dy down to -6 covers 4/5/6-year election and tournament cycles.
    for ym in re.finditer(r"20\d\d", title):
        y = int(ym.group(0))
        for dy in (-1, -2, -3, -4, -5, -6, 1, 2):
            cand = title[:ym.start()] + str(y + dy) + title[ym.end():]
            if exists(cand):
                return {"recurring": True, "evidence": cand}
    # Ordinal edition markers: "94th Academy Awards"
    om = re.search(r"\b(\d{1,3})(st|nd|rd|th)\b", title)
    if om:
        n = int(om.group(1))
        for dn in (-1, 1):
            k = n + dn
            suf = ("th" if 10 <= k % 100 <= 20 else
                   {1: "st", 2: "nd", 3: "rd"}.get(k % 10, "th"))
            cand = title[:om.start()] + f"{k}{suf}" + title[om.end():]
            if exists(cand):
                return {"recurring": True, "evidence": cand}
    # Roman-numeral editions: "Super Bowl LVI"
    rm = ROMAN.search(title)
    if rm and rm.group(1) not in ("I",):
        n = roman_to_int(rm.group(1))
        if 2 <= n <= 60:
            for dn in (-1, 1):
                cand = title[:rm.start(1)] + int_to_roman(n + dn) + title[rm.end(1):]
                if exists(cand):
                    return {"recurring": True, "evidence": cand}
    return {"recurring": False, "evidence": ""}


def main() -> None:
    rows = list(csv.DictReader(open(INP / "event_metadata.csv", encoding="utf-8")))
    path = OUT / "recurring_flags.json"
    done: dict[str, dict] = {}
    if path.exists():
        done = json.loads(path.read_text())
    todo = [r for r in rows if r["id"] not in done]
    print(f"{len(todo)} events to flag ({len(done)} cached)")
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(check, r["title"]): r["id"] for r in todo}
        for i, fut in enumerate(as_completed(futs)):
            done[futs[fut]] = fut.result()
            if (i + 1) % 50 == 0:
                path.write_text(json.dumps(done, indent=0))
                print(f"  {i+1}/{len(todo)}")
    path.write_text(json.dumps(done, indent=0))
    n_rec = sum(1 for v in done.values() if v["recurring"])
    print(f"Done: {n_rec}/{len(done)} flagged recurring")


if __name__ == "__main__":
    main()
