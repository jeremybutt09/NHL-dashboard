import GameRow from './GameRow.jsx';

const HEADER_STYLE = {
  fontSize: 10,
  fontWeight: 600,
  color: 'var(--faint)',
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
};

const GRID_COLS = '120px minmax(280px, 1.1fr) minmax(360px, 1.4fr) 160px 110px 110px';

/**
 * Renders the full slate table: column header row + one GameRow per game.
 *
 * @param {{ games: Array, loading: boolean, error: Error|null }} props
 */
export default function SlateTable({ games, loading, error }) {
  return (
    <div>
      {/* Column header */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: GRID_COLS,
        gap: 24,
        padding: '12px 24px',
        borderBottom: '1px solid var(--rule)',
        background: 'var(--paper)',
        position: 'sticky',
        top: 57,
        zIndex: 1,
      }}>
        <div style={HEADER_STYLE}>Status</div>
        <div style={HEADER_STYLE}>Matchup · Score</div>
        <div style={HEADER_STYLE}>Moneyline · Implied Win %</div>
        <div style={HEADER_STYLE}>Line movement (24h)</div>
        <div style={{ ...HEADER_STYLE, textAlign: 'right' }}>Edge ↓</div>
        <div style={{ ...HEADER_STYLE, textAlign: 'right' }}>Details</div>
      </div>

      {/* Game rows */}
      {games && games.map((g) => (
        <GameRow key={g.id} g={g} />
      ))}
    </div>
  );
}
