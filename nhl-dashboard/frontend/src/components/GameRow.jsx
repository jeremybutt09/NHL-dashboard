import { useState } from 'react';
import StatusCell from './StatusCell';
import MatchupCell from './MatchupCell';
import MoneylineCell from './MoneylineCell';
import SparklineCell from './SparklineCell';
import EdgeCell from './EdgeCell';

export default function GameRow({ g, state, series, density, book, market }) {
  const padV = density === 'compact' ? 14 : density === 'comfy' ? 22 : 18;
  const [expanded, setExpanded] = useState(false);
  const toggle = () => setExpanded((v) => !v);

  const MarketCell = market === 'spreads' || market === 'totals'
    ? <MoneylineCell g={g} state={state} book={book} />
    : <MoneylineCell g={g} state={state} book={book} />;

  return (
    <div style={{ borderBottom: '1px solid var(--rule)', background: 'var(--paper)' }}>
      <div
        className="game-row slate-table-row"
        onClick={toggle}
        style={{
          padding: `${padV}px 24px`,
          background: expanded
            ? 'color-mix(in oklab, var(--paper) 92%, var(--accent) 8%)'
            : 'var(--paper)',
          cursor: 'pointer',
        }}
      >
        <StatusCell g={g} state={state} />
        <MatchupCell g={g} state={state} density={density} />
        {MarketCell}
        <SparklineCell series={series} />
        <EdgeCell edge={g.edge ?? null} />
        <button
          className="row-action icon-btn"
          aria-expanded={expanded}
          title={expanded ? 'Hide book comparison' : 'Compare books · best odds per side'}
          aria-label={expanded ? 'Collapse game details' : 'Expand game details'}
          onClick={(e) => { e.stopPropagation(); toggle(); }}
        >
          <span className="row-action-label">{expanded ? 'Hide' : 'Compare'}</span>
          <svg
            width="11" height="11" viewBox="0 0 12 12" fill="none"
            stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"
            style={{ transition: 'transform .18s ease', transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)' }}
          >
            <path d="M3 4.5L6 7.5L9 4.5" />
          </svg>
        </button>
      </div>
    </div>
  );
}
