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
    <div className="stat-strip">
      {stats.map((s) => (
        <div key={s.label} className="stat-card">
          <div className="stat-card-label">{s.label}</div>
          <div className="stat-card-value-row">
            <span
              className="mono tnum stat-card-value"
              style={{ color: s.accent ? 'var(--accent-deep)' : 'var(--ink)' }}
            >
              {s.value}
            </span>
            <span className="stat-card-sub">{s.sub}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
