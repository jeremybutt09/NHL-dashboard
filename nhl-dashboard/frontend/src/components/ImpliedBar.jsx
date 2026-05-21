export default function ImpliedBar({ ipA, ipH, awayCode, homeCode, live, leftLabel, rightLabel }) {
  const lLabel = leftLabel != null ? leftLabel : awayCode;
  const rLabel = rightLabel != null ? rightLabel : homeCode;
  return (
    <div className="implied-bar">
      <div className={`implied-bar-track${live ? ' bar-shimmer' : ''}`}>
        <div className="mono" style={{
          width: `${ipA}%`,
          background: 'linear-gradient(180deg, color-mix(in oklab, var(--accent) 88%, white), var(--accent))',
          display: 'flex', alignItems: 'center', justifyContent: 'flex-start',
          paddingLeft: 8, paddingRight: 8,
          color: 'white', fontSize: 11, fontWeight: 600, letterSpacing: '0.02em',
          textShadow: '0 1px 1px rgba(0,0,0,0.18)',
        }}>
          {ipA >= 18 ? `${lLabel} ${Number(ipA).toFixed(0)}%` : ''}
        </div>
        <div className="mono" style={{
          width: `${ipH}%`,
          background: 'color-mix(in oklab, var(--ink) 8%, var(--bg))',
          display: 'flex', alignItems: 'center', justifyContent: 'flex-end',
          paddingLeft: 8, paddingRight: 8,
          color: 'var(--ink)', fontSize: 11, fontWeight: 600, letterSpacing: '0.02em',
        }}>
          {ipH >= 18 ? `${rLabel} ${Number(ipH).toFixed(0)}%` : ''}
        </div>
        <div style={{
          position: 'absolute', left: '50%', top: 0, bottom: 0, width: 1,
          background: 'color-mix(in oklab, var(--ink) 25%, transparent)',
          pointerEvents: 'none',
        }} />
      </div>
    </div>
  );
}
