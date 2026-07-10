"""Secondary salience source: GDELT 2.0 DOC API news-coverage volume.

For each sampled event, queries the GDELT full-text news index for the event's
name phrase (leading year stripped) and records the timeline of coverage
volume (percent of all monitored articles) over the 12 months from the event
month. Used only as a cross-check on the Wikipedia-pageview salience measure.

GDELT asks for <=1 request / 5 s; we honor that, so ~260 events take ~25 min.
"""
from __future__ import annotations

import json
import re
import time
from datetime import date, timedelta
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent.parent
INP = HERE / "inputs"
OUT = HERE / "outputs"
UA = {"User-Agent": "NameRankResearch/1.0 (bojieli@gmail.com)"}
API = "https://api.gdeltproject.org/api/v2/doc/doc"


def gdelt_query(title: str) -> str:
    t = re.sub(r"^20(21|22|23)(–\d{2,4})?\s+", "", title)   # strip leading year
    t = t.replace("–", " ").replace("—", " ").replace("-", " ")
    t = re.sub(r"\s+", " ", t).strip()
    words = t.split()
    if len(words) > 6:
        t = " ".join(words[:6])
    return f'"{t}"'


def fetch(title: str, y: int, m: int) -> dict | None:
    start = date(y, m, 1)
    end = start + timedelta(days=365)
    params = {
        "query": gdelt_query(title) + " sourcelang:english",
        "mode": "timelinevol",
        "startdatetime": start.strftime("%Y%m%d") + "000000",
        "enddatetime": end.strftime("%Y%m%d") + "000000",
        "format": "json",
    }
    for attempt in range(3):
        try:
            r = requests.get(API, params=params, headers=UA, timeout=40)
            if r.status_code != 200:
                time.sleep(10)
                continue
            j = r.json()
            series = (j.get("timeline") or [{}])[0].get("data", [])
            vals = [pt.get("value", 0.0) for pt in series]
            if not vals:
                return {"gdelt_sum": 0.0, "gdelt_peak": 0.0, "gdelt_n": 0}
            return {"gdelt_sum": round(sum(vals), 4),
                    "gdelt_peak": round(max(vals), 4),
                    "gdelt_n": len(vals)}
        except Exception:  # noqa: BLE001
            time.sleep(10)
    return None


def main() -> None:
    import csv
    rows = list(csv.DictReader(open(INP / "event_metadata.csv", encoding="utf-8")))
    path = OUT / "gdelt.json"
    done: dict[str, dict] = {}
    if path.exists():
        done = json.loads(path.read_text())
    todo = [r for r in rows if r["id"] not in done]
    print(f"{len(todo)} GDELT queries to run ({len(done)} cached)", flush=True)
    for i, r in enumerate(todo):
        res = fetch(r["title"], int(r["start_year"]), int(r["start_month"]))
        if res is not None:
            done[r["id"]] = {"query": gdelt_query(r["title"]), **res}
        if (i + 1) % 10 == 0:
            path.write_text(json.dumps(done, indent=0))
            print(f"  {i+1}/{len(todo)} ({sum(1 for v in done.values() if v['gdelt_sum']>0)} nonzero)", flush=True)
        time.sleep(15)
    path.write_text(json.dumps(done, indent=0))
    nz = sum(1 for v in done.values() if v["gdelt_sum"] > 0)
    print(f"Done: {len(done)} fetched, {nz} with nonzero coverage")


if __name__ == "__main__":
    main()
