"""Sample per-university CS-faculty cohorts from CSRankings rosters.

The user-directed redesign of the per-university baselines: role-defined
membership (CSRankings faculty roster, the same source as the main run's
cs_faculty cohort) with NO bibliometric conditioning — no citation window,
no first-author screen. This preserves each university's real composition,
which the citation-window design deliberately erased.

Roster: inputs/csrankings_all.csv (concatenation of the CSRankings
csrankings-[a-z].csv files, fetched 2026-07-12 from
github.com/emeryberger/CSrankings, gh-pages branch).

Sample: min(100, roster) per university, seed-42 random draw.
Writes outputs/faculty_candidates.json.
"""
from __future__ import annotations

import csv
import json
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

AFFIL = {
    "univ_fac_mit": ("Massachusetts Inst. of Technology",
                     "Massachusetts Institute of Technology"),
    "univ_fac_uc_berkeley": ("Univ. of California - Berkeley",
                             "University of California, Berkeley"),
    "univ_fac_ucsd": ("Univ. of California - San Diego",
                      "University of California San Diego"),
    "univ_fac_uc_irvine": ("Univ. of California - Irvine",
                           "University of California, Irvine"),
}
TARGET = 100


def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return s or "x"


def main() -> None:
    rows = list(csv.DictReader(open(HERE / "inputs" / "csrankings_all.csv")))
    out = {}
    rng = random.Random(42)
    for cohort, (roster_name, display_name) in AFFIL.items():
        # strip CSRankings homonym disambiguators like "Jun Wang 0001"
        members, seen = [], set()
        for r in rows:
            if r["affiliation"] != roster_name:
                continue
            name = re.sub(r"\s+\d{4}$", "", r["name"]).strip()
            if name.lower() in seen:
                continue
            seen.add(name.lower())
            members.append({"name": name, "scholarid": r.get("scholarid", ""),
                            "homepage": r.get("homepage", "")})
        picked = rng.sample(members, min(TARGET, len(members)))
        for m in picked:
            m.update({"cohort": cohort, "institution": display_name})
        out[cohort] = picked
        print(f"{cohort}: roster {len(members)}, sampled {len(picked)}")
    (HERE / "outputs" / "faculty_candidates.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
