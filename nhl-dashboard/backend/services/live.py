"""Service for updating in-progress game state from boxscore data."""

from datetime import datetime, timezone

from app import db
import models
import nhl_client


def refresh_live() -> None:
    """Fetch boxscores for all live games and update their DB rows.

    Queries only games with status='live', fetches each boxscore from
    nhl_client, applies the updated fields, and commits once at the end.
    """
    live_games = db.session.query(models.Game).filter_by(status="live").all()
    for game in live_games:
        boxscore = nhl_client.get_game_boxscore(game.id)
        _apply_boxscore(game, boxscore)
    db.session.commit()


def _apply_boxscore(game: models.Game, boxscore: dict) -> None:
    """Write boxscore fields onto a Game row.

    Args:
        game: The Game ORM instance to update.
        boxscore: Boxscore dict from nhl_client.get_game_boxscore().
    """
    away = boxscore.get("awayTeam", {})
    home = boxscore.get("homeTeam", {})

    game.away_score = away.get("score", game.away_score)
    game.home_score = home.get("score", game.home_score)
    game.away_sog = away.get("sog", game.away_sog)
    game.home_sog = home.get("sog", game.home_sog)
    game.clock = boxscore.get("clock", {}).get("timeRemaining", game.clock)

    period_num = boxscore.get("periodDescriptor", {}).get("number")
    game.period = str(period_num) if period_num is not None else game.period

    game.updated_at = datetime.now(timezone.utc)
