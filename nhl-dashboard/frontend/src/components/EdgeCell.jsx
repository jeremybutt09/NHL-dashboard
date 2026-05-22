export default function EdgeCell({ edge }) {
  if (edge == null || Number.isNaN(edge)) {
    return (
      <div className="edge-cell">
        <div style={{
          display: 'inline-flex', alignItems: 'center',
          padding: '4px 10px', borderRadius: 8,
          background: 'color-mix(in oklab, var(--ink) 5%, transparent)',
          color: 'var(--faint)', fontWeight: 600, fontSize: 14,
          border: '1px solid transparent',
        }} className="mono">—</div>
        <span style={{ fontSize: 10, color: 'var(--faint)', letterSpacing: '0.04em' }}>FAIR vs MKT</span>
      </div>
    );
  }
  const positive = edge > 0;
  const strong = Math.abs(edge) >= 2;
  return (
    <div className="edge-cell">
      <div style={{
        display: 'inline-flex', alignItems: 'center', gap: 4,
        padding: '4px 10px',
        borderRadius: 8,
        background: positive ? 'var(--up-soft)' : 'color-mix(in oklab, var(--down) 12%, transparent)',
        color: positive ? 'var(--up)' : 'var(--down)',
        fontWeight: 700, fontSize: 14, letterSpacing: '-0.01em',
        border: strong
          ? `1px solid ${positive ? 'var(--up)' : 'var(--down)'}`
          : '1px solid transparent',
      }} className={`mono tnum ${positive ? 'edge-positive' : 'edge-negative'}`}>
        {positive ? '+' : ''}{edge.toFixed(1)}%
      </div>
      <span style={{ fontSize: 10, color: 'var(--faint)', letterSpacing: '0.04em' }}>FAIR vs MKT</span>
    </div>
  );
}
