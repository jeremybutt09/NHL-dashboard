// FilterBar — "Tonight's slate" heading + market tabs + sort button + odds selector
const MARKETS = [
  { id: 'h2h',     label: 'Moneyline' },
  { id: 'spreads', label: 'Puck Line' },
  { id: 'totals',  label: 'Total (O/U)' },
]

// Stub odds partners — real provider integration is out of v1 scope (HANDOFF.md §7)
const PARTNERS = [
  { id: 'consensus', name: 'Consensus', short: 'AVG', color: '#1ba1b8' },
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

function OddsPartnerSelector({ book, onChange }) {
  const current = PARTNERS.find(p => p.id === book) || PARTNERS[0]
  return (
    <button
      onClick={() => {}}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 8,
        padding: '6px 12px 6px 10px',
        background: 'var(--paper)',
        border: '1px solid var(--rule)',
        borderRadius: 8,
        fontSize: 12, fontWeight: 500, color: 'var(--ink)',
        cursor: 'default',
        boxShadow: 'var(--shadow)',
      }}>
      <span style={{ fontSize: 10, color: 'var(--faint)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Odds</span>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
        <span style={{ width: 8, height: 8, borderRadius: '50%', background: current.color }} />
        <span style={{ fontWeight: 600 }}>{current.name}</span>
      </span>
      <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.6" style={{ color: 'var(--faint)' }}>
        <path d="M2.5 4l2.5 2.5L7.5 4"/>
      </svg>
    </button>
  )
}

export function FilterBar({ numGames, totalGames, liveCount, market, onMarketChange, day }) {
  const todayKey = () => {
    const d = new Date()
    return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
  }
  const tomorrowKey = () => {
    const d = new Date(); d.setDate(d.getDate() + 1)
    return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
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
        <OddsPartnerSelector book="consensus" onChange={() => {}} />
      </div>
    </div>
  )
}
