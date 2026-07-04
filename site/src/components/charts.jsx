import React, { useEffect, useRef, useState } from 'react'
import { fmt, modelLabel, isThinking, scoreColor, useTip } from '../lib/ui.jsx'

/* measure a container's width */
export function useWidth(min = 320) {
  const ref = useRef(null)
  const [w, setW] = useState(min)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const ro = new ResizeObserver(([e]) => setW(Math.max(min, e.contentRect.width)))
    ro.observe(el)
    return () => ro.disconnect()
  }, [min])
  return [ref, w]
}

const isDark = () => document.documentElement.dataset.theme === 'dark'

/* ————————————————————————————— DotStrip —————————————————————————————
   One entity across the 37-model panel: a row of dots in fixed panel
   order, colored by score; refusals/zeros read as near-empty. */
export function DotStrip({ scores, models, height = 64, showMean = true, meanLabel = 'NameRank' }) {
  const tip = useTip()
  const [ref, w] = useWidth()
  const n = scores.length
  const pad = 8
  const cell = (w - pad * 2) / n
  const r = Math.min(7, Math.max(3.5, cell * 0.32))
  const valid = scores.filter((s) => s != null)
  const mean = valid.length ? valid.reduce((a, b) => a + b, 0) / valid.length : null
  const cy = height / 2 - 6
  return (
    <div ref={ref}>
      <svg width={w} height={height} role="img" aria-label="scores across the model panel">
        {scores.map((s, i) => {
          const cx = pad + cell * (i + 0.5)
          return (
            <g key={i}>
              <circle
                cx={cx} cy={cy} r={Math.max(r, 8)} fill="transparent"
                onMouseMove={(e) => tip.show(e, (
                  <>
                    <b>{modelLabel(models[i])}</b>
                    <br />
                    score <b>{fmt(s, 2)}</b>
                    {s === 0 && <span className="dim"> · no credit</span>}
                  </>
                ))}
                onMouseLeave={tip.hide}
              />
              <circle
                cx={cx} cy={cy} r={r}
                fill={s == null ? 'transparent' : scoreColor(s, isDark())}
                stroke={s == null || s < 0.08 ? 'var(--line-strong)' : 'var(--paper)'}
                strokeWidth={s == null ? 1.2 : 1.5}
                strokeDasharray={s == null ? '2 2' : undefined}
                style={{ pointerEvents: 'none' }}
              />
            </g>
          )
        })}
        {showMean && mean != null && (
          <g>
            <line x1={pad + (w - pad * 2) * 0} x2={w - pad} y1={height - 9} y2={height - 9} className="grid-line" />
            <line
              x1={pad + (w - pad * 2) * mean} x2={pad + (w - pad * 2) * mean}
              y1={cy + r + 5} y2={height - 4}
              stroke="var(--ink)" strokeWidth="2"
            />
            <text
              x={pad + (w - pad * 2) * mean + (mean > 0.72 ? -7 : 7)} y={height - 13}
              textAnchor={mean > 0.72 ? 'end' : 'start'}
              className="axis-label" style={{ fill: 'var(--ink)', fontWeight: 600 }}
            >
              {meanLabel} {fmt(mean, 2)}
            </text>
          </g>
        )}
      </svg>
    </div>
  )
}

/* ————————————————————————————— HBarChart —————————————————————————————
   Generic horizontal bars with an optional reference line.
   rows: [{label, sub, value, muted, color}] */
export function HBarChart({ rows, max = null, refLine = null, valueFmt = (v) => fmt(v, 2), rowH = 34, labelW = 240 }) {
  const tip = useTip()
  const [ref, w] = useWidth()
  const vmax = max ?? Math.max(...rows.map((r) => r.value)) * 1.15
  const chartW = w - labelW - 60
  const topPad = refLine ? 22 : 0
  const H = rows.length * rowH + 24 + topPad
  const x = (v) => labelW + (v / vmax) * chartW
  return (
    <div ref={ref}>
      <svg width={w} height={H} role="img">
        {[0.2, 0.4, 0.6].filter((g) => g < vmax).map((g) => (
          <line key={g} x1={x(g)} x2={x(g)} y1={topPad + 4} y2={H - 20} className="grid-line" />
        ))}
        {rows.map((row, i) => {
          const y = i * rowH + 6 + topPad
          const bh = Math.min(18, rowH - 12)
          const color = row.color ?? 'var(--person)'
          return (
            <g key={row.label}
              onMouseMove={row.tip ? (e) => tip.show(e, row.tip) : undefined}
              onMouseLeave={row.tip ? tip.hide : undefined}
            >
              <text x={labelW - 12} y={y + bh / 2 + 4} textAnchor="end"
                style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fill: row.muted ? 'var(--ink-3)' : 'var(--ink)', fontWeight: row.strong ? 600 : 400 }}>
                {row.label}
              </text>
              {row.sub && (
                <text x={labelW - 12} y={y + bh / 2 + 16} textAnchor="end" className="axis-label">
                  {row.sub}
                </text>
              )}
              <rect x={labelW} y={y} width={Math.max(2, (row.value / vmax) * chartW)} height={bh}
                rx={4} fill={color} opacity={row.muted ? 0.35 : 1} />
              <text x={x(row.value) + 8} y={y + bh / 2 + 4} className="num"
                style={{ fontSize: 12, fill: 'var(--ink-2)' }}>
                {valueFmt(row.value)}
              </text>
            </g>
          )
        })}
        {refLine && (
          <g>
            <line x1={x(refLine.value)} x2={x(refLine.value)} y1={14} y2={H - 18}
              stroke="var(--ink)" strokeWidth="1.6" strokeDasharray="5 4" />
            <text x={x(refLine.value) - 8} y={12} textAnchor="end"
              className="axis-label" style={{ fill: 'var(--ink)', fontWeight: 600 }}>
              {refLine.label}
            </text>
          </g>
        )}
        {[0, 0.2, 0.4, 0.6].filter((g) => g < vmax).map((g) => (
          <text key={g} x={x(g)} y={H - 6} textAnchor="middle" className="axis-label">{g}</text>
        ))}
      </svg>
    </div>
  )
}

/* ————————————————————————————— Dumbbell —————————————————————————————
   Creator (blue) vs artifact (amber) NameRank per pair. */
export function Dumbbell({ pairs }) {
  const tip = useTip()
  const [ref, w] = useWidth()
  const rowH = 56
  const padL = 16
  const padR = 76
  const H = pairs.length * rowH + 36
  const x = (v) => padL + v * (w - padL - padR)
  const clampX = (v) => Math.max(padL + 30, Math.min(w - padR - 10, v))
  return (
    <div ref={ref}>
      <svg width={w} height={H} role="img" aria-label="creator vs artifact recognition per pair">
        {[0, 0.25, 0.5, 0.75, 1].map((g) => (
          <g key={g}>
            <line x1={x(g)} x2={x(g)} y1={16} y2={H - 22} className="grid-line" />
            <text x={x(g)} y={H - 8} textAnchor="middle" className="axis-label">{g}</text>
          </g>
        ))}
        {pairs.map((p, i) => {
          const y = i * rowH + 38
          const inverted = p.delta > 0
          const cx = x(p.nrCreator)
          const ax = x(p.nrArtifact)
          const show = (e) => tip.show(e, (
            <>
              <b>{p.creator}</b> {fmt(p.nrCreator)} · <b>{p.artifact}</b> {fmt(p.nrArtifact)}
              <br />
              <span className="dim">asked about the person, {Math.round(p.cToA * 100)}% of answers name the tool</span>
              <br />
              <span className="dim">asked about the tool, {Math.round(p.aToC * 100)}% name the person</span>
            </>
          ))
          return (
            <g key={p.creator} onMouseMove={show} onMouseLeave={tip.hide}>
              <rect x={0} y={y - 24} width={w} height={rowH - 4} fill="transparent" />
              <line x1={cx} x2={ax} y1={y} y2={y} stroke="var(--line-strong)" strokeWidth="2" />
              <circle cx={cx} cy={y} r={7} fill="var(--person)" stroke="var(--paper)" strokeWidth="2" />
              <circle cx={ax} cy={y} r={7} fill="var(--artifact)" stroke="var(--paper)" strokeWidth="2" />
              {/* each name labels its OWN dot: creator above, artifact below */}
              <text x={clampX(cx)} y={y - 13} textAnchor="middle"
                style={{ fontFamily: 'var(--font-mono)', fontSize: 11.5, fill: 'var(--person)', fontWeight: 600 }}>
                {p.creator}
              </text>
              <text x={clampX(ax)} y={y + 22} textAnchor="middle"
                style={{ fontFamily: 'var(--font-mono)', fontSize: 11.5, fill: 'var(--artifact-ink)', fontWeight: 600 }}>
                {p.artifact}
              </text>
              <text x={w - 4} y={y + 4} textAnchor="end" className="num"
                style={{ fontSize: 11.5, fill: inverted ? 'var(--good)' : 'var(--ink-3)' }}>
                {inverted ? '+' : ''}{fmt(p.delta)}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}

/* ————————————————————————————— IntervalChart —————————————————————————————
   Dot + CI whisker per row (country gradient). */
export function IntervalChart({ rows, domain = [0, 0.8] }) {
  const tip = useTip()
  const [ref, w] = useWidth()
  const rowH = 34
  const labelW = 130
  const padR = 30
  const H = rows.length * rowH + 30
  const x = (v) => labelW + ((v - domain[0]) / (domain[1] - domain[0])) * (w - labelW - padR)
  const ticks = [0, 0.2, 0.4, 0.6, 0.8].filter((t) => t >= domain[0] && t <= domain[1])
  return (
    <div ref={ref}>
      <svg width={w} height={H} role="img" aria-label="mean recognition by country with confidence intervals">
        {ticks.map((g) => (
          <g key={g}>
            <line x1={x(g)} x2={x(g)} y1={4} y2={H - 22} className="grid-line" />
            <text x={x(g)} y={H - 8} textAnchor="middle" className="axis-label">{g}</text>
          </g>
        ))}
        {rows.map((r, i) => {
          const y = i * rowH + 18
          return (
            <g key={r.country}
              onMouseMove={(e) => tip.show(e, (
                <>
                  <b>{r.country}</b> · {r.n} faculty
                  <br />mean {fmt(r.mean)} <span className="dim">(95% CI {fmt(r.lo)}–{fmt(r.hi)})</span>
                  {!r.firm && <><br /><span className="dim">small sample — suggestive only</span></>}
                </>
              ))}
              onMouseLeave={tip.hide}
            >
              <rect x={0} y={y - 14} width={w} height={rowH - 6} fill="transparent" />
              <text x={labelW - 12} y={y + 4} textAnchor="end"
                style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fill: r.firm ? 'var(--ink)' : 'var(--ink-3)', fontWeight: r.firm ? 600 : 400 }}>
                {r.country}
              </text>
              <line x1={x(r.lo)} x2={x(r.hi)} y1={y} y2={y}
                stroke={r.firm ? 'var(--person)' : 'var(--line-strong)'} strokeWidth="2" />
              <circle cx={x(r.mean)} cy={y} r={r.firm ? 6.5 : 5}
                fill={r.firm ? 'var(--person)' : 'var(--paper)'}
                stroke={r.firm ? 'var(--paper)' : 'var(--ink-3)'} strokeWidth={r.firm ? 2 : 1.5} />
              <text x={x(r.hi) + 9} y={y + 4} className="num" style={{ fontSize: 11, fill: 'var(--ink-3)' }}>
                n={r.n}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}

/* ————————————————————————————— Leaderboard —————————————————————————————
   The 37-model panel: aligned twin panels (score | share saying unknown). */
export function Leaderboard({ models }) {
  const tip = useTip()
  const [ref, w] = useWidth()
  const rowH = 26
  const labelW = Math.min(210, w * 0.28)
  const gap = 26
  const colW = (w - labelW - gap) / 2
  const H = models.length * rowH + 40
  const maxScore = 0.75
  const maxRef = Math.max(...models.map((m) => m.refusal)) * 1.15
  return (
    <div ref={ref}>
      <svg width={w} height={H} role="img" aria-label="per-model mean score and refusal rate">
        <text x={labelW} y={12} className="axis-label" style={{ fill: 'var(--ink-2)', fontWeight: 600 }}>
          MEAN SCORE ACROSS 5,719 ENTITIES
        </text>
        <text x={labelW + colW + gap} y={12} className="axis-label" style={{ fill: 'var(--ink-2)', fontWeight: 600 }}>
          SHARE OF ANSWERS SAYING “UNKNOWN”
        </text>
        {models.map((m, i) => {
          const y = i * rowH + 24
          const bh = 13
          return (
            <g key={m.id}
              onMouseMove={(e) => tip.show(e, (
                <>
                  <b>{modelLabel(m.id)}</b> · {m.lab}{isThinking(m.id) ? ' · reasoning' : ''}
                  <br />mean score <b>{fmt(m.mean, 3)}</b> · says unknown {Math.round(m.refusal * 100)}%
                  <br /><span className="dim">score when it does answer: {fmt(m.meanNonRefusal, 3)}</span>
                  {m.cutoff && <><br /><span className="dim">training cutoff {m.cutoff}</span></>}
                </>
              ))}
              onMouseLeave={tip.hide}
            >
              <rect x={0} y={y - 4} width={w} height={rowH - 2} fill="transparent" />
              <text x={labelW - 10} y={y + bh - 3} textAnchor="end"
                style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fill: 'var(--ink-2)' }}>
                {modelLabel(m.id)}
              </text>
              <rect x={labelW} y={y} width={(m.mean / maxScore) * colW} height={bh} rx={3.5} fill="var(--person)" />
              <text x={labelW + (m.mean / maxScore) * colW + 6} y={y + bh - 3} className="num"
                style={{ fontSize: 10.5, fill: 'var(--ink-3)' }}>
                {fmt(m.mean, 2)}
              </text>
              <rect x={labelW + colW + gap} y={y} width={Math.max(1.5, (m.refusal / maxRef) * colW)} height={bh}
                rx={3.5} fill="var(--line-strong)" />
              <text x={labelW + colW + gap + Math.max(1.5, (m.refusal / maxRef) * colW) + 6} y={y + bh - 3}
                className="num" style={{ fontSize: 10.5, fill: 'var(--ink-3)' }}>
                {Math.round(m.refusal * 100)}%
              </text>
            </g>
          )
        })}
      </svg>
      <div className="chart-note" style={{ marginTop: 6 }}>
        ✱ = extended-reasoning variant. Panel sorted by mean score. Saying “unknown” is honest, not
        bad — models that refuse more often score higher on the answers they do give.
      </div>
    </div>
  )
}

/* ————————————————————————————— Heatmap —————————————————————————————
   54 cohorts × 37 models, sequential single-hue ramp. */
export function Heatmap({ data, cohortNames, onPick }) {
  const tip = useTip()
  const { cohorts, models, grid } = data
  const labelW = 218
  const topH = 132
  const cw = 22
  const ch = 15
  const w = labelW + models.length * cw + 10
  const H = topH + cohorts.length * ch + 8
  return (
    <div style={{ overflowX: 'auto' }}>
      <svg width={w} height={H} role="img" aria-label="mean score for every cohort and model">
        {models.map((m, j) => (
          <text key={m}
            transform={`translate(${labelW + j * cw + cw / 2 + 3}, ${topH - 6}) rotate(-52)`}
            style={{ fontFamily: 'var(--font-mono)', fontSize: 9.5, fill: 'var(--ink-3)' }}>
            {modelLabel(m)}
          </text>
        ))}
        {cohorts.map((c, i) => (
          <g key={c}>
            <text x={labelW - 8} y={topH + i * ch + ch - 4} textAnchor="end"
              style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fill: 'var(--ink-2)', cursor: onPick ? 'pointer' : 'default' }}
              onClick={onPick ? () => onPick(c) : undefined}>
              {cohortNames[c] ?? c}
            </text>
            {grid[i].map((v, j) => (
              <rect key={j}
                x={labelW + j * cw} y={topH + i * ch}
                width={cw - 2} height={ch - 2} rx={2}
                fill={v == null ? 'transparent' : scoreColor(v, isDark())}
                stroke={v == null ? 'var(--line)' : 'none'}
                onMouseMove={(e) => tip.show(e, (
                  <>
                    <b>{cohortNames[c] ?? c}</b> × <b>{modelLabel(models[j])}</b>
                    <br />mean score {fmt(v, 2)}
                  </>
                ))}
                onMouseLeave={tip.hide}
              />
            ))}
          </g>
        ))}
      </svg>
    </div>
  )
}

/* legend for the sequential ramp */
export function RampLegend({ lo = 'not known', hi = 'fully known' }) {
  const stops = [0, 0.14, 0.28, 0.42, 0.56, 0.7, 0.84, 1]
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }} className="chart-note">
      <span>{lo}</span>
      <div style={{ display: 'flex', gap: 2 }}>
        {stops.map((s) => (
          <div key={s} style={{ width: 17, height: 11, borderRadius: 2, background: scoreColor(s, isDark()) }} />
        ))}
      </div>
      <span>{hi}</span>
    </div>
  )
}
