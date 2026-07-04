import React, { useEffect, useMemo, useRef, useState } from 'react'
import cohorts from '../data/cohorts.json'
import heatmapData from '../data/heatmap.json'
import { fmt, pct, modelLabel, MiniMd, scoreColor, useData, classifyCase, CASE_KIND_META, Reveal } from '../lib/ui.jsx'
import { DotStrip, Heatmap, RampLegend } from '../components/charts.jsx'

const COHORT_NAME = Object.fromEntries(cohorts.map((c) => [c.slug, c.name]))
const COHORT_CAT = Object.fromEntries(cohorts.map((c) => [c.slug, c.category]))
const CAT_LABEL = { person: 'People', artifact: 'Tools & artifacts', credential: 'Credential cohorts' }

const isDark = () => document.documentElement.dataset.theme === 'dark'

/* row → object for entities.json's array-of-arrays format */
const entObj = (r) => ({
  id: r[0], name: r[1], cohort: r[2], country: r[3], year: r[4], nr: r[5], sd: r[6], refusal: r[7],
})

function ScoreBar({ v, w = 120 }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
      <span style={{ width: w, height: 9, background: 'var(--paper-deep)', border: '1px solid var(--line)', borderRadius: 5, overflow: 'hidden', display: 'inline-block' }}>
        <span style={{ display: 'block', height: '100%', width: `${v * 100}%`, background: scoreColor(v, isDark()), borderRadius: 4 }} />
      </span>
      <span className="num" style={{ fontSize: 12.5, minWidth: 34 }}>{fmt(v)}</span>
    </span>
  )
}

/* ————————————————— entity browser ————————————————— */

function EntityDetail({ ent, matrix, cases, onOpenCase }) {
  const gold = useData(`gold/${ent.cohort}.json`)
  const scores = matrix?.scores?.[ent.id]
  const myCases = useMemo(
    () => (cases ?? []).filter((c) => c.entity === ent.id),
    [cases, ent.id],
  )
  return (
    <div className="ent-detail card" key={ent.id}>
      <div style={{ padding: '20px 22px', borderBottom: '1px solid var(--line)' }}>
        <div className="tag">{COHORT_NAME[ent.cohort]}{ent.country ? ` · ${ent.country}` : ''}{ent.year ? ` · ${ent.year}` : ''}</div>
        <h4 style={{ fontSize: 26, margin: '6px 0 2px' }}>{ent.name}</h4>
        <div style={{ display: 'flex', gap: 22, flexWrap: 'wrap', marginTop: 10 }}>
          <span className="tag">NameRank <b className="num" style={{ fontSize: 16, color: 'var(--ink)' }}>{fmt(ent.nr)}</b></span>
          <span className="tag">says “unknown” <b className="num" style={{ fontSize: 16, color: 'var(--ink)' }}>{pct(ent.refusal)}</b></span>
          <span className="tag">spread across models <b className="num" style={{ fontSize: 16, color: 'var(--ink)' }}>±{fmt(ent.sd)}</b></span>
        </div>
      </div>
      <div style={{ padding: '16px 22px' }}>
        <div className="tag" style={{ marginBottom: 4 }}>All 37 model scores — hover the dots</div>
        {scores
          ? <DotStrip scores={scores} models={matrix.models} height={72} />
          : <div className="chart-note" style={{ padding: '18px 0' }}>loading panel scores…</div>}
        {gold?.[ent.id] && (
          <>
            <div className="tag" style={{ margin: '14px 0 6px' }}>The fact sheet answers were graded against</div>
            <div className="gold-box" style={{ marginTop: 0 }}>{gold[ent.id]}</div>
          </>
        )}
        {myCases.length > 0 && (
          <>
            <div className="tag" style={{ margin: '16px 0 8px' }}>
              {myCases.length} full graded answer{myCases.length > 1 ? 's' : ''} available — read them
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {myCases.slice(0, 12).map((c) => {
                const kind = classifyCase(c)
                return (
                  <button key={c.i} className="btn" onClick={() => onOpenCase(c.i)}>
                    {modelLabel(c.model)} · <span style={{ color: CASE_KIND_META[kind].color }}>{fmt(c.judges.gemini.score)}</span>
                  </button>
                )
              })}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function EntityBrowser({ entities, matrix, cases, onOpenCase, initialCohort, pickKey }) {
  const [q, setQ] = useState('')
  const [cohort, setCohort] = useState('all')
  const [cat, setCat] = useState('all')
  const [limit, setLimit] = useState(50)
  const [sel, setSel] = useState(null)

  useEffect(() => {
    if (initialCohort) { setCohort(initialCohort); setCat('all'); setQ(''); setSel(null) }
  }, [initialCohort, pickKey])

  const rows = useMemo(() => {
    if (!entities) return []
    const ql = q.trim().toLowerCase()
    return entities.rows.filter((r) => {
      if (cohort !== 'all' && r[2] !== cohort) return false
      if (cat !== 'all' && COHORT_CAT[r[2]] !== cat) return false
      if (ql && !r[1].toLowerCase().includes(ql)) return false
      return true
    })
  }, [entities, q, cohort, cat])

  const selEnt = useMemo(() => {
    if (!entities || !sel) return null
    const r = entities.rows.find((r) => r[0] === sel)
    return r ? entObj(r) : null
  }, [entities, sel])

  if (!entities) return <div className="chart-note" style={{ padding: 40 }}>loading 5,719 entities…</div>

  const groups = { person: [], artifact: [], credential: [] }
  cohorts.forEach((c) => groups[c.category].push(c))

  return (
    <div className="ex-browser">
      <div className="ex-controls">
        <input className="search" placeholder="Search a name… (e.g. Karpathy, Tianshou)" value={q}
          onChange={(e) => { setQ(e.target.value); setLimit(50) }} />
        <select className="search" value={cohort} onChange={(e) => { setCohort(e.target.value); setLimit(50) }}>
          <option value="all">All 54 cohorts</option>
          {Object.entries(groups).map(([g, list]) => (
            <optgroup key={g} label={CAT_LABEL[g]}>
              {list.map((c) => <option key={c.slug} value={c.slug}>{c.name} ({c.n})</option>)}
            </optgroup>
          ))}
        </select>
        <div className="seg">
          {['all', 'person', 'artifact', 'credential'].map((k) => (
            <button key={k} className={cat === k ? 'on' : ''} onClick={() => { setCat(k); setLimit(50) }}>
              {k === 'all' ? 'All' : CAT_LABEL[k].split(' ')[0]}
            </button>
          ))}
        </div>
      </div>
      <div className="tag" style={{ margin: '12px 2px' }}>
        <b>{rows.length.toLocaleString()}</b> entities · sorted by NameRank · click one to open its panel
      </div>
      <div className="ex-split">
        <div className="ent-list">
          {rows.slice(0, limit).map((r) => {
            const e = entObj(r)
            return (
              <button key={e.id} className={`ent-row ${sel === e.id ? 'on' : ''}`} onClick={() => setSel(e.id)}>
                <span className="ent-name">{e.name}</span>
                <span className="ent-cohort tag">{COHORT_NAME[e.cohort]}</span>
                <ScoreBar v={e.nr} />
              </button>
            )
          })}
          {rows.length > limit && (
            <button className="btn" style={{ margin: '14px auto', display: 'block' }} onClick={() => setLimit(limit + 100)}>
              Show more ({(rows.length - limit).toLocaleString()} remaining)
            </button>
          )}
        </div>
        <div className="ent-side">
          {selEnt
            ? <EntityDetail ent={selEnt} matrix={matrix} cases={cases} onOpenCase={onOpenCase} />
            : (
              <div className="ent-placeholder card">
                <div style={{ fontFamily: 'var(--font-display)', fontSize: 20, fontStyle: 'italic', color: 'var(--ink-3)' }}>
                  ← pick a name
                </div>
                <p style={{ fontSize: 14.5, color: 'var(--ink-3)', marginTop: 8 }}>
                  You’ll see its full 37-model panel, the fact sheet it was graded against, and —
                  for 359 sampled entities — the models’ verbatim answers.
                </p>
              </div>
            )}
        </div>
      </div>
    </div>
  )
}

/* ————————————————— case viewer (trajectory visualizer) ————————————————— */

const JUDGE_LABEL = { gemini: 'Gemini judge (primary)', claude: 'Claude judge', gpt: 'GPT judge' }

function JudgePanel({ judges }) {
  return (
    <div className="judge-grid">
      {Object.entries(judges).map(([name, j]) => (
        <div key={name} className="judge-cell">
          <div className="tag" style={{ marginBottom: 8 }}>{JUDGE_LABEL[name] ?? name}</div>
          <div className="judge-bars">
            {[['coverage', j.cov, 'var(--person)'], ['accuracy', j.acc, 'var(--good)']].map(([l, v, col]) => (
              <div key={l} className="judge-bar-row">
                <span className="tag" style={{ width: 74 }}>{l}</span>
                <span className="judge-track"><span style={{ width: `${v * 100}%`, background: col }} /></span>
                <span className="num" style={{ fontSize: 12 }}>{fmt(v, 2)}</span>
              </div>
            ))}
          </div>
          <div className="num" style={{ fontSize: 14, margin: '8px 0' }}>
            score <b style={{ fontSize: 17 }}>{fmt(j.score, 2)}</b>
          </div>
          {j.rationale && j.rationale !== 'refusal' && (
            <div className="judge-rationale">“{j.rationale}”</div>
          )}
        </div>
      ))}
    </div>
  )
}

function CaseDetail({ c, onPrev, onNext, hasPrev, hasNext }) {
  const [showGold, setShowGold] = useState(false)
  const kind = classifyCase(c)
  useEffect(() => setShowGold(false), [c.i])
  return (
    <div className="case-detail card" key={c.i}>
      <div className="case-detail-head">
        <div>
          <div className="tag">{COHORT_NAME[c.cohort]} · NameRank {fmt(c.nr)}</div>
          <h4 style={{ fontSize: 23, margin: '4px 0 2px' }}>
            {c.name} <span style={{ color: 'var(--ink-3)', fontWeight: 400 }}>×</span> {modelLabel(c.model)}
          </h4>
          <span className="kind-badge" style={{ color: CASE_KIND_META[kind].color, borderColor: 'currentColor' }}>
            {CASE_KIND_META[kind].label}
          </span>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn" disabled={!hasPrev} onClick={onPrev} style={{ opacity: hasPrev ? 1 : 0.4 }}>←</button>
          <button className="btn" disabled={!hasNext} onClick={onNext} style={{ opacity: hasNext ? 1 : 0.4 }}>→</button>
        </div>
      </div>
      <div style={{ padding: '16px 22px 22px' }}>
        <div className="tag" style={{ marginBottom: 8 }}>The question</div>
        <div className="probe-box" style={{ fontSize: 13 }}>
          Tell me what you know about <span className="chip-person">{c.name}</span>, who is{' '}
          <span className="probe-ctx">{c.context}</span>…
        </div>
        <div className="tag" style={{ margin: '16px 0 8px' }}>The model’s answer, verbatim</div>
        <div className={`response-box ${c.refusal ? 'is-refusal' : ''}`}>
          {c.response ? <MiniMd text={c.response} /> : '(empty response)'}
        </div>
        <button className="btn" style={{ margin: '14px 0' }} onClick={() => setShowGold(!showGold)}>
          {showGold ? 'Hide' : 'Compare with'} the fact sheet
        </button>
        {showGold && <div className="gold-box" style={{ marginTop: 0, marginBottom: 14 }}>{c.gold}</div>}
        <div className="tag" style={{ margin: '6px 0 10px' }}>
          Three independent judges graded this same answer
        </div>
        <JudgePanel judges={c.judges} />
      </div>
    </div>
  )
}

function CaseViewer({ cases, selCase, setSelCase }) {
  const [kind, setKind] = useState('all')
  const [model, setModel] = useState('all')
  const [q, setQ] = useState('')
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
    // keep selected row visible
    const el = listRef.current?.querySelector('.on')
    el?.scrollIntoView({ block: 'nearest' })
  }, [selCase])

  if (!cases) return <div className="chart-note" style={{ padding: 40 }}>loading 615 graded answers…</div>

  const counts = { all: enriched.length }
  enriched.forEach(({ kind: k }) => { counts[k] = (counts[k] ?? 0) + 1 })

  return (
    <div>
      <div className="ex-controls">
        <input className="search" placeholder="Search a name…" value={q} onChange={(e) => setQ(e.target.value)} />
        <select className="search" value={model} onChange={(e) => setModel(e.target.value)}>
          <option value="all">All models</option>
          {modelsInCases.map((m) => <option key={m} value={m}>{modelLabel(m)}</option>)}
        </select>
        <div className="seg">
          {['all', 'recognized', 'partial', 'hallucination', 'refusal'].map((k) => (
            <button key={k} className={kind === k ? 'on' : ''} onClick={() => setKind(k)}>
              {k === 'all' ? `All ${counts.all}` : `${CASE_KIND_META[k].label} ${counts[k] ?? 0}`}
            </button>
          ))}
        </div>
      </div>
      <div className="tag" style={{ margin: '12px 2px' }}>
        <b>{rows.length}</b> graded answers · each was independently re-scored by three judge models
      </div>
      <div className="ex-split">
        <div className="ent-list" ref={listRef}>
          {rows.slice(0, 400).map(({ c, kind: k }) => (
            <button key={c.i} className={`ent-row case-row ${current?.i === c.i ? 'on' : ''}`} onClick={() => setSelCase(c.i)}>
              <span className="ent-name">{c.name}</span>
              <span className="ent-cohort tag">{modelLabel(c.model)}</span>
              <span className="kind-dot" style={{ background: CASE_KIND_META[k].color }} />
              <span className="num" style={{ fontSize: 12.5, minWidth: 34, textAlign: 'right' }}>{fmt(c.judges.gemini.score)}</span>
            </button>
          ))}
        </div>
        <div className="ent-side">
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

/* ————————————————— section shell ————————————————— */

const TABS = [
  { key: 'entities', label: 'Browse 5,719 entities' },
  { key: 'cases', label: 'Read real graded answers' },
  { key: 'heatmap', label: 'The whole grid at once' },
]

export default function Explorer() {
  const [visible, setVisible] = useState(false)
  const [tab, setTab] = useState('entities')
  const [selCase, setSelCase] = useState(null)
  const [pickedCohort, setPickedCohort] = useState(null)
  const [pickKey, setPickKey] = useState(0)
  const rootRef = useRef(null)

  useEffect(() => {
    const io = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) { setVisible(true); io.disconnect() } },
      { rootMargin: '600px' },
    )
    if (rootRef.current) io.observe(rootRef.current)
    return () => io.disconnect()
  }, [])

  const entities = useData('entities.json', visible)
  const matrix = useData('matrix.json', visible)
  const cases = useData('cases.json', visible)

  const openCase = (i) => { setSelCase(i); setTab('cases'); rootRef.current?.scrollIntoView({ behavior: 'smooth' }) }
  const pickCohort = (slug) => { setPickedCohort(slug); setPickKey((k) => k + 1); setTab('entities') }

  return (
    <section className="section" id="explorer" ref={rootRef}>
      <div className="wrap-wide">
        <Reveal>
          <div className="section-kicker">
            <span className="rule" />
            <span className="tag">Section 03 · The evidence, unabridged</span>
          </div>
          <h2 className="section-title">Explore every test case yourself</h2>
          <p className="section-lede">
            Don’t take the charts’ word for it. Every entity, every model score, and hundreds of
            verbatim model answers with their judge verdicts are browsable below.
          </p>
        </Reveal>

        <div className="ex-tabs">
          {TABS.map((t) => (
            <button key={t.key} className={`ex-tab ${tab === t.key ? 'on' : ''}`} onClick={() => setTab(t.key)}>
              {t.label}
            </button>
          ))}
        </div>

        {tab === 'entities' && (
          <EntityBrowser
            entities={entities} matrix={matrix} cases={cases}
            onOpenCase={openCase} initialCohort={pickedCohort} pickKey={pickKey}
          />
        )}
        {tab === 'cases' && <CaseViewer cases={cases} selCase={selCase} setSelCase={setSelCase} />}
        {tab === 'heatmap' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12, margin: '4px 2px 14px' }}>
              <div className="tag">54 cohorts × 37 models — every cell is the mean over a cohort’s entities. Click a cohort name to browse it.</div>
              <RampLegend />
            </div>
            <div className="card" style={{ padding: 16 }}>
              <Heatmap data={heatmapData} cohortNames={COHORT_NAME} onPick={pickCohort} />
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
