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


# ---------------------------------------------------------------------------
# Team last-5 history on dashboard (Issue #7)
# ---------------------------------------------------------------------------

MOCK_GAME_FOR_HISTORY = {
    "id": 7,
    "gameDate": "2026-05-11",
    "homeTeam": {"abbrev": "TOR", "score": 3},
    "awayTeam": {"abbrev": "MTL", "score": 1},
    "gameState": "LIVE",
}

_SINGLE_COMPLETED_GAME = {
    "id": 200, "gameDate": "2026-04-01", "gameState": "FINAL",
    "homeTeam": {"abbrev": "TOR", "score": 4},
    "awayTeam": {"abbrev": "MTL", "score": 2},
}


def _make_fake_get(scoreboard_data, schedule_data):
    """Return a side_effect callable that dispatches mock responses by URL."""
    from unittest.mock import MagicMock

    def fake_get(url):
        mock = MagicMock()
        if "scoreboard" in url:
            mock.json.return_value = scoreboard_data
        else:
            mock.json.return_value = schedule_data
        return mock

    return fake_get


def test_dashboard_includes_last5_fields(client):
    """GET /dashboard renders win/loss history for each team in each game."""
    scoreboard = {
        "focusedDate": "2026-05-11",
        "gamesByDate": [{"date": "2026-05-11", "games": [MOCK_GAME_FOR_HISTORY]}],
    }
    schedule = {"games": [_SINGLE_COMPLETED_GAME]}

    with patch(
        "app.agents.nhl_client.requests.get",
        side_effect=_make_fake_get(scoreboard, schedule),
    ):
        response = client.get("/dashboard")
        html = response.data.decode("utf-8")

        assert response.status_code == 200
        assert "4-2" in html


def test_dashboard_history_shows_win_result(client):
    """GET /dashboard shows W for a won game in team history."""
    scoreboard = {
        "focusedDate": "2026-05-11",
        "gamesByDate": [{"date": "2026-05-11", "games": [MOCK_GAME_FOR_HISTORY]}],
    }
    schedule = {"games": [_SINGLE_COMPLETED_GAME]}

    with patch(
        "app.agents.nhl_client.requests.get",
        side_effect=_make_fake_get(scoreboard, schedule),
    ):
        response = client.get("/dashboard")
        html = response.data.decode("utf-8")

        assert "W" in html


def test_dashboard_graceful_when_team_history_fails(client):
    """GET /dashboard still renders with HTTP 200 when team history API calls fail."""
    from unittest.mock import MagicMock

    def fake_get(url):
        mock = MagicMock()
        if "scoreboard" in url:
            mock.json.return_value = {
                "focusedDate": "2026-05-11",
                "gamesByDate": [{"date": "2026-05-11", "games": [MOCK_GAME_FOR_HISTORY]}],
            }
        else:
            mock.raise_for_status.side_effect = requests.HTTPError("503")
        return mock

    with patch("app.agents.nhl_client.requests.get", side_effect=fake_get):
        response = client.get("/dashboard")
        assert response.status_code == 200


def test_api_scores_includes_last5_fields(client):
    """GET /api/scores returns away_last5 and home_last5 keys in each game dict."""
    scoreboard = {
        "focusedDate": "2026-05-11",
        "gamesByDate": [{"date": "2026-05-11", "games": [MOCK_GAME_FOR_HISTORY]}],
    }
    schedule = {"games": [_SINGLE_COMPLETED_GAME]}

    with patch(
        "app.agents.nhl_client.requests.get",
        side_effect=_make_fake_get(scoreboard, schedule),
    ):
        response = client.get("/api/scores")
        data = response.get_json()

        assert len(data) == 1
        assert "away_last5" in data[0]
        assert "home_last5" in data[0]


# ---------------------------------------------------------------------------
# Season series on dashboard (Issue #8)
# ---------------------------------------------------------------------------

MOCK_GAME_FOR_SERIES = {
    "id": 8,
    "gameDate": "2026-05-11",
    "homeTeam": {"abbrev": "TOR", "score": 2},
    "awayTeam": {"abbrev": "MTL", "score": 1},
    "gameState": "LIVE",
}

_SERIES_COMPLETED_GAME = {
    "id": 300, "gameDate": "2026-03-01", "gameState": "FINAL",
    "homeTeam": {"abbrev": "TOR", "score": 4},
    "awayTeam": {"abbrev": "MTL", "score": 2},
}


def test_api_scores_includes_season_series_field(client):
    """GET /api/scores returns a season_series key in each game dict."""
    scoreboard = {
        "focusedDate": "2026-05-11",
        "gamesByDate": [{"date": "2026-05-11", "games": [MOCK_GAME_FOR_SERIES]}],
    }
    schedule = {"games": [_SERIES_COMPLETED_GAME]}

    with patch(
        "app.agents.nhl_client.requests.get",
        side_effect=_make_fake_get(scoreboard, schedule),
    ):
        response = client.get("/api/scores")
        data = response.get_json()

        assert len(data) == 1
        assert "season_series" in data[0]


def test_dashboard_displays_season_series(client):
    """GET /dashboard renders season series wins when series data is available."""
    scoreboard = {
        "focusedDate": "2026-05-11",
        "gamesByDate": [{"date": "2026-05-11", "games": [MOCK_GAME_FOR_SERIES]}],
    }
    schedule = {"games": [_SERIES_COMPLETED_GAME]}

    with patch(
        "app.agents.nhl_client.requests.get",
        side_effect=_make_fake_get(scoreboard, schedule),
    ):
        response = client.get("/dashboard")
        html = response.data.decode("utf-8")

        assert response.status_code == 200
        assert "season" in html.lower() or "series" in html.lower()


def test_dashboard_graceful_when_series_api_fails(client):
    """GET /dashboard still renders HTTP 200 when season series API call fails."""
    from unittest.mock import MagicMock

    def fake_get(url):
        mock = MagicMock()
        if "scoreboard" in url:
            mock.json.return_value = {
                "focusedDate": "2026-05-11",
                "gamesByDate": [{"date": "2026-05-11", "games": [MOCK_GAME_FOR_SERIES]}],
            }
        else:
            mock.raise_for_status.side_effect = requests.HTTPError("503")
        return mock

    with patch("app.agents.nhl_client.requests.get", side_effect=fake_get):
        response = client.get("/dashboard")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Dashboard loading and error states (Issue #9)
# ---------------------------------------------------------------------------


def test_api_scores_returns_empty_list_on_connection_error(client):
    """GET /api/scores returns HTTP 200 with empty list when NHL API is unreachable."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_get.side_effect = requests.ConnectionError("Connection refused")

        response = client.get("/api/scores")

        assert response.status_code == 200
        assert response.get_json() == []


def test_api_scores_returns_empty_list_on_timeout(client):
    """GET /api/scores returns HTTP 200 with empty list when NHL API request times out."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_get.side_effect = requests.Timeout("Request timed out")

        response = client.get("/api/scores")

        assert response.status_code == 200
        assert response.get_json() == []


def test_dashboard_returns_200_on_connection_error(client):
    """GET /dashboard returns HTTP 200 when NHL API is unreachable."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_get.side_effect = requests.ConnectionError("Connection refused")

        response = client.get("/dashboard")

        assert response.status_code == 200


def test_dashboard_shows_error_banner_when_api_fails(client):
    """GET /dashboard renders a visible error banner when the NHL API is unavailable."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_get.side_effect = requests.ConnectionError("Connection refused")

        response = client.get("/dashboard")
        html = response.data.decode("utf-8")

        assert "error-banner" in html


def test_dashboard_contains_loading_indicator(client):
    """GET /dashboard HTML includes a loading indicator element for JS to show during refresh."""
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

        assert "loading-indicator" in html


def test_dashboard_refresh_js_displays_error_on_failure(client):
    """GET /dashboard JS catch handler shows error-banner on fetch failure (not silent)."""
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

        assert "error-banner" in html
        assert ".catch(" in html
