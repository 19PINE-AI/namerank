import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'

/* ————————————————— formatting ————————————————— */
export const fmt = (v, nd = 2) => (v == null ? '—' : Number(v).toFixed(nd))
export const pct = (v, nd = 0) => (v == null ? '—' : `${(v * 100).toFixed(nd)}%`)
export const signed = (v, nd = 2) => (v == null ? '—' : (v >= 0 ? '+' : '') + Number(v).toFixed(nd))

export function modelLabel(id) {
  return id.replace(/-think$/, '').replace(/-/g, '‑')
}
export const isThinking = (id) => /-think$/.test(id)

export const LAB_LABELS = {
  openai: 'OpenAI', anthropic: 'Anthropic', google: 'Google', meta: 'Meta',
  deepseek: 'DeepSeek', alibaba: 'Alibaba', qwen: 'Alibaba', mistral: 'Mistral', xai: 'xAI',
  microsoft: 'Microsoft', zhipu: 'Zhipu', glm: 'Zhipu', baidu: 'Baidu', moonshot: 'Moonshot',
  kimi: 'Moonshot', minimax: 'MiniMax', stepfun: 'StepFun', nvidia: 'NVIDIA', nemotron: 'NVIDIA',
  gemma: 'Google', llama: 'Meta', phi: 'Microsoft',
}

/* ————————————————— color: recognition instrument —————————————————
   Semantic entity colors live as CSS vars (--person / --artifact) and are used
   directly in SVG. This module handles the two computed needs:
     • recognition MAGNITUDE ramp (silent grey → phosphor signal), for heat cells
       and bar fills, monotone in lightness so it is CVD-safe as a single hue.
     • per-category token lookup for JS-side styling. */

const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16))
const toHex = (r, g, b) => '#' + [r, g, b].map((n) => Math.round(n).toString(16).padStart(2, '0')).join('')
const lerp = (a, b, t) => a + (b - a) * t
function ramp(stops, t) {
  const x = Math.max(0, Math.min(1, t)) * (stops.length - 1)
  const i = Math.floor(x), f = x - i
  if (i >= stops.length - 1) return stops[stops.length - 1]
  const a = hex(stops[i]), b = hex(stops[i + 1])
  return toHex(lerp(a[0], b[0], f), lerp(a[1], b[1], f), lerp(a[2], b[2], f))
}
// silent → signal, validated for lightness monotonicity in each mode
const RAMP_DARK = ['#1b2029', '#243244', '#22506a', '#1d7089', '#28a58f', '#46e0b0']
const RAMP_LIGHT = ['#e7e3d6', '#bfd8c9', '#8fc6ac', '#4fae86', '#1d9670', '#0d7a58']
export const recogColor = (v, dark = false) => (v == null ? 'transparent' : ramp(dark ? RAMP_DARK : RAMP_LIGHT, v))

export const catColor = (cat) =>
  cat === 'artifact' ? 'var(--artifact)' : cat === 'credential' ? 'var(--person)' : 'var(--person)'
export const isArtifact = (cat) => cat === 'artifact'

/* ————————————————— theme (context so charts + nav stay in sync) ————————————————— */
const ThemeCtx = createContext({ dark: true, toggle: () => {} })
export function ThemeProvider({ children }) {
  const [dark, setDark] = useState(() => document.documentElement.dataset.theme !== 'light')
  const toggle = useCallback(() => {
    setDark((d) => {
      const next = !d
      document.documentElement.dataset.theme = next ? 'dark' : 'light'
      localStorage.setItem('nr-theme', next ? 'dark' : 'light')
      return next
    })
  }, [])
  return <ThemeCtx.Provider value={{ dark, toggle }}>{children}</ThemeCtx.Provider>
}
export const useTheme = () => { const { dark, toggle } = useContext(ThemeCtx); return [dark, toggle] }
export const useDark = () => useContext(ThemeCtx).dark

/* ————————————————— tooltip ————————————————— */
const TipCtx = createContext(null)
export function TipProvider({ children }) {
  const [tip, setTip] = useState(null)
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
        <div className="tip" role="tooltip"
          style={{ left: Math.max(150, Math.min(window.innerWidth - 150, tip.x)), top: Math.max(96, tip.y) }}>
          {tip.content}
        </div>
      )}
    </TipCtx.Provider>
  )
}
export const useTip = () => useContext(TipCtx)

/* ————————————————— responsive width ————————————————— */
export function useWidth() {
  const ref = useRef(null)
  const [w, setW] = useState(720)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const ro = new ResizeObserver(([e]) => setW(e.contentRect.width))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  return [ref, w]
}

/* ————————————————— lazy data store ————————————————— */
const DataCtx = createContext(null)
export function DataProvider({ children }) {
  const cache = useRef({})
  const [, force] = useState(0)
  const load = useCallback((key, path) => {
    const c = cache.current
    if (c[key]) return c[key].data ?? null
    c[key] = { data: null }
    fetch(`${import.meta.env.BASE_URL}data/${path}`)
      .then((r) => { if (!r.ok) throw new Error(`${r.status} loading ${path}`); return r.json() })
      .then((data) => { c[key].data = data; force((n) => n + 1) })
      .catch((err) => { c[key].error = err; force((n) => n + 1); console.error(err) })
    return null
  }, [])
  return <DataCtx.Provider value={{ load, cache }}>{children}</DataCtx.Provider>
}
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
  const [seen, setSeen] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setSeen(true); io.disconnect() } }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' })
    io.observe(el)
    return () => io.disconnect()
  }, [])
  return (
    <As ref={ref} className={className} style={{ opacity: seen ? 1 : 0, transform: seen ? 'none' : 'translateY(16px)', transition: `opacity .7s cubic-bezier(.2,.7,.2,1) ${delay}ms, transform .7s cubic-bezier(.2,.7,.2,1) ${delay}ms` }} {...rest}>
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
  recognized: { label: 'Recognized', color: 'var(--signal)' },
  partial: { label: 'Partial', color: 'var(--person)' },
  hallucination: { label: 'Hallucinated', color: 'var(--bad)' },
  refusal: { label: 'Said “unknown”', color: 'var(--ink-3)' },
}
export const useMemoOnce = (fn, deps) => useMemo(fn, deps) // eslint helper alias
