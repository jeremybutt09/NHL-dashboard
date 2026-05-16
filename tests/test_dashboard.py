"""Tests for the /dashboard route and format_game helper (Issue #4)."""
import pytest
from unittest.mock import MagicMock, patch

from app import create_app
from app.agents.nhl_client import format_game


# ---------------------------------------------------------------------------
# Fixtures / shared test data
# ---------------------------------------------------------------------------

@pytest.fixture
def app():
    """Create a Flask app configured for testing."""
    return create_app({"TESTING": True})


@pytest.fixture
def client(app):
    """Return a test client for the app."""
    return app.test_client()


LIVE_GAME = {
    "id": 1,
    "gameDate": "2026-05-16",
    "homeTeam": {"abbrev": "TOR", "score": 3},
    "awayTeam": {"abbrev": "MTL", "score": 1},
    "gameState": "LIVE",
}

CRIT_GAME = {
    "id": 2,
    "gameDate": "2026-05-16",
    "homeTeam": {"abbrev": "NYR", "score": 2},
    "awayTeam": {"abbrev": "BOS", "score": 2},
    "gameState": "CRIT",
}

FINAL_GAME = {
    "id": 3,
    "gameDate": "2026-05-16",
    "homeTeam": {"abbrev": "EDM", "score": 4},
    "awayTeam": {"abbrev": "VAN", "score": 2},
    "gameState": "OFF",
}

UPCOMING_GAME = {
    "id": 4,
    "gameDate": "2026-05-16",
    "homeTeam": {"abbrev": "FLA", "score": 0},
    "awayTeam": {"abbrev": "CAR", "score": 0},
    "gameState": "PRE",
}

MOCK_GAMES = [LIVE_GAME, CRIT_GAME, FINAL_GAME, UPCOMING_GAME]


# ---------------------------------------------------------------------------
# format_game unit tests
# ---------------------------------------------------------------------------

def test_format_game_live_state_returns_live_status():
    """format_game maps gameState LIVE to status 'live'."""
    result = format_game(LIVE_GAME)
    assert result["status"] == "live"


def test_format_game_crit_state_returns_live_status():
    """format_game maps gameState CRIT to status 'live'."""
    result = format_game(CRIT_GAME)
    assert result["status"] == "live"


def test_format_game_off_state_returns_final_status():
    """format_game maps gameState OFF to status 'final'."""
    result = format_game(FINAL_GAME)
    assert result["status"] == "final"


def test_format_game_pre_state_returns_upcoming_status():
    """format_game maps gameState PRE to status 'upcoming'."""
    result = format_game(UPCOMING_GAME)
    assert result["status"] == "upcoming"


def test_format_game_extracts_team_abbreviations():
    """format_game extracts home and away team abbreviations."""
    result = format_game(LIVE_GAME)
    assert result["home"] == "TOR"
    assert result["away"] == "MTL"


def test_format_game_extracts_scores():
    """format_game extracts home and away scores."""
    result = format_game(LIVE_GAME)
    assert result["home_score"] == 3
    assert result["away_score"] == 1


def test_format_game_defaults_score_to_zero_when_missing():
    """format_game defaults score to 0 when score key is absent (pre-game)."""
    game = {"gameState": "PRE", "homeTeam": {"abbrev": "FLA"}, "awayTeam": {"abbrev": "CAR"}}
    result = format_game(game)
    assert result["home_score"] == 0
    assert result["away_score"] == 0


# ---------------------------------------------------------------------------
# /dashboard route tests
# ---------------------------------------------------------------------------

def test_dashboard_returns_200(client):
    """GET /dashboard responds with HTTP 200."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"games": MOCK_GAMES}
        mock_get.return_value = mock_resp

        response = client.get("/dashboard")

        assert response.status_code == 200


def test_dashboard_returns_html(client):
    """GET /dashboard returns an HTML response."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"games": MOCK_GAMES}
        mock_get.return_value = mock_resp

        response = client.get("/dashboard")

        assert b"html" in response.data.lower()


def test_dashboard_shows_team_abbreviations(client):
    """GET /dashboard renders team abbreviations for each game."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"games": MOCK_GAMES}
        mock_get.return_value = mock_resp

        response = client.get("/dashboard")
        body = response.data

        assert b"TOR" in body
        assert b"MTL" in body
        assert b"EDM" in body


def test_dashboard_live_game_marked_as_live(client):
    """GET /dashboard marks live games with a 'live' indicator."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"games": [LIVE_GAME]}
        mock_get.return_value = mock_resp

        response = client.get("/dashboard")

        assert b"live" in response.data.lower()


def test_dashboard_shows_empty_state_when_no_games(client):
    """GET /dashboard shows a no-games message when the schedule is empty."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"games": []}
        mock_get.return_value = mock_resp

        response = client.get("/dashboard")

        assert response.status_code == 200
        assert b"No games" in response.data


def test_dashboard_returns_200_when_nhl_api_fails(client):
    """GET /dashboard returns 200 with empty state when NHL API fails."""
    import requests as req
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req.HTTPError("503")
        mock_get.return_value = mock_resp

        response = client.get("/dashboard")

        assert response.status_code == 200
        assert b"No games" in response.data
