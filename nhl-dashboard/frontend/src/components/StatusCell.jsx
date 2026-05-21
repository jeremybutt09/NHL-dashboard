import LiveDot from './LiveDot';

export default function StatusCell({ g, state }) {
  if (g.final && g.final.completed) {
    return (
      <div className="status-cell">
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: 'var(--muted)', fontWeight: 600, fontSize: 12, letterSpacing: '0.06em' }}>
          FINAL
        </span>
        <span className="mono" style={{ fontSize: 12, color: 'var(--faint)' }}>{g.start}</span>
      </div>
    );
  }
  if (g.final && !g.final.completed && g.final.a != null) {
    return (
      <div className="status-cell">
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: 'var(--hot)', fontWeight: 600, fontSize: 12, letterSpacing: '0.04em' }}>
          <LiveDot /> LIVE
        </span>
        <span className="mono" style={{ fontSize: 12, color: 'var(--faint)' }}>in progress</span>
      </div>
    );
  }
  const isLive = state === 'live' && !!g.live;
  if (isLive) {
    return (
      <div className="status-cell">
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: 'var(--hot)', fontWeight: 600, fontSize: 12, letterSpacing: '0.04em' }}>
          <LiveDot /> LIVE
        </span>
        <span className="mono" style={{ fontSize: 13, color: 'var(--ink)', fontWeight: 500 }}>
          {g.live.period} · {g.live.clock}
        </span>
      </div>
    );
  }
  return (
    <div className="status-cell">
      <span className="mono" style={{ fontSize: 13, color: 'var(--ink)', fontWeight: 500 }}>{g.start}</span>
      <span style={{ fontSize: 11, color: 'var(--faint)', letterSpacing: '0.04em' }}>{g.tz} · TONIGHT</span>
    </div>
  );
}
