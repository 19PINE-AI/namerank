"""Regression analysis: which bibliometric predictor best explains NameRank
in the long_tail_researcher_openalex cohort?

Compares (sole-predictor R² and joint OLS) for:
  log1p(h_index), log1p(cited_by_count), log1p(fractional_citations),
  log1p(first_last_citations), log1p(n_works), log1p(mean_authors).

Plus a per-decile mean NameRank table for each predictor (Appendix-F style).

Outputs:
  regression_results.csv  -- sole-R^2 + joint OLS coefficients
  decile_comparison.csv   -- mean NameRank by decile of each predictor
"""
from __future__ import annotations

import csv
import json
import math
import statistics
from pathlib import Path

import numpy as np

EXP_DIR = Path("/home/ubuntu/namerank/experiments/t2_9_fractional_citations")
NR_CSV = Path("/home/ubuntu/namerank/data/analysis/namerank_per_entity.csv")
WORKS_CSV = EXP_DIR / "author_works_metrics.csv"

PREDICTORS = [
    "h_index",
    "cited_by_count",
    "fractional_citations",
    "first_last_citations",
    "n_works",
    "mean_authors",
]


def load_data() -> list[dict]:
    nr = {
        row["entity_id"]: float(row["namerank"])
        for row in csv.DictReader(NR_CSV.open())
    }
    rows: list[dict] = []
    with WORKS_CSV.open() as f:
        for r in csv.DictReader(f):
            eid = r["entity_id"]
            if eid not in nr:
                continue
            try:
                row = dict(
                    entity_id=eid,
                    name=r["name"],
                    namerank=nr[eid],
                    h_index=float(r["h_index"]),
                    cited_by_count=float(r["cited_by_count"]),
                    fractional_citations=float(r["fractional_citations"]),
                    first_last_citations=float(r["first_last_citations"]),
                    n_works=float(r["n_works"]),
                    mean_authors=float(r["mean_authors"]),
                    n_first_or_last=float(r["n_first_or_last"]),
                    total_citations_from_works=float(r["total_citations_from_works"]),
                )
            except ValueError:
                continue
            # only keep authors with at least one work fetched
            if row["n_works"] <= 0:
                continue
            rows.append(row)
    return rows


def pearson(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 3:
        return 0.0
    mx, my = x.mean(), y.mean()
    num = ((x - mx) * (y - my)).sum()
    den = math.sqrt(((x - mx) ** 2).sum() * ((y - my) ** 2).sum())
    return num / den if den > 0 else 0.0


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    rx = np.argsort(np.argsort(x))
    ry = np.argsort(np.argsort(y))
    return pearson(rx.astype(float), ry.astype(float))


def ols(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, float]:
    """Plain OLS with intercept. Returns (coefs incl intercept, R²)."""
    Xb = np.column_stack([np.ones(len(X)), X])
    # Use pinv for safety with collinear inputs.
    beta, *_ = np.linalg.lstsq(Xb, y, rcond=None)
    yhat = Xb @ beta
    ss_res = ((y - yhat) ** 2).sum()
    ss_tot = ((y - y.mean()) ** 2).sum()
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return beta, r2


def sole_predictor_table(data: list[dict]) -> list[dict]:
    y = np.array([r["namerank"] for r in data])
    out = []
    for p in PREDICTORS:
        raw = np.array([r[p] for r in data])
        lg = np.log1p(raw)
        r_raw = pearson(raw, y)
        r_log = pearson(lg, y)
        sp = spearman(raw, y)
        out.append(
            dict(
                predictor=p,
                n=len(data),
                pearson_raw=round(r_raw, 4),
                r2_raw=round(r_raw**2, 4),
                pearson_log1p=round(r_log, 4),
                r2_log1p=round(r_log**2, 4),
                spearman=round(sp, 4),
            )
        )
    return out


def joint_ols(data: list[dict]) -> dict:
    y = np.array([r["namerank"] for r in data])
    feat_names = [f"log1p_{p}" for p in PREDICTORS]
    X = np.column_stack(
        [np.log1p(np.array([r[p] for r in data])) for p in PREDICTORS]
    )
    beta, r2 = ols(X, y)
    # Standardized coefficients to compare magnitudes.
    sd_X = X.std(axis=0)
    sd_y = y.std()
    std_beta = beta[1:] * (sd_X / sd_y) if sd_y > 0 else beta[1:] * 0
    return dict(
        r2=r2,
        intercept=float(beta[0]),
        coefs={n: float(b) for n, b in zip(feat_names, beta[1:])},
        std_coefs={n: float(b) for n, b in zip(feat_names, std_beta)},
    )


def two_way_table(data: list[dict]) -> list[dict]:
    """For each (h, X) pair, report marginal R² gain of X over h_index alone."""
    y = np.array([r["namerank"] for r in data])
    h = np.log1p(np.array([r["h_index"] for r in data]))
    _, r2_h = ols(h.reshape(-1, 1), y)
    rows = []
    rows.append(dict(model="log1p_h_index", r2=round(r2_h, 4), delta_over_h=0.0))
    for p in PREDICTORS:
        if p == "h_index":
            continue
        xp = np.log1p(np.array([r[p] for r in data]))
        # sole
        _, r2_sole = ols(xp.reshape(-1, 1), y)
        # joint with h
        _, r2_joint = ols(np.column_stack([h, xp]), y)
        rows.append(
            dict(
                model=f"log1p_h_index + log1p_{p}",
                r2=round(r2_joint, 4),
                delta_over_h=round(r2_joint - r2_h, 4),
                sole_r2=round(r2_sole, 4),
            )
        )
    return rows


def decile_table(data: list[dict]) -> list[dict]:
    rows = []
    for p in PREDICTORS:
        items = sorted(data, key=lambda r: r[p])
        n = len(items)
        chunk = max(1, n // 10)
        for d in range(10):
            sub = items[d * chunk : (d + 1) * chunk] if d < 9 else items[d * chunk :]
            if not sub:
                continue
            rows.append(
                dict(
                    predictor=p,
                    decile=d + 1,
                    n=len(sub),
                    mean_predictor=round(
                        statistics.mean([r[p] for r in sub]), 3
                    ),
                    mean_namerank=round(
                        statistics.mean([r["namerank"] for r in sub]), 4
                    ),
                    median_namerank=round(
                        statistics.median([r["namerank"] for r in sub]), 4
                    ),
                )
            )
    return rows


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    if not rows:
        return
    fn = fieldnames or list(rows[0].keys())
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main() -> None:
    data = load_data()
    print(f"n authors with works data and NameRank: {len(data)}")

    sole = sole_predictor_table(data)
    print("\n=== Sole-predictor R² (log1p) ===")
    for r in sole:
        print(
            f"  {r['predictor']:<22}  R²_log={r['r2_log1p']:.3f}  "
            f"R²_raw={r['r2_raw']:.3f}  ρ={r['spearman']:+.3f}"
        )

    joint = joint_ols(data)
    print(f"\n=== Joint OLS (all {len(PREDICTORS)} log1p predictors) ===")
    print(f"  R² = {joint['r2']:.3f}")
    print("  raw coefs:")
    for k, v in joint["coefs"].items():
        print(f"    {k:<28} {v:+.4f}")
    print("  standardized coefs:")
    for k, v in joint["std_coefs"].items():
        print(f"    {k:<28} {v:+.4f}")

    two_way = two_way_table(data)
    print("\n=== Marginal R² of adding each feature on top of log1p(h_index) ===")
    for r in two_way:
        extra = f"  sole_R²={r['sole_r2']:.3f}" if "sole_r2" in r else ""
        print(f"  {r['model']:<50}  R²={r['r2']:.3f}  Δ={r['delta_over_h']:+.4f}{extra}")

    deciles = decile_table(data)

    # Write outputs
    reg_rows: list[dict] = []
    for r in sole:
        reg_rows.append(
            {
                "section": "sole_predictor",
                "predictor": r["predictor"],
                "metric": "r2_log1p",
                "value": r["r2_log1p"],
                "extra": json.dumps(
                    {
                        "pearson_raw": r["pearson_raw"],
                        "r2_raw": r["r2_raw"],
                        "pearson_log1p": r["pearson_log1p"],
                        "spearman": r["spearman"],
                        "n": r["n"],
                    }
                ),
            }
        )
    reg_rows.append(
        {
            "section": "joint_ols",
            "predictor": "ALL",
            "metric": "r2",
            "value": round(joint["r2"], 4),
            "extra": json.dumps(joint["coefs"]),
        }
    )
    reg_rows.append(
        {
            "section": "joint_ols_standardized",
            "predictor": "ALL",
            "metric": "std_coefs",
            "value": round(joint["r2"], 4),
            "extra": json.dumps(joint["std_coefs"]),
        }
    )
    for r in two_way:
        reg_rows.append(
            {
                "section": "two_way_vs_h_index",
                "predictor": r["model"],
                "metric": "r2",
                "value": r["r2"],
                "extra": json.dumps(
                    {
                        "delta_over_h": r["delta_over_h"],
                        "sole_r2": r.get("sole_r2"),
                    }
                ),
            }
        )
    write_csv(
        EXP_DIR / "regression_results.csv",
        reg_rows,
        ["section", "predictor", "metric", "value", "extra"],
    )

    write_csv(EXP_DIR / "decile_comparison.csv", deciles)
    print(f"\nWrote {EXP_DIR/'regression_results.csv'}")
    print(f"Wrote {EXP_DIR/'decile_comparison.csv'}")


if __name__ == "__main__":
    main()
