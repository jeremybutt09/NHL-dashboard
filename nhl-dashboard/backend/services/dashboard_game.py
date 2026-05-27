"""Dashboard game view: today's app-ready game slate.

Source: boxscore table (populated by services.boxscore)
Table:  dashboard_game (see models.DashboardGame — Issue #134)

Refresh cadence: same as POLL_BOXSCORE_INTERVAL (default 60 s) via
APScheduler, invoked after refresh_boxscores() so live data is always current.
"""
import logging
from datetime import datetime, timezone

from extensions import db
from models import Boxscore, DashboardGame
from services.time_utils import now_et, today_et

logger = logging.getLogger(__name__)

_LIVE_STATES = frozenset({'LIVE', 'CRIT'})
_FINAL_STATES = frozenset({'FINAL', 'OFF'})


def _derive_status(game_state: str | None) -> str:
    """Map an NHL gameState string to a dashboard status label.

    Args:
        game_state: NHL API gameState value (e.g. 'LIVE', 'FINAL', 'FUT').

    Returns:
        One of 'live', 'final', or 'scheduled'.
    """
    if game_state in _LIVE_STATES:
        return 'live'
    if game_state in _FINAL_STATES:
        return 'final'
    return 'scheduled'


def refresh_dashboard_games() -> int:
    """Copy today's boxscore rows into the dashboard_game table.

    Reads all Boxscore records where game_date == today, derives a
    human-readable status from game_state, and upserts each row into
    dashboard_game.  Rows for non-today dates are never written, keeping
    the table small (one row per active game).

    Returns:
        Number of dashboard_game rows successfully upserted.
    """
    today = today_et()
    boxscores = db.session.scalars(
        db.select(Boxscore).where(Boxscore.game_date == today)
    ).all()

    if not boxscores:
        return 0

    now = now_et()
    count = 0

    for bs in boxscores:
        record = DashboardGame(
            game_id=bs.game_id,
            game_date=bs.game_date,
            venue=bs.venue,
            start_time_est=bs.start_time_est,
            away_name=bs.away_name,
            away_abbrev=bs.away_abbrev,
            home_name=bs.home_name,
            home_abbrev=bs.home_abbrev,
            away_score=bs.away_score,
            home_score=bs.home_score,
            away_sog=bs.away_sog,
            home_sog=bs.home_sog,
            period=bs.period,
            clock=bs.clock,
            status=_derive_status(bs.game_state),
            updated_at=now,
        )
        db.session.merge(record)
        count += 1

    db.session.commit()
    logger.info('[dashboard_game] Upserted %d rows for %s', count, today)
    return count
