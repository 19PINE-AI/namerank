import React, { useState } from 'react'
import heroEntities from '../data/hero_entities.json'
import stats from '../data/stats.json'
import models from '../data/models.json'
import { fmt, Reveal } from '../lib/ui.jsx'
import { DotStrip } from '../components/charts.jsx'

const STORIES = {
  sam_altman: 'Everyone knows the famous CEO — yet even here, graded answer by answer, the panel averages 0.61, not 1.0. Recognition is a spectrum, and full marks are rare.',
  andrej_karpathy: 'A famous AI educator: almost every model knows him. But ask about his little side project nanoGPT and something odd happens — the tool scores higher than he does.',
  tianshou: 'An open-source software library. No face, no biography — and it out-ranks the engineer who built it. That inversion is one of the paper’s main findings.',
  jiayi_weng: 'He built Tianshou and works at OpenAI. A third of the panel draws a blank; GPT‑5.4 answers with a single word: “unknown”.',
  bojie_li: 'The author of this very paper. NameRank 0.09 — the models barely know he exists. Measuring that gap honestly is what the project is about.',
  imo_dongyi_wei: 'A gold medalist at the world’s hardest high-school math competition. The medal alone doesn’t make the models remember the name — his later math papers do.',
}

const MODEL_IDS = models.map((m) => m.id)

export default function Hero() {
  const [pick, setPick] = useState(heroEntities[0].id)
  const ent = heroEntities.find((e) => e.id === pick)
  const answered = ent.scores.filter((s) => s != null && s >= 0.08).length
  return (
    <header className="section hero">
      <div className="wrap">
        <Reveal>
          <div className="section-kicker">
            <span className="rule" />
            <span className="tag">A field guide to machine memory · 2026</span>
          </div>
          <h1 className="hero-title">
            When someone asks an AI <em>who you are</em> — what does it say?
          </h1>
        </Reveal>
        <Reveal delay={120}>
          <p className="section-lede" style={{ marginTop: 22 }}>
            Chat assistants are becoming the first place people hear about a researcher, a founder,
            or a tool. <b>NameRank</b> measures what the machines actually remember: we asked{' '}
            <b>{stats.models} frontier AI models</b> one simple question about{' '}
            <b>{stats.entities.toLocaleString()} names</b>, graded all{' '}
            <b>{stats.records.toLocaleString()} answers</b> against the facts, and mapped who — and
            what — the models really know.
          </p>
        </Reveal>

        <Reveal delay={240}>
          <div className="card hero-demo">
            <div className="tag" style={{ marginBottom: 14 }}>
              Try it — one name, the whole {stats.models}-model panel
            </div>
            <div className="hero-chips">
              {heroEntities.map((e) => (
                <button key={e.id} className={`btn ${pick === e.id ? 'on' : ''}`} onClick={() => setPick(e.id)}>
                  {e.name}
                </button>
              ))}
            </div>
            <div className="hero-strip" key={ent.id}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: 8 }}>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 600 }}>
                  {ent.name}
                  <span style={{ color: 'var(--ink-3)', fontWeight: 400, fontSize: 16 }}> — {ent.context}</span>
                </div>
                <div className="tag"><b>{answered}</b> of {stats.models} models earn any credit</div>
              </div>
              <DotStrip scores={ent.scores} models={MODEL_IDS} height={78} />
              <p className="hero-story">{STORIES[ent.id]}</p>
            </div>
          </div>
        </Reveal>

        <Reveal delay={340}>
          <div className="hero-stats">
            {[
              [stats.entities.toLocaleString(), 'names probed, from Sam Altman to long-tail researchers'],
              [stats.models, 'frontier models, asked from memory — no web search'],
              [stats.cohorts, 'cohorts: faculty, olympiad medalists, tools, startups…'],
              [stats.records.toLocaleString(), 'answers graded by an independent AI judge'],
            ].map(([n, label]) => (
              <div key={label} className="hero-stat">
                <div className="hero-stat-n num">{n}</div>
                <div className="hero-stat-l">{label}</div>
              </div>
            ))}
          </div>
        </Reveal>
      </div>
    </header>
  )
}
