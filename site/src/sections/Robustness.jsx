import React from 'react'
import { Reveal, pct, fmt } from '../lib/ui.jsx'
import { SelfReportBars, VarianceBar, Meter } from '../components/charts.jsx'
import stats from '../data/stats.json'
import robustness from '../data/robustness.json'
import selfreport from '../data/selfreport.json'
import crosslang from '../data/crosslang.json'

const { variance, crossJudge, paraphrase, floors, confounds } = robustness

const BATTERY = [
  {
    threat: 'Score reflects the panel, not the entity',
    check: 'Variance decomposition',
    outcome: (
      <>The <b className="c-signal">entity</b> explains {variance.entity}% of the variance against just {variance.model}% for the model — which name you ask about dominates which model you ask.</>
    ),
  },
  {
    threat: 'Findings are an artifact of wording',
    check: '4-template paraphrase',
    outcome: (
      <>The probe template explains {paraphrase.templateVarPct}% of the variance; the cohort ladder is preserved at <span className="num">ρ = {paraphrase.rhoLadder}</span>.</>
    ),
  },
  {
    threat: 'Findings depend on probe language',
    check: 'Chinese re-probe · 240 entities',
    outcome: (
      <>Re-run in Chinese, no cohort mean moves by more than <span className="num">{fmt(crosslang.summary.maxAbsDelta)}</span> — the ordering is language-invariant.</>
    ),
  },
  {
    threat: 'Findings depend on the judge family',
    check: '3-family re-judge',
    outcome: (
      <>Ranking is identical across judges. GPT-5.1 is stricter overall (recognises {pct(crossJudge.gpt)} vs {pct(crossJudge.gemini)}/{pct(crossJudge.claude)}) but as a uniform offset; Gemini–Claude agree at <span className="num">κ = {crossJudge.kappaGeminiClaude}</span>.</>
    ),
  },
  {
    threat: 'Unknown names score above zero',
    check: 'Synthetic nulls',
    outcome: (
      <>Invented entities run through the whole pipeline settle at a floor of <span className="num">{fmt(floors.people, 3)}</span> for people, <span className="num">{fmt(floors.papers, 3)}</span> for papers.</>
    ),
  },
  {
    threat: 'It’s just a Wikipedia flag / web attention',
    check: 'Confound regressions',
    outcome: (
      <>A Wikipedia-presence flag explains only {pct(confounds.wikipediaR2)} of NameRank against the h-index’s {pct(confounds.hindexR2)}. Rejected.</>
    ),
  },
]

const JUDGES = [
  { k: 'gemini', label: 'Gemini', v: crossJudge.gemini, color: 'var(--signal)' },
  { k: 'claude', label: 'Claude', v: crossJudge.claude, color: 'var(--signal)' },
  { k: 'gpt', label: 'GPT-5.1', v: crossJudge.gpt, color: 'var(--artifact)' },
]

const sr = stats.selfreport
const trapMax = Math.max(...selfreport.models.map((m) => m.trapFalse))

export default function Robustness() {
  return (
    <section id="robustness" className="section">
      <div className="wrap">
        <div className="sec-head">
          <span className="sec-idx">03</span>
          <h2 className="sec-title">Does the instrument hold?</h2>
        </div>
        <Reveal className="lede sec-kicker">
          Every claim here is a <em>relative</em> gap read against the synthetic-null floor — and
          the findings survive wording, language, judge, vintage, and confound checks. Two of those
          checks earn a panel of their own.
        </Reveal>

        {/* ── validation battery ─────────────────────────────────────── */}
        <Reveal className="panel panel--pad" style={{ marginTop: 44 }}>
          <div className="panel-head">
            <span className="panel-title">The validation battery</span>
            <span className="tag">SIX THREATS · SIX CHECKS</span>
          </div>
          <div className="scroll-x">
            <table className="tbl">
              <thead>
                <tr>
                  <th style={{ width: '26%' }}>Threat to the reading</th>
                  <th style={{ width: '20%' }}>Check</th>
                  <th>Outcome</th>
                </tr>
              </thead>
              <tbody>
                {BATTERY.map((r) => (
                  <tr key={r.threat}>
                    <td style={{ color: 'var(--ink-2)' }}>{r.threat}</td>
                    <td><span className="tag" style={{ fontSize: '0.6rem', letterSpacing: '0.12em' }}>{r.check}</span></td>
                    <td style={{ color: 'var(--ink-2)' }}>{r.outcome}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Reveal>

        {/* ── two headline checks get their own panels ───────────────── */}
        <div className="grid grid-2" style={{ marginTop: 26 }}>
          <Reveal className="panel panel--pad">
            <div className="panel-head"><span className="panel-title">It measures the entity, not the panel</span></div>
            <VarianceBar variance={variance} />
            <p className="caption">
              Decomposing every verdict, the <b>entity</b> carries ~{variance.entity}% of the variance
              against {variance.model}% for the model. The name does the work, not the vendor.
            </p>
          </Reveal>

          <Reveal className="panel panel--pad" delay={80}>
            <div className="panel-head">
              <span className="panel-title">Judges disagree by an offset, not an order</span>
              <span className="tag">RE-JUDGE · 3 FAMILIES</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {JUDGES.map((j) => (
                <Meter key={j.k} value={j.v} color={j.color} label={`${j.label} · overall recognition rate`} />
              ))}
            </div>
            <p className="caption">
              GPT-5.1 recognises less across the board, but the ranking is unchanged — a level shift,
              not a reordering. Gemini and Claude agree case-by-case at <b>κ = {crossJudge.kappaGeminiClaude}</b>.
            </p>
          </Reveal>
        </div>

        {/* ── FEATURED: self-report is not measurement ───────────────── */}
        <Reveal className="panel panel--pad" style={{ marginTop: 26 }}>
          <div className="panel-head">
            <span className="panel-title">Asking a model what it knows is not measuring it</span>
            <span className="tag">SELF-REPORT PROBE</span>
          </div>
          <div className="grid grid-2" style={{ gap: 26, alignItems: 'start' }}>
            <div>
              <SelfReportBars models={selfreport.models} />
            </div>
            <div>
              <p style={{ fontSize: '0.92rem', color: 'var(--ink-2)', maxWidth: 'none' }}>
                Aggregate a model’s own self-report scale and it recovers the panel ordering at{' '}
                <span className="num c-signal">ρ ≈ {sr.rhoAggregate}</span>. But that recovery is
                <em> borrowed</em>: each model tracks how widely a name is known across the panel
                (<span className="num c-person">ρ ≈ {sr.rhoPanelFame}</span>) far better than its
                <b> own</b> behaviour on entities it demonstrably knows
                (<span className="num c-artifact">ρ ≈ 0</span>; rhoOwnKnown = {fmt(sr.rhoOwnKnown, 3)}).
                The three vendors even agree with each <b>other</b>
                (<span className="num">ρ ≈ {sr.rhoInterModel}</span>) more than any agrees with its own weights.
              </p>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 16, marginTop: 22, flexWrap: 'wrap' }}>
                <div>
                  <div className="num" style={{ fontSize: '2.2rem', color: 'var(--signal)' }}>{fmt(trapMax, 3)}</div>
                  <div className="tag" style={{ fontSize: '0.62rem' }}>TRAP · PREFERS A FICTIONAL NAME</div>
                </div>
                <p style={{ fontSize: '0.86rem', color: 'var(--ink-3)', maxWidth: 'none' }}>
                  Offered a fabricated entity, the models almost never bite — introspection is honest,
                  it just reads the shared corpus prior rather than the model’s own recall.
                </p>
              </div>
              <p className="caption">
                Usable as a <b>prior</b>, not a measurement: self-report echoes what the corpus knows,
                which is exactly what NameRank measures directly.
              </p>
            </div>
          </div>
        </Reveal>

        {/* ── closing note: relative, not absolute ───────────────────── */}
        <Reveal className="panel panel--pad" delay={60} style={{ marginTop: 26, borderLeft: '2px solid var(--signal)' }}>
          <div className="panel-head"><span className="panel-title">Read gaps, not levels</span></div>
          <p style={{ fontSize: '0.92rem', color: 'var(--ink-2)', maxWidth: 'none' }}>
            NameRank values are within-run <b>relative</b> gaps, read against the synthetic-null floor.
            Absolute recognition levels drift by roughly <span className="num">0.1–0.3 / yr</span> as
            model fleets turn over, so a re-run compares the <em>gaps between cohorts</em>, never the raw
            levels. The instrument is calibrated to the distance from the floor, not to any one vintage.
          </p>
        </Reveal>
      </div>
    </section>
  )
}
