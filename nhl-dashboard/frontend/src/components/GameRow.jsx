import StatusCell from './StatusCell.jsx';
import MatchupCell from './MatchupCell.jsx';
import MoneylineCell from './MoneylineCell.jsx';
import SparklineCell from './SparklineCell.jsx';
import EdgeCell from './EdgeCell.jsx';

/**
 * Adapts the API game object to the shape expected by cell components,
 * then renders a full row in the slate table grid.
 *
 * API shape (from GET /api/games/today):
 *   { id, away: {code, name, record, l10}, home: {code, name, record, l10},
 *     status, live: {period, clock, away_score, home_score}|null,
 *     ml: {away, home}, ml_open: {away, home},
 *     implied: {away, home}, edge, movement_24h, start }
 *
 * @param {{ g: object, density?: string }} props
 */
export default function GameRow({ g, density = 'regular' }) {
  // Normalise to the flat shape used by StatusCell / MatchupCell / MoneylineCell
  const game = {
    away:     g.away?.code   ?? g.away,
    home:     g.home?.code   ?? g.home,
    awayName: g.away?.name   ?? g.awayName ?? '',
    homeName: g.home?.name   ?? g.homeName ?? '',
    awayRec:  g.away?.record ?? g.awayRec  ?? '',
    homeRec:  g.home?.record ?? g.homeRec  ?? '',
    awayL10:  g.away?.l10    ?? g.awayL10  ?? '',
    homeL10:  g.home?.l10    ?? g.homeL10  ?? '',
    start:    g.start ?? '',
    tz:       'ET',
    ml: {
      a: g.ml?.away != null ? (g.ml.away > 0 ? `+${g.ml.away}` : String(g.ml.away)) : (g.ml?.a ?? '—'),
      h: g.ml?.home != null ? (g.ml.home > 0 ? `+${g.ml.home}` : String(g.ml.home)) : (g.ml?.h ?? '—'),
    },
    mlOpen: {
      a: g.ml_open?.away != null ? (g.ml_open.away > 0 ? `+${g.ml_open.away}` : String(g.ml_open.away)) : (g.mlOpen?.a ?? '—'),
      h: g.ml_open?.home != null ? (g.ml_open.home > 0 ? `+${g.ml_open.home}` : String(g.ml_open.home)) : (g.mlOpen?.h ?? '—'),
    },
    ip: {
      a: g.implied?.away ?? g.ip?.a ?? 50,
      h: g.implied?.home ?? g.ip?.h ?? 50,
    },
    edge:  g.edge ?? 0,
    live:  g.live
      ? {
          period: g.live.period ?? '',
          clock:  g.live.clock  ?? '',
          as:     g.live.away_score ?? g.live.as ?? 0,
          hs:     g.live.home_score ?? g.live.hs ?? 0,
        }
      : null,
  };

  const state = game.live ? 'live' : 'scheduled';
  const series = g.movement_24h ?? g.series ?? [];

  return (
    <div className="game-row">
      <StatusCell g={game} state={state} />
      <MatchupCell g={game} state={state} density={density} />
      <MoneylineCell g={game} state={state} />
      <SparklineCell series={series.length ? series : Array(24).fill(50)} delta={0} />
      <EdgeCell edge={game.edge} />
      <button
        className="row-action icon-btn"
        title="Game details · line history · props · book comparison"
        aria-label="Open game details"
      >
        <span className="row-action-label">Details</span>
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
          <path d="M6 4l4 4-4 4" />
        </svg>
      </button>
    </div>
  );
}
