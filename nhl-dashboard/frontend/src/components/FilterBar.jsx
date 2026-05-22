import { useState } from 'react';

const SORT_OPTIONS = ['edge-desc', 'edge-asc', 'time-asc'];
const SORT_LABELS = { 'edge-desc': 'Edge ↓', 'edge-asc': 'Edge ↑', 'time-asc': 'Time ↑' };

const FILTER_OPTIONS = ['all', 'live', 'scheduled', 'final'];
const FILTER_LABELS = { all: 'All', live: 'Live', scheduled: 'Scheduled', final: 'Final' };

function SegmentButton({ label, value, onClick }) {
  return (
    <button className="segment-btn" onClick={onClick}>
      <span className="segment-btn-label">{label}</span>
      <span>{value}</span>
      <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.6">
        <path d="M2.5 4l2.5 2.5L7.5 4" />
      </svg>
    </button>
  );
}

export default function FilterBar({ games = [], sort = 'edge-desc', onSortChange, filter = 'all', onFilterChange, loading = false }) {
  const liveCount = games.filter((g) => g.status === 'live').length;

  function handleSortCycle() {
    if (!onSortChange) return;
    const idx = SORT_OPTIONS.indexOf(sort);
    onSortChange(SORT_OPTIONS[(idx + 1) % SORT_OPTIONS.length]);
  }

  function handleFilterCycle() {
    if (!onFilterChange) return;
    const idx = FILTER_OPTIONS.indexOf(filter);
    onFilterChange(FILTER_OPTIONS[(idx + 1) % FILTER_OPTIONS.length]);
  }

  return (
    <div className="filter-bar">
      <div className="filter-bar-title">
        <h1>Tonight's slate</h1>
        <span>
          {loading ? 'Loading…' : `${games.length} game${games.length !== 1 ? 's' : ''}${liveCount > 0 ? ` · ${liveCount} in progress` : ''}`}
        </span>
      </div>
      <div className="filter-bar-controls">
        <SegmentButton label="Sort" value={SORT_LABELS[sort]} onClick={handleSortCycle} />
        <SegmentButton label="Book" value="Consensus" />
        <SegmentButton label="Filter" value={FILTER_LABELS[filter]} onClick={handleFilterCycle} />
      </div>
    </div>
  );
}
