"""Build inputs_A and inputs_B for the artifact-mediation causal experiment.

For each of the 11 verified (creator, artifact) pairs, we construct two contexts:
- A (control): a role-only description with the artifact name deliberately stripped.
- B (artifact-hint): the same role-only description PLUS an explicit naming of the artifact.

The two contexts are constructed to differ as little as possible except for the
artifact mention, so that the causal effect of naming the artifact in the
context can be isolated.
"""
from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
INPUTS_SRC = Path("/home/ubuntu/namerank/data/inputs")

# (id, name, artifact_full, context_A, context_B)
# Conventions:
#   A: role description that does NOT name the artifact.
#   B: same role description but with "creator/co-founder/author of {artifact}" added.
PAIRS = [
    (
        "simon_willison",
        "Simon Willison",
        "Datasette",
        "a software engineer and writer, co-creator of the Django web framework, who blogs extensively about LLMs and AI tools",
        "a software engineer and writer, co-creator of the Django web framework and creator of Datasette, who blogs extensively about LLMs and AI tools",
    ),
    (
        "dario_amodei",
        "Dario Amodei",
        "Anthropic",
        "the co-founder and CEO of an AI safety lab, previously VP of Research at OpenAI",
        "the co-founder and CEO of Anthropic, previously VP of Research at OpenAI",
    ),
    (
        "andrej_karpathy",
        "Andrej Karpathy",
        "nanoGPT",
        "a computer scientist and AI educator, founder of Eureka Labs, formerly a director at Tesla and a co-founder of OpenAI",
        "a computer scientist and AI educator, author of the nanoGPT open-source project, founder of Eureka Labs, formerly a director at Tesla and a co-founder of OpenAI",
    ),
    (
        "jiayi_weng",
        "Jiayi Weng",
        "Tianshou",
        "an engineer at OpenAI working on infrastructure, formerly a research engineer at Sea AI Lab and PhD student at Tsinghua University",
        "an engineer at OpenAI working on infrastructure and the original author of the Tianshou reinforcement-learning library, formerly a research engineer at Sea AI Lab and PhD student at Tsinghua University",
    ),
    (
        "tri_dao",
        "Tri Dao",
        "FlashAttention",
        "a researcher in efficient deep-learning systems, currently faculty at Princeton University and chief scientist at Together AI",
        "a researcher in efficient deep-learning systems and the lead author of FlashAttention, currently faculty at Princeton University and chief scientist at Together AI",
    ),
    (
        "lilian_weng",
        "Lilian Weng",
        "lilianweng.github.io",
        "a researcher formerly at OpenAI heading applied research and safety, known for writing an influential ML blog",
        "a researcher formerly at OpenAI heading applied research and safety, known for writing the influential ML blog at lilianweng.github.io",
    ),
    (
        "harrison_chase",
        "Harrison Chase",
        "LangChain",
        "the co-founder and CEO of an open-source framework company for building applications with large language models",
        "the co-founder and CEO of LangChain, an open-source framework for building applications with large language models",
    ),
    (
        "aman_sanger",
        "Aman Sanger",
        "Cursor",
        "a co-founder of an AI-powered code editor company",
        "a co-founder of Cursor, an AI-powered code editor company",
    ),
    (
        "demis_hassabis",
        "Demis Hassabis",
        "Google DeepMind",
        "the co-founder and CEO of a major AI research lab now part of Google",
        "the co-founder and CEO of Google DeepMind",
    ),
    (
        "mira_murati",
        "Mira Murati",
        "Thinking Machines Lab",
        "the founder of an AI research startup, formerly Chief Technology Officer of OpenAI",
        "the founder of Thinking Machines Lab, formerly Chief Technology Officer of OpenAI",
    ),
    (
        "aravind_srinivas",
        "Aravind Srinivas",
        "Perplexity",
        "the co-founder and CEO of a company in AI search",
        "the co-founder and CEO of Perplexity, a company in AI search",
    ),
]


def main() -> None:
    # Build pilot_entities.json for inputs_A and inputs_B
    entities_a = []
    entities_b = []
    rows = []
    for pid, name, artifact, ca, cb in PAIRS:
        entities_a.append({"id": pid, "name": name, "context": ca, "cohort": "reference_pilot"})
        entities_b.append({"id": pid, "name": name, "context": cb, "cohort": "reference_pilot"})
        rows.append({"id": pid, "name": name, "artifact": artifact, "context_A": ca, "context_B": cb})

    inputs_a = ROOT / "inputs_A"
    inputs_b = ROOT / "inputs_B"
    inputs_a.mkdir(exist_ok=True)
    inputs_b.mkdir(exist_ok=True)

    (inputs_a / "pilot_entities.json").write_text(
        json.dumps(entities_a, indent=2, ensure_ascii=False)
    )
    (inputs_b / "pilot_entities.json").write_text(
        json.dumps(entities_b, indent=2, ensure_ascii=False)
    )

    # Copy the other shared inputs files verbatim
    for fname in ("gold_answers.json", "model_set.json", "probe_template_en.txt", "judge_prompt.txt"):
        shutil.copy(INPUTS_SRC / fname, inputs_a / fname)
        shutil.copy(INPUTS_SRC / fname, inputs_b / fname)

    # Write contexts.csv for reproducibility
    with open(ROOT / "contexts.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "name", "artifact", "context_A", "context_B"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"Built {len(PAIRS)} pairs into {inputs_a} and {inputs_b}")
    print(f"contexts.csv written to {ROOT / 'contexts.csv'}")


if __name__ == "__main__":
    main()
