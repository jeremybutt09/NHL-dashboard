"""Boxscore ingestion from the NHL Web API.

Source: GET https://api-web.nhle.com/v1/gamecenter/{game_id}/boxscore
Table:  boxscore (see models.Boxscore — Issue #133)

Refresh cadence: every POLL_BOXSCORE_INTERVAL seconds (default 60 s) via
APScheduler, so live score/SOG/period data stays current during games.

Today's game IDs are resolved by querying the `game` table, which is
populated by the historical ingest pipeline (models.Game).
"""
import logging
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import nhl_client
from extensions import db
from models import Boxscore, Game

logger = logging.getLogger(__name__)

_EASTERN = ZoneInfo("America/New_York")


def _parse_period(period_descriptor: dict) -> str | None:
    """Convert a periodDescriptor dict to a human-readable period string.

    Args:
        period_descriptor: NHL API periodDescriptor dict with 'number' and
            'periodType' keys.

    Returns:
        One of 'OT', 'SO', an ordinal like '1st'/'2nd'/'3rd', or None when
        the descriptor is absent.
    """
    if not period_descriptor:
        return None
    period_type = period_descriptor.get('periodType', 'REG')
    period_num = period_descriptor.get('number', 1)
    if period_type == 'OT':
        return 'OT'
    if period_type == 'SO':
        return 'SO'
    ordinals = {1: '1st', 2: '2nd', 3: '3rd'}
    return ordinals.get(period_num, f'{period_num}th')


def _build_boxscore(raw: dict, now: datetime) -> Boxscore:
    """Map a /v1/gamecenter/{id}/boxscore response to a Boxscore instance.

    Args:
        raw: Full API response dict for a single game boxscore.
        now: Current UTC datetime used for updated_at and as a fallback for
            start_time_est when startTimeUTC is missing or unparseable.

    Returns:
        An unsaved Boxscore instance ready for db.session.merge().
    """
    # Venue
    venue_raw = raw.get('venue', '')
    venue = venue_raw.get('default', '') if isinstance(venue_raw, dict) else (venue_raw or '')

    # Start time: convert UTC → Eastern
    start_raw = raw.get('startTimeUTC', '')
    try:
        start_utc = datetime.fromisoformat(start_raw.replace('Z', '+00:00'))
        start_est = start_utc.astimezone(_EASTERN)
    except Exception:
        start_est = now.astimezone(_EASTERN)

    # Team names
    away = raw.get('awayTeam', {})
    home = raw.get('homeTeam', {})
    away_name_raw = away.get('name', {})
    home_name_raw = home.get('name', {})
    away_name = away_name_raw.get('default', '') if isinstance(away_name_raw, dict) else (away_name_raw or '')
    home_name = home_name_raw.get('default', '') if isinstance(home_name_raw, dict) else (home_name_raw or '')

    # Period and clock
    period = _parse_period(raw.get('periodDescriptor') or {})
    clock_raw = raw.get('clock') or {}
    clock = clock_raw.get('timeRemaining')

    return Boxscore(
        game_id=raw['id'],
        season_id=raw.get('season'),
        game_type=raw.get('gameType'),
        game_date=raw.get('gameDate'),
        venue=venue,
        start_time_est=start_est,
        away_name=away_name,
        away_abbrev=away.get('abbrev'),
        home_name=home_name,
        home_abbrev=home.get('abbrev'),
        away_score=away.get('score'),
        home_score=home.get('score'),
        away_sog=away.get('sog'),
        home_sog=home.get('sog'),
        period=period,
        clock=clock,
        game_state=raw.get('gameState'),
        updated_at=now,
    )


def refresh_boxscores() -> int:
    """Fetch boxscore data for today's games and upsert into the boxscore table.

    Resolves today's game IDs by querying the `game` table filtered to
    game_date == today.  For each game_id, calls
    nhl_client.get_boxscore() and upserts the result.  API failures for
    individual games are logged and skipped so a single bad game does not
    block the rest.

    Returns:
        Number of boxscores successfully upserted.
    """
    today = date.today().isoformat()
    game_ids = db.session.scalars(
        db.select(Game.game_id).where(Game.game_date == today)
    ).all()

    if not game_ids:
        return 0

    now = datetime.now(timezone.utc)
    count = 0

    for game_id in game_ids:
        try:
            raw = nhl_client.get_boxscore(game_id)
        except Exception as exc:
            logger.warning('[boxscore] Failed to fetch game %s: %s', game_id, exc)
            continue

        record = _build_boxscore(raw, now)
        db.session.merge(record)
        count += 1

    db.session.commit()
    logger.info('[boxscore] Upserted %d boxscores for %s', count, today)
    return count
