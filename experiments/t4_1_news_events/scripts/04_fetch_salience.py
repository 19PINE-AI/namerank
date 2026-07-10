"""Fetch Wikimedia daily pageviews for every classified 2021-2023 event.

Salience metrics per event, computed on the 365 days from the first day of
the event's start month (user agent only, en.wikipedia, all-access):
  peak_views      max daily views
  total_views     sum of daily views
  eff_duration    total/peak — the "effective duration" in days
  days_above_10   number of days >= 10% of peak
  tail_daily      mean daily views in days 300-365 (steady-state interest)
"""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote

import requests

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "outputs"
UA = {"User-Agent": "NameRankResearch/1.0 (bojieli@gmail.com) requests"}
BASE = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        "en.wikipedia/all-access/user/{art}/daily/{start}/{end}")


def fetch_views(article: str, y: int, m: int) -> dict | None:
    start = date(y, m, 1)
    end = start + timedelta(days=365)
    url = BASE.format(art=quote(article.replace(" ", "_"), safe=""),
                      start=start.strftime("%Y%m%d"),
                      end=end.strftime("%Y%m%d"))
    for attempt in range(4):
        try:
            r = requests.get(url, headers=UA, timeout=30)
            if r.status_code == 404:
                return {"days": {}}
            r.raise_for_status()
            items = r.json().get("items", [])
            return {"days": {it["timestamp"][:8]: it["views"] for it in items}}
        except Exception:  # noqa: BLE001
            time.sleep(1.5 * (attempt + 1))
    return None


def metrics(days: dict[str, int], y: int, m: int) -> dict:
    if not days:
        return {"peak_views": 0, "total_views": 0, "eff_duration": 0.0,
                "days_above_10": 0, "tail_daily": 0.0, "peak_date": None,
                "n_days": 0}
    vals = sorted(days.items())
    views = [v for _, v in vals]
    peak = max(views)
    total = sum(views)
    start = date(y, m, 1)
    tail_lo = (start + timedelta(days=300)).strftime("%Y%m%d")
    tail = [v for d, v in vals if d >= tail_lo]
    peak_date = max(days, key=days.get)
    return {
        "peak_views": peak,
        "total_views": total,
        "eff_duration": round(total / peak, 2) if peak else 0.0,
        "days_above_10": sum(1 for v in views if v >= 0.1 * peak),
        "tail_daily": round(sum(tail) / len(tail), 1) if tail else 0.0,
        "peak_date": peak_date,
        "n_days": len(views),
    }


def main() -> None:
    classified = json.loads((OUT / "classified.json").read_text())
    summaries = {s["target"]: s for s in json.loads((OUT / "summaries.json").read_text()) if s}
    events = [c for c in classified
              if c.get("is_discrete_event") and c.get("start_year") in (2021, 2022, 2023)
              and 1 <= c.get("start_month", 0) <= 12]
    print(f"{len(events)} events to fetch pageviews for")

    path = OUT / "salience.json"
    done: dict[str, dict] = {}
    if path.exists():
        done = {d["target"]: d for d in json.loads(path.read_text())}
    todo = [e for e in events if e["target"] not in done]
    print(f"{len(todo)} remaining ({len(done)} cached)")

    def work(ev):
        s = summaries.get(ev["target"]) or {}
        art = (s.get("canonical") or ev["target"].replace(" ", "_"))
        res = fetch_views(art, ev["start_year"], ev["start_month"])
        if res is None:
            return None
        m = metrics(res["days"], ev["start_year"], ev["start_month"])
        return {"target": ev["target"], "article": art, **m}

    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(work, e): e["target"] for e in todo}
        for i, fut in enumerate(as_completed(futs)):
            r = fut.result()
            if r:
                done[r["target"]] = r
            if (i + 1) % 100 == 0:
                path.write_text(json.dumps(list(done.values()), ensure_ascii=False))
                print(f"  {i+1}/{len(todo)}")
    path.write_text(json.dumps(list(done.values()), indent=0, ensure_ascii=False))
    nz = sum(1 for d in done.values() if d["total_views"] > 0)
    print(f"Done: {len(done)} fetched, {nz} with nonzero views")


if __name__ == "__main__":
    main()
