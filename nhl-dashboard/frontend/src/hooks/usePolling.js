import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Polls a URL on an interval and returns the latest data.
 *
 * @param {string} url - Endpoint to fetch.
 * @param {number} intervalMs - Polling interval in milliseconds.
 * @returns {{ data: *, error: Error|null, loading: boolean }}
 */
export default function usePolling(url, intervalMs) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const timerRef = useRef(null);

  const fetchData = useCallback(async () => {
    if (document.visibilityState === 'hidden') return;
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
      setError(null);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [url]);

  useEffect(() => {
    fetchData();

    timerRef.current = setInterval(fetchData, intervalMs);

    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        fetchData();
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);

    return () => {
      clearInterval(timerRef.current);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [fetchData, intervalMs]);

  return { data, error, loading };
}
