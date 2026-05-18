"""Service for fetching and upserting today's game slate."""

from datetime import datetime, timezone

from app import db
import models
import nhl_client

# Maps NHL API gameState values to internal status strings
_STATUS_MAP = {
    "FUT": "scheduled",
    "PRE": "scheduled",
    "LIVE": "live",
    "CRIT": "live",
    "OFF": "final",
    "FINAL": "final",
    "OFFICIAL": "final",
}


def refresh_slate() -> None:
    """Fetch today's schedule and upsert Game and Team rows.

    Calls nhl_client.get_schedule_today(), then for each game upserts
    the away/home Team rows and the Game row. Commits once at the end.
    Idempotent: safe to call multiple times.
    """
    games = nhl_client.get_schedule_today()
    for game_data in games:
        _upsert_teams(game_data)
        _upsert_game(game_data)
    db.session.commit()


def _upsert_teams(game_data: dict) -> None:
    """Upsert Team rows for the away and home teams in a game dict.

    Args:
        game_data: A game dict from the NHL schedule API.
    """
    for key in ("awayTeam", "homeTeam"):
        team_data = game_data.get(key, {})
        code = team_data.get("abbrev")
        if not code:
            continue
        team = db.session.get(models.Team, code)
        if team is None:
            team = models.Team(code=code)
            db.session.add(team)
        team.name = team_data.get("placeName", {}).get("default", code)


def _upsert_game(game_data: dict) -> None:
    """Upsert a single Game row from a schedule API game dict.

    Args:
        game_data: A game dict from the NHL schedule API.
    """
    game_id = game_data["id"]
    game_state = game_data.get("gameState", "FUT").upper()
    status = _STATUS_MAP.get(game_state, "scheduled")

    venue_raw = game_data.get("venue", {})
    venue = venue_raw.get("default", "") if isinstance(venue_raw, dict) else str(venue_raw)

    start_utc_str = game_data.get("startTimeUTC")
    start_utc = (
        datetime.fromisoformat(start_utc_str.replace("Z", "+00:00"))
        if start_utc_str
        else None
    )

    game = db.session.get(models.Game, game_id)
    if game is None:
        game = models.Game(id=game_id)
        db.session.add(game)

    game.away_code = game_data["awayTeam"]["abbrev"]
    game.home_code = game_data["homeTeam"]["abbrev"]
    game.status = status
    game.venue = venue
    game.start_utc = start_utc
    game.away_score = game_data.get("awayTeam", {}).get("score", 0) or 0
    game.home_score = game_data.get("homeTeam", {}).get("score", 0) or 0
    game.updated_at = datetime.now(timezone.utc)
