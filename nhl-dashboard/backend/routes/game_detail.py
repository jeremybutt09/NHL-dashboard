from flask import Blueprint, jsonify

game_detail_bp = Blueprint('game_detail', __name__)


@game_detail_bp.get('/api/games/<game_id>')
def game_detail(game_id):
    """Return detail for a single game.

    Args:
        game_id: Game identifier from the URL path.

    Returns:
        200 JSON stub on success, 400 JSON if game_id is not an integer.
    """
    try:
        game_id_int = int(game_id)
    except ValueError:
        return jsonify({
            'error': 'bad_request',
            'message': f'game_id must be an integer, got: {game_id!r}',
        }), 400
    # v1 stub — full detail endpoint not required for the dashboard
    return jsonify({'game_id': game_id_int, 'detail': 'not implemented in v1'})
