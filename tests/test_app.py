"""Tests for the Flask application scaffold (Issue #2) and routes (Issue #3)."""
import pytest
import requests
from unittest.mock import patch
from app import create_app


@pytest.fixture
def app():
    """Create a Flask app configured for testing."""
    app = create_app({"TESTING": True})
    return app


@pytest.fixture
def client(app):
    """Return a test client for the app."""
    return app.test_client()


def test_create_app_returns_flask_app(app):
    """create_app returns a Flask application instance."""
    from flask import Flask
    assert isinstance(app, Flask)


def test_app_is_in_testing_mode(app):
    """create_app sets TESTING flag when provided in config."""
    assert app.testing is True


def test_health_endpoint_returns_200(client):
    """GET /health responds with HTTP 200."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_endpoint_returns_json(client):
    """GET /health returns a JSON body with status ok."""
    response = client.get("/health")
    data = response.get_json()
    assert data is not None
    assert data.get("status") == "ok"


# ---------------------------------------------------------------------------
# /games endpoint (Issue #3)
# ---------------------------------------------------------------------------

MOCK_GAMES = [
    {
        "id": 2,
        "gameDate": "2026-05-11",
        "homeTeam": {"abbrev": "TOR"},
        "awayTeam": {"abbrev": "MTL"},
        "gameState": "LIVE",
    }
]


def test_games_endpoint_returns_200(client):
    """GET /games responds with HTTP 200 on a successful NHL API call."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        from unittest.mock import MagicMock
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "focusedDate": "2026-05-11",
            "gamesByDate": [{"date": "2026-05-11", "games": MOCK_GAMES}],
        }
        mock_get.return_value = mock_resp

        response = client.get("/games")

        assert response.status_code == 200


def test_games_endpoint_returns_game_list(client):
    """GET /games returns a JSON list of today's games."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        from unittest.mock import MagicMock
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "focusedDate": "2026-05-11",
            "gamesByDate": [{"date": "2026-05-11", "games": MOCK_GAMES}],
        }
        mock_get.return_value = mock_resp

        response = client.get("/games")
        data = response.get_json()

        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == 2


def test_games_endpoint_returns_502_on_http_error(client):
    """GET /games returns HTTP 502 when the NHL API responds with an error."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        from unittest.mock import MagicMock
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("503 Service Unavailable")
        mock_get.return_value = mock_resp

        response = client.get("/games")

        assert response.status_code == 502


# ---------------------------------------------------------------------------
# /api/scores endpoint (Issue #5 — auto-refresh data source)
# ---------------------------------------------------------------------------


def test_api_scores_endpoint_returns_200(client):
    """GET /api/scores responds with HTTP 200 on a successful NHL API call."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        from unittest.mock import MagicMock
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "focusedDate": "2026-05-11",
            "gamesByDate": [{"date": "2026-05-11", "games": MOCK_GAMES}],
        }
        mock_get.return_value = mock_resp

        response = client.get("/api/scores")

        assert response.status_code == 200


def test_api_scores_endpoint_returns_formatted_games(client):
    """GET /api/scores returns a JSON list of formatted game dicts."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        from unittest.mock import MagicMock
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "focusedDate": "2026-05-11",
            "gamesByDate": [{"date": "2026-05-11", "games": MOCK_GAMES}],
        }
        mock_get.return_value = mock_resp

        response = client.get("/api/scores")
        data = response.get_json()

        assert isinstance(data, list)
        assert len(data) == 1
        game = data[0]
        assert "away" in game
        assert "home" in game
        assert "away_score" in game
        assert "home_score" in game
        assert "status" in game


def test_api_scores_endpoint_returns_empty_list_on_http_error(client):
    """GET /api/scores returns HTTP 200 with an empty list when the NHL API fails."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        from unittest.mock import MagicMock
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("503 Service Unavailable")
        mock_get.return_value = mock_resp

        response = client.get("/api/scores")
        data = response.get_json()

        assert response.status_code == 200
        assert data == []


# ---------------------------------------------------------------------------
# Dashboard auto-refresh JavaScript (Issue #5)
# ---------------------------------------------------------------------------


def test_dashboard_contains_auto_refresh_script(client):
    """GET /dashboard HTML includes JavaScript that polls /api/scores."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        from unittest.mock import MagicMock
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "focusedDate": "2026-05-11",
            "gamesByDate": [{"date": "2026-05-11", "games": []}],
        }
        mock_get.return_value = mock_resp

        response = client.get("/dashboard")
        html = response.data.decode("utf-8")

        assert "setInterval" in html
        assert "/api/scores" in html


def test_dashboard_auto_refresh_interval_value_present(client):
    """GET /dashboard HTML includes the 30-second polling interval value."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        from unittest.mock import MagicMock
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "focusedDate": "2026-05-11",
            "gamesByDate": [{"date": "2026-05-11", "games": []}],
        }
        mock_get.return_value = mock_resp

        response = client.get("/dashboard")
        html = response.data.decode("utf-8")

        assert "30000" in html


# ---------------------------------------------------------------------------
# Dashboard money line odds display (Issue #6)
# ---------------------------------------------------------------------------

MOCK_GAME_WITH_ODDS = {
    "id": 5,
    "gameDate": "2026-05-11",
    "homeTeam": {"abbrev": "TOR", "score": 2},
    "awayTeam": {"abbrev": "MTL", "score": 1},
    "gameState": "LIVE",
    "odds": [{"providerId": 1, "awayOdds": -120, "homeOdds": 105}],
}

MOCK_GAME_WITHOUT_ODDS = {
    "id": 6,
    "gameDate": "2026-05-11",
    "homeTeam": {"abbrev": "NYR"},
    "awayTeam": {"abbrev": "BOS"},
    "gameState": "PRE",
}


def test_dashboard_displays_odds_when_available(client):
    """GET /dashboard renders money line odds values when game has odds."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        from unittest.mock import MagicMock
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "focusedDate": "2026-05-11",
            "gamesByDate": [{"date": "2026-05-11", "games": [MOCK_GAME_WITH_ODDS]}],
        }
        mock_get.return_value = mock_resp

        response = client.get("/dashboard")
        html = response.data.decode("utf-8")

        assert "-120" in html
        assert "105" in html


def test_dashboard_graceful_when_odds_missing(client):
    """GET /dashboard renders without error when game has no odds."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        from unittest.mock import MagicMock
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "focusedDate": "2026-05-11",
            "gamesByDate": [{"date": "2026-05-11", "games": [MOCK_GAME_WITHOUT_ODDS]}],
        }
        mock_get.return_value = mock_resp

        response = client.get("/dashboard")

        assert response.status_code == 200


def test_api_scores_includes_odds_fields(client):
    """GET /api/scores returns away_ml and home_ml keys in each game dict."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        from unittest.mock import MagicMock
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "focusedDate": "2026-05-11",
            "gamesByDate": [{"date": "2026-05-11", "games": [MOCK_GAME_WITH_ODDS]}],
        }
        mock_get.return_value = mock_resp

        response = client.get("/api/scores")
        data = response.get_json()

        assert len(data) == 1
        assert "away_ml" in data[0]
        assert "home_ml" in data[0]
