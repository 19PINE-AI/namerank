"""T2.8 — Gendered-name attenuation in NameRank.

Question: does NameRank attenuate for woman-coded first names compared to
man-coded first names, controlling for bibliometric impact?

Pipeline:
  1. Heuristic gender labeling (gender-guesser + East-Asian-name flag).
  2. Headline gender gap on cs_faculty (n=698).
  3. Replication on long_tail_researcher_openalex (n=771), with h-index decile adjustment.
  4. Matched pairs on cs_faculty (country + institution proxy).
  5. Cross-cohort breakdown for n>=20 per side.
  6. Robustness: ambiguous-name drop rate.

Outputs (CSV/MD in this directory):
  entity_gender.csv, gender_gap_by_cohort.csv, matched_pairs_cs_faculty.csv,
  h_index_adjusted_gap.csv.
"""
from __future__ import annotations

import csv
import json
import math
import re
import statistics
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import gender_guesser.detector as gg

ROOT = Path("/home/ubuntu/namerank")
OUT = ROOT / "experiments" / "t2_8_gendered_names"
ENTITIES_FILE = ROOT / "data" / "inputs" / "pilot_entities.json"
NR_FILE = ROOT / "data" / "analysis" / "namerank_per_entity.csv"

PERSON_COHORTS = {
    "cs_faculty", "long_tail_researcher_openalex", "long_tail_researcher_ikp",
    "imo_gold", "ioi_gold", "msra_phd_fellowship", "cmo_china_gold",
    "cpho_china_first_prize", "noi_china_gold", "icpc_world_finals_gold",
    "rhodes_scholar", "putnam_fellow", "gpt5_system_card_author",
    "deepseek_v3_author", "reference_pilot",
    "mid_tier_writer", "mid_tier_athlete", "mid_tier_actor",
    "mid_tier_historical", "mid_tier_politician", "mid_tier_journalist",
    "mid_tier_musician", "mid_tier_artist", "mid_tier_medical",
    "mid_tier_founder", "mid_tier_filmmaker", "mid_tier_architect",
    "mid_tier_chef", "mid_tier_comedian", "mid_tier_religious",
    "mid_tier_vc", "mid_tier_activist",
}

# East-Asian (Chinese/Korean/Vietnamese) surnames whose romanization triggers
# "ambiguous" flag. Single-syllable pinyin given names are unreliable for
# gender-from-name, so we conservatively drop any entity whose name contains
# any of these surnames.
EA_SURNAMES = set("""
Wang Li Zhang Liu Chen Yang Huang Zhao Wu Zhou Xu Sun Ma Zhu Hu Guo Lin He Gao
Liang Zheng Luo Song Xie Tang Han Cao Deng Xiao Feng Zeng Cheng Yu Yuan
Pan Du Dai Xia Zhong Wen Tian Ren Jiang Shi Bai Cui Kong Lu Lai Yan Yin Mao
Mu Cai Ye Jia Fang Wei Ding Shen Qiu Qi Qin Qu Niu Long Lou Luan
Tan Tu Wan Weng Xi Xian Xiang Xin Xing Xiong Xue Yao Yi Ying Yong You Yue Yun
Zan Zang Zhai Zhan Zhen Zhi Zhuang Zhuo Zou Lv Lue Tao Geng Bian Pang Mei Meng
Min Mo Nie Ni Pi Pian Qiao Ran Rui Ruan Shao Shu Shuang Sui Tong
Ouyang Sima Zhuge Shangguan Dongfang
Tsai Tsao Tseng Tsui Tso Hsu Hsiao Hsieh Hsing Hsiung Hsuan Hsueh
Lei Cong Ji Wo Jin
Kim Lee Park Choi Jeong Jung Cho Yoon Yoo Han Shin Kang Lim Oh Hwang Bae Nam
Sim Ko Seo Hong Moon Ahn
Nguyen Tran Le Pham Hoang Phan Vu Vo Dang Bui Do Duong Truong Ngo Ho Dinh
""".split())

DETECTOR = gg.Detector(case_sensitive=False)


# ---------------------------------------------------------------------------
# Gender labeling
# ---------------------------------------------------------------------------

def _strip_brackets(name: str) -> str:
    name = re.sub(r"\[[^\]]*\]", "", name)
    name = re.sub(r"\([^\)]*\)", "", name)
    return name.strip()


def _ascii_fold(s: str) -> str:
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _tokens(name: str) -> list[str]:
    name = _strip_brackets(name)
    return [t for t in re.split(r"[\s,]+", name) if t]


def _is_ea_name(toks: list[str]) -> bool:
    for t in toks:
        clean = _ascii_fold(t.strip(".,-")).capitalize()
        if clean in EA_SURNAMES:
            return True
    return False


def predict_gender(name: str) -> tuple[str, str]:
    """Return (gender, confidence_tag).

    gender in {'male', 'female', 'ambiguous'}.
    confidence_tag explains the labeling decision.
    """
    toks = _tokens(name)
    if not toks:
        return "ambiguous", "no_tokens"

    # Drop suffix tokens.
    toks = [t for t in toks if t.rstrip(".").lower()
            not in ("jr", "sr", "ii", "iii", "iv", "phd", "dr", "mr", "ms", "mrs")]
    if not toks:
        return "ambiguous", "only_suffix"

    # East-Asian-surname rule: gender-from-romanized-pinyin is unreliable
    # because most pinyin tokens (Wei, Min, Hui, Ling, …) are unisex.
    if _is_ea_name(toks):
        return "ambiguous", "east_asian_name"

    # Pick the first non-initial token as the "first name" candidate.
    candidate = None
    for t in toks:
        cf = t.strip(".,'").split("-")[0]
        if len(cf) >= 2:
            candidate = _ascii_fold(cf).capitalize()
            break
    if candidate is None:
        return "ambiguous", "initial_only"

    g = DETECTOR.get_gender(candidate)
    if g == "male":
        return "male", "high"
    if g == "female":
        return "female", "high"
    if g == "mostly_male":
        return "male", "medium"
    if g == "mostly_female":
        return "female", "medium"
    if g == "andy":
        return "ambiguous", "androgynous"
    return "ambiguous", "unknown_to_detector"


# ---------------------------------------------------------------------------
# Stats helpers
# ---------------------------------------------------------------------------

def welch_t(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Welch's t-test; returns (t, two-sided p) using normal approx."""
    if len(xs) < 2 or len(ys) < 2:
        return float("nan"), float("nan")
    mx, my = statistics.mean(xs), statistics.mean(ys)
    vx = statistics.variance(xs)
    vy = statistics.variance(ys)
    nx, ny = len(xs), len(ys)
    se = math.sqrt(vx / nx + vy / ny)
    if se == 0:
        return float("nan"), float("nan")
    t = (mx - my) / se
    # Normal approx for p (sample sizes are large enough)
    p = 2 * (1 - _norm_cdf(abs(t)))
    return t, p


def _norm_cdf(z: float) -> float:
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def paired_t(diffs: list[float]) -> tuple[float, float]:
    if len(diffs) < 2:
        return float("nan"), float("nan")
    m = statistics.mean(diffs)
    sd = statistics.stdev(diffs)
    if sd == 0:
        return float("nan"), float("nan")
    se = sd / math.sqrt(len(diffs))
    t = m / se
    p = 2 * (1 - _norm_cdf(abs(t)))
    return t, p


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_data():
    ents = json.loads(ENTITIES_FILE.read_text())
    by_id = {e["id"]: e for e in ents}
    nr = {}
    with open(NR_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            nr[row["entity_id"]] = float(row["namerank"])
    return ents, by_id, nr


def write_entity_gender(ents, by_id, nr):
    rows = []
    for e in ents:
        if e["cohort"] not in PERSON_COHORTS:
            continue
        g, conf = predict_gender(e["name"])
        rows.append({
            "id": e["id"],
            "name": e["name"],
            "cohort": e["cohort"],
            "predicted_gender": g,
            "confidence": conf,
            "namerank": nr.get(e["id"]),
            "h_index": e.get("h_index"),
            "cited_by_count": e.get("cited_by_count"),
            "credential_country": e.get("credential_country"),
            "institution": e.get("institution"),
            "subfield": e.get("subfield"),
        })
    path = OUT / "entity_gender.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"[wrote] {path} ({len(rows)} rows)")
    return rows


def cohort_gap_table(rows):
    """Per-cohort mean NR by gender, plus drop rate."""
    out = []
    by_cohort = defaultdict(list)
    for r in rows:
        by_cohort[r["cohort"]].append(r)
    for c in sorted(by_cohort.keys()):
        xs_m = [r["namerank"] for r in by_cohort[c]
                if r["predicted_gender"] == "male" and r["namerank"] is not None]
        xs_f = [r["namerank"] for r in by_cohort[c]
                if r["predicted_gender"] == "female" and r["namerank"] is not None]
        n_amb = sum(1 for r in by_cohort[c] if r["predicted_gender"] == "ambiguous")
        n_total = len(by_cohort[c])
        mean_m = statistics.mean(xs_m) if xs_m else float("nan")
        mean_f = statistics.mean(xs_f) if xs_f else float("nan")
        sd_m = statistics.stdev(xs_m) if len(xs_m) > 1 else float("nan")
        sd_f = statistics.stdev(xs_f) if len(xs_f) > 1 else float("nan")
        delta = mean_m - mean_f if xs_m and xs_f else float("nan")
        t, p = welch_t(xs_m, xs_f)
        out.append({
            "cohort": c,
            "n_total": n_total,
            "n_male": len(xs_m),
            "n_female": len(xs_f),
            "n_ambiguous": n_amb,
            "frac_ambiguous": round(n_amb / n_total, 3),
            "mean_NR_male": round(mean_m, 4) if not math.isnan(mean_m) else "",
            "sd_NR_male": round(sd_m, 4) if not math.isnan(sd_m) else "",
            "mean_NR_female": round(mean_f, 4) if not math.isnan(mean_f) else "",
            "sd_NR_female": round(sd_f, 4) if not math.isnan(sd_f) else "",
            "delta_male_minus_female": round(delta, 4) if not math.isnan(delta) else "",
            "welch_t": round(t, 3) if not math.isnan(t) else "",
            "p_value": round(p, 4) if not math.isnan(p) else "",
        })
    path = OUT / "gender_gap_by_cohort.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print(f"[wrote] {path}")
    return out


def h_index_adjusted_gap(rows):
    """Within long_tail_researcher_openalex (only cohort with h_index), bin
    by h-index decile and compute gender gap per bin."""
    cohort = "long_tail_researcher_openalex"
    sub = [r for r in rows if r["cohort"] == cohort
           and r["namerank"] is not None and r["h_index"] is not None
           and r["predicted_gender"] in ("male", "female")]
    # Decile thresholds across the male+female subset
    h_values = sorted([r["h_index"] for r in sub])
    n = len(h_values)
    if n == 0:
        print("h_index_adjusted_gap: no data")
        return []
    decile_edges = [h_values[min(n - 1, int(n * i / 10))] for i in range(11)]
    out = []
    pooled_delta_num = 0.0
    pooled_delta_den = 0
    for d in range(10):
        lo, hi = decile_edges[d], decile_edges[d + 1]
        if d < 9:
            chunk = [r for r in sub if lo <= r["h_index"] < hi]
        else:
            chunk = [r for r in sub if lo <= r["h_index"] <= hi]
        xs_m = [r["namerank"] for r in chunk if r["predicted_gender"] == "male"]
        xs_f = [r["namerank"] for r in chunk if r["predicted_gender"] == "female"]
        mean_m = statistics.mean(xs_m) if xs_m else float("nan")
        mean_f = statistics.mean(xs_f) if xs_f else float("nan")
        delta = mean_m - mean_f if xs_m and xs_f else float("nan")
        t, p = welch_t(xs_m, xs_f)
        if xs_m and xs_f:
            w = min(len(xs_m), len(xs_f))
            pooled_delta_num += delta * w
            pooled_delta_den += w
        out.append({
            "decile": f"D{d+1}",
            "h_index_lo": lo,
            "h_index_hi": hi,
            "n_male": len(xs_m),
            "n_female": len(xs_f),
            "mean_NR_male": round(mean_m, 4) if xs_m else "",
            "mean_NR_female": round(mean_f, 4) if xs_f else "",
            "delta_male_minus_female": round(delta, 4) if not math.isnan(delta) else "",
            "welch_t": round(t, 3) if not math.isnan(t) else "",
            "p_value": round(p, 4) if not math.isnan(p) else "",
        })
    pooled = pooled_delta_num / pooled_delta_den if pooled_delta_den else float("nan")
    out.append({
        "decile": "POOLED_WITHIN",
        "h_index_lo": "",
        "h_index_hi": "",
        "n_male": sum(r["n_male"] for r in out),
        "n_female": sum(r["n_female"] for r in out),
        "mean_NR_male": "",
        "mean_NR_female": "",
        "delta_male_minus_female": round(pooled, 4) if not math.isnan(pooled) else "",
        "welch_t": "",
        "p_value": "",
    })
    path = OUT / "h_index_adjusted_gap.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print(f"[wrote] {path}")
    return out


def matched_pairs_cs_faculty(rows):
    """Match female cs_faculty to male cs_faculty on institution.

    cs_faculty has no h_index, so the match is on institution (a strong proxy
    for tier / subfield prestige). For long_tail_researcher_openalex we use
    the h_index-decile breakdown as the bibliometric adjustment.
    """
    sub = [r for r in rows if r["cohort"] == "cs_faculty"
           and r["predicted_gender"] in ("male", "female")
           and r["namerank"] is not None]
    males_by_inst = defaultdict(list)
    for r in sub:
        if r["predicted_gender"] == "male":
            males_by_inst[r["institution"]].append(r)
    used_male_ids = set()
    pairs = []
    females = [r for r in sub if r["predicted_gender"] == "female"]
    for f in females:
        pool = [m for m in males_by_inst.get(f["institution"], [])
                if m["id"] not in used_male_ids]
        if not pool:
            continue
        # Greedy match: pick male with the same institution (any).
        # Pop the first to keep deterministic behavior.
        m = pool[0]
        used_male_ids.add(m["id"])
        pairs.append({
            "institution": f["institution"],
            "female_id": f["id"],
            "female_name": f["name"],
            "female_NR": f["namerank"],
            "male_id": m["id"],
            "male_name": m["name"],
            "male_NR": m["namerank"],
            "delta_male_minus_female": round(m["namerank"] - f["namerank"], 4),
        })
    path = OUT / "matched_pairs_cs_faculty.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(pairs[0].keys()))
        w.writeheader()
        w.writerows(pairs)
    diffs = [p["delta_male_minus_female"] for p in pairs]
    t, p_val = paired_t(diffs)
    print(f"[wrote] {path} ({len(pairs)} pairs); "
          f"mean delta={statistics.mean(diffs):+.4f}, paired-t={t:.3f}, p={p_val:.4f}")
    return pairs, diffs, t, p_val


def matched_pairs_openalex(rows):
    """Bonus: match female openalex authors to male with h_index ±2 and same
    subfield+country if available. Reports mean paired delta in stdout."""
    sub = [r for r in rows if r["cohort"] == "long_tail_researcher_openalex"
           and r["predicted_gender"] in ("male", "female")
           and r["namerank"] is not None and r["h_index"] is not None]
    males = [r for r in sub if r["predicted_gender"] == "male"]
    used = set()
    pairs = []
    females = sorted([r for r in sub if r["predicted_gender"] == "female"],
                     key=lambda r: -r["h_index"])
    for f in females:
        cand = None
        # Try increasingly relaxed match.
        for tol in (2, 5, 10):
            best = None
            for m in males:
                if m["id"] in used:
                    continue
                if abs(m["h_index"] - f["h_index"]) > tol:
                    continue
                if (f["subfield"] and m["subfield"] and m["subfield"] != f["subfield"]):
                    continue
                if (f["credential_country"] and m["credential_country"]
                        and m["credential_country"] != f["credential_country"]):
                    continue
                if best is None or abs(m["h_index"] - f["h_index"]) < abs(best["h_index"] - f["h_index"]):
                    best = m
            if best is not None:
                cand = best
                break
        if cand is None:
            continue
        used.add(cand["id"])
        pairs.append({
            "female_id": f["id"], "female_name": f["name"],
            "female_h": f["h_index"], "female_NR": f["namerank"],
            "male_id": cand["id"], "male_name": cand["name"],
            "male_h": cand["h_index"], "male_NR": cand["namerank"],
            "delta_male_minus_female": round(cand["namerank"] - f["namerank"], 4),
            "h_diff": cand["h_index"] - f["h_index"],
            "subfield": f["subfield"],
            "country": f["credential_country"],
        })
    path = OUT / "matched_pairs_openalex.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        if pairs:
            w = csv.DictWriter(f, fieldnames=list(pairs[0].keys()))
            w.writeheader()
            w.writerows(pairs)
    diffs = [p["delta_male_minus_female"] for p in pairs]
    if diffs:
        t, p_val = paired_t(diffs)
        print(f"[wrote] {path} ({len(pairs)} pairs); "
              f"mean delta={statistics.mean(diffs):+.4f}, "
              f"paired-t={t:.3f}, p={p_val:.4f}")
    return pairs


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ents, by_id, nr = load_data()
    rows = write_entity_gender(ents, by_id, nr)

    print("\n=== Per-cohort gender gaps ===")
    table = cohort_gap_table(rows)
    for r in table:
        if isinstance(r["n_male"], int) and r["n_male"] >= 20 and isinstance(r["n_female"], int) and r["n_female"] >= 20:
            print(f"  {r['cohort']:38s} n_m={r['n_male']:4d} n_f={r['n_female']:4d} "
                  f"mean_m={r['mean_NR_male']:.4f} mean_f={r['mean_NR_female']:.4f} "
                  f"delta={r['delta_male_minus_female']:+.4f} p={r['p_value']}")

    print("\n=== h-index-adjusted gap on long_tail_researcher_openalex ===")
    h_table = h_index_adjusted_gap(rows)
    for r in h_table:
        print(f"  {r['decile']:14s} n_m={r['n_male']:4d} n_f={r['n_female']:4d} "
              f"delta={r['delta_male_minus_female']}")

    print("\n=== Matched pairs (cs_faculty, by institution) ===")
    matched_pairs_cs_faculty(rows)

    print("\n=== Matched pairs (openalex, h_index ±tol, subfield+country) ===")
    matched_pairs_openalex(rows)


if __name__ == "__main__":
    main()
