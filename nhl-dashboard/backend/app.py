"""Flask app factory."""

from flask import Flask, jsonify

from config import Config
from extensions import db
import models  # noqa: F401 — registers models with SQLAlchemy
from routes.health import health_bp
from routes.games import games_bp
from routes.game_detail import game_detail_bp
from routes.logos import logos_bp


def create_app(test_config=None):
    """Create and configure the Flask application.

    Args:
        test_config: Optional dict of config overrides (used in tests).

    Returns:
        Configured Flask app instance.
    """
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    if test_config is not None:
        app.config.update(test_config)

    db.init_app(app)

    if not app.config.get("TESTING"):
        with app.app_context():
            db.create_all()

        from scheduler import _scheduler, init_scheduler
        init_scheduler(app)
        _scheduler.start()

    app.register_blueprint(health_bp)
    app.register_blueprint(games_bp)
    app.register_blueprint(game_detail_bp)
    app.register_blueprint(logos_bp)

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "not_found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "server_error"}), 500

    return app
