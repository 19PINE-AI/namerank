"""Institution-string -> country keyword map for the CS-faculty cohort.

The cohort has ~100% institution coverage, so a keyword match on the affiliation
string is enough to assign a country. This module is imported for its
``COUNTRY_KEYWORDS`` / ``lookup_country`` by the country-gradient figures
(paper/figures/make_fig_country.py, compute_all_numbers.py) and by the release
table builder (code/build_release_tables.py, which inlines the same map).
"""
from __future__ import annotations

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
    il = (inst or "").lower()
    for country, kws in COUNTRY_KEYWORDS.items():
        if any(kw.lower() in il for kw in kws):
            return country
    return "Other/Unknown"
