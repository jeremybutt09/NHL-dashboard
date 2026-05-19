import LiveDot from './LiveDot.jsx';

export default function StatusCell({ g, state }) {
  const isLive = state === 'live' && !!g.live;
  if (isLive) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: 'var(--hot)', fontWeight: 600, fontSize: 12, letterSpacing: '0.04em' }}>
          <LiveDot /> LIVE
        </span>
        <span className="mono" style={{ fontSize: 13, color: 'var(--ink)', fontWeight: 500 }}>{g.live.period} · {g.live.clock}</span>
      </div>
    );
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <span className="mono" style={{ fontSize: 13, color: 'var(--ink)', fontWeight: 500 }}>{g.start}</span>
      <span style={{ fontSize: 11, color: 'var(--faint)', letterSpacing: '0.04em' }}>{g.tz} · TONIGHT</span>
    </div>
  );
}
