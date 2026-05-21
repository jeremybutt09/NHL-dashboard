"""Health check blueprint."""

from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.route("/api/health")
def health():
    """Return service health status.

    Returns:
        JSON with ok, db, and last_poll fields.
    """
    from scheduler import get_last_poll
    last_poll = get_last_poll()
    return jsonify({
        "ok": True,
        "db": "connected",
        "last_poll": last_poll.isoformat() if last_poll else None,
    })
