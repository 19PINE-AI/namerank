"""Cutoff sensitivity for the appendix: the three oldest panel models'
cutoffs (Mistral-Small-24b 2023-10, Llama-3.1/3.3 2023-12) trail the final
weeks of the event window. Recompute the peak/duration decomposition
(a) excluding events beginning 2023-10..12, (b) excluding those models.
"""
from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
OLD_CUTOFF_MODELS = {"mistral-small-24b", "llama-3.1-8b", "llama-3.3-70b"}


def ols(X, y):
    X1 = np.column_stack([np.ones(len(y)), X])
    b, *_ = np.linalg.lstsq(X1, y, rcond=None)
    yh = X1 @ b
    return b, 1 - ((y - yh) ** 2).sum() / ((y - y.mean()) ** 2).sum()


def betas(rows, nr):
    y = np.array([nr[r["id"]] for r in rows])
    lp = np.array([math.log10(max(float(r["peak_views"]), 1)) for r in rows])
    ld = np.array([math.log10(max(float(r["eff_duration"]), 1.0)) for r in rows])
    zp = (lp - lp.mean()) / lp.std()
    zd = (ld - ld.mean()) / ld.std()
    b, _ = ols(np.column_stack([zp, zd]), y)
    return b[1], b[2]


def main() -> None:
    rows = list(csv.DictReader(open(HERE / "outputs/event_namerank.csv",
                                    encoding="utf-8")))
    nr_full = {r["id"]: float(r["namerank"]) for r in rows}

    bp, bd = betas(rows, nr_full)
    print(f"headline (all events, full panel): peak {bp:+.3f} / dur {bd:+.3f}")

    keep = [r for r in rows if not (int(r["start_year"]) == 2023
                                    and int(r["start_month"]) >= 10)]
    bp1, bd1 = betas(keep, nr_full)
    print(f"excl {len(rows)-len(keep)} late-2023 events (n={len(keep)}): "
          f"peak {bp1:+.3f} / dur {bd1:+.3f}")

    sc = defaultdict(list)
    for x in csv.DictReader(open(HERE / "outputs/event_summary.csv",
                                 encoding="utf-8")):
        if x["model_id"] in OLD_CUTOFF_MODELS:
            continue
        sc[x["entity_id"]].append(float(x["score"]))
    nr_sub = {eid: float(np.mean(v)) for eid, v in sc.items()}
    bp2, bd2 = betas(rows, nr_sub)
    print(f"excl 3 old-cutoff models (all events): peak {bp2:+.3f} / dur {bd2:+.3f}")


if __name__ == "__main__":
    main()
