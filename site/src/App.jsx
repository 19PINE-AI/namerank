import React, { useEffect, useState } from 'react'
import { DataProvider, TipProvider, useTheme } from './lib/ui.jsx'
import Hero from './sections/Hero.jsx'
import HowItWorks from './sections/HowItWorks.jsx'
import Findings from './sections/Findings.jsx'
import Explorer from './sections/Explorer.jsx'

const SECTIONS = [
  { id: 'how', label: '01 · How it works' },
  { id: 'findings', label: '02 · Findings' },
  { id: 'explorer', label: '03 · Explorer' },
]

function Nav() {
  const [dark, toggleTheme] = useTheme()
  const [active, setActive] = useState('')
  useEffect(() => {
    const els = SECTIONS.map((s) => document.getElementById(s.id)).filter(Boolean)
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) if (e.isIntersecting) setActive(e.target.id)
      },
      { rootMargin: '-30% 0px -60% 0px' },
    )
    els.forEach((el) => io.observe(el))
    return () => io.disconnect()
  }, [])
  return (
    <nav className="nav">
      <div className="wrap-wide nav-inner">
        <a className="nav-logo" href="#top">Name<span className="r">Rank</span></a>
        <div className="nav-links">
          {SECTIONS.map((s) => (
            <a key={s.id} href={`#${s.id}`} className={`nav-link ${active === s.id ? 'active' : ''}`}>
              {s.label}
            </a>
          ))}
          <a className="nav-link optional" href="https://github.com/19PINE-AI/namerank" target="_blank" rel="noreferrer">
            Paper ↗
          </a>
          <button className="nav-btn" onClick={toggleTheme} title="Toggle color theme" aria-label="Toggle color theme">
            {dark ? '☾' : '☀'}
          </button>
        </div>
      </div>
    </nav>
  )
}

function Footer() {
  return (
    <footer className="footer">
      <div className="wrap" style={{ display: 'flex', flexWrap: 'wrap', gap: 24, justifyContent: 'space-between', alignItems: 'baseline' }}>
        <div>
          <div className="tag" style={{ marginBottom: 6 }}>NameRank · 2026</div>
          <div style={{ fontSize: 15, maxWidth: '38em' }}>
            An interactive companion to the paper <i>NameRank: Measuring Entity Recognition in
            Frontier Language Models</i>. All numbers, responses, and judge verdicts on this page
            are real records from the study — nothing is mocked up.
          </div>
        </div>
        <div className="tag" style={{ lineHeight: 2 }}>
          <a href="https://github.com/19PINE-AI/namerank" target="_blank" rel="noreferrer">code &amp; data ↗</a>
          <br />
          <a href="https://01.me/research/namerank" target="_blank" rel="noreferrer">project page ↗</a>
        </div>
      </div>
    </footer>
  )
}

export default function App() {
  return (
    <DataProvider>
      <TipProvider>
        <div id="top" />
        <Nav />
        <main style={{ paddingTop: 'var(--nav-h)' }}>
          <Hero />
          <HowItWorks />
          <Findings />
          <Explorer />
        </main>
        <Footer />
      </TipProvider>
    </DataProvider>
  )
}
