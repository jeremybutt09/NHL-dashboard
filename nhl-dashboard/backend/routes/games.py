from flask import Blueprint, jsonify, current_app
from services.slate import build_today_response

games_bp = Blueprint('games', __name__)


@games_bp.get('/api/games/today')
def games_today():
    """Return today's game slate with odds and probabilities.

    Returns:
        200 JSON with games array on success, 500 JSON on unexpected error.
    """
    try:
        return jsonify(build_today_response())
    except Exception as exc:
        current_app.logger.exception("Unhandled error in /api/games/today")
        return jsonify({
            'error': 'internal_server_error',
            'message': str(exc),
        }), 500
