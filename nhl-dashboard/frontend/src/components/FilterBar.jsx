import { useState, useRef, useEffect } from 'react'

// FilterBar — "Tonight's slate" heading + market tabs + sort button + odds selector
const MARKETS = [
  { id: 'h2h',     label: 'Moneyline' },
  { id: 'spreads', label: 'Puck Line' },
  { id: 'totals',  label: 'Total (O/U)' },
]

function SegmentButton({ label, value }) {
  return (
    <button style={{
      display: 'inline-flex', alignItems: 'center', gap: 8,
      padding: '6px 12px',
      background: 'var(--paper)',
      border: '1px solid var(--rule)',
      borderRadius: 8,
      fontSize: 12, fontWeight: 500, color: 'var(--ink)',
      cursor: 'pointer',
      boxShadow: 'var(--shadow)',
    }}>
      <span style={{ color: 'var(--faint)' }}>{label}</span>
      <span>{value}</span>
      <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.6">
        <path d="M2.5 4l2.5 2.5L7.5 4"/>
      </svg>
    </button>
  )
}

function OddsPartnerSelector({ partners, partnerId, onChange }) {
  if (!partners || partners.length === 0) return null
  const current = partners.find(p => p.partner_id === partnerId) || partners[0]
  const [open, setOpen] = useState(false)
  const containerRef = useRef(null)

  useEffect(() => {
    const onDoc = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  return (
    <div ref={containerRef} style={{ position: 'relative', display: 'inline-flex' }}>
      {/* Trigger pill */}
      <button
        onClick={() => setOpen(o => !o)}
        onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--rule-strong)' }}
        onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--rule)' }}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          padding: '6px 10px',
          background: 'var(--paper)',
          border: '1px solid var(--rule)',
          borderRadius: 8,
          fontSize: 12, fontWeight: 600, color: 'var(--ink)',
          cursor: 'pointer',
          boxShadow: 'var(--shadow)',
          fontFamily: 'inherit',
        }}
      >
        <span style={{ fontSize: 10, color: 'var(--faint)', letterSpacing: '0.08em', textTransform: 'uppercase', marginRight: 2 }}>
          Odds
        </span>
        <span style={{ width: 10, height: 10, borderRadius: '50%', background: current.bg_color, flexShrink: 0 }} />
        <span>{current.name}</span>
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.6"
             style={{ color: 'var(--faint)', marginLeft: 2 }}>
          <path d="M2.5 4l2.5 2.5L7.5 4"/>
        </svg>
      </button>

      {/* Dropdown panel */}
      {open && (
        <div style={{
          position: 'absolute', top: 'calc(100% + 6px)', right: 0,
          minWidth: 180,
          background: 'var(--paper)',
          border: '1px solid var(--rule)',
          borderRadius: 10,
          boxShadow: 'var(--shadow-lg)',
          zIndex: 50,
          overflow: 'hidden',
        }}>
          <div style={{
            padding: '8px 12px 6px',
            fontSize: 10, fontWeight: 700, color: 'var(--faint)',
            letterSpacing: '0.08em', textTransform: 'uppercase',
          }}>
            ODDS SOURCE
          </div>
          <div style={{ borderTop: '1px solid var(--rule)', marginBottom: 4 }} />
          {partners.map(p => {
            const active = p.partner_id === (partnerId ?? partners[0].partner_id)
            return (
              <div
                key={p.partner_id}
                role="option"
                aria-selected={active}
                onClick={() => { onChange(p.partner_id); setOpen(false) }}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '7px 12px',
                  fontSize: 12, fontWeight: active ? 600 : 400,
                  color: 'var(--ink)',
                  background: active ? 'color-mix(in oklab, var(--accent) 8%, transparent)' : 'transparent',
                  cursor: 'pointer',
                  userSelect: 'none',
                }}
                onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'color-mix(in oklab, var(--accent) 8%, transparent)' }}
                onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent' }}
              >
                <span style={{ width: 10, height: 10, borderRadius: '50%', background: p.bg_color, flexShrink: 0 }} />
                <span style={{ flex: 1 }}>{p.name}</span>
                {active && (
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor"
                       strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                       style={{ color: 'var(--accent)' }}>
                    <path d="M2 6l3 3 5-5"/>
                  </svg>
                )}
              </div>
            )
          })}
          <div style={{ height: 4 }} />
        </div>
      )}
    </div>
  )
}

export function FilterBar({ numGames, totalGames, liveCount, market, onMarketChange, day, partners, partnerId, onPartnerChange }) {
  // en-CA locale produces YYYY-MM-DD matching game_date keys; timeZone keeps this in ET.
  const todayKey = () =>
    new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' })
  const tomorrowKey = () => {
    const etToday = new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' })
    const d = new Date(etToday + 'T12:00:00')
    d.setDate(d.getDate() + 1)
    return d.toLocaleDateString('en-CA', { timeZone: 'America/New_York' })
  }
  const formatDateLabel = (key) => {
    const d = new Date(key + 'T12:00:00')
    return d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })
  }

  const resolved = day === 'today' ? todayKey() : day === 'tomorrow' ? tomorrowKey() : (day || todayKey())
  const title = resolved === todayKey()    ? "Tonight's slate"
              : resolved === tomorrowKey() ? "Tomorrow's slate"
              : `${formatDateLabel(resolved)} slate`

  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '20px 32px 16px',
      gap: 16, flexWrap: 'wrap',
    }}>
      {/* Left: heading + count */}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 16 }}>
        <h1 style={{ margin: 0, fontSize: 26, fontWeight: 600, letterSpacing: '-0.02em' }}>
          {title}
        </h1>
        <span style={{ fontSize: 13, color: 'var(--muted)' }}>
          {numGames} of {totalGames} game{totalGames !== 1 ? 's' : ''}
          {liveCount > 0 ? ` · ${liveCount} in progress` : ''}
        </span>
      </div>

      {/* Right: market tabs + sort + odds */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        {/* Market segment */}
        <div style={{
          display: 'inline-flex', alignItems: 'center', padding: 3,
          background: 'var(--paper)', border: '1px solid var(--rule)', borderRadius: 9,
          boxShadow: 'var(--shadow)',
        }}>
          {MARKETS.map(m => {
            const active = m.id === market
            return (
              <button key={m.id} onClick={() => onMarketChange(m.id)}
                aria-pressed={active ? 'true' : 'false'}
                style={{
                padding: '5px 12px', borderRadius: 6,
                fontSize: 12, fontWeight: 600, letterSpacing: '0.01em',
                color: active ? 'white' : 'var(--muted)',
                background: active ? 'var(--accent)' : 'transparent',
                border: 'none', cursor: 'pointer', transition: 'all .15s',
              }}>
                {m.label}
              </button>
            )
          })}
        </div>
        <SegmentButton label="Sort" value="Edge ↓" />
        <OddsPartnerSelector partners={partners} partnerId={partnerId} onChange={onPartnerChange} />
      </div>
    </div>
  )
}
