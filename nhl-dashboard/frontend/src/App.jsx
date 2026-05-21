import { useState } from 'react';
import { usePolling } from './hooks/usePolling';
import Topbar from './components/Topbar';
import SlateTable from './components/SlateTable';

/**
 * Root application shell.
 * Polls /api/games/today every 15 s and passes the result down to SlateTable.
 */
export default function App() {
  const [density, setDensity] = useState(
    () => localStorage.getItem('density') || 'regular'
  );

  const { data, error, loading } = usePolling('/api/games/today', 15000);
  const games = data?.games ?? [];

  return (
    <div id="app" style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      <Topbar density={density} onDensityChange={setDensity} />

      <main style={{ maxWidth: 1400, margin: '0 auto', padding: '24px 32px' }}>
        {loading && !data && (
          <div style={{ color: 'var(--muted)', fontSize: 14, padding: 32, textAlign: 'center' }}>
            Loading…
          </div>
        )}

        {error && (
          <div style={{
            color: 'var(--hot)', background: 'var(--hot-soft)',
            border: '1px solid color-mix(in oklab, var(--hot) 30%, transparent)',
            borderRadius: 8, padding: '12px 16px', marginBottom: 16, fontSize: 13,
          }}>
            Failed to load games: {error.message}
          </div>
        )}

        <SlateTable games={games} density={density} />
      </main>
    </div>
  );
}
