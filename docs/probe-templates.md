# Probe and Judge Templates

The exact prompts used in the NameRank pipeline. The templates are also shipped
as plain-text inputs in [`data/inputs/`](../data/inputs/)
(`probe_template_en.txt`, `probe_template_zh.txt`).

## English probe template

```
Tell me what you know about {name}, who is {context}.
If you do not recognize this entity, respond with "unknown".
Limit your response to about 150 words.
```

- `{name}` — the canonical entity name.
- `{context}` — a short disambiguating clause (role + affiliation + field). The
  context never names specific contributions, papers, dates, or named
  artifacts; the paper's context-ablation experiment confirms it anchors
  disambiguation without leaking the gold answer.

## Chinese probe template

Used for the 240-entity Chinese-prompt sub-run (8,880 records). Gold answers
and the judge prompt remain in English; the judge grades across languages.

```
请告诉我你了解的关于 {name} 的信息，该实体是 {context}。如果你不认识此实体，请回答"未知"。请将回答控制在大约 150 字以内。
```

English back-translation:

```
Please tell me what you know about {name}, which is {context}.
If you do not recognize this entity, respond with "unknown".
Please keep your response to about 150 characters.
```

## Judge prompt

The judge is Gemini 3 Flash Preview (direct Google API, temperature 0, low
reasoning budget). It receives the gold answer and the model response and
returns independent coverage and accuracy scores in [0, 1]; the per-record
NameRank contribution is their product.

```
ENTITY: {name}

GOLD ANSWER (authoritative reference, ~150 words):
{gold_answer}

MODEL RESPONSE (to be graded):
{response}

Score the response on two axes:

1. COVERAGE (0.0-1.0): How much of the gold answer's substantive
   content does the response include?
   Substantive content = named artifacts, named affiliations,
   named contributions, identifying facts (year, location, role
   title). Vague statements like "works in AI" or "is famous"
   are NOT substantive content.
   - 1.0: covers all major facts;
   - 0.7: most major facts (>=70%);
   - 0.4: some (>=30%);
   - 0.1: very little (<30%);
   - 0.0: unrelated/refused/unknown.

2. ACCURACY (0.0-1.0): Are the factual claims in the response
   correct, per the gold answer?
   A "factual claim" is a specific named entity, year, role, or
   relationship asserted by the response. Penalize hallucinations
   heavily.
   - 1.0: all claims correct;
   - 0.7: most correct, minor errors;
   - 0.4: mix of correct and incorrect;
   - 0.1: mostly incorrect (hallucinations dominate);
   - 0.0: entirely fabricated/unrelated.

IMPORTANT:
a) Hallucinated bios (high coverage, low accuracy) MUST
   score LOW on accuracy.
b) Refusals ("I don't know", "unknown") score 0.0 on both axes.
c) Don't penalize correct extra facts that aren't in the gold.
d) Don't credit vague statements that could apply to many.
e) If the gold answer names a contribution and the response
   names it too, count as a substantive fact covered.

Output ONLY JSON: {"coverage": <0.0-1.0>, "accuracy": <0.0-1.0>,
                   "rationale": "<one sentence>"}
```

## Paraphrase templates (robustness)

The prompt-paraphrase robustness experiment (paper, robustness section) probes
a 200-entity subset under three paraphrases (T1–T3) of the original template
(T0). All four preserve the name slot, the context cue, the literal "unknown"
escape token, and the ~150-word length hint:

```
T0: Tell me what you know about {name}, who is {context}. If you do
    not recognize this entity, respond with "unknown". Limit your
    response to about 150 words.
T1: What can you tell me about {name}? They are {context}. Reply with
    only "unknown" if you are not familiar with this entity. Aim for
    about 150 words.
T2: Please share what you know about {name}, {context}. If unknown to
    you, answer with just "unknown". Keep it under ~150 words.
T3: Briefly describe {name}, who is {context}. Respond "unknown" if
    you have no information. Around 150 words please.
```
