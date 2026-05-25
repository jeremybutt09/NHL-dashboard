import { GameRow } from './GameRow.jsx'

function InfoTip({ title, children, align = 'center', dir = 'up' }) {
  return (
    <span className="info-tip" tabIndex={0} role="button" aria-label={`What is ${title}?`}>
      <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.3" aria-hidden="true">
        <circle cx="6" cy="6" r="4.6" />
        <path d="M6 5.4v3" strokeLinecap="round" />
        <circle cx="6" cy="3.6" r="0.55" fill="currentColor" stroke="none" />
      </svg>
      <span className={`info-tip-bubble dir-${dir} align-${align}`}>
        {title && <strong>{title}</strong>}
        {children}
      </span>
    </span>
  )
}

function ColumnHeader() {
  const cellStyle = {
    fontSize: 10, fontWeight: 600, color: 'var(--faint)',
    letterSpacing: '0.08em', textTransform: 'uppercase',
  }

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '120px minmax(280px, 1.1fr) minmax(360px, 1.4fr) 160px 110px 110px',
      gap: 24,
      padding: '12px 24px',
      borderBottom: '1px solid var(--rule)',
      background: 'var(--paper)',
      position: 'sticky', top: 56, zIndex: 1,
    }}>
      <div style={cellStyle}>Status</div>
      <div style={cellStyle}>Matchup · Score</div>
      <div style={cellStyle}>
        Moneyline · Implied Win %
        <InfoTip title="Moneyline · Implied Win %" dir="down" align="left">
          The win probability the moneyline price implies for each team, after removing the book's vig so the two sides sum to 100%.
          <em>Example: MTL at −115 → 53.5% raw, ~49% after de-vig. If you think the Canadiens have a better than 49% chance to win, the moneyline favors that view.</em>
        </InfoTip>
      </div>
      <div style={cellStyle}>Line movement (24h)</div>
      <div style={{ ...cellStyle, textAlign: 'right' }}>
        Edge ↓
        <InfoTip title="Edge" align="right" dir="down">
          Gap between our fair probability and what the book's price implies. Positive (green) = price treats the team as a longer shot than the math supports.
          <em>Example: model gives MTL 47.5% chance. Book implies 45.4%. Edge = +2.1%.</em>
        </InfoTip>
      </div>
      <div style={{ ...cellStyle, textAlign: 'right' }}>Details</div>
    </div>
  )
}

export function SlateTable({ games, loading, density }) {
  return (
    <div style={{
      background: 'var(--paper)',
      border: '1px solid var(--rule)',
      borderRadius: 12,
      overflow: 'visible',
      boxShadow: 'var(--shadow)',
    }}>
      <ColumnHeader />
      <div style={{ overflow: 'hidden', borderRadius: '0 0 12px 12px' }}>
        {loading && games.length === 0 ? (
          <SkeletonRows />
        ) : games.length === 0 ? (
          <EmptyState />
        ) : (
          games.map((g) => (
            <GameRow key={g.game_id} g={g} density={density} />
          ))
        )}
      </div>
    </div>
  )
}

function SkeletonRows() {
  return (
    <>
      {[...Array(4)].map((_, i) => (
        <div key={i} style={{
          display: 'grid',
          gridTemplateColumns: '120px minmax(280px, 1.1fr) minmax(360px, 1.4fr) 160px 110px 110px',
          gap: 24, padding: '18px 24px', borderBottom: '1px solid var(--rule)',
          alignItems: 'center',
        }}>
          <div className="skeleton" style={{ height: 36, borderRadius: 6 }} />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div className="skeleton" style={{ height: 16, width: '70%' }} />
            <div className="skeleton" style={{ height: 16, width: '50%' }} />
          </div>
          <div className="skeleton" style={{ height: 22, borderRadius: 7 }} />
          <div className="skeleton" style={{ height: 32, borderRadius: 4 }} />
          <div className="skeleton" style={{ height: 28, borderRadius: 8, marginLeft: 'auto', width: 64 }} />
          <div />
        </div>
      ))}
    </>
  )
}

function EmptyState() {
  return (
    <div style={{ padding: '80px 24px', textAlign: 'center' }}>
      <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--muted)', marginBottom: 4 }}>
        No NHL games today
      </div>
      <div style={{ fontSize: 12, color: 'var(--faint)' }}>
        The NHL may be off-season or between game days.
      </div>
    </div>
  )
}
