from flask import Blueprint, jsonify
from extensions import db
import scheduler as _sched

health_bp = Blueprint('health', __name__)


@health_bp.get('/api/health')
def health():
    """Check database connectivity and return scheduler poll status.

    Returns:
        200 JSON with status "ok" when DB is reachable, 500 JSON with
        status "error" when the DB execute probe fails.
    """
    try:
        db.session.execute(db.text('SELECT 1'))
    except Exception:
        return jsonify({'status': 'error', 'db': 'unavailable', 'last_poll': None}), 500

    last = _sched.last_poll_time
    return jsonify({
        'status': 'ok',
        'db': 'connected',
        'last_poll': last.isoformat() + 'Z' if last else None,
    }), 200
