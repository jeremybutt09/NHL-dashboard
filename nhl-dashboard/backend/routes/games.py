"""Games blueprint — GET /api/games/today."""

from datetime import datetime, timezone

from flask import Blueprint, jsonify

from extensions import db
from models import Game, Team
from odds_client import get_odds

games_bp = Blueprint("games", __name__)


def _build_game_row(game: Game) -> dict:
    """Serialize a Game model row into the API response shape.

    Args:
        game: SQLAlchemy Game instance.

    Returns:
        Dict matching the HANDOFF.md §4 game row shape.
    """
    away_team = db.session.get(Team, game.away_code)
    home_team = db.session.get(Team, game.home_code)
    odds = get_odds(game.id)

    live = None
    if game.status in ("live", "final"):
        live = {
            "period": game.period,
            "clock": game.clock,
            "away_score": game.away_score,
            "home_score": game.home_score,
            "away_sog": game.away_sog,
            "home_sog": game.home_sog,
        }

    return {
        "id": game.id,
        "away": {
            "code": game.away_code,
            "name": away_team.name if away_team else "",
            "record": (
                f"{away_team.wins}-{away_team.losses}-{away_team.ot_losses}"
                if away_team else ""
            ),
            "l10": (
                f"{away_team.l10_wins}-{away_team.l10_losses}-{away_team.l10_ot_losses}"
                if away_team else ""
            ),
        },
        "home": {
            "code": game.home_code,
            "name": home_team.name if home_team else "",
            "record": (
                f"{home_team.wins}-{home_team.losses}-{home_team.ot_losses}"
                if home_team else ""
            ),
            "l10": (
                f"{home_team.l10_wins}-{home_team.l10_losses}-{home_team.l10_ot_losses}"
                if home_team else ""
            ),
        },
        "start": game.start_utc.strftime("%Y-%m-%dT%H:%M:%SZ") if game.start_utc else None,
        "venue": game.venue,
        "status": game.status,
        "live": live,
        "ml": odds["ml"],
        "ml_open": odds["ml_open"],
        "implied": odds["implied"],
        "fair": odds["fair"],
        "edge": odds["edge"],
        "movement_24h": odds["movement_24h"],
    }


@games_bp.route("/api/games/today")
def games_today():
    """Return today's NHL slate with odds and implied probabilities.

    Returns:
        JSON with updated_at timestamp and a games array. Each game row
        includes id, away, home, start, venue, status, live, ml, ml_open,
        implied, fair, edge, and movement_24h.
    """
    games = Game.query.all()
    return jsonify({
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "games": [_build_game_row(g) for g in games],
    })
