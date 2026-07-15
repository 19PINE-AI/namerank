import React, { useState } from 'react'
import { Reveal } from '../lib/ui.jsx'
import { DotStrip } from '../components/charts.jsx'
import hero from '../data/hero.json'
import stats from '../data/stats.json'

const CAT = { tianshou: 'artifact', nanogpt: 'artifact' }
const STORY = {
  sam_altman: 'Every model on the panel knows the CEO of OpenAI. Fame this size saturates the instrument — there is no headroom left to measure.',
  andrej_karpathy: 'Recognised by most of the panel, for a whole career rather than one repo. One of the few people who out-ranks their own famous tool.',
  tianshou: 'A reinforcement-learning library most models can describe in detail — while its sole author sits near the floor. The tool propagated; the name behind it did not.',
  jiayi_weng: 'The author of Tianshou. Four of the thirty-six models recognise him. Recognition attached to what he built and barely reached the builder.',
  bojie_li: 'A 2009 olympiad bronze medallist turned systems researcher and founder — recognised for what he later shipped, not for the medal.',
  imo_dongyi_wei: 'An International Mathematical Olympiad gold medallist. The credential selects a few hundred people a year — fewer than half the panel recognises this one.',
}

function Readout({ v, l, s }) {
  return (
    <div className="readout">
      <div className="rs">{s}</div>
      <div className="rv">{v}</div>
      <div className="rl">{l}</div>
    </div>
  )
}

export default function Hero() {
  const [sel, setSel] = useState(hero[2] || hero[0])
  const cat = CAT[sel.id] || 'person'
  const lit = sel.scores.filter((x) => x >= 0.5).length
  return (
    <header className="hero wrap wrap--wide">
      <div className="hero-grid">
        <div>
          <Reveal className="tag tag--signal" style={{ display: 'block', marginBottom: 22 }}>
            RECOGNITION IN THE LLM CHANNEL · {stats.models}-MODEL PANEL
          </Reveal>
          <Reveal as="h1" className="display" delay={60}>
            The model knows<br />your <em>project</em>,<br />not you.
          </Reveal>
          <Reveal className="lede" delay={140} style={{ marginTop: 26, maxWidth: '40ch' }}>
            Ask a frontier model who someone is and, from memory alone, it answers in
            detail — or says <span className="mono" style={{ color: 'var(--ink)' }}>“unknown.”</span>{' '}
            NameRank measures which, for {stats.entities.toLocaleString()} people and things
            across {stats.models} models. The verdict is paid to <span className="u-artifact">named, indexable
            artifacts</span> — not to <span className="u-person">credentials or titles</span>.
          </Reveal>
          <Reveal delay={220} style={{ display: 'flex', gap: 12, marginTop: 30, flexWrap: 'wrap' }}>
            <a href="#method" className="btn">How the instrument works</a>
            <a href="#findings" className="btn btn--ghost">Jump to findings</a>
          </Reveal>
        </div>

        <Reveal delay={200}>
          <div className="panel panel--pad">
            <div className="panel-head">
              <span className="tag">LIVE READOUT · one entity × {stats.models} models</span>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7, marginBottom: 20 }}>
              {hero.map((h) => (
                <button key={h.id} className={`chip ${h.id === sel.id ? 'is-on' : ''}`} onClick={() => setSel(h)}>
                  <span className="dot" style={{ background: (CAT[h.id] || 'person') === 'artifact' ? 'var(--artifact)' : 'var(--person)' }} />
                  {h.name}
                </button>
              ))}
            </div>

            <DotStrip key={sel.id} scores={sel.scores} cat={cat} size="md" />

            <div style={{ display: 'flex', alignItems: 'baseline', gap: 16, marginTop: 22, flexWrap: 'wrap' }}>
              <div className="num" style={{ fontSize: '2.6rem', lineHeight: 1, color: cat === 'artifact' ? 'var(--artifact)' : 'var(--person)' }}>{sel.nr.toFixed(2)}</div>
              <div>
                <div className="mono" style={{ fontSize: '0.82rem', color: 'var(--ink)' }}>{lit} / {sel.scores.length} models recognised</div>
                <div className="tag" style={{ fontSize: '0.62rem' }}>NAMERANK · {cat === 'artifact' ? 'ARTIFACT' : 'PERSON'} · {sel.context}</div>
              </div>
            </div>
            <p className="caption" style={{ minHeight: 42 }}>{STORY[sel.id]}</p>
          </div>
        </Reveal>
      </div>

      <div className="grid grid-4 keep2" style={{ marginTop: 'clamp(40px, 6vw, 72px)' }}>
        <Reveal delay={0}><Readout s="ENTITIES" v={stats.entities.toLocaleString()} l="people, tools, papers, events on one scale" /></Reveal>
        <Reveal delay={60}><Readout s="PANEL" v={stats.models} l="frontier models, Western & Chinese" /></Reveal>
        <Reveal delay={120}><Readout s="COHORTS" v={stats.cohorts} l="from olympiad medallists to OSS tools" /></Reveal>
        <Reveal delay={180}><Readout s="VERDICT" v="0 / 1" l="a specific, non-guessable, verified fact?" /></Reveal>
      </div>
    </header>
  )
}
