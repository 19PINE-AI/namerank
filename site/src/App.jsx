import React, { useEffect, useState } from 'react'
import { ThemeProvider, DataProvider, TipProvider, useTheme } from './lib/ui.jsx'
import Hero from './sections/Hero.jsx'
import HowItWorks from './sections/HowItWorks.jsx'
import Findings from './sections/Findings.jsx'
import Robustness from './sections/Robustness.jsx'
import Explorer from './sections/Explorer.jsx'
import stats from './data/stats.json'

const SECTIONS = [
  { id: 'method', n: '01', label: 'The instrument' },
  { id: 'findings', n: '02', label: 'Findings' },
  { id: 'robustness', n: '03', label: 'Robustness' },
  { id: 'explorer', n: '04', label: 'Explorer' },
]

function SunMoon({ dark }) {
  return dark ? (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="12" r="4.2" /><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5 5l1.5 1.5M17.5 17.5L19 19M19 5l-1.5 1.5M6.5 17.5L5 19" strokeLinecap="round" /></svg>
  ) : (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5Z" strokeLinejoin="round" /></svg>
  )
}

function Nav() {
  const [dark, toggle] = useTheme()
  const [active, setActive] = useState('method')
  useEffect(() => {
    const obs = new IntersectionObserver(
      (entries) => entries.forEach((e) => { if (e.isIntersecting) setActive(e.target.id) }),
      { rootMargin: '-45% 0px -50% 0px' },
    )
    SECTIONS.forEach((s) => { const el = document.getElementById(s.id); if (el) obs.observe(el) })
    return () => obs.disconnect()
  }, [])
  return (
    <nav className="nav">
      <div className="nav-in">
        <a href="#top" className="brand"><span className="mk" />NameRank<span className="bsub tag" style={{ fontSize: '0.6rem', marginLeft: 2 }}>/ recognition instrument</span></a>
        <div className="nav-links">
          {SECTIONS.map((s) => (
            <a key={s.id} href={`#${s.id}`} className={`nfull ${active === s.id ? 'active' : ''}`}>
              <span style={{ opacity: 0.55 }}>{s.n}</span>&nbsp;{s.label}
            </a>
          ))}
        </div>
        <a className="icon-btn" href="https://github.com/19PINE-AI/namerank" target="_blank" rel="noreferrer" aria-label="GitHub" title="Code & data">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.58 2 12.25c0 4.53 2.87 8.37 6.84 9.73.5.1.68-.22.68-.49l-.01-1.7c-2.78.62-3.37-1.37-3.37-1.37-.46-1.18-1.11-1.49-1.11-1.49-.91-.64.07-.62.07-.62 1 .07 1.53 1.06 1.53 1.06.89 1.56 2.34 1.11 2.91.85.09-.66.35-1.11.63-1.36-2.22-.26-4.56-1.14-4.56-5.07 0-1.12.39-2.03 1.03-2.75-.1-.26-.45-1.3.1-2.7 0 0 .84-.28 2.75 1.05a9.4 9.4 0 0 1 5 0c1.91-1.33 2.75-1.05 2.75-1.05.55 1.4.2 2.44.1 2.7.64.72 1.03 1.63 1.03 2.75 0 3.94-2.34 4.81-4.57 5.06.36.32.68.94.68 1.9l-.01 2.82c0 .27.18.6.69.49A10.02 10.02 0 0 0 22 12.25C22 6.58 17.52 2 12 2Z" /></svg>
        </a>
        <button className="icon-btn" onClick={toggle} aria-label="Toggle theme" title="Toggle light / dark"><SunMoon dark={dark} /></button>
      </div>
    </nav>
  )
}

function Footer() {
  return (
    <footer className="footer">
      <div className="wrap wrap--wide" style={{ display: 'flex', flexWrap: 'wrap', gap: 28, justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div style={{ maxWidth: 460 }}>
          <div className="brand" style={{ marginBottom: 12 }}><span className="mk" />NameRank</div>
          <p className="ink-2" style={{ fontSize: '0.92rem' }}>
            A companion to <em>“The Model Knows Your Project, Not You: Measuring Recognition in LLMs with NameRank.”</em>{' '}
            Every number here is regenerated from the recognition-verdict run over the {stats.models}-model panel.
          </p>
        </div>
        <div style={{ display: 'grid', gap: 8, fontFamily: 'var(--mono)', fontSize: '0.82rem' }}>
          <a className="link" href="https://github.com/19PINE-AI/namerank" target="_blank" rel="noreferrer">→ Code, probes, golds & responses</a>
          <a className="link" href="https://01.me/research/namerank" target="_blank" rel="noreferrer">→ Research page</a>
          <span className="ink-3">Pine AI · University of Washington</span>
        </div>
      </div>
    </footer>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <DataProvider>
        <TipProvider>
          <span id="top" />
          <Nav />
          <main>
            <Hero />
            <HowItWorks />
            <Findings />
            <Robustness />
            <Explorer />
          </main>
          <Footer />
        </TipProvider>
      </DataProvider>
    </ThemeProvider>
  )
}
