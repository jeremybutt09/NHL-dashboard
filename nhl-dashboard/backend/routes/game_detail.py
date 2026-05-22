"""Game detail blueprint — GET /api/games/<id>."""

from flask import Blueprint, jsonify

from extensions import db
from models import Game
from nhl_client import nhl_client
from routes.games import _build_game_row

game_detail_bp = Blueprint("game_detail", __name__)


@game_detail_bp.route("/api/games/<int:game_id>")
def game_detail(game_id: int):
    """Return detail for a single game including season series record.

    Returns the same shape as one row from GET /api/games/today plus a
    'series' key with the head-to-head season record between the two teams.

    Args:
        game_id: NHL game ID.

    Returns:
        JSON game row with series field, or 404 JSON if the game is not found.
    """
    game = db.session.get(Game, game_id)
    if game is None:
        return jsonify({"error": "not found"}), 404
    row = _build_game_row(game)
    row["series"] = nhl_client.get_series(game.away_code, game.home_code)
    return jsonify(row)
