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
    }}>
      <span style={{ color: 'var(--faint)' }}>{label}</span>
      <span>{value}</span>
      <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.6">
        <path d="M2.5 4l2.5 2.5L7.5 4" />
      </svg>
    </button>
  );
}

export default function FilterBar({ games = [] }) {
  const liveCount = games.filter((g) => g.status === 'live').length;
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '20px 32px 16px',
    }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 16 }}>
        <h1 style={{ margin: 0, fontSize: 26, fontWeight: 600, letterSpacing: '-0.02em' }}>
          Tonight's slate
        </h1>
        <span style={{ fontSize: 13, color: 'var(--muted)' }}>
          {games.length} game{games.length !== 1 ? 's' : ''}{liveCount > 0 ? ` · ${liveCount} in progress` : ''}
        </span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <SegmentButton label="Sort" value="Edge ↓" />
        <SegmentButton label="Book" value="Consensus" />
        <SegmentButton label="Filter" value="All" />
      </div>
    </div>
  );
}
