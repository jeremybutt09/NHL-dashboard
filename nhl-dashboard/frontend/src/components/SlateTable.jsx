import GameRow from './GameRow';

const GRID = '120px minmax(280px, 1.1fr) minmax(360px, 1.4fr) 160px 110px 110px';

function SkeletonRow() {
  return (
    <div style={{ borderBottom: '1px solid var(--rule)' }}>
      <div className="slate-table-row" style={{ padding: '18px 24px' }}>
        {[40, 100, 160, 80, 50, 36].map((w, i) => (
          <div
            key={i}
            className="bar-shimmer"
            style={{
              height: 24,
              width: w,
              borderRadius: 6,
              background: 'var(--rule)',
              position: 'relative',
              overflow: 'hidden',
            }}
          />
        ))}
      </div>
    </div>
  );
}

export default function SlateTable({ games = [], loading = false, state, density, book, market, history = {}, filterActive = false }) {
  const header = (
    <div style={{
      display: 'grid',
      gridTemplateColumns: GRID,
      gap: 24,
      padding: '12px 24px',
      borderBottom: '1px solid var(--rule)',
      background: 'var(--paper)',
      position: 'sticky', top: 0, zIndex: 1,
    }}>
      {[
        { label: 'Status' },
        { label: 'Matchup · Score' },
        { label: 'Moneyline · Implied Win %' },
        { label: 'Line movement (24h)' },
        { label: 'Edge ↓', textAlign: 'right' },
        { label: 'Details', textAlign: 'right' },
      ].map(({ label, textAlign }) => (
        <div key={label} style={{
          fontSize: 10, fontWeight: 600, color: 'var(--faint)',
          letterSpacing: '0.08em', textTransform: 'uppercase',
          textAlign,
        }}>
          {label}
        </div>
      ))}
    </div>
  );

  return (
    <div style={{
      background: 'var(--paper)',
      border: '1px solid var(--rule)',
      borderRadius: 12,
      overflow: 'visible',
      boxShadow: 'var(--shadow)',
    }}>
      {header}
      <div style={{ overflow: 'hidden', borderRadius: '0 0 12px 12px' }}>
        {loading && games.length === 0 ? (
          [0, 1, 2].map((i) => <SkeletonRow key={i} />)
        ) : games.length === 0 ? (
          <div style={{
            padding: '48px 24px',
            textAlign: 'center',
            color: 'var(--muted)',
            fontSize: 14,
          }}>
            {filterActive ? 'No games match this filter' : 'No games scheduled today'}
          </div>
        ) : (
          games.map((g) => (
            <GameRow
              key={g.id}
              g={g}
              state={state}
              series={(history[g.id]?.consensus || []).map((p) => p.ipA)}
              density={density}
              book={book}
              market={market}
            />
          ))
        )}
      </div>
    </div>
  );
}
