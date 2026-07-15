import React, { useEffect, useMemo, useRef, useState } from 'react'
import cohorts from '../data/cohorts.json'
import stats from '../data/stats.json'
import {
  fmt, pct, modelLabel, MiniMd, catColor, useData, useMedia,
  classifyCase, CASE_KIND_META, Reveal,
} from '../lib/ui.jsx'
import { DotStrip, Heatmap, RampLegend, Meter } from '../components/charts.jsx'

/* ————————————————— cohort lookups ————————————————— */
const COHORT = Object.fromEntries(cohorts.map((c) => [c.slug, c]))
const COHORT_NAME = (slug) => COHORT[slug]?.name ?? slug
const COHORT_CAT = (slug) => COHORT[slug]?.category ?? 'person'
/* DotStrip / Meter only speak person|artifact — credentials render as person-blue */
const dotCat = (slug) => (COHORT_CAT(slug) === 'artifact' ? 'artifact' : 'person')

const CAT_LABEL = { person: 'People', artifact: 'Tools & artifacts', credential: 'Credentials' }
const CAT_GROUP = { person: 'People', artifact: 'Tools & artifacts', credential: 'Credential cohorts' }

/* entities.json row → object: cols = id,name,cohort,country,year,nr,refusal */
const entObj = (r) => ({
  id: r[0], name: r[1], cohort: r[2], country: r[3], year: r[4], nr: r[5], refusal: r[6],
})

const CAP = 60

const fieldStyle = {
  fontFamily: 'var(--mono)', fontSize: '0.82rem', color: 'var(--ink)',
  background: 'var(--surface)', border: '1px solid var(--line-2)',
  borderRadius: 2, padding: '9px 12px', outline: 'none',
}

/* ————————————————— shared bits ————————————————— */
function Loader({ label }) {
  return (
    <div className="panel panel--pad" style={{ display: 'flex', alignItems: 'center', gap: 14, justifyContent: 'center' }}>
      <span className="spin" />
      <span className="tag">{label}</span>
    </div>
  )
}

function Segmented({ options, value, onChange }) {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7 }}>
      {options.map((o) => (
        <button key={o.key} className={`chip ${value === o.key ? 'is-on' : ''}`} onClick={() => onChange(o.key)}>
          {o.dot && <span className="dot" style={{ background: o.dot }} />}
          {o.label}
        </button>
      ))}
    </div>
  )
}

/* rows list wrapper (scroll, capped) */
function CountNote({ shown, total, unit }) {
  return (
    <div className="tag" style={{ margin: '12px 2px' }}>
      showing <b className="num" style={{ color: 'var(--ink)' }}>{Math.min(shown, total).toLocaleString()}</b>
      {' '}of <b className="num" style={{ color: 'var(--ink)' }}>{total.toLocaleString()}</b> {unit}
    </div>
  )
}

/* ═══════════════════ 1 · ENTITY BROWSER ═══════════════════ */

const AVERDICT = {
  recognised: { label: 'Recognised', color: 'var(--signal)' },
  unknown: { label: 'Said “unknown”', color: 'var(--ink-3)' },
  silent: { label: 'Answered, not recognised', color: 'var(--bad)' },
}
const answerVerdict = (a) => (a.recognized ? 'recognised' : a.refusal ? 'unknown' : 'silent')

function AnswerCard({ a }) {
  const v = answerVerdict(a)
  const m = AVERDICT[v]
  const [open, setOpen] = useState(false)
  const long = a.response && a.response.length > 300
  const text = a.response || '(empty response)'
  return (
    <div style={{ borderBottom: '1px solid var(--line)', padding: '12px 2px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 7, flexWrap: 'wrap' }}>
        <span style={{ width: 8, height: 8, borderRadius: '50%', background: m.color, flex: 'none' }} />
        <span className="mono" style={{ fontSize: '0.8rem', color: 'var(--ink)' }}>{modelLabel(a.model)}</span>
        <span className={`verdict ${v === 'recognised' ? 'verdict--yes' : 'verdict--no'}`} style={{ color: m.color, borderColor: v === 'recognised' ? 'var(--signal)' : 'var(--line-2)' }}>{m.label}</span>
      </div>
      <div style={{ fontSize: '0.87rem', lineHeight: 1.5, color: a.refusal ? 'var(--ink-3)' : 'var(--ink-2)', fontStyle: a.refusal ? 'italic' : 'normal', maxWidth: 'none' }}>
        <MiniMd text={long && !open ? text.slice(0, 300) + '…' : text} />
        {long && <button onClick={() => setOpen((o) => !o)} className="tag" style={{ marginLeft: 8, color: 'var(--signal)', cursor: 'pointer' }}>{open ? 'less' : 'more'}</button>}
      </div>
      {a.rationale && a.rationale !== 'refusal' && v !== 'recognised' && (
        <div className="tag" style={{ fontSize: '0.6rem', marginTop: 6, color: 'var(--ink-faint)' }}>judge: {a.rationale.slice(0, 140)}</div>
      )}
    </div>
  )
}

function AnswersBlock({ id, name }) {
  const data = useData(`answers/${id}.json`)
  const [vf, setVf] = useState('all')
  if (!data) return <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '14px 0' }}><span className="spin" /><span className="tag">loading every answer…</span></div>
  const answers = data.answers || []
  const counts = { all: answers.length, recognised: 0, unknown: 0, silent: 0 }
  answers.forEach((a) => { counts[answerVerdict(a)]++ })
  const rows = vf === 'all' ? answers : answers.filter((a) => answerVerdict(a) === vf)
  return (
    <>
      <div className="tag" style={{ margin: '20px 0 6px' }}>The probe — sent verbatim to all {answers.length} models</div>
      <div className="mono" style={{ fontSize: '0.8rem', color: 'var(--ink-2)', border: '1px solid var(--line)', borderRadius: 3, padding: '10px 12px', marginBottom: 16 }}>
        “Tell me what you know about <b style={{ color: 'var(--ink)' }}>{name}</b>, who is {data.context}. …”
      </div>
      <div className="panel-head" style={{ marginBottom: 4 }}>
        <span className="panel-title" style={{ fontSize: '0.85rem' }}>Every model’s answer</span>
      </div>
      <div style={{ marginBottom: 6 }}>
        <Segmented value={vf} onChange={setVf} options={[
          { key: 'all', label: `All ${counts.all}` },
          { key: 'recognised', label: `Recognised ${counts.recognised}`, dot: 'var(--signal)' },
          { key: 'unknown', label: `“unknown” ${counts.unknown}`, dot: 'var(--ink-3)' },
          { key: 'silent', label: `Not recognised ${counts.silent}`, dot: 'var(--bad)' },
        ]} />
      </div>
      <div style={{ maxHeight: 460, overflowY: 'auto', marginTop: 6, paddingRight: 6 }}>
        {rows.map((a) => <AnswerCard key={a.model} a={a} />)}
        {rows.length === 0 && <div className="tag" style={{ padding: 20, textAlign: 'center' }}>none in this verdict</div>}
      </div>
    </>
  )
}

function EntityDetail({ ent, matrix }) {
  const gold = useData(`gold/${ent.cohort}.json`)
  const scores = matrix?.scores?.[ent.id]
  const lit = scores ? scores.filter((s) => s >= 0.5).length : null
  const total = scores ? scores.length : stats.models
  const cat = COHORT_CAT(ent.cohort)

  return (
    <div className="panel panel--pad" key={ent.id}>
      <div className="tag" style={{ color: catColor(cat) }}>
        {COHORT_NAME(ent.cohort)}
        {ent.country ? ` · ${ent.country}` : ''}{ent.year ? ` · ${ent.year}` : ''}
      </div>
      <h3 style={{ margin: '6px 0 14px' }}>{ent.name}</h3>

      <div style={{ display: 'flex', gap: 26, alignItems: 'baseline', flexWrap: 'wrap', marginBottom: 18 }}>
        <div>
          <div className="num" style={{ fontSize: '2.6rem', lineHeight: 1, color: 'var(--signal)' }}>{fmt(ent.nr)}</div>
          <div className="tag" style={{ marginTop: 6 }}>NameRank</div>
        </div>
        <div>
          <div className="num" style={{ fontSize: '1.3rem', color: 'var(--ink)' }}>
            {lit == null ? '—' : lit} <span style={{ color: 'var(--ink-3)' }}>/ {total}</span>
          </div>
          <div className="tag" style={{ marginTop: 6 }}>models recognised</div>
        </div>
        <div>
          <div className="num" style={{ fontSize: '1.3rem', color: 'var(--ink)' }}>{pct(ent.refusal)}</div>
          <div className="tag" style={{ marginTop: 6 }}>said “unknown”</div>
        </div>
      </div>

      <div className="tag" style={{ marginBottom: 8 }}>All {total} models — one dot each, lit = recognised</div>
      {scores
        ? <DotStrip scores={scores} models={matrix.models} cat={dotCat(ent.cohort)} size="md" />
        : <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 0' }}><span className="spin" /><span className="tag">loading the panel…</span></div>}

      <AnswersBlock id={ent.id} name={ent.name} />

      {gold?.[ent.id] && (
        <>
          <div className="tag" style={{ margin: '18px 0 8px' }}>The fact sheet answers were graded against</div>
          <p style={{ fontSize: '0.86rem', color: 'var(--ink-2)', maxWidth: 'none', borderLeft: '2px solid var(--line-2)', paddingLeft: 12 }}>
            {gold[ent.id]}
          </p>
        </>
      )}
    </div>
  )
}

function EntityBrowser({ entities, matrix, initialCohort, pickKey }) {
  const [q, setQ] = useState('')
  const [cohort, setCohort] = useState('all')
  const [cat, setCat] = useState('all')
  const [sel, setSel] = useState(null)
  const narrow = useMedia('(max-width: 900px)')

  useEffect(() => {
    if (initialCohort) { setCohort(initialCohort); setCat('all'); setQ(''); setSel(null) }
  }, [initialCohort, pickKey])

  const rows = useMemo(() => {
    if (!entities) return []
    const ql = q.trim().toLowerCase()
    return entities.rows.filter((r) => {
      if (cohort !== 'all' && r[2] !== cohort) return false
      if (cat !== 'all' && COHORT_CAT(r[2]) !== cat) return false
      if (ql && !r[1].toLowerCase().includes(ql)) return false
      return true
    })
  }, [entities, q, cohort, cat])

  const selEnt = useMemo(() => {
    if (!entities || !sel) return null
    const r = entities.rows.find((rr) => rr[0] === sel)
    return r ? entObj(r) : null
  }, [entities, sel])

  if (!entities) return <Loader label="loading entities…" />

  const groups = { person: [], artifact: [], credential: [] }
  cohorts.forEach((c) => groups[c.category]?.push(c))

  return (
    <div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 14 }}>
        <input
          style={{ ...fieldStyle, flex: '1 1 240px' }}
          placeholder="Search a name… (e.g. Karpathy)"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <select style={fieldStyle} value={cohort} onChange={(e) => setCohort(e.target.value)}>
          <option value="all">All {cohorts.length} cohorts</option>
          {Object.entries(groups).map(([g, list]) => (
            <optgroup key={g} label={CAT_GROUP[g]}>
              {list.map((c) => <option key={c.slug} value={c.slug}>{c.name} ({c.n})</option>)}
            </optgroup>
          ))}
        </select>
      </div>
      <Segmented
        value={cat}
        onChange={(k) => setCat(k)}
        options={[
          { key: 'all', label: 'All' },
          { key: 'person', label: CAT_LABEL.person, dot: 'var(--person)' },
          { key: 'artifact', label: CAT_LABEL.artifact, dot: 'var(--artifact)' },
          { key: 'credential', label: CAT_LABEL.credential, dot: 'var(--person)' },
        ]}
      />

      <CountNote shown={CAP} total={rows.length} unit="entities · click one to open its panel" />

      <div style={{ display: 'grid', gridTemplateColumns: narrow ? '1fr' : 'minmax(0, 0.95fr) minmax(0, 1.05fr)', gap: 18, alignItems: 'start' }}>
        <div className="panel" style={{ maxHeight: 560, overflowY: 'auto' }}>
          {rows.slice(0, CAP).map((r) => {
            const e = entObj(r)
            const on = sel === e.id
            return (
              <button
                key={e.id}
                onClick={() => setSel(e.id)}
                style={{
                  display: 'grid', gridTemplateColumns: '1fr auto', gap: '2px 12px', alignItems: 'center',
                  width: '100%', textAlign: 'left', padding: '11px 16px',
                  borderBottom: '1px solid var(--line)',
                  background: on ? 'var(--surface-2)' : 'transparent',
                  borderLeft: `2px solid ${on ? catColor(COHORT_CAT(e.cohort)) : 'transparent'}`,
                }}
              >
                <span style={{ fontWeight: on ? 600 : 400, color: 'var(--ink)' }}>{e.name}</span>
                <span className="num" style={{ fontSize: '0.82rem', color: 'var(--ink-2)' }}>{fmt(e.nr)}</span>
                <span className="tag" style={{ gridColumn: '1 / 2' }}>{COHORT_NAME(e.cohort)}</span>
                <span style={{ gridColumn: '1 / -1', marginTop: 4 }}>
                  <Meter value={e.nr} color={catColor(COHORT_CAT(e.cohort))} />
                </span>
              </button>
            )
          })}
          {rows.length === 0 && <div className="tag" style={{ padding: 24, textAlign: 'center' }}>no matches</div>}
        </div>

        <div>
          {selEnt
            ? <EntityDetail ent={selEnt} matrix={matrix} />
            : (
              <div className="panel panel--pad">
                <div className="serif" style={{ fontSize: '1.3rem', fontStyle: 'italic', color: 'var(--ink-3)' }}>← pick a name</div>
                <p style={{ fontSize: '0.9rem', color: 'var(--ink-3)', marginTop: 8, maxWidth: 'none' }}>
                  Every name opens its full {stats.models}-model recognition panel — one dot per model,
                  lit when the model genuinely recognised it — plus the fact sheet it was graded against.
                </p>
              </div>
            )}
        </div>
      </div>
    </div>
  )
}

/* ═══════════════════ 2 · CASE VIEWER ═══════════════════ */

const JUDGE_LABEL = { gemini: 'Gemini (primary)', claude: 'Claude', gpt: 'GPT' }

function JudgePanel({ judges }) {
  return (
    <div className="grid grid-3" style={{ gap: 12 }}>
      {['gemini', 'claude', 'gpt'].filter((k) => judges[k]).map((name) => {
        const j = judges[name]
        return (
          <div key={name} style={{ border: '1px solid var(--line)', borderRadius: 3, padding: '12px 14px' }}>
            <div className="tag" style={{ marginBottom: 10 }}>{JUDGE_LABEL[name] ?? name}</div>
            {[['coverage', j.cov, 'var(--person)'], ['accuracy', j.acc, 'var(--signal)']].map(([l, v, col]) => (
              <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 7 }}>
                <span className="tag" style={{ width: 66, fontSize: '0.6rem' }}>{l}</span>
                <span style={{ flex: 1 }}><Meter value={v} color={col} /></span>
                <span className="num" style={{ fontSize: '0.74rem', color: 'var(--ink)', minWidth: 26, textAlign: 'right' }}>{fmt(v)}</span>
              </div>
            ))}
          </div>
        )
      })}
    </div>
  )
}

function CaseDetail({ c, onPrev, onNext, hasPrev, hasNext }) {
  const [showGold, setShowGold] = useState(false)
  const kind = classifyCase(c)
  const recognised = kind === 'recognized' || kind === 'partial'
  useEffect(() => setShowGold(false), [c.i])

  return (
    <div className="panel panel--pad" key={c.i}>
      <div className="panel-head">
        <div>
          <div className="tag">{COHORT_NAME(c.cohort)} · NameRank {fmt(c.nr)}</div>
          <h3 style={{ fontSize: '1.5rem', margin: '4px 0 8px' }}>
            {c.name} <span style={{ color: 'var(--ink-3)', fontFamily: 'var(--sans)' }}>×</span> {modelLabel(c.model)}
          </h3>
          <span className={`verdict ${recognised ? 'verdict--yes' : 'verdict--no'}`}>
            {recognised ? '● recognised' : '○ no recognition'}
          </span>
          <span className="tag" style={{ marginLeft: 10, color: CASE_KIND_META[kind].color }}>{CASE_KIND_META[kind].label}</span>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn--ghost" disabled={!hasPrev} onClick={onPrev} style={{ opacity: hasPrev ? 1 : 0.35 }}>←</button>
          <button className="btn btn--ghost" disabled={!hasNext} onClick={onNext} style={{ opacity: hasNext ? 1 : 0.35 }}>→</button>
        </div>
      </div>

      <div className="tag" style={{ marginBottom: 6 }}>The probe</div>
      <div className="mono" style={{ fontSize: '0.8rem', color: 'var(--ink-2)', border: '1px solid var(--line)', borderRadius: 3, padding: '10px 12px' }}>
        “…about <b style={{ color: 'var(--ink)' }}>{c.name}</b>, who is {c.context}.”
      </div>

      <div className="tag" style={{ margin: '16px 0 6px' }}>The model’s answer, verbatim</div>
      <div style={{ fontSize: '0.9rem', color: c.refusal ? 'var(--ink-3)' : 'var(--ink-2)', border: '1px solid var(--line)', borderRadius: 3, padding: '12px 14px', maxWidth: 'none', fontStyle: c.refusal ? 'italic' : 'normal' }}>
        {c.response ? <MiniMd text={c.response} /> : '(empty response)'}
      </div>

      <button className="btn btn--ghost" style={{ margin: '14px 0' }} onClick={() => setShowGold((v) => !v)}>
        {showGold ? 'Hide' : 'Compare with'} the fact sheet
      </button>
      {showGold && (
        <p style={{ fontSize: '0.84rem', color: 'var(--ink-3)', maxWidth: 'none', borderLeft: '2px solid var(--line-2)', paddingLeft: 12, marginBottom: 14 }}>
          {c.gold}
        </p>
      )}

      <div className="tag" style={{ margin: '6px 0 10px' }}>
        Cross-judge diagnostic — three judges re-scored this same answer (illustrative)
      </div>
      <JudgePanel judges={c.judges} />
    </div>
  )
}

function CaseViewer({ cases, selCase, setSelCase }) {
  const [kind, setKind] = useState('all')
  const [model, setModel] = useState('all')
  const [q, setQ] = useState('')
  const narrow = useMedia('(max-width: 900px)')
  const listRef = useRef(null)

  const enriched = useMemo(
    () => (cases ?? []).map((c) => ({ c, kind: classifyCase(c) })),
    [cases],
  )
  const modelsInCases = useMemo(
    () => [...new Set((cases ?? []).map((c) => c.model))].sort(),
    [cases],
  )
  const rows = useMemo(() => {
    const ql = q.trim().toLowerCase()
    return enriched.filter(({ c, kind: k }) => {
      if (kind !== 'all' && k !== kind) return false
      if (model !== 'all' && c.model !== model) return false
      if (ql && !c.name.toLowerCase().includes(ql)) return false
      return true
    })
  }, [enriched, kind, model, q])

  const idx = rows.findIndex(({ c }) => c.i === selCase)
  const current = idx >= 0 ? rows[idx].c : (rows[0]?.c ?? null)

  useEffect(() => {
    const el = listRef.current?.querySelector('[data-on="1"]')
    el?.scrollIntoView({ block: 'nearest' })
  }, [selCase])

  if (!cases) return <Loader label="loading graded answers…" />

  const counts = { all: enriched.length }
  enriched.forEach(({ kind: k }) => { counts[k] = (counts[k] ?? 0) + 1 })

  const kindOpts = [
    { key: 'all', label: `All ${counts.all}` },
    ...['recognized', 'partial', 'hallucination', 'refusal'].map((k) => ({
      key: k, label: `${CASE_KIND_META[k].label} ${counts[k] ?? 0}`, dot: CASE_KIND_META[k].color,
    })),
  ]

  return (
    <div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 14 }}>
        <input style={{ ...fieldStyle, flex: '1 1 200px' }} placeholder="Search a name…" value={q} onChange={(e) => setQ(e.target.value)} />
        <select style={fieldStyle} value={model} onChange={(e) => setModel(e.target.value)}>
          <option value="all">All models</option>
          {modelsInCases.map((m) => <option key={m} value={m}>{modelLabel(m)}</option>)}
        </select>
      </div>
      <Segmented value={kind} onChange={setKind} options={kindOpts} />

      <CountNote shown={CAP} total={rows.length} unit="illustrative graded answers" />

      <div style={{ display: 'grid', gridTemplateColumns: narrow ? '1fr' : 'minmax(0, 0.9fr) minmax(0, 1.1fr)', gap: 18, alignItems: 'start' }}>
        <div className="panel" ref={listRef} style={{ maxHeight: 560, overflowY: 'auto' }}>
          {rows.slice(0, CAP).map(({ c, kind: k }) => {
            const on = current?.i === c.i
            return (
              <button
                key={c.i}
                data-on={on ? '1' : '0'}
                onClick={() => setSelCase(c.i)}
                style={{
                  display: 'grid', gridTemplateColumns: 'auto 1fr auto', gap: 10, alignItems: 'center',
                  width: '100%', textAlign: 'left', padding: '10px 14px',
                  borderBottom: '1px solid var(--line)',
                  background: on ? 'var(--surface-2)' : 'transparent',
                  borderLeft: `2px solid ${on ? CASE_KIND_META[k].color : 'transparent'}`,
                }}
              >
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: CASE_KIND_META[k].color, display: 'inline-block' }} />
                <span style={{ minWidth: 0 }}>
                  <span style={{ display: 'block', color: 'var(--ink)', fontWeight: on ? 600 : 400, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{c.name}</span>
                  <span className="tag">{modelLabel(c.model)}</span>
                </span>
                <span className="num" style={{ fontSize: '0.8rem', color: 'var(--ink-2)' }}>{fmt(c.judges.gemini.score)}</span>
              </button>
            )
          })}
          {rows.length === 0 && <div className="tag" style={{ padding: 24, textAlign: 'center' }}>no matches</div>}
        </div>

        <div>
          {current && (
            <CaseDetail
              c={current}
              hasPrev={idx > 0}
              hasNext={idx >= 0 && idx < rows.length - 1}
              onPrev={() => setSelCase(rows[idx - 1].c.i)}
              onNext={() => setSelCase(rows[(idx >= 0 ? idx : 0) + 1].c.i)}
            />
          )}
        </div>
      </div>
    </div>
  )
}

/* ═══════════════════ 3 · HEATMAP ═══════════════════ */

function HeatmapTab({ entities, matrix }) {
  const grid = useMemo(() => {
    if (!entities || !matrix) return null
    // slug → list of entity ids that have a recognition panel
    const byCohort = {}
    entities.rows.forEach((r) => {
      const id = r[0], slug = r[2]
      if (!matrix.scores[id]) return
      ;(byCohort[slug] ??= []).push(id)
    })
    const nModels = matrix.models.length
    return cohorts.map((c) => {
      const ids = byCohort[c.slug] ?? []
      if (ids.length === 0) return new Array(nModels).fill(null)
      const sums = new Array(nModels).fill(0)
      ids.forEach((id) => {
        const s = matrix.scores[id]
        for (let k = 0; k < nModels; k++) sums[k] += s[k] >= 0.5 ? 1 : 0
      })
      return sums.map((v) => v / ids.length)
    })
  }, [entities, matrix])

  if (!entities || !matrix || !grid) return <Loader label="computing the cohort × model grid…" />

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12, margin: '0 2px 14px' }}>
        <div className="tag">{cohorts.length} cohorts × {matrix.models.length} models — each cell is the mean recognition over a cohort’s entities</div>
        <RampLegend />
      </div>
      <div className="panel panel--pad" style={{ overflowX: 'auto' }}>
        <Heatmap cohorts={cohorts.map((c) => c.name)} models={matrix.models} grid={grid} />
      </div>
    </div>
  )
}

/* ═══════════════════ section shell ═══════════════════ */

const TABS = [
  { key: 'entities', label: 'Browse every answer' },
  { key: 'cases', label: 'Cross-judge examples' },
  { key: 'heatmap', label: 'The whole grid' },
]

export default function Explorer() {
  const [visible, setVisible] = useState(false)
  const [tab, setTab] = useState('entities')
  const [selCase, setSelCase] = useState(null)
  const [pickedCohort] = useState(null)
  const [pickKey] = useState(0)
  const rootRef = useRef(null)

  useEffect(() => {
    const io = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) { setVisible(true); io.disconnect() } },
      { rootMargin: '600px' },
    )
    if (rootRef.current) io.observe(rootRef.current)
    return () => io.disconnect()
  }, [])

  /* lazy: only fetch a tab's data once the section is visible and the tab is active */
  const entities = useData('entities.json', visible && (tab === 'entities' || tab === 'heatmap'))
  const matrix = useData('matrix.json', visible && (tab === 'entities' || tab === 'heatmap'))
  const cases = useData('cases.json', visible && tab === 'cases')

  return (
    <section className="section" id="explorer" ref={rootRef}>
      <div className="wrap wrap--wide">
        <Reveal>
          <div className="sec-head">
            <span className="sec-idx">04</span>
            <h2 className="sec-title">Explore the full run</h2>
          </div>
          <p className="lede sec-kicker">
            Don’t take the charts’ word for it. Pick any of the {stats.entities.toLocaleString()} entities and
            read all {stats.models} verbatim answers — every probe, every model, with its recognition
            verdict. Browse by category, or filter to who said “unknown.”
          </p>
        </Reveal>

        <Reveal style={{ marginTop: 34 }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 22 }}>
            {TABS.map((t) => (
              <button key={t.key} className={`chip ${tab === t.key ? 'is-on' : ''}`} onClick={() => setTab(t.key)}>
                {t.label}
              </button>
            ))}
          </div>

          {tab === 'entities' && (
            <EntityBrowser entities={entities} matrix={matrix} initialCohort={pickedCohort} pickKey={pickKey} />
          )}
          {tab === 'cases' && <CaseViewer cases={cases} selCase={selCase} setSelCase={setSelCase} />}
          {tab === 'heatmap' && <HeatmapTab entities={entities} matrix={matrix} />}
        </Reveal>
      </div>
    </section>
  )
}
