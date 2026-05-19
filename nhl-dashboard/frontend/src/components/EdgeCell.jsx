export default function EdgeCell({ edge }) {
  const positive = edge > 0;
  const strong = Math.abs(edge) >= 2;
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 2,
    }}>
      <div
        className={`mono tnum ${positive ? 'positive' : 'negative'}`}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 4,
          padding: '4px 10px',
          borderRadius: 8,
          background: positive ? 'var(--up-soft)' : 'color-mix(in oklab, var(--down) 12%, transparent)',
          color: positive ? 'var(--up)' : 'var(--down)',
          fontWeight: 700, fontSize: 14, letterSpacing: '-0.01em',
          border: strong
            ? `1px solid ${positive ? 'var(--up)' : 'var(--down)'}`
            : '1px solid transparent',
        }}
      >
        {positive ? '+' : ''}{edge.toFixed(1)}%
      </div>
      <span style={{ fontSize: 10, color: 'var(--faint)', letterSpacing: '0.04em' }}>FAIR vs MKT</span>
    </div>
  );
}
