"""Flask app factory."""

from flask import Flask

from config import Config
from routes.health import health_bp
from routes.games import games_bp
from routes.game_detail import game_detail_bp


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

    app.register_blueprint(health_bp)
    app.register_blueprint(games_bp)
    app.register_blueprint(game_detail_bp)

    return app
