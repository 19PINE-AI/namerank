import React, { useMemo, useState } from 'react'
import { useWidth, useTip, useDark, recogColor, pct, fmt, signed, modelLabel } from '../lib/ui.jsx'

/* shared helpers ----------------------------------------------------------- */
const AX_TICKS = [0, 0.2, 0.4, 0.6, 0.8, 1]
function XAxis({ x0, x1, y, sx }) {
  return (
    <g>
      <line className="axis-line" x1={x0} x2={x1} y1={y} y2={y} />
      {AX_TICKS.map((t) => (
        <g key={t}>
          <line className="grid-line" x1={sx(t)} x2={sx(t)} y1={y} y2={y - 4} />
          <text className="tick-txt" x={sx(t)} y={y + 14} textAnchor="middle">{t.toFixed(1)}</text>
        </g>
      ))}
    </g>
  )
}
const catFill = (cat) => (cat === 'artifact' ? 'var(--artifact)' : 'var(--person)')

/* ═══════════════ DotStrip — one entity, 36-channel recognition readout ═══ */
export function DotStrip({ scores, models, cat = 'person', size = 'md', animate = true }) {
  const tip = useTip()
  const n = scores.length
  const cols = size === 'sm' ? 18 : n
  const gap = size === 'sm' ? 5 : 6
  const r = size === 'sm' ? 4 : 5
  const rows = Math.ceil(n / cols)
  const w = cols * (r * 2 + gap)
  const h = rows * (r * 2 + gap)
  const fill = catFill(cat)
  return (
    <div className="dotstrip">
      <svg viewBox={`0 0 ${w} ${h}`} style={{ width: '100%', maxWidth: cols * (r * 2 + gap) }} role="img" aria-label={`${scores.filter(Boolean).length} of ${n} models recognized`}>
        {scores.map((s, i) => {
          const cx = (i % cols) * (r * 2 + gap) + r + gap / 2
          const cy = Math.floor(i / cols) * (r * 2 + gap) + r + gap / 2
          const lit = s >= 0.5
          const m = models?.[i]
          return (
            <circle key={i} className="ch" cx={cx} cy={cy} r={r}
              fill={lit ? fill : 'transparent'} stroke={lit ? fill : 'var(--silent)'} strokeWidth={lit ? 0 : 1.4}
              style={animate ? { transitionDelay: `${i * 12}ms` } : undefined}
              onMouseMove={m ? (e) => tip.show(e, <><div className="tt">{modelLabel(m)}</div><div className="tv">{lit ? 'recognized' : 'no recognition'}</div></>) : undefined}
              onMouseLeave={m ? tip.hide : undefined} />
          )
        })}
      </svg>
    </div>
  )
}

/* ═══════════════ CohortAxis — every cohort on one recognition scale ═══════ */
export function CohortAxis({ cohorts, floor = 0.02, highlight = [] }) {
  const [ref, W] = useWidth()
  const tip = useTip()
  const rows = cohorts
  const padL = Math.min(190, W * 0.34), padR = 20, padT = 30, rowH = 15
  const H = rows.length * rowH + padT + 34
  const x0 = padL, x1 = W - padR
  const sx = (v) => x0 + v * (x1 - x0)
  const zones = [
    { a: 0, b: 0.22, label: 'silent' },
    { a: 0.22, b: 0.85, label: 'discriminative' },
    { a: 0.85, b: 1, label: 'universal' },
  ]
  return (
    <div className="chart" ref={ref}>
      {W > 0 && (
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Recognition by cohort">
          {zones.map((z, i) => (
            <g key={z.label}>
              {i > 0 && <line className="grid-line" x1={sx(z.a)} x2={sx(z.a)} y1={padT} y2={H - 22} />}
              <text className="tag" style={{ fontSize: 9 }} x={sx((z.a + z.b) / 2)} y={padT - 12} textAnchor="middle" fill="var(--ink-3)">{z.label}</text>
            </g>
          ))}
          <rect x={x0} y={padT} width={sx(floor) - x0} height={H - padT - 22} fill="var(--bad)" opacity="0.06" />
          <line x1={sx(floor)} x2={sx(floor)} y1={padT} y2={H - 22} stroke="var(--bad)" strokeWidth="1" strokeDasharray="2 3" opacity="0.5" />
          {rows.map((c, i) => {
            const y = padT + i * rowH + rowH / 2
            const hot = highlight.includes(c.slug)
            const col = catFill(c.category)
            return (
              <g key={c.slug} onMouseMove={(e) => tip.show(e, <><div className="tt">{c.name} · n={c.n}</div><div className="tv">{pct(c.mean, 0)} recognized</div></>)} onMouseLeave={tip.hide} style={{ cursor: 'default' }}>
                <rect x={0} y={y - rowH / 2} width={W} height={rowH} fill={hot ? 'var(--surface-2)' : 'transparent'} />
                <text className="mark-lbl" x={x0 - 10} y={y + 3.5} textAnchor="end" style={{ fontSize: 10.5, fontWeight: hot ? 700 : 400, fill: hot ? 'var(--ink)' : 'var(--ink-2)' }}>{c.name}</text>
                {c.ci95 ? <line x1={sx(Math.max(0, c.mean - c.ci95))} x2={sx(Math.min(1, c.mean + c.ci95))} y1={y} y2={y} stroke={col} strokeWidth="1" opacity="0.4" /> : null}
                <line x1={x0} x2={sx(c.mean)} y1={y} y2={y} stroke={col} strokeWidth="1" opacity="0.18" />
                <circle cx={sx(c.mean)} cy={y} r={hot ? 4.5 : 3.4} fill={col} />
              </g>
            )
          })}
          <XAxis x0={x0} x1={x1} y={H - 20} sx={sx} />
        </svg>
      )}
    </div>
  )
}

/* ═══════════════ LadderBars — credentials vs baseline ═══════════════════ */
export function LadderBars({ rows, baseline, floor, valueKey = 'mean', labelKey = 'credential' }) {
  const [ref, W] = useWidth()
  const tip = useTip()
  const data = [...rows].sort((a, b) => a[valueKey] - b[valueKey])
  const padL = Math.min(210, W * 0.4), padR = 46, padT = 26
  const rowH = 34, H = data.length * rowH + padT + 30
  const x0 = padL, x1 = W - padR
  const sx = (v) => x0 + v * (x1 - x0)
  return (
    <div className="chart" ref={ref}>
      {W > 0 && (
        <svg viewBox={`0 0 ${W} ${H}`} role="img">
          {baseline != null && (
            <g>
              <line x1={sx(baseline)} x2={sx(baseline)} y1={padT - 8} y2={H - 24} className="ref-line" />
              <text className="tag" x={sx(baseline)} y={padT - 12} textAnchor="middle" style={{ fontSize: 9 }} fill="var(--ink-2)">baseline {baseline.toFixed(2)}</text>
            </g>
          )}
          {floor != null && <rect x={x0} y={padT - 6} width={sx(floor) - x0} height={H - padT - 18} fill="var(--bad)" opacity="0.06" />}
          {data.map((d, i) => {
            const y = padT + i * rowH + rowH / 2
            const below = baseline != null && d[valueKey] < baseline
            return (
              <g key={d[labelKey] + i} onMouseMove={(e) => tip.show(e, <><div className="tt">{d[labelKey]}{d.n ? ` · n=${d.n}` : ''}</div><div className="tv">{pct(d[valueKey], 0)}</div></>)} onMouseLeave={tip.hide}>
                <text className="mark-lbl" x={x0 - 12} y={y + 4} textAnchor="end" style={{ fontSize: 12 }}>{d[labelKey]}</text>
                <rect x={x0} y={y - 5} width={Math.max(2, sx(d[valueKey]) - x0)} height={10} rx={2} fill="var(--person)" opacity={below ? 0.62 : 1} />
                <text className="mark-val" x={sx(d[valueKey]) + 8} y={y + 4} style={{ fontSize: 11 }}>{d[valueKey].toFixed(2)}</text>
              </g>
            )
          })}
          <XAxis x0={x0} x1={x1} y={H - 20} sx={sx} />
        </svg>
      )}
    </div>
  )
}

/* ═══════════════ CareerArc — awards grouped ladder ══════════════════════ */
const GROUP_LABEL = { early: 'Olympiad / early credential', llm: 'Named papers & methods', mid: 'Mid-career honor', marquee: 'Marquee prize' }
export function CareerArc({ entries, baseline, floor }) {
  const [ref, W] = useWidth()
  const tip = useTip()
  const order = ['early', 'llm', 'mid', 'marquee']
  const data = [...entries].sort((a, b) => a.mean - b.mean)
  const padL = Math.min(190, W * 0.36), padR = 46, padT = 26, rowH = 30
  const H = data.length * rowH + padT + 30
  const x0 = padL, x1 = W - padR
  const sx = (v) => x0 + v * (x1 - x0)
  const gcol = { early: 'var(--person)', llm: 'var(--signal)', mid: 'var(--artifact)', marquee: 'var(--artifact)' }
  return (
    <div className="chart" ref={ref}>
      {W > 0 && (
        <svg viewBox={`0 0 ${W} ${H}`} role="img">
          <line x1={sx(baseline)} x2={sx(baseline)} y1={padT - 8} y2={H - 24} className="ref-line" />
          <text className="tag" x={sx(baseline)} y={padT - 12} textAnchor="middle" style={{ fontSize: 9 }} fill="var(--ink-2)">working researcher {baseline.toFixed(2)}</text>
          {floor != null && <rect x={x0} y={padT - 6} width={sx(floor) - x0} height={H - padT - 18} fill="var(--bad)" opacity="0.06" />}
          {data.map((d, i) => {
            const y = padT + i * rowH + rowH / 2
            return (
              <g key={d.key} onMouseMove={(e) => tip.show(e, <><div className="tt">{d.label} · {GROUP_LABEL[d.group]}</div><div className="tv">{pct(d.mean, 0)} · {signed(d.vsBaseline)} vs base</div></>)} onMouseLeave={tip.hide}>
                <text className="mark-lbl" x={x0 - 12} y={y + 4} textAnchor="end" style={{ fontSize: 11.5 }}>{d.label}</text>
                <rect x={x0} y={y - 4.5} width={Math.max(2, sx(d.mean) - x0)} height={9} rx={2} fill={gcol[d.group]} />
                <text className="mark-val" x={sx(d.mean) + 8} y={y + 4} style={{ fontSize: 11 }}>{d.mean.toFixed(2)}</text>
              </g>
            )
          })}
          <XAxis x0={x0} x1={x1} y={H - 20} sx={sx} />
        </svg>
      )}
      <div className="legend" style={{ marginTop: 14 }}>
        {order.map((g) => <span key={g} className="dot-key"><i style={{ background: gcol[g] }} />{GROUP_LABEL[g]}</span>)}
      </div>
    </div>
  )
}

/* ═══════════════ Dumbbell — artifact vs creator inversion ═══════════════ */
export function Dumbbell({ pairs }) {
  const [ref, W] = useWidth()
  const tip = useTip()
  const data = [...pairs].sort((a, b) => b.delta - a.delta)
  const padL = Math.min(150, W * 0.28), padR = 130, padT = 20, rowH = 34
  const H = data.length * rowH + padT + 30
  const x0 = padL, x1 = W - padR
  const sx = (v) => x0 + v * (x1 - x0)
  return (
    <div className="chart" ref={ref}>
      {W > 0 && (
        <svg viewBox={`0 0 ${W} ${H}`} role="img">
          {data.map((d, i) => {
            const y = padT + i * rowH + rowH / 2
            const invert = d.nrArtifact >= d.nrCreator
            return (
              <g key={d.creator} onMouseMove={(e) => tip.show(e, <><div className="tt">{d.creator} → {d.artifact}</div><div className="tv">creator {d.nrCreator.toFixed(2)} · artifact {d.nrArtifact.toFixed(2)} · Δ{signed(d.delta)}</div></>)} onMouseLeave={tip.hide}>
                <text className="mark-lbl" x={x0 - 12} y={y + 4} textAnchor="end" style={{ fontSize: 11.5 }}>{d.creator}</text>
                <line x1={sx(Math.min(d.nrCreator, d.nrArtifact))} x2={sx(Math.max(d.nrCreator, d.nrArtifact))} y1={y} y2={y} stroke="var(--line-strong)" strokeWidth="1.5" />
                <circle cx={sx(d.nrCreator)} cy={y} r={5} fill="var(--person)" stroke="var(--surface)" strokeWidth="1.5" />
                <circle cx={sx(d.nrArtifact)} cy={y} r={5} fill="var(--artifact)" stroke="var(--surface)" strokeWidth="1.5" />
                <text className="mark-val" x={x1 + 10} y={y + 4} style={{ fontSize: 11, fill: invert ? 'var(--artifact)' : 'var(--ink-3)' }}>{d.artifact}</text>
              </g>
            )
          })}
          <XAxis x0={x0} x1={x1} y={H - 20} sx={sx} />
        </svg>
      )}
      <div className="legend" style={{ marginTop: 12 }}>
        <span className="dot-key"><i style={{ background: 'var(--person)' }} />creator (person)</span>
        <span className="dot-key"><i style={{ background: 'var(--artifact)' }} />artifact / tool</span>
      </div>
    </div>
  )
}

/* ═══════════════ MedalTiers — NOI gold/silver/bronze ════════════════════ */
export function MedalTiers({ tiers, scatter, floor }) {
  const [ref, W] = useWidth()
  const tip = useTip()
  const order = ['gold', 'silver', 'bronze']
  const tcol = { gold: '#d9a520', silver: '#9aa7b4', bronze: '#b5764a' }
  const padL = 70, padR = 20, padT = 20, padB = 34
  const bandH = 84, H = order.length * bandH + padT + padB
  const x0 = padL, x1 = W - padR
  const maxX = 0.42
  const sx = (v) => x0 + Math.min(v, maxX) / maxX * (x1 - x0)
  return (
    <div className="chart" ref={ref}>
      {W > 0 && (
        <svg viewBox={`0 0 ${W} ${H}`} role="img">
          <rect x={x0} y={padT} width={sx(floor) - x0} height={order.length * bandH} fill="var(--bad)" opacity="0.06" />
          {order.map((t, i) => {
            const yc = padT + i * bandH + bandH / 2
            const tt = tiers[t]
            const pts = (scatter || []).filter((s) => s.tier === t)
            return (
              <g key={t}>
                <text className="tag" x={x0 - 12} y={yc - 6} textAnchor="end" style={{ fontSize: 11, letterSpacing: '0.1em', fill: tcol[t] }}>{t}</text>
                <text className="tick-txt" x={x0 - 12} y={yc + 9} textAnchor="end">n={tt.n}</text>
                <line x1={x0} x2={x1} y1={yc + bandH / 2 - 1} y2={yc + bandH / 2 - 1} className="grid-line" />
                {pts.map((s, k) => {
                  const jitter = ((k * 37) % 40 - 20)
                  return <circle key={k} cx={sx(s.nr)} cy={yc + jitter * 0.7} r={3} fill={tcol[t]} opacity="0.5"
                    onMouseMove={(e) => tip.show(e, <><div className="tt">{s.name}</div><div className="tv">{pct(s.nr, 0)} recognized</div></>)} onMouseLeave={tip.hide} />
                })}
                <line x1={sx(tt.mean)} x2={sx(tt.mean)} y1={yc - bandH / 2 + 8} y2={yc + bandH / 2 - 4} stroke={tcol[t]} strokeWidth="2" />
                <text className="mark-val" x={sx(tt.mean)} y={yc - bandH / 2 + 2} textAnchor="middle" style={{ fontSize: 11 }}>mean {tt.mean.toFixed(3)}</text>
              </g>
            )
          })}
          <XAxis x0={x0} x1={x1} y={H - 18} sx={(v) => sx(v)} />
        </svg>
      )}
    </div>
  )
}

/* ═══════════════ DecileLadder — dose–response (events, h-index) ═════════ */
export function DecileLadder({ rows, xKey = 'decile', yKey = 'meanNr', xLabel = 'decile', accent = 'var(--signal)', fmtX }) {
  const [ref, W] = useWidth()
  const tip = useTip()
  const padL = 42, padR = 16, padT = 18, padB = 40
  const H = 300
  const x0 = padL, x1 = W - padR, y0 = H - padB, y1 = padT
  const bw = (x1 - x0) / rows.length
  const sy = (v) => y0 - v * (y0 - y1)
  return (
    <div className="chart" ref={ref}>
      {W > 0 && (
        <svg viewBox={`0 0 ${W} ${H}`} role="img">
          {[0, 0.25, 0.5, 0.75, 1].map((t) => (
            <g key={t}><line className="grid-line" x1={x0} x2={x1} y1={sy(t)} y2={sy(t)} /><text className="tick-txt" x={x0 - 6} y={sy(t) + 3} textAnchor="end">{t.toFixed(1)}</text></g>
          ))}
          {rows.map((d, i) => {
            const cx = x0 + i * bw + bw / 2
            const v = d[yKey]
            return (
              <g key={i} onMouseMove={(e) => tip.show(e, <><div className="tt">{xLabel} {d[xKey]}{d.n ? ` · n=${d.n}` : ''}{fmtX ? ` · ${fmtX(d)}` : ''}</div><div className="tv">{pct(v, 0)} recognized</div></>)} onMouseLeave={tip.hide}>
                <rect x={cx - bw * 0.32} y={sy(v)} width={bw * 0.64} height={y0 - sy(v)} rx={2} fill={accent} opacity="0.85" />
                <text className="tick-txt" x={cx} y={y0 + 14} textAnchor="middle">{d[xKey]}</text>
              </g>
            )
          })}
          <line className="axis-line" x1={x0} x2={x1} y1={y0} y2={y0} />
          <text className="tag" x={(x0 + x1) / 2} y={H - 6} textAnchor="middle" style={{ fontSize: 9 }}>{xLabel} →</text>
        </svg>
      )}
    </div>
  )
}

/* ═══════════════ TwoBar — peak vs duration standardized coefficients ════ */
export function TwoBar({ items, max, unit = '' }) {
  const [ref, W] = useWidth()
  const padL = 120, padR = 60, padT = 12
  const rowH = 46, H = items.length * rowH + padT + 10
  const x0 = padL, x1 = W - padR
  const m = max || Math.max(...items.map((d) => d.value)) * 1.15
  const sx = (v) => x0 + (v / m) * (x1 - x0)
  return (
    <div className="chart" ref={ref}>
      {W > 0 && (
        <svg viewBox={`0 0 ${W} ${H}`} role="img">
          {items.map((d, i) => {
            const y = padT + i * rowH + rowH / 2
            return (
              <g key={d.label}>
                <text className="mark-lbl" x={x0 - 12} y={y + 4} textAnchor="end" style={{ fontSize: 12.5 }}>{d.label}</text>
                <rect x={x0} y={y - 8} width={Math.max(2, sx(d.value) - x0)} height={16} rx={2} fill={d.color || 'var(--signal)'} />
                <text className="mark-val" x={sx(d.value) + 8} y={y + 4}>{signed(d.value, 3)}{unit}</text>
              </g>
            )
          })}
        </svg>
      )}
    </div>
  )
}

/* ═══════════════ IntervalDots — institution / country with CI ═══════════ */
export function IntervalDots({ rows, valueKey = 'mean', labelKey = 'country', baseline }) {
  const [ref, W] = useWidth()
  const tip = useTip()
  const data = [...rows].sort((a, b) => b[valueKey] - a[valueKey])
  const padL = Math.min(150, W * 0.3), padR = 40, padT = 18, rowH = 30
  const H = data.length * rowH + padT + 28
  const x0 = padL, x1 = W - padR
  const sx = (v) => x0 + v * (x1 - x0)
  return (
    <div className="chart" ref={ref}>
      {W > 0 && (
        <svg viewBox={`0 0 ${W} ${H}`} role="img">
          {baseline != null && <line x1={sx(baseline)} x2={sx(baseline)} y1={padT - 6} y2={H - 22} className="ref-line" />}
          {data.map((d, i) => {
            const y = padT + i * rowH + rowH / 2
            const faded = d.firm === false || (d.n != null && d.n < 8)
            return (
              <g key={d[labelKey]} opacity={faded ? 0.5 : 1} onMouseMove={(e) => tip.show(e, <><div className="tt">{d[labelKey]}{d.n != null ? ` · n=${d.n}` : ''}</div><div className="tv">{pct(d[valueKey], 0)}</div></>)} onMouseLeave={tip.hide}>
                <text className="mark-lbl" x={x0 - 12} y={y + 4} textAnchor="end" style={{ fontSize: 12 }}>{d[labelKey]}</text>
                {d.lo != null && d.hi != null && <line x1={sx(d.lo)} x2={sx(d.hi)} y1={y} y2={y} stroke="var(--person)" strokeWidth="1.5" opacity="0.4" />}
                <circle cx={sx(d[valueKey])} cy={y} r={5} fill="var(--person)" />
                <text className="mark-val" x={sx(d[valueKey]) + 9} y={y + 4} style={{ fontSize: 11 }}>{d[valueKey].toFixed(2)}</text>
              </g>
            )
          })}
          <XAxis x0={x0} x1={x1} y={H - 18} sx={sx} />
        </svg>
      )}
    </div>
  )
}

/* ═══════════════ SelfReportBars — per model, fame vs own knowledge ══════ */
export function SelfReportBars({ models }) {
  const [ref, W] = useWidth()
  const tip = useTip()
  const padL = 130, padR = 20, padT = 30, groupH = 66
  const H = models.length * groupH + padT + 10
  const x0 = padL, x1 = W - padR
  const sx = (v) => x0 + v * (x1 - x0)
  return (
    <div className="chart" ref={ref}>
      {W > 0 && (
        <svg viewBox={`0 0 ${W} ${H}`} role="img">
          {AX_TICKS.map((t) => <line key={t} className="grid-line" x1={sx(t)} x2={sx(t)} y1={padT} y2={H - 8} />)}
          {models.map((m, i) => {
            const y = padT + i * groupH + 14
            const own = Math.max(0, m.rhoOwnKnown)
            return (
              <g key={m.model}>
                <text className="mark-lbl" x={x0 - 12} y={y + 8} textAnchor="end" style={{ fontSize: 11.5 }}>{modelLabel(m.model)}</text>
                <g onMouseMove={(e) => tip.show(e, <><div className="tt">{modelLabel(m.model)} · tracks shared fame</div><div className="tv">ρ = {m.rhoPanel.toFixed(2)}</div></>)} onMouseLeave={tip.hide}>
                  <rect x={x0} y={y - 2} width={Math.max(1, sx(m.rhoPanel) - x0)} height={11} rx={2} fill="var(--person)" />
                  <text className="mark-val" x={sx(m.rhoPanel) + 7} y={y + 8} style={{ fontSize: 10 }}>{m.rhoPanel.toFixed(2)}</text>
                </g>
                <g onMouseMove={(e) => tip.show(e, <><div className="tt">{modelLabel(m.model)} · tracks own behaviour (known)</div><div className="tv">ρ = {m.rhoOwnKnown.toFixed(2)}</div></>)} onMouseLeave={tip.hide}>
                  <rect x={x0} y={y + 14} width={Math.max(1, sx(own) - x0)} height={11} rx={2} fill="var(--artifact)" opacity="0.9" />
                  <text className="mark-val" x={sx(own) + 7} y={y + 24} style={{ fontSize: 10 }}>{m.rhoOwnKnown.toFixed(2)}</text>
                </g>
              </g>
            )
          })}
          <XAxis x0={x0} x1={x1} y={H - 4} sx={sx} />
        </svg>
      )}
      <div className="legend" style={{ marginTop: 12 }}>
        <span className="dot-key"><i style={{ background: 'var(--person)' }} />tracks shared fame across the panel</span>
        <span className="dot-key"><i style={{ background: 'var(--artifact)' }} />tracks its own knowledge (≈ 0)</span>
      </div>
    </div>
  )
}

/* ═══════════════ VarianceBar — 100% stacked ═════════════════════════════ */
export function VarianceBar({ variance }) {
  const parts = [
    { k: 'entity', label: 'Entity', color: 'var(--signal)' },
    { k: 'cohort', label: 'Cohort', color: 'var(--person)' },
    { k: 'model', label: 'Model', color: 'var(--artifact)' },
  ]
  const total = parts.reduce((s, p) => s + variance[p.k], 0)
  return (
    <div>
      <div style={{ display: 'flex', height: 30, borderRadius: 3, overflow: 'hidden', gap: 2 }}>
        {parts.map((p) => <div key={p.k} style={{ width: `${(variance[p.k] / total) * 100}%`, background: p.color }} title={`${p.label} ${variance[p.k]}%`} />)}
      </div>
      <div className="legend" style={{ marginTop: 12 }}>
        {parts.map((p) => <span key={p.k} className="dot-key"><i style={{ background: p.color }} />{p.label} <b className="num" style={{ color: 'var(--ink)', marginLeft: 4 }}>{variance[p.k]}%</b></span>)}
      </div>
    </div>
  )
}

/* ═══════════════ Leaderboard — 36-model recognition mean ════════════════ */
export function Leaderboard({ models }) {
  const [ref, W] = useWidth()
  const tip = useTip()
  const data = [...models].sort((a, b) => b.mean - a.mean)
  const padL = 150, padR = 44, padT = 8, rowH = 20
  const H = data.length * rowH + padT + 24
  const x0 = padL, x1 = W - padR
  const sx = (v) => x0 + v * (x1 - x0)
  return (
    <div className="chart" ref={ref}>
      {W > 0 && (
        <svg viewBox={`0 0 ${W} ${H}`} role="img">
          {AX_TICKS.map((t) => <line key={t} className="grid-line" x1={sx(t)} x2={sx(t)} y1={padT} y2={H - 20} />)}
          {data.map((m, i) => {
            const y = padT + i * rowH + rowH / 2
            return (
              <g key={m.id} onMouseMove={(e) => tip.show(e, <><div className="tt">{modelLabel(m.id)} · {m.lab}</div><div className="tv">{pct(m.mean, 0)} recognized · {pct(m.refusal, 0)} refusal</div></>)} onMouseLeave={tip.hide}>
                <text className="mark-lbl" x={x0 - 10} y={y + 3.5} textAnchor="end" style={{ fontSize: 10.5 }}>{modelLabel(m.id)}</text>
                <rect x={x0} y={y - 5} width={Math.max(1, sx(m.mean) - x0)} height={10} rx={2} fill="var(--person)" />
                <text className="mark-val" x={sx(m.mean) + 7} y={y + 3.5} style={{ fontSize: 10 }}>{m.mean.toFixed(2)}</text>
              </g>
            )
          })}
          <XAxis x0={x0} x1={x1} y={H - 16} sx={sx} />
        </svg>
      )}
    </div>
  )
}

/* ═══════════════ Heatmap — cohort × model recognition ═══════════════════ */
export function Heatmap({ cohorts, models, grid }) {
  const [ref, W] = useWidth()
  const dark = useDark()
  const tip = useTip()
  const padL = Math.min(170, W * 0.32), padT = 8
  const cw = Math.max(6, (W - padL - 8) / models.length)
  const ch = 15
  const H = cohorts.length * ch + padT + 4
  return (
    <div className="chart" ref={ref}>
      {W > 0 && (
        <svg viewBox={`0 0 ${W} ${H}`} role="img">
          {cohorts.map((c, r) => (
            <g key={c}>
              <text className="mark-lbl" x={padL - 8} y={padT + r * ch + ch - 4} textAnchor="end" style={{ fontSize: 9.5 }}>{c}</text>
              {models.map((m, k) => {
                const v = grid[r][k]
                return <rect key={k} x={padL + k * cw} y={padT + r * ch} width={cw - 1} height={ch - 1} fill={v == null ? 'var(--surface-2)' : recogColor(v, dark)}
                  onMouseMove={(e) => tip.show(e, <><div className="tt">{c} × {modelLabel(m)}</div><div className="tv">{v == null ? 'no data' : pct(v, 0) + ' recognized'}</div></>)} onMouseLeave={tip.hide} />
              })}
            </g>
          ))}
        </svg>
      )}
    </div>
  )
}

/* ═══════════════ Meter — single recognition fraction ════════════════════ */
export function Meter({ value, color = 'var(--signal)', label }) {
  return (
    <div>
      {label && <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}><span className="tag" style={{ fontSize: 10 }}>{label}</span><span className="num" style={{ fontSize: 13, color: 'var(--ink)' }}>{pct(value, 0)}</span></div>}
      <div className="meter"><i style={{ width: `${Math.max(2, value * 100)}%`, background: color }} /></div>
    </div>
  )
}

export function RampLegend() {
  const dark = useDark()
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <span className="tag" style={{ fontSize: 9 }}>silent</span>
      <div style={{ display: 'flex', width: 160, height: 9, borderRadius: 2, overflow: 'hidden' }}>
        {Array.from({ length: 24 }, (_, i) => <div key={i} style={{ flex: 1, background: recogColor(i / 23, dark) }} />)}
      </div>
      <span className="tag" style={{ fontSize: 9 }}>recognized</span>
    </div>
  )
}
