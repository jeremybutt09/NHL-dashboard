"""Game detail blueprint — GET /api/games/<id>."""

from flask import Blueprint, jsonify

from extensions import db
from models import Game
from routes.games import _build_game_row

game_detail_bp = Blueprint("game_detail", __name__)


@game_detail_bp.route("/api/games/<int:game_id>")
def game_detail(game_id: int):
    """Return detail for a single game.

    Returns the same shape as one row from GET /api/games/today.
    Richer v1+ fields (goal scorers, period-by-period score) are
    omitted; live fields are empty when the game is not in progress.

    Args:
        game_id: NHL game ID.

    Returns:
        JSON game row, or 404 JSON if the game is not found.
    """
    game = db.session.get(Game, game_id)
    if game is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(_build_game_row(game))
