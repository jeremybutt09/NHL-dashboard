from flask import Blueprint, jsonify, current_app, request
from services.slate import build_today_response

games_bp = Blueprint('games', __name__)


@games_bp.get('/api/games/today')
def games_today():
    """Return today's game slate with odds and probabilities.

    Query params:
        partner_id: Optional int.  When provided, odds come from nhl_odds_line
            filtered to that partner rather than the consensus OddsSnapshot.

    Returns:
        200 JSON with games array on success, 500 JSON on unexpected error.
    """
    try:
        partner_id_raw = request.args.get('partner_id')
        partner_id = int(partner_id_raw) if partner_id_raw else None
        date = request.args.get('date')  # optional YYYY-MM-DD
        return jsonify(build_today_response(partner_id=partner_id, date=date))
    except Exception as exc:
        current_app.logger.exception("Unhandled error in /api/games/today")
        return jsonify({
            'error': 'internal_server_error',
            'message': str(exc),
        }), 500
