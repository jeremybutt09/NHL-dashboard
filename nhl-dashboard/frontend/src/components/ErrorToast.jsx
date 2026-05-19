/**
 * Non-blocking toast shown while polling has an active error.
 * Renders nothing when error is null (auto-dismisses on recovery).
 *
 * @param {{ error: Error|null }} props
 */
export default function ErrorToast({ error }) {
  if (!error) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        position: 'fixed',
        bottom: 24,
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 100,
        background: 'var(--ink)',
        color: 'var(--paper)',
        fontSize: 13,
        fontWeight: 500,
        padding: '10px 20px',
        borderRadius: 8,
        pointerEvents: 'none',
        boxShadow: 'var(--shadow-lg)',
        whiteSpace: 'nowrap',
      }}
    >
      Connection lost — retrying...
    </div>
  );
}
