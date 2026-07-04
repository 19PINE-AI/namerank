import React from 'react'
import ladder from '../data/ladder.json'
import inversion from '../data/inversion.json'
import country from '../data/country.json'
import crosslang from '../data/crosslang.json'
import stats from '../data/stats.json'
import models from '../data/models.json'
import { fmt, pct, Reveal } from '../lib/ui.jsx'
import { HBarChart, Dumbbell, IntervalChart, Leaderboard } from '../components/charts.jsx'

function Finding({ id, n, title, chart, note, children, wide = false }) {
  return (
    <article className={`finding ${wide ? 'finding-wide' : ''}`} id={id}>
      <Reveal className="finding-text">
        <div className="finding-n num">Finding {n}</div>
        <h3 className="finding-title">{title}</h3>
        <div className="prose">{children}</div>
      </Reveal>
      <Reveal className="finding-chart" delay={120}>
        <div className="card" style={{ padding: '22px 22px 16px' }}>
          {chart}
          {note && <div className="chart-note" style={{ marginTop: 10 }}>{note}</div>}
        </div>
      </Reveal>
    </article>
  )
}

/* ————— F1: credential treadmill ————— */

const SHORT_CREDENTIAL = {
  'International Math Olympiad gold (2005-2015)': 'Math Olympiad gold (IMO)',
  'International Olympiad in Informatics gold': 'Informatics Olympiad gold (IOI)',
  'ICPC World Finalist gold': 'ICPC World Finals gold',
  'Putnam top-25 fellow': 'Putnam top-25 fellow',
  'China Math Olympiad gold': 'China Math Olympiad gold',
  'National Olympiad in Informatics China gold': 'China Informatics Olympiad gold',
  'China Physics Olympiad first prize': 'China Physics Olympiad 1st prize',
  'Rhodes Scholarship recipient': 'Rhodes Scholar',
  'MSRA PhD Fellowship': 'MSRA PhD Fellowship',
}

function TreadmillChart() {
  const rows = ladder.rows
    .filter((r) => r.prestige !== 'ind')
    .sort((a, b) => b.mean - a.mean)
    .map((r) => ({
      label: SHORT_CREDENTIAL[r.credential] ?? r.credential,
      sub: `${r.n} medalists · ${r.years}`,
      value: r.mean,
      strong: r.mean > ladder.baselines.longTail.mean,
      tip: (
        <>
          <b>{r.credential}</b>
          <br />mean NameRank {fmt(r.mean)} · {r.n} people · cohort years {r.years}
        </>
      ),
    }))
  return (
    <HBarChart
      rows={rows}
      max={0.72}
      labelW={300}
      rowH={44}
      refLine={{ value: ladder.baselines.longTail.mean, label: `ordinary researchers ${fmt(ladder.baselines.longTail.mean)}` }}
    />
  )
}

/* ————— F3: h-index tiles ————— */

function R2Chart() {
  const rows = [
    { label: 'h-index', desc: 'how many distinct works carry your name', value: stats.cvR2H, sd: stats.cvR2HSd, color: 'var(--person)' },
    { label: 'raw citations', desc: 'how many times your work is cited in total', value: stats.cvR2Cites, sd: stats.cvR2CitesSd, color: 'var(--line-strong)' },
  ]
  return (
    <div>
      <div className="tag" style={{ marginBottom: 16 }}>
        How well each statistic predicts a researcher’s NameRank
      </div>
      {rows.map((r) => (
        <div key={r.label} style={{ marginBottom: 22 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 600 }}>{r.label}</span>
            <span className="num" style={{ fontSize: 15 }}>
              R² = {fmt(r.value, 2)} <span style={{ color: 'var(--ink-3)', fontSize: 12 }}>± {fmt(r.sd, 2)}</span>
            </span>
          </div>
          <div style={{ position: 'relative', height: 20, background: 'var(--paper-deep)', border: '1px solid var(--line)', borderRadius: 6 }}>
            <div style={{ position: 'absolute', inset: '3px auto 3px 3px', width: `${r.value * 100}%`, background: r.color, borderRadius: 4 }} />
            <div style={{
              position: 'absolute', top: 2, bottom: 2, left: `${(r.value - r.sd) * 100}%`,
              width: `${2 * r.sd * 100}%`, border: '1px solid var(--ink-2)', borderRadius: 3, opacity: 0.5,
            }} />
          </div>
          <div style={{ fontSize: 13.5, color: 'var(--ink-3)', marginTop: 5 }}>{r.desc}</div>
        </div>
      ))}
      <div className="chart-note">
        Repeated 10-fold cross-validation on {'≈'}1,500 researchers with public bibliometrics.
        Once h-index is known, adding citation counts improves the prediction by nothing.
      </div>
    </div>
  )
}

/* ————— F4: gradient extras ————— */

function GradientExtras() {
  return (
    <div className="gradient-tiles">
      <div className="g-tile">
        <div className="tag">Same job, different campus</div>
        <div className="g-pair num">
          <span><b>{fmt(stats.stanford.mean, 2)}</b> Stanford</span>
          <span className="g-vs">vs</span>
          <span><b>{fmt(stats.tsinghua.mean, 2)}</b> Tsinghua</span>
        </div>
        <div className="g-note">
          mean NameRank of CS faculty (n={stats.stanford.n} / n={stats.tsinghua.n}) — roughly 2× —
          driven by how much English-language text mentions each community
        </div>
      </div>
      <div className="g-tile">
        <div className="tag">Asking in Chinese doesn’t close the gap</div>
        <div className="g-pair num">
          <span><b>{fmt(crosslang.enMean, 2)}</b> English probes</span>
          <span className="g-vs">vs</span>
          <span><b>{fmt(crosslang.zhMean, 2)}</b> Chinese probes</span>
        </div>
        <div className="g-note">
          {crosslang.n} entities re-probed in Chinese: {pct(crosslang.fracZhLower)} score{' '}
          <i>lower</i> — recognition lives in the training corpus, not the prompt language
        </div>
      </div>
    </div>
  )
}

/* ————— section ————— */

export default function Findings() {
  return (
    <section className="section" id="findings">
      <div className="wrap">
        <Reveal>
          <div className="section-kicker">
            <span className="rule" />
            <span className="tag">Section 02 · Results</span>
          </div>
          <h2 className="section-title">Four things the machines told us about reputation</h2>
          <p className="section-lede">
            Every chart below is computed from the study’s real records. Hover any mark for the
            underlying numbers — then dig into individual answers in the <a href="#explorer">explorer</a>.
          </p>
        </Reveal>

        <div className="findings-list">
          <Finding
            n="1" id="f-treadmill"
            title="The credential treadmill: gold medals don’t make the models remember you"
            chart={<TreadmillChart />}
            note={<>Mean NameRank per credential cohort. Dashed line: long-tail working researchers
              from OpenAlex ({ladder.baselines.longTail.n} people) — no medals, just published work.</>}
          >
            <p>
              Take the most selective credentials on earth — International Math Olympiad gold, Rhodes
              Scholarships, elite PhD fellowships — and ask the models about the winners a decade
              later. <b>Seven of nine credential cohorts score at or below ordinary working
              researchers</b> who simply kept publishing under their own name.
            </p>
            <p>
              The credential opens doors for humans, but it doesn’t propagate a <i>name</i> into
              training corpora. Named, findable output does. The two exceptions — ICPC and Putnam —
              are the two whose winner lists live on heavily-crawled English websites.
            </p>
          </Finding>

          <Finding
            n="2" id="f-inversion"
            title="The tool becomes more famous than its maker"
            wide
            chart={
              <>
                <div style={{ display: 'flex', gap: 18, marginBottom: 6, flexWrap: 'wrap' }}>
                  <span className="score-pill"><span className="swatch" style={{ background: 'var(--person)' }} /> the person</span>
                  <span className="score-pill"><span className="swatch" style={{ background: 'var(--artifact)' }} /> their creation</span>
                </div>
                <Dumbbell pairs={inversion} />
              </>
            }
            note={<>All 11 verified creator–creation pairs, sorted by gap. Hover a pair for the
              attribution flow. The three bottom pairs are the exceptions: leaders who were famous
              before their organizations existed.</>}
          >
            <p>
              We measured 11 pairs of <span className="chip-person">creator</span> and{' '}
              <span className="chip-artifact">creation</span> independently. In <b>8 of 11 pairs the
              creation out-ranks its creator</b> — for independent builders of a single tool, the
              inversion is universal in our data.
            </p>
            <p>
              The mechanism is a one-way street in how the internet writes: documentation, tutorials
              and README files repeat the <i>tool’s</i> name thousands of times and the author’s
              once. Ask about Jiayi Weng and a quarter of answers mention his library Tianshou; ask
              about Tianshou and <b>not one model in 37</b> names him back.
            </p>
            <p style={{ fontSize: 15.5 }}>
              A controlled follow-up backs this up: silently adding the artifact’s name to the
              question lifts scores by +{fmt(stats.contextLiftMean, 3)} on average — and by{' '}
              +{fmt(stats.contextLiftJiayi, 2)} for Jiayi Weng himself.
            </p>
          </Finding>

          <Finding
            n="3" id="f-hindex"
            title="It’s not how much you’re cited — it’s how many things carry your name"
            chart={<R2Chart />}
          >
            <p>
              Bibliometrics do predict recognition — but the <i>right</i> statistic is the h-index,
              a count of how many distinct works a researcher is known for. Total citations, the
              number careers are judged by, adds <b>no extra signal at all</b>.
            </p>
            <p>
              That’s exactly what you’d expect if models learn names by <b>repeated exposure across
              different documents</b>: one blockbuster paper cited 10,000 times prints your name in
              one place; ten solid papers print it in ten.
            </p>
          </Finding>

          <Finding
            n="4" id="f-gradient"
            title="Recognition follows the English-language corpus — a geography of being known"
            wide
            chart={
              <>
                <IntervalChart rows={country} />
                <GradientExtras />
              </>
            }
            note={<>Mean NameRank of CS faculty by country of affiliation, with 95% confidence
              intervals. Solid dots: n ≥ 10 (firm). Hollow dots: small samples, suggestive only.</>}
          >
            <p>
              Hold the job constant — CS faculty, similar seniority — and vary the place. A clear
              gradient appears: <b>working where the English-language internet writes a lot gets you
              remembered; working elsewhere gets you silence.</b>
            </p>
            <p>
              Crucially, when models don’t know a name they overwhelmingly say “unknown” rather than
              fabricate — the metric fails <i>silent</i>, not misleading. And asking in Chinese
              doesn’t rescue Chinese-affiliated researchers: what matters is the training corpus,
              not the conversation language.
            </p>
          </Finding>
        </div>

        <Reveal>
          <div className="panel-block card" id="panel">
            <div style={{ padding: '26px 26px 8px' }}>
              <div className="tag" style={{ marginBottom: 8 }}>The instrument itself</div>
              <h3 style={{ fontSize: 24, marginBottom: 8 }}>All 37 models, side by side</h3>
              <p className="prose" style={{ fontSize: 16 }}>
                Bigger, newer models know more names — but every model, even the best, has a
                threshold below which the world goes quiet. The right panel shows each model’s
                honesty about that threshold.
              </p>
            </div>
            <div style={{ padding: '10px 26px 24px' }}>
              <Leaderboard models={models} />
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
