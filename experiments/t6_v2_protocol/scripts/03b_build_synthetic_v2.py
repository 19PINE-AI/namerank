"""Synthetic nulls v2: fictional entities recipe-matched to every v2 gold family.

Reuses the 30 validated-ungoogleable t1_3 names (floors comparable across
protocol versions) and rewrites their contexts/golds in the v2 recipes; adds
15 new fictional entities for recipes t1_3 did not cover (OpenAlex-style
researchers, NOI contestants, papers, MSRA fellows).

Writes inputs/synthetic_v2_entities.json and inputs/synthetic_v2_gold.json.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent

t13 = {e["id"]: e for e in json.loads(
    (REPO / "experiments/t1_3_synthetic_null/inputs/pilot_entities.json").read_text())}
t13_gold = json.loads(
    (REPO / "experiments/t1_3_synthetic_null/inputs/gold_answers.json").read_text())

ents, gold = [], {}


def add(eid, name, context, cohort, g):
    ents.append({"id": eid, "name": name, "context": context,
                 "cohort": cohort, "synthetic": True})
    gold[eid] = g


# ── t1_3 faculty (10): keep names/affiliations, v2 works-based recipe ──
FAC_WORKS = {
    "synthetic_faculty_yorel_heskenwald": (
        "ETH Zurich", "programming language theory",
        [("Gradual Effect Systems for Dependently Typed Intermediate Languages", "POPL", 2019),
         ("Metatheory Without Tears: Mechanized Soundness for Gradual Unions", "ICFP", 2021),
         ("Kindly Typed: Effect Polymorphism for Staged Compilation", "OOPSLA", 2017)]),
}
for eid, e in t13.items():
    if e["cohort"] != "synthetic_cs_faculty":
        continue
    # parse affiliation + field from the t1_3 context ("a computer science
    # faculty member at X working on Y" or similar)
    ctx = e["context"]
    g_old = t13_gold[eid]
    inst = ctx.split(" at ")[-1].split(" working")[0].strip()
    field = ctx.split("working on ")[-1].strip() if "working on " in ctx else "computer science"
    name = e["name"]
    if eid in FAC_WORKS:
        inst, field, works = FAC_WORKS[eid]
    else:
        stem = name.split()[0]
        works = [
            (f"Compositional {field.title()} via Stratified Abstraction: the {stem} Calculus", "POPL", 2018),
            (f"On the Decidability of Layered {field.title()} Refinements", "LICS", 2020),
            (f"{stem}Lib: A Verified Toolkit for {field.title()}", "PLDI", 2016)]
    works_s = ", ".join(f"'{t}' ({v}, {y})" for t, v, y in works)
    add(eid, name, f"a computer science faculty member at {inst}",
        "synthetic_cs_faculty_v2",
        f"{name} is a computer science faculty member at {inst} working on "
        f"{field}. Their most-cited works include {works_s}. They received "
        f"their PhD in 2011 and joined {inst} in 2014, where they lead a "
        f"small research group and teach graduate courses on {field}.")

# ── t1_3 IMO (6): v2 participation context + official-record-style gold ──
IMO_DETAILS = [(2014, 33, 21), (2014, 36, 12), (2014, 30, 34),
               (2014, 38, 8), (2014, 31, 29), (2014, 34, 18)]
i = 0
for eid, e in t13.items():
    if e["cohort"] != "synthetic_imo_gold":
        continue
    country = e["context"].split("representing ")[-1].strip()
    year, total, rank = IMO_DETAILS[i % len(IMO_DETAILS)]
    i += 1
    add(eid, e["name"],
        f"a participant at the International Mathematical Olympiad (IMO) {year} representing {country}",
        "synthetic_imo_gold_v2",
        f"{e['name']} represented {country} at the International "
        f"Mathematical Olympiad {year}, winning a gold medal with a total "
        f"score of {total}/42 (rank {rank}). They later studied mathematics "
        f"at a national research university.")

# ── t1_3 founders (6): v2 wikipedia-style bios, generic context ──
for eid, e in t13.items():
    if e["cohort"] != "synthetic_founder":
        continue
    add(eid, e["name"], "a technology company co-founder or executive",
        "synthetic_founder_v2", t13_gold[eid])

# ── t1_3 OSS (4): v2 github recipe ──
OSS = {"spindleflow": ("a workflow orchestration library", "Python", 2019),
       "default": ("a developer library", "Python", 2020)}
for eid, e in t13.items():
    if e["cohort"] != "synthetic_oss_project":
        continue
    desc = e["context"].rstrip(".")
    add(eid, e["name"], desc, "synthetic_oss_project_v2",
        f"{e['name']} is {desc}. The project was created in 2019 by an "
        f"independent developer and is written primarily in Python; its "
        f"repository documents a plugin architecture, a declarative "
        f"configuration format, and integrations with common data tools. "
        f"It is distributed under the MIT license.")

# ── t1_3 mid-tier (4): keep dense fictional bios, v2 thin contexts ──
MT_CTX = {"synthetic_mid_tier_musician": "an American indie singer-songwriter",
          "synthetic_mid_tier_chef": "a chef",
          "synthetic_mid_tier_journalist": "a journalist",
          "synthetic_mid_tier_podcast": "a weekly interview podcast"}
for eid, e in t13.items():
    if e["cohort"] in MT_CTX:
        add(eid, e["name"], MT_CTX[e["cohort"]], e["cohort"] + "_v2",
            t13_gold[eid])

# ── NEW: 6 OpenAlex-recipe researchers ──
RES = [
    ("Farnaz Oduya-Lindqvist", "computational epidemiology",
     [("Latent Contact Manifolds for Seasonal Outbreak Forecasting", "PLOS Computational Biology", 2020),
      ("Sparse Mobility Priors Improve District-Level Epidemic Nowcasts", "Epidemics", 2021),
      ("A Semi-Mechanistic Framework for Pathogen Co-Circulation", 2018)]),
    ("Tevin Bramsgaard", "underwater acoustics",
     [("Waveguide-Invariant Beamforming for Shallow-Water Arrays", "Journal of the Acoustical Society of America", 2017),
      ("Self-Calibrating Hydrophone Networks under Tidal Drift", "IEEE JOE", 2019),
      ("Broadband Reverberation Nulling with Sparse Priors", 2015)]),
    ("Ilaria Vantorre-Meszaros", "organic photovoltaics",
     [("Non-Fullerene Acceptors with Torsion-Locked Backbones", "Advanced Energy Materials", 2021),
      ("Ternary Blends for Humid-Climate Module Stability", "Solar RRL", 2022),
      ("Interfacial Dipole Tuning in Inverted OPV Stacks", 2019)]),
    ("Kwabena Osterlund-Adjei", "operations research",
     [("Two-Stage Robust Rostering under Endogenous No-Shows", "Operations Research", 2018),
      ("Dual Decomposition for Metro Headway Recovery", "Transportation Science", 2020),
      ("Fair Overbooking with Reference-Dependent Utilities", 2016)]),
    ("Marisol Grieveson-Ku", "sedimentology",
     [("Turbidite Stacking Signatures of Deglacial Meltwater Pulses", "Sedimentology", 2019),
      ("Grain-Shape Entropy as a Provenance Tracer", "Journal of Sedimentary Research", 2021),
      ("Levee Aggradation Rates from Optically Stimulated Luminescence", 2017)]),
    ("Bogdan Ferreyra-Nakade", "compiler verification",
     [("Translation Validation for Polyhedral Schedulers", "PLDI", 2020),
      ("A Certified Peephole Framework for RISC-V Vector Extensions", "CAV", 2021),
      ("Semantic Diffing of Optimization Pipelines", 2018)]),
]
for name, field, works in RES:
    eid = "synthetic_oa_" + name.split()[0].lower()
    works_s = ", ".join(
        f"'{w[0]}' ({w[1]}, {w[2]})" if len(w) == 3 else f"'{w[0]}' ({w[1]})"
        for w in works)
    add(eid, name, f"an academic researcher in {field}",
        "synthetic_openalex_researcher_v2",
        f"{name} is a researcher in {field}. Their most-cited works include "
        f"{works_s}. They have published on related problems since the early "
        f"2010s and have held research appointments at two European "
        f"universities.")

# ── NEW: 3 NOI contestants ──
NOI = [("Sang Weihuan (桑纬奂)", "江苏省苏州中学", 512, 43),
       ("Nie Qiongzhao (聂穹肇)", "四川省成都七中", 488, 57),
       ("Qiu Zhenlue (仇箴略)", "浙江省镇海中学", 530, 31)]
for name, school, score, rank in NOI:
    eid = "synthetic_noi_" + name.split()[0].lower() + "_" + name.split()[1].lower()
    add(eid, name, "a contestant at the 2009 NOI (China National Olympiad in Informatics)",
        "synthetic_noi_v2",
        f"{name} won a gold medal at the 2009 National Olympiad in "
        f"Informatics (NOI), representing {school} as a second-year "
        f"high-school student, scoring {score} points (rank {rank} "
        f"nationally). They later studied computer science at a Project 985 "
        f"university.")

# ── NEW: 4 papers ──
PAPERS = [
    ("Cross-Basin Bathymetric Super-Resolution with Multiscale Attention Priors",
     2021, "Remote Sensing of Environment",
     "We propose a multiscale attention prior for reconstructing high-resolution seafloor bathymetry from sparse sonar transects. The method fuses swath geometry with learned spectral priors and enforces slope-consistency constraints, improving RMSE by 31% over interpolation baselines across three ocean basins, and transfers zero-shot to unseen shelf morphologies."),
    ("Endogenous Queue Abandonment in Two-Sided Service Platforms: Identification and Welfare",
     2020, "Management Science",
     "We study how customer abandonment responds to displayed wait estimates on two-sided platforms. Using a regression-discontinuity design around estimate rounding thresholds, we identify a structural abandonment elasticity and show that platform-optimal display policies recover 12% of lost welfare without increasing server idleness."),
    ("A Uracil-Bridged Bimetallic Scaffold for Selective CO2-to-Formate Electroreduction",
     2022, "ACS Catalysis",
     "We report a uracil-bridged Cu-Bi scaffold that steers CO2 electroreduction toward formate with 94% Faradaic efficiency at industrially relevant current densities. Operando spectroscopy attributes selectivity to a hydrogen-bond-stabilized *OCHO intermediate, and 200-hour electrolysis shows negligible degradation."),
    ("Curriculum Distillation Under Label Scarcity for Edge Vision Transformers",
     2022, "WACV",
     "We introduce a curriculum distillation schedule that orders unlabeled samples by teacher disagreement, enabling ViT students on edge devices to match full-supervision accuracy with 8% of labels across four benchmarks while cutting training energy by 3.4x."),
]
for title, year, venue, abstract in PAPERS:
    eid = "synthetic_paper_" + title.split()[0].lower() + "_" + title.split()[1].lower().strip(",")
    add(eid, title, f"a {year} academic paper",
        "synthetic_paper_v2",
        f"{title} is a {year} paper published in {venue}. {abstract}")

# ── NEW: 2 MSRA fellows ──
MSRA = [("Ruan Xilai (阮析莱)", "Zhejiang University", 2021,
         [("Latency-Aware Speculative Sharding for Serverless DAGs", "OSDI", 2022),
          ("Cold-Start Amortization via Snapshot Forests", "NSDI", 2021)]),
        ("Pang Yunche (庞筠澈)", "Nanjing University", 2022,
         [("Contrastive Program Sketches for Few-Shot API Migration", "ICSE", 2023),
          ("Type-Directed Retrieval for Repository-Level Completion", "FSE", 2022)])]
for name, uni, year, works in MSRA:
    eid = "synthetic_msra_" + name.split()[0].lower()
    works_s = ", ".join(f"'{t}' ({v}, {y})" for t, v, y in works)
    add(eid, name, f"a computer science PhD student at {uni} (circa {year})",
        "synthetic_msra_v2",
        f"{name} received the {year} Microsoft Research Asia PhD Fellowship "
        f"while a PhD student at {uni}. Their published works include "
        f"{works_s}. Their research focuses on systems for cloud computing.")

(HERE / "inputs" / "synthetic_v2_entities.json").write_text(
    json.dumps(ents, ensure_ascii=False, indent=1))
(HERE / "inputs" / "synthetic_v2_gold.json").write_text(
    json.dumps(gold, ensure_ascii=False, indent=1))
from collections import Counter
print(len(ents), "synthetic entities:", dict(Counter(e["cohort"] for e in ents)))
print("mean gold words:", sum(len(g.split()) for g in gold.values()) // len(gold))
