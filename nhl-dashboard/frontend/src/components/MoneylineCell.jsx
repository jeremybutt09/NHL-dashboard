import ImpliedBar from './ImpliedBar';

function mlToProb(ml) {
  const n = parseInt(String(ml).replace('+', ''), 10);
  return n < 0 ? (-n) / ((-n) + 100) : 100 / (n + 100);
}

function oddsForGame(g) {
  const ml = g.ml || { away: '—', home: '—' };
  const mlOpen = g.ml_open || ml;
  const pa = mlToProb(ml.away), ph = mlToProb(ml.home);
  const sum = pa + ph || 1;
  return { ml, mlOpen, ip: { a: (pa / sum) * 100, h: (ph / sum) * 100 } };
}

function pickForCalc(detail) {
  window.dispatchEvent(new CustomEvent('betcalc:pick', { detail }));
}

export default function MoneylineCell({ g, state, book }) {
  if (!g.ml || g.ml.away == null) {
    return <div style={{ color: 'var(--faint)', fontSize: 12, fontStyle: 'italic' }}>No odds available</div>;
  }
  const isLive = state === 'live' && !!g.live;
  const adj = oddsForGame(g);
  const numeric = (s) => parseInt(String(s).replace(/[+]/, ''), 10) || 0;
  const dA = numeric(adj.ml.away) - numeric(adj.mlOpen.away);
  const dH = numeric(adj.ml.home) - numeric(adj.mlOpen.home);
  const arrow = (d) => d === 0 ? null : (
    <span style={{ fontSize: 10, color: d > 0 ? 'var(--up)' : 'var(--down)', fontWeight: 600, marginLeft: 4 }} className="mono">
      {d > 0 ? '▲' : '▼'}{Math.abs(d)}
    </span>
  );
  const Price = ({ price, delta, ip, side, sideId }) => (
    <button
      type="button"
      title="Send to payout calculator"
      onClick={(e) => { e.stopPropagation(); pickForCalc({ gameId: g.id, market: 'h2h', side: sideId, price, point: null }); }}
      style={{
        display: 'flex', flexDirection: 'column', alignItems: side, gap: 2, minWidth: 64,
        background: 'transparent', border: 'none', padding: '4px 6px', margin: '-4px -6px',
        borderRadius: 6, cursor: 'pointer', fontFamily: 'inherit', color: 'inherit',
        transition: 'background-color .12s',
      }}
      onMouseEnter={(e) => { e.currentTarget.style.background = 'color-mix(in oklab, var(--accent) 10%, transparent)'; }}
      onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
    >
      <span className="mono tnum" style={{ fontSize: 18, fontWeight: 600, letterSpacing: '-0.01em' }}>
        {price}
      </span>
      <span style={{ fontSize: 10, color: 'var(--faint)', letterSpacing: '0.03em' }}>
        from <span className="mono">{ip}</span>{arrow(delta)}
      </span>
    </button>
  );
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <Price price={adj.ml.away} delta={dA} ip={adj.mlOpen.away} side="flex-start" sideId="a" />
        <div style={{ flex: 1 }}>
          <ImpliedBar ipA={adj.ip.a} ipH={adj.ip.h} awayCode={g.away.code} homeCode={g.home.code} live={isLive} />
        </div>
        <Price price={adj.ml.home} delta={dH} ip={adj.mlOpen.home} side="flex-end" sideId="h" />
      </div>
    </div>
  );
}
