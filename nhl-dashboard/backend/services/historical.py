"""Historical game ingestion from the NHL Stats REST API.

Source: GET https://api.nhle.com/stats/rest/en/game
Table:  nhl_historical_game (see models.NhlHistoricalGame)
"""
import logging

import nhl_client
from extensions import db
from models import NhlHistoricalGame

logger = logging.getLogger(__name__)


def ingest_historical_games() -> int:
    """Fetch all historical NHL games from the Stats API and upsert them.

    Uses db.session.merge() on game_id (PK) so repeated runs are idempotent —
    existing rows are updated in place and no duplicates are created.

    Returns:
        Number of rows processed.
    """
    rows = nhl_client.get_all_games()
    for raw in rows:
        record = NhlHistoricalGame(
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
            visiting_score=raw.get('visitingScore'),
            visiting_team_id=raw.get('visitingTeamId'),
        )
        db.session.merge(record)
    db.session.commit()
    logger.info("ingest_historical_games: upserted %d rows", len(rows))
    return len(rows)
