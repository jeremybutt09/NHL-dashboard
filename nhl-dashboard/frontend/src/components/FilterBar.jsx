function SegmentButton({ label, value }) {
  return (
    <button className="segment-btn">
      <span className="segment-btn-label">{label}</span>
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
    <div className="filter-bar">
      <div className="filter-bar-title">
        <h1>Tonight's slate</h1>
        <span>
          {games.length} game{games.length !== 1 ? 's' : ''}{liveCount > 0 ? ` · ${liveCount} in progress` : ''}
        </span>
      </div>
      <div className="filter-bar-controls">
        <SegmentButton label="Sort" value="Edge ↓" />
        <SegmentButton label="Book" value="Consensus" />
        <SegmentButton label="Filter" value="All" />
      </div>
    </div>
  );
}
