import logging
import os
from flask import Flask
from extensions import db
from config import Config


def _configure_logging():
    """Set root logger level from FLASK_LOG_LEVEL and add a StreamHandler if none exist."""
    level_name = os.environ.get("FLASK_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        root.addHandler(handler)


def create_app(config_class=Config, test_config=None):
    _configure_logging()
    """Create and configure the Flask application.

    Args:
        config_class: Configuration class to load defaults from.
        test_config: Optional dict of overrides applied after config_class,
            used by the test suite to inject TESTING=True and an in-memory DB.
    """
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    if test_config is not None:
        app.config.from_mapping(test_config)

    # Ensure instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)

    # Extensions
    db.init_app(app)

    with app.app_context():
        # Import models so SQLAlchemy registers them before create_all
        import models  # noqa: F401
        db.create_all()

    # Blueprints
    from routes.health import health_bp
    from routes.games import games_bp
    from routes.game_detail import game_detail_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(games_bp)
    app.register_blueprint(game_detail_bp)

    # CORS headers for Vite dev server
    @app.after_request
    def add_cors(response):
        response.headers['Access-Control-Allow-Origin'] = 'http://localhost:5173'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    # Start background scheduler (skip in test env)
    if app.config.get('ENV') != 'testing' and not app.config.get('TESTING'):
        from scheduler import start_scheduler
        start_scheduler(app)

    return app


app = create_app()
