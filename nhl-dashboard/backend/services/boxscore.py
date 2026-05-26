"""Boxscore ingestion from the NHL Web API.

Source: GET https://api-web.nhle.com/v1/gamecenter/{game_id}/boxscore
Table:  boxscore (see models.Boxscore — Issue #133)

Refresh cadence: every POLL_BOXSCORE_INTERVAL seconds (default 60 s) via
APScheduler, so live score/SOG/period data stays current during games.

Today's game IDs are resolved by querying the `game` table, which is
populated by the historical ingest pipeline (models.Game).

backfill_boxscores() (Issue #135) is a one-time (but re-runnable) operation
that fetches a boxscore for every game_id in the `game` table, not just today.
"""
import logging
import time
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import nhl_client
from extensions import db
from models import Boxscore, Game
from services.time_utils import now_et

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

    now = now_et()
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


# 300 ms between requests — polite rate-limiting for long backfill runs.
_BACKFILL_DELAY_SECONDS: float = 0.3


def backfill_boxscores(
    delay: float = _BACKFILL_DELAY_SECONDS,
    season: int | None = None,
) -> int:
    """Fetch and upsert boxscore data for every game in the game table.

    One-time (but re-runnable) backfill.  Iterates game_ids in the
    ``game`` table (optionally filtered to a single season), calls
    ``/v1/gamecenter/{id}/boxscore`` for each, and upserts the result.
    API failures for individual games are logged and skipped so a single
    bad game does not abort the run.  Commits in batches of 100 to bound
    transaction size.

    Args:
        delay: Seconds to sleep between successive API calls.  Defaults to
            ``_BACKFILL_DELAY_SECONDS`` (0.3 s).  Pass ``0`` in tests to
            keep runs fast.
        season: Optional season integer (e.g. ``20252026``).  When set, only
            games whose ``season`` column matches are processed.  Omit or
            pass ``None`` to process the full table.

    Returns:
        Number of boxscores successfully upserted.
    """
    query = db.select(Game.game_id)
    if season is not None:
        query = query.where(Game.season == season)
    game_ids = db.session.scalars(query).all()

    if not game_ids:
        return 0

    total = len(game_ids)
    now = now_et()
    count = 0
    skipped = 0

    for i, game_id in enumerate(game_ids):
        try:
            raw = nhl_client.get_boxscore(game_id)
        except Exception as exc:
            logger.warning('[backfill_boxscores] Failed to fetch game %s: %s', game_id, exc)
            skipped += 1
            time.sleep(delay)
            continue

        if not raw or 'id' not in raw:
            logger.warning('[backfill_boxscores] No data for game_id %s, skipping', game_id)
            skipped += 1
            time.sleep(delay)
            continue

        record = _build_boxscore(raw, now)
        db.session.merge(record)
        count += 1

        # Commit every 100 rows to avoid holding an unbounded transaction.
        if (i + 1) % 100 == 0:
            db.session.commit()
            logger.info('[backfill_boxscores] Progress: %d/%d', i + 1, total)

        time.sleep(delay)

    db.session.commit()
    season_label = str(season) if season is not None else 'all'
    logger.info(
        '[backfill_boxscores] Season %s: %d upserted, %d skipped',
        season_label, count, skipped,
    )
    return count
