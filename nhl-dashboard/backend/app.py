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

    # Global JSON error handlers — prevent Flask from returning HTML error pages
    from flask import jsonify as _jsonify

    @app.errorhandler(404)
    def not_found(exc):
        return _jsonify({'error': 'not_found', 'message': 'The requested resource was not found'}), 404

    @app.errorhandler(500)
    def internal_server_error(exc):
        return _jsonify({'error': 'internal_server_error', 'message': 'An unexpected error occurred'}), 500

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

    @app.cli.command("backfill-historical")
    def backfill_historical_cmd():
        """One-time backfill: upsert all available NHL historical games into the game table."""
        import click
        from services.historical import ingest_historical_games
        count = ingest_historical_games()
        click.echo(f"Backfilled {count} historical games.")

    @app.cli.command("migrate-game-table")
    def migrate_game_table_cmd():
        """Migration (Issue #131): DROP legacy game table, RENAME nhl_historical_game → game.

        Run this once against a production DB that was created before Issue #131.
        Both steps execute in a single transaction to avoid naming conflicts.
        After migration, run db.create_all() (or restart the app) to create live_game.
        """
        import click
        from sqlalchemy import text
        try:
            with db.engine.begin() as conn:
                conn.execute(text("DROP TABLE IF EXISTS game"))
                conn.execute(text("ALTER TABLE nhl_historical_game RENAME TO game"))
            click.echo("Migration complete: dropped legacy 'game', renamed 'nhl_historical_game' → 'game'.")
        except Exception as exc:
            click.echo(f"Migration failed: {exc}", err=True)
            raise SystemExit(1)

    return app


app = create_app()
