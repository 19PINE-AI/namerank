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

Used for the 240-entity Chinese-prompt sub-run (8,640 records). Gold answers
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

The judge is Gemini 3 Flash Preview (direct Google API, temperature 0). It is
shown the entity name, the probe context, the gold answer, and the model
response, and returns a BINARY `recognized` verdict. `recognized` is true only
if the response states at least one specific, non-guessable fact that is (a)
true of this exact entity per the gold answer or the judge's own reliable
knowledge, (b) not derivable from the probe context, and (c) about the same
entity the gold identifies (not a same-name person). The judge uses knowledge
asymmetrically — it may refute freely but credits only positively-verified
facts — and applies an anti-confabulation rule for competition,
fellowship, and minor-paper entities. Coverage and accuracy are also recorded
per response, but they are retained only as diagnostics and do not enter
NameRank; NameRank is the fraction of the panel whose `recognized` verdict is
true.

```
ENTITY: {name}

PROBE CONTEXT (already given to the model in the question; repeating it earns nothing):
{context}

GOLD ANSWER (reference facts that IDENTIFY which specific entity this is — use it to disambiguate the person/thing and as a correctness anchor):
{gold_answer}

MODEL RESPONSE (to be graded):
{response}

Judge whether the model genuinely RECOGNIZES this specific entity.

RECOGNIZED = true only if the response states at least one SPECIFIC, NON-GUESSABLE fact that is:
  (a) TRUE of THIS entity, established by EITHER (i) the gold answer, OR (ii) your own independent knowledge — meaning you actually recognize this fact as true of this specific entity, not merely that it sounds plausible; and
  (b) not derivable from the probe context; and
  (c) about the SAME entity the gold identifies (same person/thing), not a different entity that shares the name.

CRITICAL ASYMMETRY between crediting and refuting:
  - To CREDIT a fact not in the gold, you must POSITIVELY know it is true of this entity. If you do not already know this entity, you CANNOT verify novel claims about it — a plausible-sounding but unverified specific is exactly what a model hallucinates about obscure or non-existent people, and it scores FALSE. When you do not know the entity, ignore your own knowledge and grade STRICTLY against the gold answer only.
  - To REFUTE, use all of your knowledge freely: if you know the response describes a same-name DIFFERENT entity, or states something false about this entity, do not credit it.

ANTI-CONFABULATION RULE (important — you do NOT have reliable per-individual memory of most competition participants, fellowship recipients, or minor-paper authors):
  - For an entity who is a COMPETITION PARTICIPANT (olympiad/contest medalist), a FELLOWSHIP/AWARD recipient, or the author/subject of a NON-FAMOUS paper: do NOT credit fine-grained biographical minutiae via "your own knowledge" — e.g. other-year participations, secondary-competition medals, exact scores or ranks, specific host-city trivia, or co-author names of minor works. You cannot reliably recall these for individuals, and asserting you "verified them against official records" is confabulation. For such entities, credit ONLY facts that are present in the GOLD ANSWER, or a MAJOR, widely-documented public achievement you are highly confident about (a well-known company they founded, a famous theorem/tool bearing their name, a professorship at a named university you actually recognize them for).
  - The credential OUTCOME itself is guessable and does NOT count on its own: given a probe saying someone "participated in" a competition, asserting they "won a gold medal / a prize / the fellowship" is a low-entropy guess and is NOT recognition unless accompanied by a genuinely-known, non-guessable specific about THIS person.

Further guards (RECOGNIZED = false):
  - Wrong entity: specifics consistent with a different same-name person/thing.
  - Hallucination / fabrication-dominated response. (One genuinely-verified correct specific still counts even if a minor detail is off; a response that is mostly wrong does not.)
  - Guessable/generic: broad field, nationality, an employer/school implied by the context or inferable from the name, generic praise, restating the context. For a PAPER, naming its journal/venue alone does NOT count (inferable from topic); a real author name, specific result, or exact contribution does — but only if you actually know the paper.
  - Refusal / "I don't have information" / hedged non-answer.
  - When genuinely unsure whether a fact is specific-and-verified-true, default to false.

Also output coverage and accuracy in [0,1] for diagnostics.

Output ONLY JSON: {"recognized": <true|false>, "coverage": <0.0-1.0>, "accuracy": <0.0-1.0>, "rationale": "<one sentence: name the qualifying fact and how it was verified (gold or your knowledge), or why none qualifies>"}
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
