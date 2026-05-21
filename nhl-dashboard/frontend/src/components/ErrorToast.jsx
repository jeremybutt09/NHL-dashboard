import { useEffect } from 'react';

/**
 * Dismissible toast displayed at the bottom of the viewport when a poll error occurs.
 * Auto-dismisses after 5 seconds.
 *
 * @param {{ error: Error, onDismiss: function }} props
 */
export default function ErrorToast({ error, onDismiss }) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 5000);
    return () => clearTimeout(timer);
  }, [error, onDismiss]);

  return (
    <div style={{
      position: 'fixed',
      bottom: 24,
      left: '50%',
      transform: 'translateX(-50%)',
      zIndex: 100,
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      background: 'var(--hot-soft)',
      border: '1px solid color-mix(in oklab, var(--hot) 40%, transparent)',
      borderRadius: 10,
      padding: '12px 16px',
      fontSize: 13,
      color: 'var(--hot)',
      boxShadow: 'var(--shadow)',
      minWidth: 280,
      maxWidth: 480,
    }}>
      <span style={{ flex: 1 }}>
        Failed to load games: {error?.message ?? 'Network error'}
      </span>
      <button
        onClick={onDismiss}
        style={{
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          color: 'var(--hot)',
          fontSize: 16,
          lineHeight: 1,
          padding: '0 2px',
          flexShrink: 0,
        }}
        aria-label="Dismiss error"
      >
        ×
      </button>
    </div>
  );
}
