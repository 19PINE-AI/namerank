import React, { useState } from 'react'
import cases from '../data/explainer_cases.json'
import stats from '../data/stats.json'
import heroEntities from '../data/hero_entities.json'
import models from '../data/models.json'
import { fmt, modelLabel, MiniMd, Reveal } from '../lib/ui.jsx'
import { DotStrip } from '../components/charts.jsx'

/* ————— shared bits ————— */

function StepHeader({ n, title, children }) {
  return (
    <Reveal className="step-head">
      <div className="step-num num">{n}</div>
      <div>
        <h3 className="step-title">{title}</h3>
        <div className="prose" style={{ marginTop: 8 }}>{children}</div>
      </div>
    </Reveal>
  )
}

function Meter({ label, value, color }) {
  return (
    <div className="meter">
      <div className="meter-top">
        <span className="tag">{label}</span>
        <span className="num" style={{ fontSize: 15, fontWeight: 600 }}>{fmt(value, 2)}</span>
      </div>
      <div className="meter-track">
        <div className="meter-fill" style={{ width: `${value * 100}%`, background: color }} />
      </div>
    </div>
  )
}

/* ————— step 3: the four real archetype cases ————— */

const CASE_TABS = [
  { key: 'full', label: 'Fully recognized', blurb: 'The model knows the story and gets it right.' },
  { key: 'partial', label: 'Partially known', blurb: 'True as far as it goes — but most of the story is missing.' },
  { key: 'hallucination', label: 'Confidently wrong', blurb: 'Fluent, specific… and invented. This is why we multiply.' },
  { key: 'refusal', label: '“Unknown”', blurb: 'Below its threshold the model goes silent instead of guessing.' },
]

function CaseStudy() {
  const [tab, setTab] = useState('full')
  const [showGold, setShowGold] = useState(false)
  const c = cases[tab]
  const j = c.judges.gemini
  const meta = CASE_TABS.find((t) => t.key === tab)
  return (
    <div className="card case-study">
      <div className="case-tabs">
        {CASE_TABS.map((t) => (
          <button key={t.key} className={`case-tab ${tab === t.key ? 'on' : ''}`}
            onClick={() => { setTab(t.key); setShowGold(false) }}>
            {t.label}
          </button>
        ))}
      </div>
      <div className="case-body" key={tab}>
        <div className="case-left">
          <div className="tag" style={{ marginBottom: 10 }}>
            The question — sent to <b>{modelLabel(c.model)}</b>
          </div>
          <div className="probe-box">
            Tell me what you know about <span className="chip-person">{c.name}</span>, who is{' '}
            <span className="probe-ctx">{c.context}</span>. If you do not recognize this entity,
            respond with “unknown”. Limit your response to about 150 words.
          </div>
          <div className="tag" style={{ margin: '18px 0 10px' }}>The model’s real answer</div>
          <div className={`response-box ${tab === 'refusal' ? 'is-refusal' : ''}`}>
            {c.response ? <MiniMd text={c.response} /> : '(empty response)'}
          </div>
          <button className="btn" style={{ marginTop: 14 }} onClick={() => setShowGold(!showGold)}>
            {showGold ? 'Hide' : 'Show'} the fact sheet the judge used
          </button>
          {showGold && <div className="gold-box">{c.gold}</div>}
        </div>
        <div className="case-right">
          <div className="tag" style={{ marginBottom: 4 }}>The judge’s verdict</div>
          <p style={{ fontSize: 15, color: 'var(--ink-2)', marginBottom: 16 }}>{meta.blurb}</p>
          <Meter label="Coverage — how much of the story?" value={j.cov} color="var(--person)" />
          <Meter label="Accuracy — is it actually true?" value={j.acc} color="var(--good)" />
          <div className="verdict-math num">
            {fmt(j.cov, 2)} × {fmt(j.acc, 2)} = <b>{fmt(j.score, 2)}</b>
          </div>
          <blockquote className="rationale">
            “{j.rationale === 'refusal' ? 'Refusal — the model answered “unknown”, so both axes score zero.' : j.rationale}”
            <footer className="tag" style={{ marginTop: 8 }}>— the judge model, verbatim</footer>
          </blockquote>
        </div>
      </div>
    </div>
  )
}

/* ————— step 3b: why multiply ————— */

function MultiplyDemo() {
  const [cov, setCov] = useState(0.75)
  const [acc, setAcc] = useState(0.1)
  return (
    <div className="card multiply-demo">
      <div className="tag" style={{ marginBottom: 14 }}>Why multiply? Drag and see</div>
      <div className="mult-sliders">
        <label>
          <span className="tag">Coverage <b className="num">{fmt(cov, 2)}</b></span>
          <input type="range" min="0" max="1" step="0.05" value={cov}
            onChange={(e) => setCov(+e.target.value)} style={{ accentColor: 'var(--person)' }} />
        </label>
        <label>
          <span className="tag">Accuracy <b className="num">{fmt(acc, 2)}</b></span>
          <input type="range" min="0" max="1" step="0.05" value={acc}
            onChange={(e) => setAcc(+e.target.value)} style={{ accentColor: 'var(--good)' }} />
        </label>
      </div>
      <div className="mult-outs">
        <div className="mult-out">
          <div className="tag">If we averaged</div>
          <div className="num mult-n" style={{ color: 'var(--ink-3)', textDecoration: 'line-through' }}>
            {fmt((cov + acc) / 2, 2)}
          </div>
          <div className="mult-note">a fluent fabrication still gets half credit</div>
        </div>
        <div className="mult-out">
          <div className="tag">NameRank multiplies</div>
          <div className="num mult-n" style={{ color: 'var(--ink)' }}>{fmt(cov * acc, 2)}</div>
          <div className="mult-note">either axis at zero → the whole answer is worth zero</div>
        </div>
      </div>
    </div>
  )
}

/* ————— step 4: the scale ————— */

const SCALE_ANCHORS = [
  { nr: 0.9, label: 'Household names of the field', ex: 'top OSS libraries, famous benchmarks' },
  { nr: 0.61, label: 'Sam Altman, Andrej Karpathy', ex: 'famous — yet answers still miss facts' },
  { nr: 0.42, label: 'Tianshou (a software library)', ex: 'solidly known to most of the panel' },
  { nr: 0.33, label: 'Jiayi Weng — Tianshou’s creator', ex: 'a third of models draw a blank' },
  { nr: 0.09, label: 'This paper’s author', ex: 'barely present in training data' },
  { nr: 0.04, label: 'GPT‑5 system-card authors', ex: 'the silent zone: models say “unknown”' },
]

function ScaleRuler() {
  return (
    <div className="scale-ruler card">
      <div className="tag" style={{ marginBottom: 18 }}>How to read a NameRank</div>
      {SCALE_ANCHORS.map((a) => (
        <div key={a.nr + a.label} className="scale-row">
          <div className="num scale-n">{fmt(a.nr, 2)}</div>
          <div className="scale-bar-track">
            <div className="scale-bar" style={{ width: `${a.nr * 100}%` }} />
          </div>
          <div className="scale-txt">
            <b>{a.label}</b>
            <span> — {a.ex}</span>
          </div>
        </div>
      ))}
    </div>
  )
}

/* ————— main section ————— */

const MODEL_IDS = models.map((m) => m.id)

export default function HowItWorks() {
  const karpathy = heroEntities.find((e) => e.id === 'andrej_karpathy')
  return (
    <section className="section" id="how">
      <div className="wrap">
        <Reveal>
          <div className="section-kicker">
            <span className="rule" />
            <span className="tag">Section 01 · Mechanism</span>
          </div>
          <h2 className="section-title">How do you measure whether a machine knows a name?</h2>
          <p className="section-lede">
            No leaderboards, no vibes. NameRank is built from four ordinary steps — ask, grade,
            multiply, average — applied {stats.records.toLocaleString()} times. Every example below
            is a real record from the study.
          </p>
        </Reveal>

        <div className="steps">
          <div className="step">
            <StepHeader n="1" title="Ask 37 models one plain question">
              <p>
                Every name gets the same probe, with a one-line hint so the model can’t confuse two
                people who share a name. The models answer <b>from memory alone</b> — web search is
                off. If a name never propagated into a model’s training data, there is nothing to
                retrieve.
              </p>
            </StepHeader>
            <Reveal delay={100}>
              <div className="probe-box big">
                Tell me what you know about <span className="chip-person">&#123;name&#125;</span>, who is{' '}
                <span className="probe-ctx">&#123;a one-line hint&#125;</span>. If you do not recognize this
                entity, respond with “unknown”. Limit your response to about 150 words.
              </div>
              <div className="chart-note" style={{ marginTop: 8 }}>
                The verbatim probe template from the study. The panel spans OpenAI, Anthropic, Google,
                Meta, DeepSeek, Alibaba, Mistral, xAI and more — big flagship models and small open ones.
              </div>
            </Reveal>
          </div>

          <div className="step">
            <StepHeader n="2" title="Grade every answer against the facts">
              <p>
                For each name the authors curated a <b>fact sheet</b> (a “gold answer”): the person’s
                affiliations, their named work, key dates. An <b>independent judge model</b> — one
                not in the panel — compares each answer to the fact sheet and scores two things:{' '}
                <b style={{ color: 'var(--person)' }}>coverage</b> (how much of the story did it
                tell?) and <b style={{ color: 'var(--good)' }}>accuracy</b> (was what it said true?).
                Vague flattery like “a respected researcher” earns nothing.
              </p>
            </StepHeader>
          </div>

          <div className="step">
            <StepHeader n="3" title="Multiply — so confident nonsense scores zero">
              <p>
                The score for one answer is <b>coverage × accuracy</b>. Multiplying, not averaging,
                is the design decision the whole metric rests on: an answer that invents a plausible
                biography can cover a lot of ground while being false — and it should be worth
                nothing. Explore all four ways an answer can go, with real responses:
              </p>
            </StepHeader>
            <Reveal delay={100}><CaseStudy /></Reveal>
            <Reveal delay={80}><MultiplyDemo /></Reveal>
          </div>

          <div className="step">
            <StepHeader n="4" title="Average the panel — that’s the NameRank">
              <p>
                One model’s memory is an anecdote; thirty-seven are a measurement. Averaging the
                graded scores across the whole panel gives each name a single number between 0 and 1.
                Here is Andrej Karpathy’s full panel — every dot is one model’s graded answer:
              </p>
            </StepHeader>
            <Reveal delay={100}>
              <div className="card" style={{ padding: '22px 24px' }}>
                <div className="tag" style={{ marginBottom: 6 }}>
                  Andrej Karpathy — 37 graded answers → one number
                </div>
                <DotStrip scores={karpathy.scores} models={MODEL_IDS} height={80} />
              </div>
            </Reveal>
            <Reveal delay={140}><ScaleRuler /></Reveal>
          </div>

          <div className="step">
            <StepHeader n="5" title="Then ask: who does the machine remember — and why?">
              <p>
                With {stats.entities.toLocaleString()} names scored the same way — CS professors,
                olympiad medalists, Rhodes scholars, open-source tools, startups, long-tail
                researchers — patterns appear that no single anecdote could show. Four of them
                reshaped how we think about reputation in the age of AI. <a href="#findings">See the
                findings ↓</a>
              </p>
            </StepHeader>
          </div>
        </div>
      </div>
    </section>
  )
}
