# NameRank Tool

`namerank.py` is a self-contained CLI that measures **how recognizable a named
entity is to a panel of LLMs**. It mirrors the [IKP tool](../../ikp): you bring
your own OpenAI-compatible API key, and it prints every model's raw response and
verdict, then a single score.

```
NameRank = (# panel models that genuinely recognize the entity) / (panel size)
```

Unlike a factual-QA benchmark, NameRank asks one *open-ended* question —
*"Tell me what you know about {name}, who is {context}"* — and an **open-book
recognition judge** decides, per model, whether the response contains at least
one **specific, non-guessable, beyond-the-context fact** that is true of *this*
entity. Restating the context, generic praise, plausible hallucination, and
refusals all score as **not recognized**. The score is the fraction of the panel
that clears that bar.

## Install

```bash
pip install -r requirements.txt        # only httpx is strictly required
```

Python ≥ 3.9. No GPU. The one required dependency is `httpx`; `google-genai` is
optional and only used for the canonical Gemini gold backend.

## One-liner

```bash
export OPENROUTER_API_KEY=sk-or-...
python namerank.py --name "Bojie Li" --context "a computer scientist and AI researcher"
```

This (1) generates a web-grounded **gold answer**, (2) probes the full 37-model
panel in parallel, (3) judges each response with the recognition rubric, and
(4) prints a per-model table and the NameRank. Typical cost per entity:
**$0.05–$0.30** at OpenRouter list prices (37 probes + 37 judge calls + 1 gold).

## The two pieces you asked for

### 1. Gold-answer agent (web search)

The gold is the reference the judge anchors against. It is produced by an LLM
agent that **searches the web** and writes ONE length-disciplined (~55-word),
namesake-guarded factual profile — the exact generator from the paper
(`code/generate_golds.py`). Three ways to get one:

| Mode | Flag | Needs |
|---|---|---|
| Canonical: Gemini + Google Search grounding | `--gold-backend gemini` | `GEMINI_API_KEY` + `google-genai` |
| Single-key: an OpenRouter `:online` model | `--gold-backend openrouter` | just your OpenRouter key |
| **Auto** (default) | `--gold-backend auto` | Gemini if available, else OpenRouter |

Inspect the gold without probing anything:

```bash
python namerank.py --name "Tri Dao" --context "an ML researcher" --gold-only
```

### 2. The probe

The panel is queried with the exact open-ended probe (`--show-probe` to see it
and the judge rubric). Each response is truncated to 200 words, then graded by
the open-book judge (`google/gemini-3-flash-preview` by default).

## Supply your own gold

```bash
python namerank.py --name "Ada Lovelace" --context "a 19th-century mathematician" \
    --gold "English mathematician; wrote the first published algorithm intended for Babbage's Analytical Engine; daughter of Lord Byron."
# or --gold-file ada.txt
```

In a batch file, any entity object may carry its own `"gold"`.

## CLI reference

```
python namerank.py [options]
```

**Entity** — `--name` + `--context`, or `--entities FILE` (JSON list of
`{name, context, [gold]}`) for a batch ranking.

**Gold** — `--gold TEXT` / `--gold-file FILE` (supply your own);
`--gold-backend {auto,gemini,openrouter}`, `--gold-model`, `--gold-maxwords 55`;
`--gold-only` (print gold and exit).

**Panel API** — `--api-base URL` (default OpenRouter), `--api-key KEY`
(default `$OPENROUTER_API_KEY`), `--models a,b,c` (subset by id or slug),
`--panel FILE` (custom panel JSON), `--sample N` (probe N of the 37),
`--thinking` (force reasoning for custom `--models`).

**Judge** — `--judge-model` (default `google/gemini-3-flash-preview`),
`--judge-api-base`, `--judge-api-key` (default: same as the panel).

**Output** — `--workers N` (default 12), `--timeout SEC` (per-request timeout
for panel + judge calls, default 60), `--output FILE` (combined JSON of the whole
run), `--no-save` (disable the automatic per-entity dumps), `--inspect` (print
every response + judge rationale).

**Info (no tokens)** — `--show-panel`, `--show-probe`.

## Output

```
  ╔══════════════════════════════════════════════════════════╗
  ║  NameRank Result                                         ║
  ╠══════════════════════════════════════════════════════════╣
  ║  Entity:    Tri Dao                                      ║
  ║  NameRank:  0.500  (2/4 models recognize)                ║
  ║  Depth:     0.350  (mean coverage×accuracy)              ║
  ╚══════════════════════════════════════════════════════════╝
```

- **NameRank** — headline: fraction of the panel that recognizes the entity.
- **Depth** — mean coverage×accuracy, an appendix-grade diagnostic of *how much*
  the recognizers say, not just whether they recognize. Lower-weight than NameRank.

While the panel runs, each model's verdict is streamed to the terminal on its
own line as it returns (no overwriting progress bar), so the final result table
above is preserved intact in the scrollback.

By default every entity's full run is saved to a descriptively-named
`namerank_<entity-slug>.json` in the current directory — the probe, gold, judge
prompt, and per-model `records[]` (each with the model's raw `response`, the
judge's raw `judge_raw` output, and the parsed `recognized`/`coverage`/`accuracy`/
`rationale`/`is_refusal`). Pass `--no-save` to skip these dumps, or `--output FILE`
to additionally write one combined JSON for the whole run.

## Notes & limitations

- **The judge is open-book by design.** It uses its own knowledge to *refute*
  (catch same-name namesakes and hallucinations) but only credits a novel fact
  it positively knows; when it does not know the entity, it grades strictly
  against the gold. This is what stops a fluent hallucination from scoring as
  recognition (see the gemma-3-4b "different Tri Dao" case in a live run).
- **The gold matters.** A too-narrow gold can under-credit a genuinely famous
  entity whose known facts differ from the gold's picks; the open-book judge
  mitigates this but does not eliminate it. Prefer the web-search gold or a
  hand-written one covering the entity's most-named facts.
- **Panel slugs are OpenRouter IDs.** On a different endpoint, pass your own
  model list via `--models` (with `--thinking` if applicable) or `--panel FILE`.
- **NameRank measures name-propagation, not accomplishment.** A diffuse
  contributor with no named, indexed artifact scores low even if accomplished —
  that is the paper's thesis, not a bug.
