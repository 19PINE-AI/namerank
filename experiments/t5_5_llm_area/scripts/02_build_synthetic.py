"""Synthetic-null entities for the LLM-area cohorts: fictional ML researchers
matched to the works-list gold recipe, ungoogleable names. Their recognition
rate calibrates the floor for the three cohorts (all share the same gold
recipe: "NAME is a machine learning researcher. Their most-cited works
include ...").
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

# fictional ML researchers + plausible-but-fake work titles (ungoogleable)
SYN = [
    ("Kestrel Vanterpool", [
        ("Gradient-Aligned Sparse Mixtures for Low-Rank Adapter Fusion", "NeurIPS", 2023),
        ("Spectral Dropout Schedules for Long-Context Transformers", "ICML", 2022),
        ("On the Convergence of Anchored Preference Optimization", 2024)]),
    ("Thaddeus Oyelaran", [
        ("Latent Curriculum Distillation for Edge Vision Encoders", "CVPR", 2022),
        ("Rotational Key-Value Compression in Autoregressive Decoders", "ICLR", 2023),
        ("Benchmarking Compositional Reasoning under Token Scarcity", 2023)]),
    ("Marisela Quibell", [
        ("Contrastive Retrieval Priors for Instruction Following", "ACL", 2023),
        ("Sublinear Attention via Householder Sketches", "NeurIPS", 2022),
        ("A Calibrated Reward Model for Multi-Turn Dialogue", 2024)]),
    ("Bramwell Ashkani", [
        ("Diffusion Guidance with Learned Energy Corridors", "ICML", 2023),
        ("Quantization-Aware Prefix Tuning for Serving", "MLSys", 2023),
        ("Emergent Tool Use in Sandboxed Language Agents", 2024)]),
    ("Isolde Fennimore", [
        ("Speculative Verification with Draft Ensembles", "NeurIPS", 2024),
        ("Positional Aliasing in Rotary Embeddings", "ICLR", 2023),
        ("Data-Efficient Alignment via Synthetic Critiques", 2023)]),
    ("Cornelius Vraibley", [
        ("Hierarchical State-Space Routing for Sequence Models", "ICML", 2024),
        ("Robust Watermarking of Autoregressive Text", "ACL", 2023),
        ("Scaling Laws for Retrieval-Augmented Pretraining", 2024)]),
    ("Delphine Ashgrove", [
        ("Cross-Lingual Adapter Stitching for Low-Resource NMT", "EMNLP", 2022),
        ("Memory-Bounded Beam Search with Learned Pruners", "NAACL", 2023),
        ("A Unified View of Prompt Compression", 2024)]),
    ("Ephraim Toskovic", [
        ("Contrastive Chain-of-Thought for Symbolic Tasks", "NeurIPS", 2023),
        ("Gradient Surgery for Multi-Objective RLHF", "ICML", 2023),
        ("Detecting Fabricated Citations in LLM Output", 2024)]),
    ("Ottoline Bracegirdle", [
        ("Token-Level Uncertainty for Selective Generation", "ICLR", 2024),
        ("Sparse Expert Routing without Auxiliary Losses", "NeurIPS", 2023),
        ("Curriculum Sampling for Preference Datasets", 2023)]),
    ("Zephyrin Kohlrieser", [
        ("Attention Sink Mitigation in Streaming Decoders", "ICML", 2024),
        ("Distributional Reward Shaping for Code Agents", "NeurIPS", 2023),
        ("Probing Positional Generalization in Long Context", 2024)]),
    ("Marguerite Ansaldi", [
        ("Low-Precision Optimizer States for Trillion-Parameter Training", "MLSys", 2024),
        ("Retrieval Fusion with Late-Interaction Rerankers", "SIGIR", 2022),
        ("A Taxonomy of Hallucination in Summarization", 2023)]),
    ("Gideon Vasquenilla", [
        ("Structured Pruning via Optimal Brain Adapters", "NeurIPS", 2023),
        ("Self-Refinement Loops for Program Synthesis", "ICLR", 2024),
        ("Measuring Sycophancy in Instruction-Tuned Models", 2023)]),
]

ROLE = "a machine learning researcher"
ents, gold = [], {}
for name, works in SYN:
    wl = []
    for w in works:
        if len(w) == 3:
            wl.append(f"“{w[0]} ({w[1]}, {w[2]})”")
        else:
            wl.append(f"“{w[0]} ({w[1]})”")
    eid = "syn_llm_" + name.split()[0].lower()
    ents.append({"id": eid, "name": name, "context": ROLE,
                 "cohort": "synthetic_llm_area_v2", "gold_v2": True,
                 "gold_source": "synthetic", "synthetic": True})
    gold[eid] = (f"{name} is {ROLE}. Their most-cited works include "
                 + ", ".join(wl) + ".")

(HERE / "inputs" / "synthetic_entities.json").write_text(
    json.dumps(ents, ensure_ascii=False, indent=1))
(HERE / "inputs" / "synthetic_gold.json").write_text(
    json.dumps(gold, ensure_ascii=False, indent=1))
print(f"{len(ents)} synthetic LLM-area nulls written")
print("sample:", gold[ents[0]["id"]][:120])
