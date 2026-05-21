import { useState, useEffect, useRef } from 'react';

/**
 * Polls a URL on a fixed interval and returns the latest response data.
 *
 * @param {string} url - Endpoint to fetch.
 * @param {number} interval - Poll interval in milliseconds.
 * @returns {{ data: any, error: Error|null, loading: boolean }}
 */
export function usePolling(url, interval) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const timerRef = useRef(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchData() {
      if (document.visibilityState === 'hidden') return;
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        if (!cancelled) {
          setData(json);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError(err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchData();
    timerRef.current = setInterval(fetchData, interval);

    function handleVisibilityChange() {
      if (document.visibilityState === 'visible') {
        fetchData();
      }
    }
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      cancelled = true;
      clearInterval(timerRef.current);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [url, interval]);

  return { data, error, loading };
}
