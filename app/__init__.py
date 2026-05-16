"""NHL Dashboard Flask application factory."""
import requests
from flask import Flask, jsonify

from app.agents.nhl_client import get_todays_games


def create_app(test_config: dict | None = None) -> Flask:
    """Create and configure the Flask application.

    Args:
        test_config: Optional dict of config values to override defaults.
            Typically used in tests to set TESTING=True or override secrets.

    Returns:
        Flask: A configured Flask application instance.
    """
    app = Flask(__name__)

    if test_config:
        app.config.update(test_config)

    @app.route("/health")
    def health():
        """Return a simple health-check response.

        Returns:
            Response: JSON body ``{"status": "ok"}`` with HTTP 200.
        """
        return jsonify({"status": "ok"})

    @app.route("/games")
    def games():
        """Return today's NHL games from the scoreboard API.

        Returns:
            Response: JSON array of game objects with HTTP 200, or a JSON
                error body with HTTP 502 if the upstream NHL API fails.
        """
        try:
            return jsonify(get_todays_games())
        except requests.HTTPError as exc:
            return jsonify({"error": str(exc)}), 502

    return app
