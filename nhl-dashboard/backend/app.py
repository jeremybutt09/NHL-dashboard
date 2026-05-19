from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()


def create_app(config=None):
    """Application factory.

    Args:
        config: Optional dict of config overrides (e.g. for testing).

    Returns:
        Configured Flask application instance.
    """
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.update(config)

    db.init_app(app)

    from routes.health import health_bp
    from routes.games import games_bp
    app.register_blueprint(health_bp)
    app.register_blueprint(games_bp)

    with app.app_context():
        import models  # noqa: F401 — registers models with SQLAlchemy metadata
        db.create_all()

    import scheduler
    scheduler.init_scheduler(app)

    return app
