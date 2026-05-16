"""NHL Dashboard Flask application factory."""
import requests
from flask import Flask, jsonify, render_template

from app.agents.nhl_client import (
    format_game,
    get_season_series,
    get_team_last_5,
    get_todays_games,
)


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

    def _format_game_with_history(game: dict) -> dict:
        """Enrich a raw game dict with team history and season series before formatting.

        Calls get_team_last_5 for both teams and get_season_series for the
        matchup.  Silently falls back to empty lists / None on API failure.

        Args:
            game: Raw game dict from the NHL scoreboard API.

        Returns:
            dict: Formatted game dict including away_last5, home_last5, and
                season_series.
        """
        away_abbrev = game.get("awayTeam", {}).get("abbrev", "")
        home_abbrev = game.get("homeTeam", {}).get("abbrev", "")
        try:
            away_hist = get_team_last_5(away_abbrev)
        except requests.HTTPError:
            away_hist = []
        try:
            home_hist = get_team_last_5(home_abbrev)
        except requests.HTTPError:
            home_hist = []
        try:
            series = get_season_series(away_abbrev, home_abbrev)
        except requests.HTTPError:
            series = None
        return format_game(
            game,
            away_history=away_hist,
            home_history=home_hist,
            season_series=series,
        )

    @app.route("/api/scores")
    def api_scores():
        """Return today's formatted NHL game scores as JSON for auto-refresh polling.

        Returns:
            Response: JSON array of formatted game dicts (keys: away, home,
                away_score, home_score, status, away_last5, home_last5).
                Returns an empty list with HTTP 200 when the upstream NHL API
                is unavailable, so the polling client does not break on
                transient failures.
        """
        try:
            raw_games = get_todays_games()
            return jsonify([_format_game_with_history(g) for g in raw_games])
        except requests.HTTPError:
            return jsonify([])

    @app.route("/dashboard")
    def dashboard():
        """Render today's NHL scoreboard as an HTML dashboard.

        Returns:
            Response: Rendered HTML page showing all of today's games grouped
                by status (live, final, upcoming). Falls back to an empty-state
                page if the NHL API is unavailable.
        """
        try:
            raw_games = get_todays_games()
        except requests.HTTPError:
            raw_games = []
        games = [_format_game_with_history(g) for g in raw_games]
        return render_template("dashboard.html", games=games)

    return app
