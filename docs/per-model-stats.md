# Per-Model Recognition and Refusal Statistics

Per-model statistics across the 36-model recognition run. "Rec." is the
per-model recognition rate — the fraction of that model's ~4,730 records the
recognition judge marked `recognized` — and "Ref." is the refusal rate.
Source: `data/analysis/per_model_summary.csv`.

| Model | Rec. | Ref. |
|---|---:|---:|
| gemini-3-flash-think | 0.784 | 5% |
| claude-fable-5-think | 0.737 | 5% |
| gemini-3.1-pro | 0.708 | 24% |
| deepseek-v4-pro-think | 0.669 | 18% |
| gemini-2.5-pro-think | 0.653 | 5% |
| gpt-5.5-think | 0.652 | 18% |
| claude-opus-4.6-think | 0.636 | 23% |
| claude-sonnet-4.6-think | 0.620 | 11% |
| glm-5.2-think | 0.603 | 28% |
| glm-5.1-think | 0.600 | 30% |
| qwen3.7-max-think | 0.595 | 29% |
| deepseek-v4-flash-think | 0.586 | 30% |
| deepseek-v3.2-think | 0.582 | 18% |
| glm-4.7-think | 0.577 | 23% |
| qwen3.5-397b-a17b-think | 0.558 | 3% |
| kimi-k2.7-code-think | 0.553 | 32% |
| kimi-k2.6-think | 0.539 | 41% |
| gpt-5.3 | 0.517 | 42% |
| minimax-m3-think | 0.512 | 28% |
| gpt-5.4 | 0.510 | 31% |
| llama-4-maverick | 0.500 | 0% |
| nemotron-3-ultra-think | 0.491 | 42% |
| step-3.7-flash-think | 0.481 | 35% |
| llama-3.3-70b | 0.408 | 8% |
| qwen3-235b-a22b-think | 0.389 | 44% |
| minimax-m2.7-think | 0.386 | 51% |
| gemma-4-31b | 0.366 | 24% |
| gemma-3-12b | 0.359 | 19% |
| llama-3.1-8b | 0.321 | 3% |
| qwen3-32b-think | 0.304 | 33% |
| nemotron-3-nano-30b-think | 0.303 | 43% |
| phi-4 | 0.302 | 0% |
| mistral-small-24b | 0.299 | 53% |
| gemma-3-4b | 0.268 | 0% |
| qwen3-8b-think | 0.260 | 33% |
| gpt-oss-20b-think | 0.242 | 57% |

Each model contributes ~4,730 records. Two failure styles are visible at the
row level. A strict, high-refusal cluster sits at the bottom
(gpt-oss-20b-think, mistral-small-24b, qwen3-8b-think): these models decline
whenever they are unsure, so most of their un-recognized records are outright
refusals. Against them stands a zero-refusal, fluent cluster
(llama-4-maverick, phi-4, gemma-3-4b) that answers every probe. Because the
recognition verdict credits only positively-verified, non-guessable facts, it
disciplines that fluent cluster — a smoothly written but unverifiable bio earns
no recognition — so their recognition rates stay moderate despite near-zero
refusal.
