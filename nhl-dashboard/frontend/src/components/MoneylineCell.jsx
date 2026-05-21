import ImpliedBar from './ImpliedBar';

function mlToProb(ml) {
  const n = parseInt(String(ml).replace('+', ''), 10);
  return n < 0 ? (-n) / ((-n) + 100) : 100 / (n + 100);
}

function oddsForBook(g, bookId) {
  if (g.__source === 'api') {
    const map = g.booksMap || {};
    const b = map[bookId] || Object.values(map).find((x) => x.a) || Object.values(map)[0];
    if (!b || !b.a) {
      return { ml: { a: '—', h: '—' }, mlOpen: { a: '—', h: '—' }, ip: { a: 50, h: 50 }, blank: true };
    }
    const ml = { a: b.a, h: b.h };
    const mlOpen = { a: b.a, h: b.h };
    const pa = mlToProb(ml.a), ph = mlToProb(ml.h);
    const sum = pa + ph;
    return { ml, mlOpen, ip: { a: (pa / sum) * 100, h: (ph / sum) * 100 } };
  }
  const ml = g.ml || { a: '—', h: '—' };
  const mlOpen = g.mlOpen || ml;
  const pa = mlToProb(ml.a), ph = mlToProb(ml.h);
  const sum = pa + ph || 1;
  return { ml, mlOpen, ip: { a: (pa / sum) * 100, h: (ph / sum) * 100 } };
}

function pickForCalc(detail) {
  window.dispatchEvent(new CustomEvent('betcalc:pick', { detail }));
}

export default function MoneylineCell({ g, state, book }) {
  if (g.__source === 'api' && !g.booksMap) {
    return <div style={{ color: 'var(--faint)', fontSize: 12, fontStyle: 'italic' }}>No odds available</div>;
  }
  const isLive = state === 'live' && !!g.live;
  const adj = oddsForBook(g, book);
  if (adj.blank) {
    return <div style={{ color: 'var(--faint)', fontSize: 12, fontStyle: 'italic' }}>No moneyline offered</div>;
  }
  const numeric = (s) => parseInt(String(s).replace(/[+]/, ''), 10) || 0;
  const dA = numeric(adj.ml.a) - numeric(adj.mlOpen.a);
  const dH = numeric(adj.ml.h) - numeric(adj.mlOpen.h);
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
        {g.__source === 'api'
          ? <span className="mono">current</span>
          : <>from <span className="mono">{ip}</span>{arrow(delta)}</>}
      </span>
    </button>
  );
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <Price price={adj.ml.a} delta={dA} ip={adj.mlOpen.a} side="flex-start" sideId="a" />
        <div style={{ flex: 1 }}>
          <ImpliedBar ipA={adj.ip.a} ipH={adj.ip.h} awayCode={g.away} homeCode={g.home} live={isLive} />
        </div>
        <Price price={adj.ml.h} delta={dH} ip={adj.mlOpen.h} side="flex-end" sideId="h" />
      </div>
    </div>
  );
}
