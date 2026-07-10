"""Fetch REST page summaries for all candidates (extract, description, canonical title)."""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote

import requests

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "outputs"
UA = {"User-Agent": "NameRankResearch/1.0 (bojieli@gmail.com) requests"}


def fetch(target: str) -> dict | None:
    url = ("https://en.wikipedia.org/api/rest_v1/page/summary/"
           + quote(target.replace(" ", "_"), safe=""))
    for attempt in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=20,
                             params={"redirect": "true"})
            if r.status_code == 404:
                return None
            r.raise_for_status()
            j = r.json()
            return {
                "target": target,
                "title": j.get("title"),
                "canonical": (j.get("titles") or {}).get("canonical"),
                "description": j.get("description"),
                "type": j.get("type"),
                "extract": j.get("extract"),
            }
        except Exception:  # noqa: BLE001
            time.sleep(1 + attempt)
    return None


def main() -> None:
    cands = json.loads((OUT / "candidates.json").read_text())
    done: dict[str, dict] = {}
    path = OUT / "summaries.json"
    if path.exists():
        done = {d["target"]: d for d in json.loads(path.read_text())}
    todo = [c["target"] for c in cands if c["target"] not in done]
    print(f"{len(todo)} summaries to fetch ({len(done)} cached)")
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(fetch, t): t for t in todo}
        for i, fut in enumerate(as_completed(futs)):
            res = fut.result()
            t = futs[fut]
            done[t] = res if res else {"target": t, "type": "missing"}
            if (i + 1) % 300 == 0:
                path.write_text(json.dumps(list(done.values()), ensure_ascii=False))
                print(f"  {i+1}/{len(todo)}")
    path.write_text(json.dumps(list(done.values()), indent=0, ensure_ascii=False))
    ok = sum(1 for d in done.values() if d.get("type") == "standard")
    print(f"Done: {len(done)} total, {ok} standard articles")


if __name__ == "__main__":
    main()
