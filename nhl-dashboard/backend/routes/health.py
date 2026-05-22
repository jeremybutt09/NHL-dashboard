"""Health check blueprint."""

from flask import Blueprint, jsonify
from sqlalchemy import text

health_bp = Blueprint("health", __name__)


@health_bp.route("/api/health")
def health():
    """Return service health status including a live DB connectivity check.

    Returns:
        JSON with ok, db, and last_poll fields.
    """
    from extensions import db
    from scheduler import get_last_poll

    last_poll = get_last_poll()

    try:
        db.session.execute(text("SELECT 1"))
        db_status = "connected"
        ok = True
    except Exception:
        db_status = "error"
        ok = False

    return jsonify({
        "ok": ok,
        "db": db_status,
        "last_poll": last_poll.isoformat() if last_poll else None,
    })
