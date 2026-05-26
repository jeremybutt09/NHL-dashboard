"""Historical game ingestion from the NHL Stats REST API.

Source: GET https://api.nhle.com/stats/rest/en/game
Table:  game (see models.Game — renamed from nhl_historical_game in Issue #131)

Refresh cadence:
  - Full ingest: ingest_historical_games() — run once manually to backfill all history.
  - Daily refresh: refresh_recent_historical_games() — scheduled daily at 08:00 UTC,
    after overnight games have completed. Compares only the last 30 days of games
    against the DB and upserts rows whose fields have changed.
"""
import logging
from datetime import date, timedelta

import nhl_client
from extensions import db
from models import Game

logger = logging.getLogger(__name__)

_REFRESH_WINDOW_DAYS = 30


def ingest_historical_games() -> int:
    """Fetch all historical NHL games from the Stats API and upsert them.

    Uses db.session.merge() on game_id (PK) so repeated runs are idempotent —
    existing rows are updated in place and no duplicates are created.

    Returns:
        Number of rows processed.
    """
    rows = nhl_client.get_all_games()
    for raw in rows:
        record = Game(
            game_id=raw['id'],
            eastern_start_time=raw.get('easternStartTime'),
            game_date=raw.get('gameDate'),
            game_number=raw.get('gameNumber'),
            game_schedule_state_id=raw.get('gameScheduleStateId'),
            game_state_id=raw.get('gameStateId'),
            game_type=raw.get('gameType'),
            home_score=raw.get('homeScore'),
            home_team_id=raw.get('homeTeamId'),
            period=raw.get('period'),
            season=raw.get('season'),
            away_score=raw.get('visitingScore'),
            away_team_id=raw.get('visitingTeamId'),
        )
        db.session.merge(record)
    db.session.commit()
    logger.info("ingest_historical_games: upserted %d rows", len(rows))
    return len(rows)


def _fields_changed(existing: Game, raw: dict) -> bool:
    """Return True if any mapped API field differs from the stored row.

    Args:
        existing: The current Game row from the database.
        raw: A game dict from the NHL Stats REST API response.

    Returns:
        True if at least one field differs; False if all fields match.
    """
    return (
        existing.eastern_start_time != raw.get('easternStartTime')
        or existing.game_date != raw.get('gameDate')
        or existing.game_number != raw.get('gameNumber')
        or existing.game_schedule_state_id != raw.get('gameScheduleStateId')
        or existing.game_state_id != raw.get('gameStateId')
        or existing.game_type != raw.get('gameType')
        or existing.home_score != raw.get('homeScore')
        or existing.home_team_id != raw.get('homeTeamId')
        or existing.period != raw.get('period')
        or existing.season != raw.get('season')
        or existing.away_score != raw.get('visitingScore')
        or existing.away_team_id != raw.get('visitingTeamId')
    )


def refresh_recent_historical_games() -> int:
    """Fetch all NHL games and upsert only those within the last 30 days.

    Optimized daily refresh that avoids scanning the full historical dataset.
    For each game in the 30-day window, the API response is compared against
    the existing DB row. Rows with changed fields are updated; unchanged rows
    are left as-is. New games (not yet in the DB) are inserted.

    Scheduled daily at 08:00 UTC after overnight games have completed.

    Returns:
        Number of games evaluated within the 30-day window.
    """
    cutoff = (date.today() - timedelta(days=_REFRESH_WINDOW_DAYS)).isoformat()

    all_games = nhl_client.get_all_games()
    recent = [g for g in all_games if (g.get('gameDate') or '') >= cutoff]

    # Load existing rows for the window into a dict keyed by game_id
    existing_ids = {g['id'] for g in recent}
    existing_rows: dict[int, Game] = {}
    if existing_ids:
        rows_in_db = db.session.scalars(
            db.select(Game).where(
                Game.game_id.in_(existing_ids)
            )
        ).all()
        existing_rows = {r.game_id: r for r in rows_in_db}

    updated = 0
    for raw in recent:
        game_id = raw['id']
        existing = existing_rows.get(game_id)
        if existing is None or _fields_changed(existing, raw):
            record = Game(
                game_id=game_id,
                eastern_start_time=raw.get('easternStartTime'),
                game_date=raw.get('gameDate'),
                game_number=raw.get('gameNumber'),
                game_schedule_state_id=raw.get('gameScheduleStateId'),
                game_state_id=raw.get('gameStateId'),
                game_type=raw.get('gameType'),
                home_score=raw.get('homeScore'),
                home_team_id=raw.get('homeTeamId'),
                period=raw.get('period'),
                season=raw.get('season'),
                away_score=raw.get('visitingScore'),
                away_team_id=raw.get('visitingTeamId'),
            )
            db.session.merge(record)
        updated += 1

    db.session.commit()
    logger.info(
        "refresh_recent_historical_games: evaluated %d games in %d-day window",
        updated, _REFRESH_WINDOW_DAYS,
    )
    return updated
