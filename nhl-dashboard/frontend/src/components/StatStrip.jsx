export default function StatStrip({ games = [] }) {
  const liveCount = games.filter((g) => g.status === 'live').length;
  const positiveEdges = games.filter((g) => (g.edge ?? 0) > 0).length;
  const totalEdge = games.reduce((a, g) => a + Math.max(0, g.edge ?? 0), 0);
  const avgIp = games.length > 0
    ? games.reduce((a, g) => a + (g.implied?.away ?? 50), 0) / games.length
    : 0;

  const stats = [
    {
      label: 'Games tonight',
      value: games.length,
      sub: liveCount > 0 ? `${liveCount} live now` : 'all pre-game',
    },
    {
      label: '+EV opportunities',
      value: positiveEdges,
      sub: `${totalEdge.toFixed(1)}% total edge`,
      accent: true,
    },
    {
      label: 'Sharp action',
      value: '—',
      sub: 'no data yet',
    },
    {
      label: 'Avg implied (away)',
      value: `${avgIp.toFixed(0)}%`,
      sub: 'consensus across books',
    },
  ];

  return (
    <div style={{
      display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14,
      padding: '0 32px 16px',
    }}>
      {stats.map((s) => (
        <div key={s.label} style={{
          padding: '14px 16px',
          background: 'var(--paper)',
          border: '1px solid var(--rule)',
          borderRadius: 12,
          boxShadow: 'var(--shadow)',
        }}>
          <div style={{
            fontSize: 11, color: 'var(--faint)', letterSpacing: '0.06em',
            textTransform: 'uppercase', marginBottom: 6,
          }}>
            {s.label}
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
            <span className="mono tnum" style={{
              fontSize: 24, fontWeight: 600, letterSpacing: '-0.02em',
              color: s.accent ? 'var(--accent-deep)' : 'var(--ink)',
            }}>
              {s.value}
            </span>
            <span style={{ fontSize: 12, color: 'var(--muted)' }}>{s.sub}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
