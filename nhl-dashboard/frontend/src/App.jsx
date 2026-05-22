import { useState, useEffect } from 'react';
import { usePolling } from './hooks/usePolling';
import Topbar from './components/Topbar';
import FilterBar from './components/FilterBar';
import StatStrip from './components/StatStrip';
import SlateTable from './components/SlateTable';
import ErrorToast from './components/ErrorToast';

/**
 * Root application shell.
 * Polls /api/games/today every 15 s and passes the result down to SlateTable.
 */
export default function App() {
  const [density, setDensity] = useState(
    () => localStorage.getItem('density') || 'regular'
  );
  const [toastDismissed, setToastDismissed] = useState(false);
  const [sort, setSort] = useState('edge-desc');
  const [filter, setFilter] = useState('all');

  const { data, error, loading } = usePolling('/api/games/today', 15000);
  const games = data?.games ?? [];

  const sortedGames = [...games].sort((a, b) => {
    if (sort === 'edge-desc') return (b.edge ?? -Infinity) - (a.edge ?? -Infinity);
    if (sort === 'edge-asc') return (a.edge ?? Infinity) - (b.edge ?? Infinity);
    // time-asc
    return (a.start_utc ?? '') < (b.start_utc ?? '') ? -1 : 1;
  });

  const filteredGames = filter === 'all'
    ? sortedGames
    : sortedGames.filter((g) => g.status === filter);

  /* Reset dismissed state on next successful poll so a future error shows again. */
  useEffect(() => {
    if (!error) setToastDismissed(false);
  }, [error]);

  const showToast = !!error && !toastDismissed;

  function handleToastDismiss() {
    setToastDismissed(true);
  }

  return (
    <div id="app" style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      <Topbar density={density} onDensityChange={setDensity} />
      <FilterBar games={games} sort={sort} onSortChange={setSort} filter={filter} onFilterChange={setFilter} />

      <main style={{ maxWidth: 1400, margin: '0 auto', padding: '0 32px' }}>
        <StatStrip games={games} />
        <SlateTable games={filteredGames} loading={loading && !data} density={density} filterActive={filter !== 'all'} />
      </main>

      {showToast && (
        <ErrorToast error={error} onDismiss={handleToastDismiss} />
      )}
    </div>
  );
}
