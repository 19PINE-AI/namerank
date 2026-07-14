"""Build v2 probe contexts for all 5,719 entities.

Principle: the context anchors disambiguation (role, field, nationality,
era, affiliation) and must not contain gold content (results, scores,
named works, credential outcomes, bibliometrics, functional descriptions
that are the entity's main claim, or notability meta-statements).

Writes inputs/contexts_v2.json {entity_id: context} plus a
context_change_report.csv. Entities not matched by any rule keep their v1
context (reported).
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent

pe = json.loads((REPO / "data/inputs/pilot_entities.json").read_text())

# manual overrides for small/heterogeneous cohorts (id -> context)
MANUAL: dict[str, str] = {}


def first_seg(ctx: str) -> str:
    return ctx.split(",")[0].strip()


def keep_parenthetical_years(ctx: str, base: str) -> str:
    m = re.search(r"\((\d{4}[–-]\d{4}|\d{4}[–-]?\)?)\)?\s*$", ctx)
    if m and re.match(r"^\(?\d{4}", m.group(1)):
        return f"{base} ({m.group(1).rstrip(')')})"
    return base


WIKIMETA = re.compile(r"^(?:an? )?(.+?) with a Wikipedia page \(mid-tier level of recognition\)$")
HONOR = re.compile(r",?\s*(?:\d{4} )?[\w\s.'-]*(?:winner|champion|medalist|MVP|Hall of Fame\w*|record holder)\b[^,]*", re.I)


def ctx_v2(e: dict) -> str | None:
    c, coh = e["context"], e["cohort"]
    year = e.get("credential_year")
    country = e.get("credential_country") or ""

    if e["id"] in MANUAL:
        return MANUAL[e["id"]]

    # generic Wikidata-boilerplate contexts, any cohort
    m = WIKIMETA.match(c)
    if m:
        noun = m.group(1)
        art = "an" if noun[0].lower() in "aeiou" else "a"
        return f"{art} {noun}"
    if coh in ("mid_tier_athlete",):
        stripped = HONOR.sub("", c).strip().strip(",")
        return stripped if stripped else c

    # ── credentials: participation stays, outcome moves to gold ──
    if coh == "imo_gold":
        return (f"a participant at the International Mathematical Olympiad "
                f"(IMO) {year} representing {country}")
    if coh == "ioi_gold":
        yrs = re.search(r"\(IOI\) ([\d/]+)", c)
        return (f"a participant at the International Olympiad in Informatics "
                f"(IOI) {yrs.group(1) if yrs else year} representing {country}")
    if coh == "noi_china_gold":
        return f"a contestant at the {year} NOI (China National Olympiad in Informatics)"
    if coh == "cmo_china_gold":
        return f"a contestant at the {year} CMO (China Mathematical Olympiad)"
    if coh == "cpho_china_first_prize":
        return f"a contestant at the {year} CPhO (China National Physics Olympiad)"
    if coh == "putnam_fellow":
        return (f"a participant in the William Lowell Putnam Mathematical "
                f"Competition ({year})")
    if coh == "icpc_world_finals_gold":
        uni = re.sub(r"^.*winning team from ", "", c)
        return f"a member of a team from {uni} at the {year} ICPC World Finals"
    if coh == "rhodes_scholar":
        m = re.search(r"from (.+)$", c)
        nat = "American" if "American" in c else (country or "").strip()
        return (f"a{'n' if nat.startswith('A') else ''} {nat} graduate"
                f"{f' of {m.group(1)}' if m else ''} (class of {year})").strip()
    if coh == "msra_phd_fellowship":
        uni = re.sub(r"^.*Fellowship recipient at ", "", c)
        return f"a computer science PhD student at {uni} (circa {year})"

    # ── researchers: strip bibliometrics ──
    if coh == "long_tail_researcher_openalex":
        m = re.match(r"an academic researcher in (.+?)(?: at (.+?))?, with approximately", c)
        if m:
            field, inst = m.group(1), m.group(2)
            return (f"an academic researcher in {field}"
                    + (f" at {inst}" if inst else ""))
        return re.sub(r",? with approximately.*$", "", c)
    if coh == "long_tail_researcher_ikp":
        return re.sub(r"\s*\(IKP.*\)$", "", c)

    # ── unchanged cohorts ──
    if coh in ("cs_faculty", "gpt5_system_card_author", "deepseek_v3_author",
               "mid_tier_product", "mid_tier_yc_company", "mid_tier_athlete",
               "mid_tier_politician", "mid_tier_vc", "mid_tier_religious",
               "mid_tier_medical", "reference_pilot"):
        return c

    # ── mid-tier people: strip named works / signature facts ──
    if coh in ("mid_tier_writer", "mid_tier_musician", "mid_tier_chef",
               "mid_tier_artist", "mid_tier_comedian", "mid_tier_filmmaker"):
        return keep_parenthetical_years(c, first_seg(c))
    if coh == "mid_tier_actor":
        base = re.sub(r"\s*known for.*$", "", first_seg(c)).strip()
        return keep_parenthetical_years(c, base)
    if coh == "mid_tier_historical":
        return first_seg(c)
    if coh == "mid_tier_journalist":
        return first_seg(c)
    if coh == "mid_tier_gov_ai_policy":
        return first_seg(c)
    if coh == "mid_tier_founder":
        return "a technology company co-founder or executive"
    if coh == "mid_tier_oss_maintainer":
        return "an open-source software developer or author"
    if coh == "mid_tier_online_course":
        return re.sub(r"\s+by .*$", "", c)
    if coh == "mid_tier_podcast":
        return re.sub(r"\s+by .*$", "", c)
    if coh in ("mid_tier_architect", "mid_tier_activist", "mid_tier_book"):
        noun = coh.replace("mid_tier_", "")
        art = "an" if noun[0] in "aeiou" else "a"
        return f"{art} {noun}" if noun != "book" else "a book"

    # ── artifacts: category-only descriptions ──
    if coh == "oss_project":
        base = re.sub(r",?\s*hosted at \S+", "", c).strip()
        return base
    if coh == "long_tail_paper":
        return re.sub(r"\s*with approximately \d+ citations", "", c)
    if coh == "research_paper":
        m = re.search(r"\b(19|20)\d{2}\b", c)
        return (f"a {m.group(0)} research paper in machine learning or AI"
                if m else "a research paper in machine learning or AI")
    if coh == "named_method":
        return "a named technique used in machine-learning models"
    if coh == "benchmark":
        return "a benchmark used in machine-learning evaluation"
    if coh == "dataset":
        return "a dataset used in machine-learning research"
    if coh == "foundation_model":
        m = re.search(r"from (\w[\w\s.]*?)(?: released.*)?$", c)
        return (f"an AI model from {m.group(1).strip()}" if m else "an AI model")
    if coh == "ai_startup_or_company":
        return "an AI-related company or research lab"
    if coh == "ai_hardware":
        m = re.search(r"^the (\w+)", c)
        return (f"a hardware product from {m.group(1)}"
                if m and m.group(1) in ("NVIDIA", "Google", "AMD", "Intel",
                                        "Apple", "Cerebras", "Groq")
                else "an AI-related hardware product")
    if coh == "programming_language":
        return "a programming language"
    if coh == "database_or_data_system":
        return "a database or data system"
    if coh == "conference":
        return "an academic conference or venue"
    if coh == "award":
        return "an academic or professional award"
    if coh == "industry_product":
        return "a consumer software product"
    if coh == "website_or_service":
        # small cohort with load-bearing descriptions; keep audience, drop function
        return "a website or online service"
    return None


def main() -> None:
    out, rows = {}, []
    for e in pe:
        v2 = ctx_v2(e)
        changed = v2 is not None and v2 != e["context"]
        out[e["id"]] = v2 if v2 is not None else e["context"]
        rows.append({"entity_id": e["id"], "cohort": e["cohort"],
                     "changed": int(changed),
                     "v1": e["context"], "v2": out[e["id"]]})
    (HERE / "inputs" / "contexts_v2.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))
    with open(HERE / "outputs" / "context_change_report.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["entity_id", "cohort", "changed", "v1", "v2"])
        w.writeheader()
        w.writerows(rows)
    import collections
    ch = collections.Counter((r["cohort"], r["changed"]) for r in rows)
    coh_tot = collections.Counter(r["cohort"] for r in rows)
    print(f"{sum(r['changed'] for r in rows)}/{len(rows)} contexts changed")
    unchanged_cohorts = [c for c in coh_tot if ch.get((c, 1), 0) == 0]
    print("cohorts fully unchanged:", sorted(unchanged_cohorts))
    # leak lint: no digits-heavy bibliometrics, no 'h-index', no 'citations'
    bad = [r for r in rows if re.search(r"h-index|citation|score[d]? \d|medalist|winner|Fellow(ship)? recipient|gold |first-prize|prestigious|Wikipedia page", out[r["entity_id"]], re.I)]
    print("leak-lint hits:", len(bad))
    for r in bad[:10]:
        print("  ", r["cohort"], "|", out[r["entity_id"]][:100])


if __name__ == "__main__":
    main()
