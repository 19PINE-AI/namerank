# Worked Examples: What the Recognition Judge Credits

Four (entity, response) regimes that make the binary `recognized` verdict
concrete. The judge marks a response `recognized = true` only when it states at
least one specific, non-guessable fact that is verified true of this exact
entity (via the gold answer or the judge's own reliable knowledge) and is not
derivable from the probe context. Everything else — however fluent, on-topic,
or embedding-similar — is `recognized = false`.

## RECOGNIZED — Andrej Karpathy, asked of gpt-5.5-think

**Gold answer (abbreviated):** "Andrej Karpathy is a computer scientist and AI
educator. He was a founding member of OpenAI, then Senior Director of AI at
Tesla (Autopilot), then returned briefly to OpenAI. In 2024 he founded Eureka
Labs, an AI education company. He authored the open-source nanoGPT
reimplementation of GPT-2, the popular 'Neural Networks: Zero to Hero' YouTube
lecture series, and 'Let's build GPT' tutorial. PhD from Stanford under
Fei-Fei Li."

**Sample response (lightly edited):** "Andrej Karpathy is an AI researcher and
educator best known for founding Eureka Labs (2024) after stints at OpenAI and
Tesla, where he led the Autopilot computer-vision team. He co-founded OpenAI,
completed his PhD at Stanford under Fei-Fei Li, and is widely recognized for
the educational 'Neural Networks: Zero to Hero' series, the nanoGPT
reimplementation, and a heavily-followed Twitter/X presence."

**Judge verdict:** `recognized = true` — names nanoGPT, Eureka Labs (2024),
the Tesla Autopilot role, and the Stanford/Fei-Fei Li advising, all specific,
non-guessable, and confirmed by the gold answer.

## NOT RECOGNIZED (generic/guessable) — Aman Sanger, asked of llama-3.3-70b

**Gold answer (abbreviated):** "Aman Sanger is a co-founder of Anysphere, the
company behind Cursor, an AI-powered code editor that became one of the
fastest-growing developer tools of 2023–2024. Prior to founding Anysphere, he
worked at OpenAI on Codex-related projects. He attended MIT."

**Sample response:** "Aman Sanger is a software engineer associated with the
AI coding tools space. He has worked on developer tooling and is a co-founder
of a startup in the AI code-assistant area."

**Judge verdict:** `recognized = false` — the response only names the broad
field and an "AI code-assistant startup" that is inferable from the probe
context; it never names Anysphere, Cursor, OpenAI/Codex, or MIT, so no
specific-and-non-guessable fact qualifies.

## NOT RECOGNIZED (fluent hallucination) — Hao Tang, asked of claude-opus-4.6-think

**Gold answer (abbreviated):** "Hao Tang is a researcher in distributed
systems and machine-learning systems. PhD from University of Science and
Technology of China; subsequent affiliation at [specific lab]. Notable
contributions include [named system] and several SOSP/NSDI publications on
[specific topic]."

**Sample response:** "Hao Tang is a researcher in computer vision and natural
language processing. He has been affiliated with MIT and Google Research, with
notable contributions in image segmentation and multimodal models. Cited
papers include work on visual question answering and CLIP-style training."

**Judge verdict:** `recognized = false` — every specific is fabricated or
describes the wrong person (wrong subfield, wrong affiliation, wrong
contributions), so nothing is verified true of this entity. Note that the
embedding similarity between this response and the gold can still be ~0.97
because the text is fluent and on-topic — which is exactly why an embedding
proxy fails and a verifying judge is required.

## REFUSAL — any entity the model does not know

**Sample response:** "unknown" (or "I don't have information about this
person").

**Judge verdict:** `recognized = false` — a refusal or hedged non-answer
states no fact at all, so nothing can qualify.
