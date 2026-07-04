import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'

/* ————————————————— formatting ————————————————— */

export const fmt = (v, nd = 2) => (v == null ? '—' : Number(v).toFixed(nd))
export const pct = (v, nd = 0) => (v == null ? '—' : `${(v * 100).toFixed(nd)}%`)

const MODEL_LABEL_OVERRIDES = {
  'lilianweng.github.io': 'lilianweng.github.io',
}
export function modelLabel(id) {
  if (MODEL_LABEL_OVERRIDES[id]) return MODEL_LABEL_OVERRIDES[id]
  return id.replace(/-think$/, ' ✱').replace(/-/g, '‑')
}
export const isThinking = (id) => /-think$/.test(id)

export const LAB_LABELS = {
  openai: 'OpenAI', anthropic: 'Anthropic', google: 'Google', meta: 'Meta',
  deepseek: 'DeepSeek', alibaba: 'Alibaba', mistral: 'Mistral', xai: 'xAI',
  microsoft: 'Microsoft', zhipu: 'Zhipu', baidu: 'Baidu', moonshot: 'Moonshot',
}

/* ————————————————— score color ramp —————————————————
   Sequential single-hue (blue) ramp from the validated palette.
   Light mode maps score 0→1 onto steps 150→700; dark mode onto 600→150
   (lighter = higher on a dark surface). Refusals/nulls are drawn hollow. */

const RAMP = ['#cde2fb', '#b7d3f6', '#9ec5f4', '#86b6ef', '#6da7ec', '#5598e7',
  '#3987e5', '#2a78d6', '#256abf', '#1c5cab', '#184f95', '#104281', '#0d366b']

export function scoreColor(v, dark = false) {
  if (v == null) return 'transparent'
  const t = Math.max(0, Math.min(1, v))
  const idx = Math.round(t * (RAMP.length - 1))
  return dark ? RAMP[RAMP.length - 1 - idx] : RAMP[idx]
}
/* ink that stays readable on top of scoreColor */
export function scoreInk(v, dark = false) {
  const t = Math.max(0, Math.min(1, v ?? 0))
  const lightBg = dark ? t > 0.55 : t < 0.5
  return lightBg ? '#1c1712' : '#ffffff'
}

/* ————————————————— theme ————————————————— */

export function useTheme() {
  const [dark, setDark] = useState(() => document.documentElement.dataset.theme === 'dark')
  const toggle = useCallback(() => {
    setDark((d) => {
      const next = !d
      document.documentElement.dataset.theme = next ? 'dark' : ''
      localStorage.setItem('nr-theme', next ? 'dark' : 'light')
      return next
    })
  }, [])
  return [dark, toggle]
}

/* ————————————————— tooltip ————————————————— */

const TipCtx = createContext(null)

export function TipProvider({ children }) {
  const [tip, setTip] = useState(null) // {x, y, content}
  const show = useCallback((e, content) => {
    const x = e.clientX ?? e.touches?.[0]?.clientX
    const y = e.clientY ?? e.touches?.[0]?.clientY
    setTip({ x, y, content })
  }, [])
  const hide = useCallback(() => setTip(null), [])
  return (
    <TipCtx.Provider value={{ show, hide }}>
      {children}
      {tip && (
        <div
          className="tip"
          style={{
            left: Math.max(150, Math.min(window.innerWidth - 150, tip.x)),
            top: Math.max(90, tip.y),
          }}
        >
          {tip.content}
        </div>
      )}
    </TipCtx.Provider>
  )
}

export const useTip = () => useContext(TipCtx)

/* ————————————————— lazy data store —————————————————
   Large assets live in public/data and are fetched once, on demand. */

const DataCtx = createContext(null)

export function DataProvider({ children }) {
  const cache = useRef({})
  const [, force] = useState(0)

  const load = useCallback((key, path) => {
    const c = cache.current
    if (c[key]) return c[key].data ?? null
    c[key] = { data: null }
    fetch(`${import.meta.env.BASE_URL}data/${path}`)
      .then((r) => {
        if (!r.ok) throw new Error(`${r.status} loading ${path}`)
        return r.json()
      })
      .then((data) => {
        c[key].data = data
        force((n) => n + 1)
      })
      .catch((err) => {
        c[key].error = err
        force((n) => n + 1)
        console.error(err)
      })
    return null
  }, [])

  return <DataCtx.Provider value={{ load, cache }}>{children}</DataCtx.Provider>
}

/** Returns null while loading. `path` relative to public/data/. */
export function useData(path, enabled = true) {
  const { load } = useContext(DataCtx)
  const [, tick] = useState(0)
  useEffect(() => { if (enabled) tick((n) => n + 1) }, [enabled])
  if (!enabled) return null
  return load(path, path)
}

/* ————————————————— reveal on scroll ————————————————— */

export function Reveal({ children, as: As = 'div', className = '', delay = 0, ...rest }) {
  const ref = useRef(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          el.style.transitionDelay = `${delay}ms`
          el.classList.add('in')
          io.disconnect()
        }
      },
      { threshold: 0.12 },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [delay])
  return (
    <As ref={ref} className={`reveal ${className}`} {...rest}>
      {children}
    </As>
  )
}

/* ————————————————— misc ————————————————— */

export function useMedia(query) {
  const [m, setM] = useState(() => window.matchMedia(query).matches)
  useEffect(() => {
    const mq = window.matchMedia(query)
    const fn = () => setM(mq.matches)
    mq.addEventListener('change', fn)
    return () => mq.removeEventListener('change', fn)
  }, [query])
  return m
}

/* Minimal markdown: model responses use **bold** — render it instead of
   showing raw asterisks. Everything else stays plain text. */
export function MiniMd({ text }) {
  const parts = String(text).split(/\*\*(.+?)\*\*/g)
  return parts.map((p, i) => (i % 2 === 1 ? <b key={i}>{p}</b> : p))
}

export function classifyCase(c) {
  const j = c.judges.gemini
  if (c.refusal || (j.cov === 0 && j.acc === 0)) return 'refusal'
  if (j.cov >= 0.3 && j.acc <= 0.45) return 'hallucination'
  if (j.score >= 0.7) return 'recognized'
  return 'partial'
}

export const CASE_KIND_META = {
  recognized: { label: 'Recognized', color: 'var(--person)' },
  partial: { label: 'Partial', color: 'var(--artifact-ink)' },
  hallucination: { label: 'Hallucinated', color: 'var(--bad)' },
  refusal: { label: 'Said “unknown”', color: 'var(--ink-3)' },
}
