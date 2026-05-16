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
