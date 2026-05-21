import TeamGlyph from './TeamGlyph';

function Row({ code, name, rec, l10, score, leading, dim, showScores, density }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, opacity: dim ? 0.85 : 1 }}>
      <TeamGlyph code={code} size={density === 'compact' ? 26 : 30} dim={dim} />
      <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0, flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
          <span style={{ fontWeight: 600, fontSize: 14, color: 'var(--ink)' }}>{code}</span>
          <span style={{ fontSize: 12, color: 'var(--muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{name}</span>
        </div>
        <div className="mono" style={{ fontSize: 11, color: 'var(--faint)' }}>
          {rec
            ? <>{rec} {l10 && <span style={{ opacity: 0.6 }}>· L10 {l10}</span>}</>
            : <span style={{ opacity: 0.5 }}>—</span>}
        </div>
      </div>
      <span className="mono tnum" style={{
        fontSize: 22, fontWeight: 600,
        color: dim ? 'var(--faint)' : leading ? 'var(--ink)' : 'var(--muted)',
        minWidth: 24, textAlign: 'right',
        letterSpacing: '-0.01em',
      }}>
        {showScores && score != null ? score : '—'}
      </span>
    </div>
  );
}

export default function MatchupCell({ g, state, density }) {
  const isFinal = g.status === "final";
  const isLive = state === "live" && !!g.live;
  const scoreA = g.live?.away_score;
  const scoreH = g.live?.home_score;
  const showScores = isLive || isFinal;
  const winA = showScores && scoreA != null && scoreH != null && scoreA > scoreH;
  const winH = showScores && scoreA != null && scoreH != null && scoreH > scoreA;
  return (
    <div className="matchup-cell" style={{ gap: density === 'compact' ? 6 : 10 }}>
      <Row code={g.away.code} name={g.away.name} rec={g.away.record} l10={g.away.l10}
           score={scoreA} leading={winA} dim={showScores && winH}
           showScores={showScores} density={density} />
      <Row code={g.home.code} name={g.home.name} rec={g.home.record} l10={g.home.l10}
           score={scoreH} leading={winH} dim={showScores && winA}
           showScores={showScores} density={density} />
    </div>
  );
}
