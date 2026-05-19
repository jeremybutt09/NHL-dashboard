import { useEffect, useState } from 'react';
import './styles/tokens.css';
import './styles/app.css';
import usePolling from './hooks/usePolling.js';
import Topbar from './components/Topbar.jsx';
import SlateTable from './components/SlateTable.jsx';
import ErrorToast from './components/ErrorToast.jsx';

/**
 * App root: initialises dark mode and density from localStorage, polls the
 * games endpoint, and renders the topbar + slate table + error toast.
 */
export default function App() {
  // Apply dark class on mount so the initial paint matches stored preference.
  useEffect(() => {
    try {
      if (localStorage.getItem('theme') === 'dark') {
        document.documentElement.classList.add('dark');
      }
    } catch {}
  }, []);

  const [density, setDensity] = useState(() => {
    try { return localStorage.getItem('density') ?? 'regular'; } catch { return 'regular'; }
  });

  const handleDensityChange = (d) => {
    setDensity(d);
    try { localStorage.setItem('density', d); } catch {}
  };

  const { data, loading, error } = usePolling('/api/games/today', 15000);
  const games = data?.games ?? [];

  return (
    <div>
      <Topbar density={density} onDensityChange={handleDensityChange} />
      <main style={{ maxWidth: 1440, margin: '0 auto', padding: '0 0 40px' }}>
        <div style={{ padding: '20px 32px 16px', display: 'flex', alignItems: 'baseline', gap: 16 }}>
          <h1 style={{ margin: 0, fontSize: 26, fontWeight: 600, letterSpacing: '-0.02em', color: 'var(--ink)' }}>
            Tonight's slate
          </h1>
          {loading && (
            <span style={{ fontSize: 13, color: 'var(--faint)' }}>Loading…</span>
          )}
        </div>
        <SlateTable games={games} loading={loading} error={error} density={density} />
      </main>
      <ErrorToast error={error} />
    </div>
  );
}
