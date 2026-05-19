import TeamGlyph from './TeamGlyph.jsx';

function Row({ code, name, rec, l10, score, leading, dim, isLive, size }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, opacity: dim ? 0.85 : 1 }}>
      <TeamGlyph code={code} size={size} dim={dim} />
      <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0, flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
          <span style={{ fontWeight: 600, fontSize: 14, color: 'var(--ink)' }}>{code}</span>
          <span style={{ fontSize: 12, color: 'var(--muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{name}</span>
        </div>
        <div className="mono" style={{ fontSize: 11, color: 'var(--faint)' }}>
          {rec} <span style={{ opacity: 0.6 }}>· L10 {l10}</span>
        </div>
      </div>
      <span className="mono tnum" style={{
        fontSize: 22, fontWeight: 600,
        color: dim ? 'var(--faint)' : leading ? 'var(--ink)' : 'var(--muted)',
        minWidth: 24, textAlign: 'right',
        letterSpacing: '-0.01em',
      }}>
        {isLive ? score : '—'}
      </span>
    </div>
  );
}

export default function MatchupCell({ g, state, density }) {
  const isLive = state === 'live' && !!g.live;
  const winA = isLive && g.live.as > g.live.hs;
  const winH = isLive && g.live.hs > g.live.as;
  const size = density === 'compact' ? 26 : 30;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: density === 'compact' ? 6 : 10 }}>
      <Row
        code={g.away} name={g.awayName} rec={g.awayRec} l10={g.awayL10}
        score={g.live?.as} leading={winA} dim={isLive && winH}
        isLive={isLive} size={size}
      />
      <Row
        code={g.home} name={g.homeName} rec={g.homeRec} l10={g.homeL10}
        score={g.live?.hs} leading={winH} dim={isLive && winA}
        isLive={isLive} size={size}
      />
    </div>
  );
}
