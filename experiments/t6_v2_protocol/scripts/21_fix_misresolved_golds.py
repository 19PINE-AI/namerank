"""Fix the 25 mis-resolved artifact golds found in the 2026-07-13 audit
(short/ambiguous names resolved to wrong repos/articles/papers by the gold
builders; the wrong-entity guard then correctly suppressed true answers).
Hand-authored corrected golds; patches gold_answers_v2.json, purges the
affected verdicts from both verdict files, and re-judges the affected
main-run responses immediately (appended to recognition_v3.jsonl so the
figure fallback stays complete; the uniform pass re-covers them later).
"""
from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

FIXES = {
    "artifact_flashattention":
        "FlashAttention is a GPU IO-aware exact-attention algorithm introduced by Tri Dao and collaborators in 2022, implemented in the open-source flash-attn library (Dao-AILab/flash-attention on GitHub). It tiles attention computation to avoid materializing the full attention matrix in GPU high-bandwidth memory, giving large speed and memory improvements for transformer training and inference; FlashAttention-2 and -3 extend it with better parallelism and hardware support. It is used by most major LLM training and serving stacks.",
    "artifact_perplexity":
        "Perplexity (Perplexity AI) is an AI-powered answer engine and search product founded in 2022 by Aravind Srinivas, Denis Yarats, Johnny Ho, and Andy Konwinski. It answers questions with cited sources by combining web search with large language models, offers a Pro tier with model choice, and grew rapidly as a Google-search alternative for research queries.",
    "artifact_cuda":
        "CUDA is NVIDIA's parallel computing platform and programming model for its GPUs, introduced in 2006-2007. It exposes GPU compute through C/C++ (and other language bindings) with kernels, threads, blocks, and a memory hierarchy, and is the foundation of the modern deep-learning software stack (cuDNN, cuBLAS, PyTorch and TensorFlow GPU backends).",
    "artifact_dpo":
        "DPO (Direct Preference Optimization) is a method for aligning language models to human preferences without training an explicit reward model or using reinforcement learning, introduced in the 2023 paper 'Direct Preference Optimization: Your Language Model is Secretly a Reward Model' by Rafael Rafailov, Archit Sharma, Eric Mitchell, Stefano Ermon, Christopher D. Manning, and Chelsea Finn (NeurIPS 2023 best-paper runner-up). It optimizes a simple classification-style loss on preference pairs and became a standard alternative to RLHF/PPO.",
    "artifact_rlhf":
        "RLHF (Reinforcement Learning from Human Feedback) is the alignment technique in which a reward model is trained from human preference comparisons and a language model is then optimized against it with reinforcement learning (typically PPO). Popularized by OpenAI's InstructGPT (Ouyang et al., 2022) building on Christiano et al. (2017), it was the key post-training recipe behind ChatGPT-style assistants.",
    "artifact_eagle":
        "EAGLE is a speculative-decoding method for accelerating LLM inference, introduced in 2024 by Yuhui Li and collaborators ('EAGLE: Speculative Sampling Requires Rethinking Feature Uncertainty'). It drafts future tokens by extrapolating second-to-top-layer features with a lightweight head and verifies them with the target model, achieving state-of-the-art lossless speedups; EAGLE-2 and EAGLE-3 refine the approach.",
    "artifact_alpaca":
        "Alpaca is the Stanford instruction-following model released in March 2023 by Rohan Taori, Ishaan Gulrajani, Tianyi Zhang, Yann Dubois, Xuechen Li and collaborators at Stanford CRFM. It fine-tuned Meta's LLaMA-7B on 52K instruction-following demonstrations generated with OpenAI's text-davinci-003 via self-instruct, showing that capable instruction models could be reproduced cheaply and sparking a wave of open instruction-tuned models.",
    "artifact_opencl":
        "OpenCL (Open Computing Language) is the open, royalty-free standard for cross-platform parallel programming of heterogeneous processors (GPUs, CPUs, FPGAs), maintained by the Khronos Group and first released in 2009 (originally proposed by Apple). It defines a C-based kernel language and runtime API, and served as the vendor-neutral alternative to CUDA.",
    "artifact_lm_studio":
        "LM Studio is a desktop application for discovering, downloading, and running open-weight large language models locally on Mac, Windows, and Linux, with a chat interface, an OpenAI-compatible local server, and support for GGUF-quantized models via llama.cpp and MLX backends. It became one of the most popular consumer tools for local LLM inference.",
    "artifact_scann":
        "ScaNN (Scalable Nearest Neighbors) is Google Research's open-source library for efficient vector similarity search / approximate nearest-neighbor retrieval (google-research/google-research tree, scann). Based on anisotropic vector quantization ('Accelerating Large-Scale Inference with Anisotropic Vector Quantization', ICML 2020), it long topped ANN benchmarks and backs embedding retrieval in Google products.",
    "artifact_snowflake":
        "Snowflake is a cloud data platform / data warehouse company founded in 2012 by Benoit Dageville, Thierry Cruanes, and Marcin Zukowski. Its architecture separates storage from elastic compute ('virtual warehouses') on AWS, Azure, and GCP; its 2020 IPO was the largest software IPO to date, and Snowflake became a standard enterprise analytics platform.",
    "artifact_vespa":
        "Vespa is an open-source platform for serving big-data applications combining full-text search, vector search, and machine-learned ranking at scale, developed at Yahoo (open-sourced 2017) and later spun out as Vespa.ai. It executes distributed query-time inference over structured, text, and tensor data and is used for search and recommendation systems.",
    "artifact_r_language":
        "R is a programming language and environment for statistical computing and graphics, created by Ross Ihaka and Robert Gentleman at the University of Auckland (first released 1993-1995) as an open-source implementation of the S language. Distributed via CRAN with thousands of packages (including the tidyverse and ggplot2), it is a standard language of statistics and data analysis.",
    "artifact_f_sharp":
        "F# is a functional-first programming language for the .NET platform, designed by Don Syme at Microsoft Research (first released 2005). Rooted in the ML family (OCaml), it combines functional, imperative, and object-oriented styles, features type inference, pattern matching, and units of measure, and is developed as an open-source language under the F# Software Foundation.",
    "artifact_stable_audio":
        "Stable Audio is Stability AI's generative audio model family (first released September 2023) that produces music and sound effects from text prompts using latent diffusion over audio. Stable Audio 2.0 (2024) generates full-length stereo tracks up to about three minutes and added audio-to-audio transformation; an open-weights variant, Stable Audio Open, was also released.",
    "artifact_math_benchmark":
        "MATH is a benchmark of 12,500 competition mathematics problems (AMC/AIME-style) with full step-by-step solutions, introduced in 'Measuring Mathematical Problem Solving With the MATH Dataset' by Dan Hendrycks and collaborators (NeurIPS 2021 Datasets track). Problems span seven subjects with difficulty levels 1-5, and it became a standard measure of LLM mathematical reasoning.",
    "artifact_stackexchange_data":
        "The Stack Exchange Data Dump is the periodically released, Creative-Commons-licensed export of the complete content of the Stack Exchange network (questions, answers, comments, votes, users) including Stack Overflow. Distributed via the Internet Archive, it became a core source of high-quality Q&A text for language-model pretraining corpora and instruction datasets.",
    "artifact_udio":
        "Udio is an AI music-generation service launched in April 2024 by former Google DeepMind researchers (backed by a16z and others), producing full songs with vocals and instrumentation from text prompts. It gained attention for high-quality output (including the viral 'BBL Drizzy'), and in 2024 was sued by major record labels over training data; it later settled with Universal Music Group.",
    "artifact_minigpt_4":
        "MiniGPT-4 is an open-source vision-language model released in April 2023 by Deyao Zhu, Jun Chen, and collaborators at KAUST. It aligns a frozen vision encoder (BLIP-2's Q-Former + ViT) with the Vicuna LLM through a single projection layer, reproducing GPT-4-style image-grounded dialogue capabilities cheaply, and became one of the most-starred early multimodal LLM projects.",
    "method_zero_shot_learning":
        "Zero-shot learning is the machine-learning paradigm in which a model must recognize or perform classes/tasks never seen during training, typically by leveraging auxiliary semantic information (attributes, class descriptions, embeddings). Formalized in work such as Lampert et al.'s attribute-based classification (2009) and Palatucci et al. (2009), it underpins modern zero-shot behavior of CLIP-style and large language models.",
    "method_siamese_network":
        "A Siamese network is a neural architecture with twin subnetworks sharing weights that map two inputs into a common embedding space, trained so that a distance function reflects semantic similarity. Introduced by Bromley, Guyon, LeCun et al. (1993) for signature verification, it became the foundation of metric learning, face verification (DeepFace/FaceNet lineage), one-shot learning (Koch et al., 2015), and modern contrastive representation learning.",
    "method_matching_networks":
        "Matching Networks is a one-shot/few-shot learning method introduced by Oriol Vinyals, Charles Blundell, Timothy Lillicrap, Koray Kavukcuoglu, and Daan Wierstra (NeurIPS 2016, 'Matching Networks for One Shot Learning'). It classifies a query by an attention-weighted match over a small labeled support set, with episodic training that matches train and test conditions, and helped establish the modern few-shot learning protocol on Omniglot and miniImageNet.",
    "method_contrastive_learning":
        "Contrastive learning is the representation-learning paradigm that trains encoders by pulling embeddings of positive pairs together and pushing negatives apart, typically with the InfoNCE loss (Oord et al., 2018). Instantiated in SimCLR, MoCo, and CLIP, it drove the self-supervised pretraining wave in vision and multimodal learning.",
    "method_variational_em":
        "Variational EM is the variant of the expectation-maximization algorithm in which the E-step's intractable posterior is replaced by an optimized variational approximation, maximizing the evidence lower bound (ELBO) by coordinate ascent. It is a foundational tool of approximate Bayesian inference — classical applications include latent Dirichlet allocation (Blei, Ng, Jordan, 2003) — and the conceptual ancestor of variational autoencoders.",
    "method_pretraining_finetuning":
        "The pretraining-finetuning paradigm trains a large model on broad unlabeled data with a self-supervised objective, then adapts it to downstream tasks with comparatively little labeled data. Established in NLP by ULMFiT, ELMo, GPT, and BERT (2018), it replaced task-specific training from scratch and is the organizing recipe of the foundation-model era.",
}


def main():
    gold_path = HERE / "inputs" / "gold_answers_v2.json"
    gold = json.loads(gold_path.read_text())
    ents = {e["id"]: e for e in json.loads(
        (HERE / "inputs" / "pilot_entities_v2.json").read_text())}
    # map FIXES keys -> real entity ids by name when key not present
    name_map = {e["name"].lower(): i for i, e in ents.items()}
    resolved = {}
    MANUAL_NAME = {
        "artifact_r_language": "r", "artifact_f_sharp": "f#",
        "artifact_math_benchmark": "math",
        "artifact_stackexchange_data": "stackexchange data",
        "artifact_udio": "udio", "artifact_minigpt_4": "minigpt-4",
        "method_zero_shot_learning": "zero-shot learning",
        "method_siamese_network": "siamese network",
        "method_matching_networks": "matching networks",
        "method_contrastive_learning": "contrastive learning",
        "method_variational_em": "variational em",
        "method_pretraining_finetuning": "pretraining-finetuning paradigm",
    }
    for k, v in FIXES.items():
        if k in gold:
            resolved[k] = v
        else:
            nm = MANUAL_NAME.get(k)
            eid = name_map.get(nm) if nm else None
            if eid:
                resolved[eid] = v
            else:
                print(f"  !! could not resolve {k}")
    for eid, v in resolved.items():
        gold[eid] = v
    gold_path.write_text(json.dumps(gold, ensure_ascii=False, indent=1))
    print(f"patched {len(resolved)} golds")

    fixed_ids = set(resolved)
    # purge affected verdicts from both verdict files
    for vf in [HERE / "outputs/recognition_v3.jsonl",
               HERE / "outputs/recognition_final.jsonl"]:
        if not vf.exists():
            continue
        kept, dropped = [], 0
        for line in open(vf):
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if (r["entity_id"] in fixed_ids
                    and r.get("dataset", "main") == "main"
                    and r.get("rationale") != "refusal"
                    and not r.get("is_refusal")):
                dropped += 1
                continue
            kept.append(line.rstrip())
        vf.write_text("\n".join(kept) + "\n")
        print(f"{vf.name}: dropped {dropped} stale verdicts")

    # re-judge affected main-run responses now (into recognition_v3.jsonl)
    from google import genai
    from google.genai import types as genai_types
    TPL = (HERE / "inputs" / "judge_prompt_v3_tightened.txt").read_text()
    SCHEMA = {"type": "object", "properties": {
        "recognized": {"type": "boolean"}, "coverage": {"type": "number"},
        "accuracy": {"type": "number"}, "rationale": {"type": "string"}},
        "required": ["recognized", "coverage", "accuracy", "rationale"]}
    SYS = ("You are an objective grader judging whether a language model "
           "genuinely recognizes a specific named entity. Use knowledge freely "
           "to refute, but credit only positively-verified non-guessable facts.")
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    recs = []
    for line in open(HERE / "outputs/full_v2_results.jsonl"):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r["entity_id"] in fixed_ids:
            recs.append(r)
    print(f"re-judging {sum(1 for r in recs if not r['is_refusal'])} answered "
          f"records for {len(fixed_ids)} entities")

    def work(r):
        e = ents[r["entity_id"]]
        if r["is_refusal"]:
            return {"entity_id": r["entity_id"], "model_id": r["model_id"],
                    "cohort": e["cohort"], "synthetic": False,
                    "is_refusal": 1, "recognized": 0, "rationale": "refusal"}
        for a in range(4):
            try:
                resp = client.models.generate_content(
                    model="gemini-3-flash-preview",
                    contents=TPL.format(name=e["name"], context=e["context"],
                                        gold_answer=gold[r["entity_id"]],
                                        response=r["response"]),
                    config=genai_types.GenerateContentConfig(
                        system_instruction=SYS, temperature=0.0,
                        response_mime_type="application/json",
                        response_schema=SCHEMA))
                p = json.loads(resp.text)
                return {"entity_id": r["entity_id"], "model_id": r["model_id"],
                        "cohort": e["cohort"], "synthetic": False,
                        "is_refusal": 0,
                        "recognized": int(bool(p["recognized"])),
                        "rationale": str(p["rationale"])[:200]}
            except Exception:
                if a == 3:
                    return None
                time.sleep(2 * (a + 1))

    out = open(HERE / "outputs/recognition_v3.jsonl", "a")
    n = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        for fut in as_completed([ex.submit(work, r) for r in recs]):
            v = fut.result()
            if v:
                out.write(json.dumps(v, ensure_ascii=False) + "\n")
                n += 1
    out.close()
    print(f"re-judged {n} records with corrected golds")


if __name__ == "__main__":
    main()
