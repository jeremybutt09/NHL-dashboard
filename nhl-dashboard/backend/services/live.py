"""Live score updater — polls NHL boxscore for in-progress games."""

import logging
from datetime import datetime, timezone

from extensions import db
from models import Game

logger = logging.getLogger(__name__)


def update_live_scores(client=None) -> None:
    """Update period, clock, scores, and SOG for all live games.

    For each Game where status == 'live', calls nhl_client.get_boxscore()
    and writes period, clock, away_score, home_score, away_sog, home_sog,
    and updated_at back to the database.

    Args:
        client: NhlClient instance. Defaults to the module-level singleton.
    """
    if client is None:
        from nhl_client import nhl_client as _default
        client = _default

    live_games = Game.query.filter_by(status="live").all()

    for game in live_games:
        boxscore = client.get_boxscore(game.id)
        if boxscore is None:
            logger.warning("update_live_scores: no boxscore for game %s", game.id)
            continue

        game.period = boxscore.get("period")
        game.clock = boxscore.get("clock")
        game.away_score = boxscore.get("away_score", 0)
        game.home_score = boxscore.get("home_score", 0)
        game.away_sog = boxscore.get("away_sog", 0)
        game.home_sog = boxscore.get("home_sog", 0)
        game.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    db.session.commit()
