import React from 'react'
import { Reveal, pct, fmt, signed } from '../lib/ui.jsx'
import {
  CohortAxis, LadderBars, CareerArc, Dumbbell, MedalTiers,
  DecileLadder, TwoBar, IntervalDots, Meter,
} from '../components/charts.jsx'
import stats from '../data/stats.json'
import cohorts from '../data/cohorts.json'
import ladder from '../data/ladder.json'
import awards from '../data/awards.json'
import inversion from '../data/inversion.json'
import noi from '../data/noi.json'
import bibliometrics from '../data/bibliometrics.json'
import geography from '../data/geography.json'
import events from '../data/events.json'

/* small readout tile — mono stat over a one-line gloss */
function Tile({ s, v, l, c }) {
  return (
    <div className="readout">
      <div className="rs">{s}</div>
      <div className="rv" style={c ? { color: c } : undefined}>{v}</div>
      <div className="rl">{l}</div>
    </div>
  )
}

/* mono finding kicker + serif sub-title */
function FHead({ tag, tone = 'signal', title }) {
  return (
    <>
      <div className={`tag tag--${tone}`} style={{ marginBottom: 10 }}>{tag}</div>
      <h3 style={{ marginBottom: 14 }}>{title}</h3>
    </>
  )
}

/* the marquee awards, for the F2 readout */
const NOBEL = awards.entries.find((e) => e.key === 'nobel')
const TURING = awards.entries.find((e) => e.key === 'turing')
const FIELDS = awards.entries.find((e) => e.key === 'fields')

/* institutions, citation-matched — reshaped for IntervalDots */
const INST = [
  { country: 'MIT', mean: geography.institutions.mit.matched },
  { country: 'Berkeley', mean: geography.institutions.berkeley.matched },
  { country: 'UC Irvine', mean: geography.institutions.irvine.matched },
  { country: 'UC San Diego', mean: geography.institutions.ucsd.matched },
]

const GOLD = noi.tiers.gold, SILVER = noi.tiers.silver, BRONZE = noi.tiers.bronze

export default function Findings() {
  return (
    <section id="findings" className="section">
      <div className="wrap">
        {/* ── section intro ─────────────────────────────────────────── */}
        <div className="sec-head">
          <span className="sec-idx">02</span>
          <h2 className="sec-title">What the instrument records</h2>
        </div>
        <Reveal className="lede sec-kicker">
          One rule explains almost everything the panel does. Recognition attaches to{' '}
          <span className="u-artifact">named, indexable artifacts</span> — a tool, a method,
          a paper the corpus repeats — and only reaches the{' '}
          <span className="u-person">people</span> behind them when their own name became one.
          Seven findings, each on the same 0-to-1 scale.
        </Reveal>

        {/* ── F1 · credentials ──────────────────────────────────────── */}
        <Reveal style={{ marginTop: 'clamp(48px, 7vw, 96px)' }}>
          <FHead tag="F1 · CREDENTIALS" title="Every credential sits below a working researcher." />
          <p className="ink-2" style={{ maxWidth: '60ch' }}>
            Put all {stats.cohorts} cohorts on one axis and the credentialed ones land in the
            silent zone — beneath the {stats.baseline.toFixed(2)} baseline of an anonymous
            OpenAlex researcher. A medal certifies a person but ships no named artifact, so it
            propagates almost nothing through the channel.
          </p>
        </Reveal>

        <Reveal className="panel panel--pad" delay={80} style={{ marginTop: 24 }}>
          <div className="panel-head">
            <span className="panel-title">Everything on one recognition scale</span>
            <span className="tag">{stats.cohorts} COHORTS · {stats.entities.toLocaleString()} ENTITIES</span>
          </div>
          <CohortAxis cohorts={cohorts} floor={0.02} highlight={['imo_gold', 'putnam_fellow', 'icpc_world_finals_gold']} />
          <p className="caption">
            Highlighted: three elite olympiad and contest credentials. Even the strongest of them
            (<b>Putnam top-25</b>, {ladder.rows[0].mean.toFixed(2)}) never reaches the discriminative
            band where named artifacts live.
          </p>
        </Reveal>

        <div className="grid grid-2" style={{ marginTop: 24, alignItems: 'start' }}>
          <Reveal className="panel panel--pad">
            <div className="panel-head"><span className="panel-title">Nine credentials vs the baseline</span></div>
            <LadderBars rows={ladder.rows} baseline={ladder.baseline.mean} floor={ladder.floor} />
            <p className="caption">
              Each blue bar is one olympiad, fellowship or scholarship cohort. Every one falls short
              of the dashed working-researcher line.
            </p>
          </Reveal>
          <Reveal delay={80} style={{ display: 'grid', gap: 'clamp(14px,1.6vw,22px)', alignContent: 'start' }}>
            <Tile s="TOP CREDENTIAL" v={pct(ladder.rows[0].mean, 0)} l="Putnam top-25 — still under the 40% baseline" c="var(--person)" />
            <Tile s="IMO GOLD" v={pct(0.12, 0)} l={`n=197 gold medallists · ${signed(-0.276)} vs baseline`} c="var(--person)" />
            <Tile s="WEAKEST" v={pct(0.028, 0)} l="CPhO China first prize — essentially the null floor" c="var(--person)" />
          </Reveal>
        </div>

        {/* ── F2 · marquee ──────────────────────────────────────────── */}
        <Reveal style={{ marginTop: 'clamp(56px, 8vw, 110px)' }}>
          <FHead tag="F2 · THE TREADMILL INVERTS" title="…but at the marquee tier the ladder flips." />
          <p className="ink-2" style={{ maxWidth: '62ch' }}>
            This is the organising result. Sort a whole career by honour and the curve reverses:
            olympiad credentials sit at the floor, named papers and methods cross the baseline, and
            the marquee prizes saturate the panel — because a lifetime of named production, not the
            prize itself, is what the corpus already carries.
          </p>
        </Reveal>

        <Reveal className="panel panel--pad" delay={80} style={{ marginTop: 24 }}>
          <div className="panel-head">
            <span className="panel-title">From olympiad medal to Nobel — one career axis</span>
            <span className="tag">RECOGNITION VS HONOUR TIER</span>
          </div>
          <CareerArc entries={awards.entries} baseline={awards.baseline} floor={awards.floor} />
          <p className="caption">
            Blue = early credentials, phosphor = named papers and methods, amber = mid-career and
            marquee prizes. The instrument is monotone in <b>named output</b>, not in prestige.
          </p>
        </Reveal>

        <div className="grid grid-3" style={{ marginTop: 24 }}>
          <Reveal><Tile s="NOBEL (PHYSICS)" v={pct(NOBEL.mean, 0)} l={`saturates the panel · ${signed(NOBEL.vsBaseline)} vs baseline`} c="var(--artifact)" /></Reveal>
          <Reveal delay={60}><Tile s="TURING AWARD" v={pct(TURING.mean, 0)} l={`${signed(TURING.vsBaseline)} vs baseline`} c="var(--artifact)" /></Reveal>
          <Reveal delay={120}><Tile s="FIELDS MEDAL" v={pct(FIELDS.mean, 0)} l={`${signed(FIELDS.vsBaseline)} vs baseline`} c="var(--artifact)" /></Reveal>
        </div>

        {/* ── F3 · inversion ────────────────────────────────────────── */}
        <Reveal style={{ marginTop: 'clamp(56px, 8vw, 110px)' }}>
          <FHead tag="F3 · INVERSION" title="The tool out-ranks its maker." />
          <p className="ink-2" style={{ maxWidth: '62ch' }}>
            Pair a well-known artifact with the person who built it and, in 7 of 10 pairs, the
            artifact wins. The reinforcement-learning library <span className="u-artifact">Tianshou</span> scores {inversion[0].nrArtifact.toFixed(2)} while
            its sole author <span className="u-person">Jiayi Weng</span> sits at {inversion[0].nrCreator.toFixed(2)} — the work propagated; the name behind it did not.
          </p>
        </Reveal>

        <div className="grid grid-2" style={{ marginTop: 24, alignItems: 'start' }}>
          <Reveal className="panel panel--pad">
            <div className="panel-head"><span className="panel-title">Creator → artifact, ten pairs</span></div>
            <Dumbbell pairs={inversion} />
            <p className="caption">
              Blue dot = the person, amber dot = the thing they made. When amber lies to the right,
              recognition attached to the artifact and only partly reached its maker.
            </p>
          </Reveal>
          <Reveal delay={80} className="panel panel--pad">
            <div className="panel-head"><span className="panel-title">You cannot prompt recognition into being</span></div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 18, marginBottom: 16 }}>
              <div className="num" style={{ fontSize: '2.6rem', lineHeight: 1, color: 'var(--signal)' }}>{signed(stats.injectionLift)}</div>
              <div className="tag" style={{ fontSize: '0.62rem' }}>Δ RECOGNITION FROM<br />NAMING THE CREATOR</div>
            </div>
            <p className="ink-2" style={{ fontSize: '0.92rem', maxWidth: 'none' }}>
              Tell a model outright that a person built a famous artifact and its recognition of the
              person moves by {signed(stats.injectionLift)} — statistically nothing. Recognition is a
              property of the corpus, not of the prompt: it can be measured but not manufactured.
            </p>
          </Reveal>
        </div>

        {/* ── F4 · medal grade ──────────────────────────────────────── */}
        <Reveal style={{ marginTop: 'clamp(56px, 8vw, 110px)' }}>
          <FHead tag="F4 · MEDAL GRADE" tone="signal" title="Within one contest, the grade barely matters." />
          <p className="ink-2" style={{ maxWidth: '62ch' }}>
            Split a single olympiad (China's NOI) into gold, silver and bronze and the gradient nearly
            vanishes. Gold ({GOLD.mean.toFixed(3)}) just clears the ~0 floor; silver ({SILVER.mean.toFixed(3)})
            and bronze ({BRONZE.mean.toFixed(3)}) are indistinguishable. The few who are recognised are
            those whose later careers produced named work.
          </p>
        </Reveal>

        <div className="grid grid-2" style={{ marginTop: 24, alignItems: 'start' }}>
          <Reveal className="panel panel--pad">
            <div className="panel-head"><span className="panel-title">NOI gold · silver · bronze</span></div>
            <MedalTiers tiers={noi.tiers} scatter={noi.scatter} floor={noi.floor} />
            <p className="caption">
              Each dot is one medallist; the vertical rule is the tier mean. Gold edges silver, but
              silver and bronze overlap almost completely.
            </p>
          </Reveal>
          <Reveal delay={80} className="panel panel--pad" style={{ display: 'grid', gap: 22, alignContent: 'center' }}>
            <div className="panel-head" style={{ marginBottom: 0 }}><span className="panel-title">Share recognised by any model</span></div>
            <Meter value={GOLD.recognizedAny / GOLD.n} color="#d9a520" label={`gold · ${GOLD.recognizedAny}/${GOLD.n}`} />
            <Meter value={SILVER.recognizedAny / SILVER.n} color="#9aa7b4" label={`silver · ${SILVER.recognizedAny}/${SILVER.n}`} />
            <Meter value={BRONZE.recognizedAny / BRONZE.n} color="#b5764a" label={`bronze · ${BRONZE.recognizedAny}/${BRONZE.n}`} />
            <p className="caption" style={{ marginTop: 0 }}>
              Even &ldquo;recognised by <b>at least one</b> of {stats.models} models&rdquo; barely separates the tiers.
            </p>
          </Reveal>
        </div>

        {/* ── F5 · bibliometrics + geography ────────────────────────── */}
        <Reveal style={{ marginTop: 'clamp(56px, 8vw, 110px)' }}>
          <FHead tag="F5 · METRICS & GEOGRAPHY" title="No bibliometric stands in for recognition." />
          <p className="ink-2" style={{ maxWidth: '62ch' }}>
            Recognition does rise with the h-index — but weakly. An h-index model explains
            R²={fmt(stats.hindex.r2H, 3)} of the variance and raw citations {fmt(stats.hindex.r2Cites, 2)}; they
            tie, and roughly three-quarters of the variance is left unexplained. What remains is not
            output but corpus density: where a name gets written about.
          </p>
        </Reveal>

        <div className="grid grid-2" style={{ marginTop: 24, alignItems: 'start' }}>
          <Reveal className="panel panel--pad">
            <div className="panel-head"><span className="panel-title">Recognition by h-index decile</span></div>
            <DecileLadder rows={bibliometrics.deciles} xKey="decile" yKey="mean" xLabel="h-index decile" accent="var(--person)" fmtX={(d) => `h≈${d.h}`} />
            <div className="legend" style={{ marginTop: 16 }}>
              <span className="dot-key"><i style={{ background: 'var(--person)' }} />h-index R² <b className="num" style={{ color: 'var(--ink)', marginLeft: 4 }}>{fmt(stats.hindex.r2H, 3)}</b></span>
              <span className="dot-key"><i style={{ background: 'var(--ink-3)' }} />raw citations R² <b className="num" style={{ color: 'var(--ink)', marginLeft: 4 }}>{fmt(stats.hindex.r2Cites, 2)}</b></span>
            </div>
            <p className="caption">A real gradient, but a shallow one — n={bibliometrics.n} researchers.</p>
          </Reveal>
          <Reveal delay={80} className="panel panel--pad">
            <div className="panel-head"><span className="panel-title">Same output, different corpus</span></div>
            <IntervalDots rows={geography.countries} valueKey="mean" labelKey="country" baseline={stats.baseline} />
            <p className="caption" style={{ marginBottom: 18 }}>
              CS faculty by country. <b>USA</b> {pct(geography.countries[0].mean, 0)} (n={geography.countries[0].n})
              leads <b>China</b> {pct(0.326, 0)} and <b>India</b> {pct(0.258, 0)} — the same academic output, a denser English-language footprint.
            </p>
            <div className="panel-head" style={{ marginTop: 8 }}><span className="tag">CITATION-MATCHED INSTITUTIONS</span></div>
            <IntervalDots rows={INST} valueKey="mean" labelKey="country" />
            <p className="caption">
              Even after matching on citations, <b>MIT</b> ({geography.institutions.mit.matched.toFixed(2)}, down
              from a raw {geography.institutions.mit.raw.toFixed(2)}) still outranks <b>UC Irvine</b> — prestige of place, not measured productivity.
            </p>
          </Reveal>
        </div>

        {/* ── F6 · events ───────────────────────────────────────────── */}
        <Reveal style={{ marginTop: 'clamp(56px, 8vw, 110px)' }}>
          <FHead tag="F6 · NEWS EVENTS" title="For events, loudness beats endurance." />
          <p className="ink-2" style={{ maxWidth: '62ch' }}>
            The pattern generalises past people. Across {events.n} news events, recognition climbs
            cleanly with peak coverage — from {pct(events.deciles[0].meanNr, 0)} in the quietest decile
            to {pct(events.deciles[events.deciles.length - 1].meanNr, 0)} in the loudest. A name is
            minted by the high-water mark of attention, not by how long the story ran.
          </p>
        </Reveal>

        <div className="grid grid-2" style={{ marginTop: 24, alignItems: 'start' }}>
          <Reveal className="panel panel--pad">
            <div className="panel-head"><span className="panel-title">Recognition by pageview decile</span></div>
            <DecileLadder rows={events.deciles} xKey="decile" yKey="meanNr" xLabel="pageview decile" accent="var(--signal)" fmtX={(d) => `${d.geomeanViews.toLocaleString()} views`} />
            <p className="caption">A clean dose-response: more peak coverage, more recognition.</p>
          </Reveal>
          <Reveal delay={80} className="panel panel--pad" style={{ display: 'grid', alignContent: 'center', gap: 20 }}>
            <div className="panel-head" style={{ marginBottom: 0 }}><span className="panel-title">Peak salience vs duration</span></div>
            <TwoBar
              items={[
                { label: 'Peak salience', value: events.stdCoef.peak, color: 'var(--signal)' },
                { label: 'Duration', value: events.stdCoef.duration, color: 'var(--ink-3)' },
              ]}
              max={0.16}
            />
            <p className="caption" style={{ marginTop: 0 }}>
              Standardised coefficients in a joint model. Peak dominates (R²={fmt(events.r2.peak, 2)});
              duration is effectively inert (R²={fmt(events.r2.duration, 3)}).
            </p>
          </Reveal>
        </div>

        {/* ── F7 · self-report teaser ───────────────────────────────── */}
        <Reveal style={{ marginTop: 'clamp(56px, 8vw, 110px)' }}>
          <FHead tag="F7 · SELF-REPORT" tone="signal" title="Asking a model what it knows is not measuring it." />
          <p className="ink-2" style={{ maxWidth: '62ch' }}>
            One tempting shortcut fails outright. A model's aggregate self-reported familiarity tracks
            shared fame at ρ≈{fmt(stats.selfreport.rhoAggregate, 2)} — but tracks its <em>own</em> demonstrated
            knowledge at ρ≈{fmt(stats.selfreport.rhoOwnKnown, 2)}. Introspection reads the corpus prior everyone
            shares, not the weights of the model doing the reporting.
          </p>
        </Reveal>

        <div className="grid grid-2" style={{ marginTop: 24 }}>
          <Reveal><Tile s="TRACKS SHARED FAME" v={`ρ ${fmt(stats.selfreport.rhoAggregate, 2)}`} l="self-report vs the panel's collective recognition" c="var(--person)" /></Reveal>
          <Reveal delay={80}><Tile s="TRACKS OWN KNOWLEDGE" v={`ρ ${fmt(stats.selfreport.rhoOwnKnown, 2)}`} l="self-report vs what that same model actually gets right" c="var(--artifact)" /></Reveal>
        </div>
        <Reveal delay={120} style={{ marginTop: 18 }}>
          <p className="ink-3" style={{ fontSize: '0.92rem' }}>
            The <a href="#robustness" className="c-signal" style={{ borderBottom: '1px solid var(--signal)' }}>robustness section</a> takes
            this apart in depth — across judges, probe phrasings and the full per-model breakdown.
          </p>
        </Reveal>

        {/* ── thesis restatement ────────────────────────────────────── */}
        <Reveal style={{ marginTop: 'clamp(56px, 8vw, 110px)' }}>
          <p className="serif" style={{ fontSize: 'clamp(1.5rem, 3vw, 2.3rem)', lineHeight: 1.2, maxWidth: '24ch', color: 'var(--ink)' }}>
            Across all seven, one verdict holds: the model knows your{' '}
            <em style={{ color: 'var(--artifact)', fontStyle: 'italic' }}>project</em>, not{' '}
            <em style={{ color: 'var(--person)', fontStyle: 'italic' }}>you</em>.
          </p>
        </Reveal>
      </div>
    </section>
  )
}
