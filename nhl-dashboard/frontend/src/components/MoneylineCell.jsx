import ImpliedBar from './ImpliedBar.jsx';

function arrow(d) {
  if (d === 0) return null;
  return (
    <span style={{ fontSize: 10, color: d > 0 ? 'var(--up)' : 'var(--down)', fontWeight: 600, marginLeft: 4 }} className="mono">
      {d > 0 ? '▲' : '▼'}{Math.abs(d)}
    </span>
  );
}

function Price({ price, delta, ip, side }) {
  const positive = price.startsWith('+');
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: side, gap: 2, minWidth: 64 }}>
      <span className={`mono tnum ${positive ? 'positive' : 'negative'}`} style={{ fontSize: 18, fontWeight: 600, letterSpacing: '-0.01em' }}>
        {price}
      </span>
      <span style={{ fontSize: 10, color: 'var(--faint)', letterSpacing: '0.03em' }}>
        from <span className="mono">{ip}</span>{arrow(delta)}
      </span>
    </div>
  );
}

export default function MoneylineCell({ g, state }) {
  const isLive = state === 'live' && !!g.live;
  const numeric = (s) => parseInt(s.replace(/[+]/, ''), 10);
  const dA = numeric(g.ml.a) - numeric(g.mlOpen.a);
  const dH = numeric(g.ml.h) - numeric(g.mlOpen.h);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <Price price={g.ml.a} delta={dA} ip={g.mlOpen.a} side="flex-start" />
        <div style={{ flex: 1 }}>
          <ImpliedBar ipA={g.ip.a} ipH={g.ip.h} awayCode={g.away} homeCode={g.home} live={isLive} />
        </div>
        <Price price={g.ml.h} delta={dH} ip={g.mlOpen.h} side="flex-end" />
      </div>
    </div>
  );
}
