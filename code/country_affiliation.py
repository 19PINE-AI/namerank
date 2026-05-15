"""CS faculty NameRank by country of institutional affiliation.

Maps institution strings to country via keyword prefixes (the cohort has 100 %
institution coverage in pilot_entities.json). Writes
data/analysis/cs_faculty_by_country.csv.
"""
from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict

from _paths import ANALYSIS, INPUTS


COUNTRY_KEYWORDS: dict[str, list[str]] = {
    "USA": [
        "Carnegie Mellon", "Cornell", "Michigan", "Washington", "Princeton", "Stanford",
        "Georgia Institute", "Johns Hopkins", "Illinois", "MIT", "Berkeley", "UCLA", "USC",
        "NYU", "Columbia", "Yale", "Harvard", "Brown", "Duke", "UT Austin", "Texas",
        "Penn", "UCSD", "UC San Diego", "Northwestern", "Wisconsin", "Maryland",
        "Massachusetts", "California", "Virginia", "Boston University", "Rutgers",
        "Rice", "Vanderbilt", "Caltech", "Buffalo", "Stony Brook", "Pittsburgh",
        "Notre Dame", "Indiana", "Ohio", "Florida", "Arizona", "Oregon", "Utah",
        "Colorado", "Iowa", "Kansas", "Minnesota", "Tennessee", "North Carolina",
        "George Washington", "Drexel",
    ],
    "UK": ["Cambridge", "Oxford", "Imperial College", "UCL", "Edinburgh", "Manchester",
           "Glasgow", "Bristol", "Sussex", "Warwick", "Sheffield", "Leeds", "Lancaster",
           "Surrey", "Southampton", "Birmingham"],
    "Canada": ["Toronto", "Waterloo", "McGill", "British Columbia", "UBC", "Alberta",
               "Montreal", "Simon Fraser", "Western Ontario", "York University"],
    "China": ["Tsinghua", "Peking", "USTC", "Shanghai Jiao Tong", "Fudan", "Zhejiang",
              "Wuhan", "Harbin Institute", "Nanjing", "Xian Jiaotong", "Beihang",
              "Renmin", "Beijing Institute"],
    "Hong Kong": ["HKUST", "Chinese University of Hong Kong", "City University of Hong Kong",
                  "Hong Kong Polytechnic"],
    "Singapore": ["NTU", "Nanyang Technological", "NUS", "National University of Singapore"],
    "Australia": ["Monash", "Melbourne", "Sydney", "ANU", "Queensland", "New South Wales"],
    "Germany": ["TUM", "Max Planck", "Heidelberg", "Munich", "Berlin", "Stuttgart",
                "Karlsruhe", "RWTH", "Saarland", "Darmstadt", "Bonn"],
    "Netherlands": ["TU Delft", "Eindhoven", "Amsterdam", "Leiden", "Utrecht", "Groningen"],
    "Switzerland": ["ETH", "EPFL", "Lausanne", "Zurich"],
    "France": ["INRIA", "Paris", "Sorbonne", "Lyon", "Grenoble"],
    "Italy": ["Roma", "Milano", "Politecnico", "Bologna"],
    "Spain": ["A Coruna", "A Coruña", "Madrid", "Barcelona", "Polytechnic"],
    "Portugal": ["Lisboa", "Porto"],
    "Israel": ["Technion", "Hebrew University", "Tel Aviv", "Weizmann"],
    "Japan": ["Tokyo", "Kyoto", "Osaka"],
    "South Korea": ["KAIST", "Seoul", "POSTECH"],
    "India": ["IIT", "IIIT"],
    "Brazil": ["UFRGS", "USP", "UNICAMP"],
    "Sweden": ["KTH", "Chalmers", "Lund", "Stockholm"],
    "Russia": ["Moscow", "Saint Petersburg"],
    "Greece": ["Athens", "Thessaloniki", "Crete"],
}


def lookup_country(inst: str) -> str:
    il = inst.lower()
    for country, kws in COUNTRY_KEYWORDS.items():
        for kw in kws:
            if kw.lower() in il:
                return country
    return "Other/Unknown"


def main() -> None:
    ents = {e["id"]: e for e in json.loads((INPUTS / "pilot_entities.json").read_text())}
    nr = {row["entity_id"]: float(row["namerank"])
          for row in csv.DictReader(open(ANALYSIS / "namerank_per_entity.csv", encoding="utf-8"))}

    by_country: dict[str, list[tuple[float, str, str]]] = defaultdict(list)
    for eid, e in ents.items():
        if e.get("cohort") != "cs_faculty" or eid not in nr:
            continue
        inst = e.get("institution", "")
        country = lookup_country(inst)
        by_country[country].append((nr[eid], e["name"], inst))

    rows = []
    for c, items in sorted(by_country.items(),
                           key=lambda x: -statistics.mean([n for n, _, _ in x[1]])):
        if len(items) < 3:
            continue
        nrs = [n for n, _, _ in items]
        rows.append({
            "country": c, "n": len(items),
            "mean": round(statistics.mean(nrs), 3),
            "median": round(statistics.median(nrs), 3),
            "sd": round(statistics.stdev(nrs) if len(nrs) > 1 else 0.0, 3),
            "frac_above_0_5": round(sum(1 for n in nrs if n >= 0.5) / len(nrs), 3),
        })

    out = ANALYSIS / "cs_faculty_by_country.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {out} ({len(rows)} countries with n>=3)")
    for r in rows:
        print(f"  {r['country']:<20} n={r['n']:<4} mean={r['mean']:.3f}")


if __name__ == "__main__":
    main()
