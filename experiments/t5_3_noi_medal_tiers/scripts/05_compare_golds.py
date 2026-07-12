"""Compare the boilerplate-gold vs canonical-gold tier picture.

Reads tier_per_entity.csv (boilerplate golds, v1) and
tier_per_entity_canonical.csv (web-researched golds) and reports how the
medal-tier finding moves under the corrected gold methodology, plus the
Bojie within-person convergence.
"""
import csv
import json
import statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "outputs"


def load(path):
    rows = {}
    for r in csv.DictReader(open(path)):
        if r.get("tier") in ("gold", "silver", "bronze") and r["control"] == "False":
            rows[r["entity_id"]] = r
    return rows


def tier_means(rows):
    out = {}
    for t in ("gold", "silver", "bronze"):
        v = [float(r["namerank"]) for r in rows.values() if r["tier"] == t]
        out[t] = (len(v), st.mean(v), st.median(v))
    return out


def main():
    old = load(OUT / "tier_per_entity.csv")
    new = load(OUT / "tier_per_entity_canonical.csv")

    print("== Tier means: boilerplate gold (v1)  ->  canonical gold ==")
    om, nm = tier_means(old), tier_means(new)
    for t in ("gold", "silver", "bronze"):
        n, o, _ = om[t]
        _, c, _ = nm[t]
        print(f"  {t:7s} n={n:3d}   {o:.3f}  ->  {c:.3f}   ({c-o:+.3f})")

    gaps = lambda m: (m["gold"][1] - m["silver"][1], m["gold"][1] - m["bronze"][1])
    print(f"\n  gold-silver gap : {gaps(om)[0]:+.3f}  ->  {gaps(nm)[0]:+.3f}")
    print(f"  gold-bronze gap : {gaps(om)[1]:+.3f}  ->  {gaps(nm)[1]:+.3f}")

    # biggest movers
    movers = []
    for eid in new:
        if eid in old:
            d = float(new[eid]["namerank"]) - float(old[eid]["namerank"])
            movers.append((d, new[eid]["entity_name"], new[eid]["tier"],
                           float(old[eid]["namerank"]), float(new[eid]["namerank"]),
                           new[eid].get("gold_words"), new[eid].get("gold_sources")))
    movers.sort(reverse=True)
    print("\n== Biggest gainers under canonical gold (recognition now credited) ==")
    for d, name, t, o, c, gw, gs in movers[:8]:
        print(f"  {o:.3f} -> {c:.3f} ({d:+.3f}) {t:6s} {name}  [gold {gw}w/{gs}src]")
    print("== Biggest drops (echo credit removed) ==")
    for d, name, t, o, c, gw, gs in movers[-6:]:
        print(f"  {o:.3f} -> {c:.3f} ({d:+.3f}) {t:6s} {name}  [gold {gw}w/{gs}src]")

    # gold-length correlation (fame -> longer gold -> harder coverage?)
    import math
    xs = [float(new[e].get("gold_words") or 0) for e in new]
    ys = [float(new[e]["namerank"]) for e in new]
    mx, my = st.mean(xs), st.mean(ys)
    num = sum((a-mx)*(b-my) for a, b in zip(xs, ys))
    den = math.sqrt(sum((a-mx)**2 for a in xs)*sum((b-my)**2 for b in ys))
    print(f"\n  corr(gold length, canonical NameRank) = {num/den:+.3f}  "
          f"(gold words: median {int(st.median(xs))}, range {int(min(xs))}-{int(max(xs))})")

    conv = OUT / "bojie_convergence.json"
    if conv.exists():
        c = json.loads(conv.read_text())
        print("\n== Bojie Li: one canonical gold, three probe contexts ==")
        for eid, d in c.items():
            print(f"  {d['namerank_vs_canonical']:.3f}  {d['context'][:55]}")
        vals = [d["namerank_vs_canonical"] for d in c.values()]
        print(f"  spread {max(vals)-min(vals):.3f} "
              f"(vs 0.09/0.35/0.41 under three different golds)")


if __name__ == "__main__":
    main()
