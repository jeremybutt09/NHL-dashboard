"""
Slate service: build today's game list and return API response.
"""
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from services.time_utils import now_et, today_et

_EASTERN = ZoneInfo("America/New_York")

from extensions import db
from models import NhlOddsLine, Boxscore

logger = logging.getLogger(__name__)


def prune_nhl_odds_lines():
    """Delete NhlOddsLine rows older than 30 days."""
    from sqlalchemy import delete
    from datetime import timedelta

    cutoff = now_et() - timedelta(days=30)
    result = db.session.execute(
        delete(NhlOddsLine).where(NhlOddsLine.fetched_at < cutoff)
    )
    db.session.commit()
    logger.info('[slate] Pruned %d nhl_odds_line rows older than 30 days', result.rowcount)


def build_today_response(partner_id: int | None = None, date: str | None = None) -> dict:
    """Return the JSON shape for GET /api/games/today, reading from the boxscore table.

    Args:
        partner_id: Optional NhlOddsPartner.partner_id.  When provided, the
            ``ml`` field in each game row is sourced from the most recent
            NhlOddsLine row for that (game, partner) pair.  When None, ml is null.
        date: Optional YYYY-MM-DD string.  When provided, filters games by
            this date instead of today's Eastern Time date.
    """
    from sqlalchemy import select

    now = datetime.now(timezone.utc)
    target_date = date if date is not None else today_et()

    boxscores = db.session.scalars(
        select(Boxscore)
        .where(Boxscore.game_date == target_date)
        .order_by(Boxscore.start_time_est)
    ).all()

    return _build_from_boxscores(boxscores, now, partner_id=partner_id)


# ── helpers ──────────────────────────────────────────────────────────────────

def _parse_ml_value(val: str | None) -> int | None:
    """Parse an American-odds string (e.g. '-152', '+126') to int, or None on failure."""
    if val is None:
        return None
    try:
        return int(str(val).replace('+', '').strip())
    except (ValueError, TypeError):
        return None


def _get_partner_ml(game_id: int, partner_id: int) -> dict | None:
    """Return the most recent NhlOddsLine ml dict for a (game, partner) pair, or None."""
    from sqlalchemy import select
    from models import NhlOddsLine

    row = db.session.scalars(
        select(NhlOddsLine)
        .where(NhlOddsLine.game_id == game_id)
        .where(NhlOddsLine.partner_id == partner_id)
        .order_by(NhlOddsLine.fetched_at.desc())
        .limit(1)
    ).first()

    if row is None:
        return None

    away = _parse_ml_value(row.away_value)
    home = _parse_ml_value(row.home_value)
    if away is None or home is None:
        return None

    return {'away': away, 'home': home}


_LIVE_STATES  = frozenset({'LIVE', 'CRIT'})
_FINAL_STATES = frozenset({'FINAL', 'OFF'})


def _build_from_boxscores(boxscores: list, now: datetime, partner_id: int | None = None) -> dict:
    """Build the /api/games/today JSON payload from Boxscore rows."""
    result = []
    for bs in boxscores:
        if bs.game_state in _LIVE_STATES:
            status = 'live'
        elif bs.game_state in _FINAL_STATES:
            status = 'final'
        else:
            status = 'scheduled'

        live_block = None
        if status in ('live', 'final'):
            live_block = {
                'period':     bs.period or '1st',
                'clock':      bs.clock or '20:00',
                'away_score': bs.away_score,
                'home_score': bs.home_score,
                'away_sog':   bs.away_sog,
                'home_sog':   bs.home_sog,
            }

        start_est_iso = None
        if bs.start_time_est:
            dt = bs.start_time_est
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=_EASTERN)
            start_est_iso = dt.isoformat()

        ml = _get_partner_ml(bs.game_id, partner_id) if partner_id is not None else None

        row = {
            'game_id':      bs.game_id,
            'away':         {'code': bs.away_abbrev, 'name': bs.away_name or bs.away_abbrev, 'record': '', 'l10': ''},
            'home':         {'code': bs.home_abbrev, 'name': bs.home_name or bs.home_abbrev, 'record': '', 'l10': ''},
            'start':        start_est_iso,
            'start_est':    start_est_iso,
            'game_date':    bs.game_date,
            'venue':        bs.venue or '',
            'status':       status,
            'live':         live_block,
            'ml':           ml,
            'ml_open':      None,
            'implied':      None,
            'fair':         None,
            'edge':         None,
            'movement_24h': [],
        }
        result.append(row)

    return {'updated_at': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'games': result}
