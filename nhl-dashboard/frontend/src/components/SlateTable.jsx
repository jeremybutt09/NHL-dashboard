import GameRow from './GameRow';

export default function SlateTable({ games = [], state, density, book, market, history = {} }) {
  const GRID = '120px minmax(280px, 1.1fr) minmax(360px, 1.4fr) 160px 110px 110px';
  return (
    <div style={{
      background: 'var(--paper)',
      border: '1px solid var(--rule)',
      borderRadius: 12,
      overflow: 'visible',
      boxShadow: 'var(--shadow)',
    }}>
      {/* Column header */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: GRID,
        gap: 24,
        padding: '12px 24px',
        borderBottom: '1px solid var(--rule)',
        background: 'var(--paper)',
        position: 'sticky', top: 0, zIndex: 1,
      }}>
        {['Status', 'Matchup · Score', 'Moneyline · Implied Win %', 'Line movement (24h)', 'Edge ↓', 'Details'].map((label) => (
          <div key={label} style={{
            fontSize: 10, fontWeight: 600, color: 'var(--faint)',
            letterSpacing: '0.08em', textTransform: 'uppercase',
          }}>
            {label}
          </div>
        ))}
      </div>
      {/* Game rows */}
      <div style={{ overflow: 'hidden', borderRadius: '0 0 12px 12px' }}>
        {games.map((g) => (
          <GameRow
            key={g.id}
            g={g}
            state={state}
            series={(history[g.id]?.consensus || []).map((p) => p.ipA)}
            density={density}
            book={book}
            market={market}
          />
        ))}
      </div>
    </div>
  );
}
