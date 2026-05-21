import { useState, useEffect } from 'react';
import { usePolling } from './hooks/usePolling';
import Topbar from './components/Topbar';
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

  const { data, error, loading } = usePolling('/api/games/today', 15000);
  const games = data?.games ?? [];

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

      <main style={{ maxWidth: 1400, margin: '0 auto', padding: '24px 32px' }}>
        <SlateTable games={games} loading={loading && !data} density={density} />
      </main>

      {showToast && (
        <ErrorToast error={error} onDismiss={handleToastDismiss} />
      )}
    </div>
  );
}
