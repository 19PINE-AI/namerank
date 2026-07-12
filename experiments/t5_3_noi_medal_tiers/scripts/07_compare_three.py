"""Three-way comparison of gold/judge methodologies on the NOI tier study.

  v1  boilerplate gold + judge v1          (tier_per_entity.csv)
  c   career-long canonical gold + judge v1 (tier_per_entity_canonical.csv)
  v2  length-normalized gold + judge v2     (tier_per_entity_v2.csv)

Reports tier means, tier gaps, the gold-length confound (corr of gold length
with NameRank -- should vanish under v2), and the Bojie within-person spread.
"""
import csv
import json
import math
import statistics as st
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "outputs"


def load(name):
    rows = {}
    for r in csv.DictReader(open(OUT / name)):
        if r.get("tier") in ("gold", "silver", "bronze") and r["control"] == "False":
            r["nr"] = float(r["namerank"])
            r["gw"] = float(r["gold_words"]) if r.get("gold_words") else None
            rows[r["entity_id"]] = r
    return rows


def corr(xs, ys):
    mx, my = st.mean(xs), st.mean(ys)
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    den = math.sqrt(sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys))
    return num / den if den else 0.0


def tmean(rows, t):
    v = [r["nr"] for r in rows.values() if r["tier"] == t]
    return st.mean(v) if v else float("nan")


def main():
    v1 = load("tier_per_entity.csv")
    c = load("tier_per_entity_canonical.csv")
    v2 = load("tier_per_entity_v2.csv")
    sets = [("v1 boilerplate+judgeV1", v1),
            ("c  career-long+judgeV1", c),
            ("v2 normalized+judgeV2", v2)]

    print(f"{'method':26s} {'gold':>6} {'silver':>7} {'bronze':>7} "
          f"{'g-s':>7} {'g-b':>7} {'len-corr':>9}")
    for label, rows in sets:
        g, s, b = tmean(rows, "gold"), tmean(rows, "silver"), tmean(rows, "bronze")
        lc = ""
        gws = [(r["gw"], r["nr"]) for r in rows.values() if r.get("gw")]
        if gws:
            lc = f"{corr([x for x, _ in gws], [y for _, y in gws]):+.3f}"
        print(f"{label:26s} {g:>6.3f} {s:>7.3f} {b:>7.3f} "
              f"{g-s:>+7.3f} {g-b:>+7.3f} {lc:>9}")

    # top medalists under v2
    top = sorted(v2.values(), key=lambda r: -r["nr"])[:12]
    print("\nTop medalists under v2 (normalized gold + echo-discounting judge):")
    for r in top:
        gw = int(r["gw"]) if r.get("gw") else 0
        print(f"  {r['nr']:.3f}  {r['tier'][0]}  {r['entity_name']}  [{gw}w]")

    for tag in ("", "_v2"):
        f = OUT / f"bojie_convergence{tag}.json"
        if f.exists():
            d = json.loads(f.read_text())
            vals = [x["namerank_vs_canonical"] for x in d.values()]
            lab = "v2" if tag else "career-long"
            print(f"\nBojie one-gold-per-person spread ({lab}): "
                  f"{min(vals):.3f}-{max(vals):.3f} (spread {max(vals)-min(vals):.3f})")


if __name__ == "__main__":
    main()
