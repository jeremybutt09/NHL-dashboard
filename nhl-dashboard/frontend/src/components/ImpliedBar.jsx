export default function ImpliedBar({ ipA, ipH, awayCode, homeCode, live }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div
        style={{
          position: 'relative',
          height: 22,
          borderRadius: 7,
          overflow: 'hidden',
          display: 'flex',
          boxShadow: 'inset 0 0 0 1px var(--rule)',
          background: 'var(--bg)',
        }}
        className={live ? 'bar-shimmer' : ''}
      >
        <div style={{
          width: `${ipA}%`,
          background: 'linear-gradient(180deg, color-mix(in oklab, var(--accent) 88%, white), var(--accent))',
          display: 'flex', alignItems: 'center', justifyContent: 'flex-start',
          paddingLeft: 8, paddingRight: 8,
          color: 'white', fontSize: 11, fontWeight: 600, letterSpacing: '0.02em',
          textShadow: '0 1px 1px rgba(0,0,0,0.18)',
        }} className="mono">
          {ipA >= 18 ? `${awayCode} ${ipA.toFixed(0)}%` : ''}
        </div>
        <div style={{
          width: `${ipH}%`,
          background: 'color-mix(in oklab, var(--ink) 8%, var(--bg))',
          display: 'flex', alignItems: 'center', justifyContent: 'flex-end',
          paddingLeft: 8, paddingRight: 8,
          color: 'var(--ink)', fontSize: 11, fontWeight: 600, letterSpacing: '0.02em',
        }} className="mono">
          {ipH >= 18 ? `${homeCode} ${ipH.toFixed(0)}%` : ''}
        </div>
        {/* 50% marker */}
        <div style={{
          position: 'absolute', left: '50%', top: 0, bottom: 0, width: 1,
          background: 'color-mix(in oklab, var(--ink) 25%, transparent)',
          pointerEvents: 'none',
        }} />
      </div>
    </div>
  );
}
