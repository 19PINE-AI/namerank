import React, { useState } from 'react'
import { Reveal, MiniMd } from '../lib/ui.jsx'
import { DotStrip, VarianceBar } from '../components/charts.jsx'
import cases from '../data/explainer_cases.json'
import stats from '../data/stats.json'

const STEPS = [
  { n: 'A', t: 'One fixed probe', d: 'Tell me what you know about [name], who [context]. Say “unknown” if you don’t recognise it.' },
  { n: 'B', t: `${stats.models}-model panel`, d: 'Every frontier model answers from its own weights — thinking mode on, no web search.' },
  { n: 'C', t: 'Recognition judge', d: 'A separate model returns a binary verdict against a curated gold answer.' },
  { n: 'D', t: 'NameRank', d: 'The fraction of the panel that genuinely recognised the entity. 0 to 1.' },
]

const TABS = [
  { k: 'full', label: 'Recognised' },
  { k: 'partial', label: 'One real fact' },
  { k: 'hallucination', label: 'Fluent, but wrong' },
  { k: 'refusal', label: 'Said “unknown”' },
]
const VERDICT = { full: true, partial: true, hallucination: false, refusal: false }
const WHY = {
  full: 'States many specific, verified facts about this exact person. Clear recognition.',
  partial: 'Coverage is partial, but it names a verified, non-guessable fact (Y Combinator). Under a binary recognition verdict that is enough — which is exactly why recognition beats a graded coverage score.',
  hallucination: 'Fluent and on-topic, but the specific claims are wrong for this person. Nothing verifiable beyond the context survives — so the verdict is no recognition, no matter how confident it sounds.',
  refusal: 'The model honestly declines. Silence, not a fabricated biography — the property that keeps the score from misleading.',
}

function CaseStudy() {
  const [tab, setTab] = useState('full')
  const c = cases[tab]
  const yes = VERDICT[tab]
  return (
    <div className="panel panel--pad">
      <div className="panel-head">
        <span className="panel-title">The judge, on four real answers</span>
        <span className="tag">CASE {c.model}</span>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7, marginBottom: 20 }}>
        {TABS.map((t) => (
          <button key={t.k} className={`chip ${tab === t.k ? 'is-on' : ''}`} onClick={() => setTab(t.k)}>{t.label}</button>
        ))}
      </div>

      <div className="grid grid-2" style={{ gap: 20 }}>
        <div>
          <div className="tag" style={{ fontSize: '0.62rem', marginBottom: 6 }}>PROBE → {c.name}</div>
          <div className="mono" style={{ fontSize: '0.82rem', color: 'var(--ink-2)', border: '1px solid var(--line)', borderRadius: 3, padding: '10px 12px', marginBottom: 14 }}>
            “…about <b style={{ color: 'var(--ink)' }}>{c.name}</b>, who is {c.context}.”
          </div>
          <div className="tag" style={{ fontSize: '0.62rem', marginBottom: 6 }}>MODEL RESPONSE</div>
          <p style={{ fontSize: '0.9rem', color: 'var(--ink-2)', maxWidth: 'none' }}>
            {c.response.length > 460 ? <><MiniMd text={c.response.slice(0, 460)} />…</> : <MiniMd text={c.response} />}
          </p>
        </div>

        <div>
          <div className="tag" style={{ fontSize: '0.62rem', marginBottom: 6 }}>CURATED GOLD (verification anchor)</div>
          <p style={{ fontSize: '0.84rem', color: 'var(--ink-3)', maxWidth: 'none', borderLeft: '2px solid var(--line-2)', paddingLeft: 12, marginBottom: 18 }}>
            {c.gold.length > 320 ? c.gold.slice(0, 320) + '…' : c.gold}
          </p>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
            <span className={`verdict ${yes ? 'verdict--yes' : 'verdict--no'}`}>{yes ? '● recognised' : '○ no recognition'}</span>
            <span className="tag">diagnostic cov×acc {c.judges.gemini.cov.toFixed(1)} · {c.judges.gemini.acc.toFixed(1)}</span>
          </div>
          <p className="caption" style={{ marginTop: 0 }}>{WHY[tab]}</p>
        </div>
      </div>
    </div>
  )
}

export default function HowItWorks() {
  return (
    <section id="method" className="section">
      <div className="wrap">
        <div className="sec-head">
          <span className="sec-idx">01</span>
          <h2 className="sec-title">A recognition instrument</h2>
        </div>
        <Reveal className="lede sec-kicker">
          NameRank asks one holistic question of each model: <em>do you actually know this
          entity?</em> Not how much it can say — whether a single specific, non-guessable,
          verified fact survives. A hallucination, a context echo, or a lucky guess all score zero.
        </Reveal>

        <Reveal className="grid grid-4" style={{ marginTop: 44 }}>
          {STEPS.map((s, i) => (
            <div key={s.n} className="panel panel--pad" style={{ position: 'relative' }}>
              <div className="num" style={{ fontSize: '0.9rem', color: 'var(--signal)', marginBottom: 10 }}>{s.n}{i < 3 && <span style={{ color: 'var(--ink-faint)', float: 'right' }}>→</span>}</div>
              <div className="panel-title" style={{ marginBottom: 8 }}>{s.t}</div>
              <p style={{ fontSize: '0.86rem', color: 'var(--ink-2)' }}>{s.d}</p>
            </div>
          ))}
        </Reveal>

        <Reveal style={{ marginTop: 26 }}><CaseStudy /></Reveal>

        <div className="grid grid-2" style={{ marginTop: 26 }}>
          <Reveal className="panel panel--pad">
            <div className="panel-head"><span className="panel-title">It measures the entity, not the panel</span></div>
            <VarianceBar variance={stats.var} />
            <p className="caption">Decomposing every verdict, the <b>entity</b> explains ~{stats.var.entity}% of the variance
              against {stats.var.model}% for the model. Which model you ask barely matters — the name does.</p>
          </Reveal>
          <Reveal className="panel panel--pad" delay={80}>
            <div className="panel-head"><span className="panel-title">A nonzero score is real recognition</span></div>
            <div style={{ display: 'flex', gap: 26, alignItems: 'baseline' }}>
              <div><div className="num" style={{ fontSize: '2.4rem', color: 'var(--signal)' }}>{stats.floors.people.toFixed(3)}</div><div className="tag" style={{ fontSize: '0.62rem' }}>SYNTHETIC-NULL FLOOR</div></div>
              <p style={{ fontSize: '0.9rem', color: 'var(--ink-2)', maxWidth: 'none' }}>
                Invented people and tools, run through the whole pipeline, earn essentially nothing —
                the judge credits only facts it can verify. So above the floor is genuine memory, not guessing.
              </p>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  )
}
