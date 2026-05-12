"""Tests for app/agents/nhl_client.py using TDD."""
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.agents.nhl_client import get_todays_games

# ---------------------------------------------------------------------------
# Fixtures / shared test data
# ---------------------------------------------------------------------------

MOCK_SCOREBOARD = {
    "focusedDate": "2026-05-11",
    "focusedDateCount": 2,
    "gamesByDate": [
        {
            "date": "2026-05-10",
            "games": [{"id": 1, "gameDate": "2026-05-10"}],
        },
        {
            "date": "2026-05-11",
            "games": [
                {
                    "id": 2,
                    "gameDate": "2026-05-11",
                    "homeTeam": {"abbrev": "TOR"},
                    "awayTeam": {"abbrev": "MTL"},
                    "gameState": "LIVE",
                },
                {
                    "id": 3,
                    "gameDate": "2026-05-11",
                    "homeTeam": {"abbrev": "NYR"},
                    "awayTeam": {"abbrev": "BOS"},
                    "gameState": "PRE",
                },
            ],
        },
    ],
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_get_todays_games_returns_list():
    """get_todays_games returns a list on a successful response."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_SCOREBOARD
        mock_get.return_value = mock_resp

        result = get_todays_games()

        assert isinstance(result, list)


def test_get_todays_games_returns_focused_date_games():
    """get_todays_games returns only games whose date matches focusedDate."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_SCOREBOARD
        mock_get.return_value = mock_resp

        result = get_todays_games()

        assert len(result) == 2
        assert all(g["gameDate"] == "2026-05-11" for g in result)


def test_get_todays_games_raises_on_http_error():
    """get_todays_games propagates HTTPError when the API returns a non-2xx status."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
        mock_get.return_value = mock_resp

        with pytest.raises(requests.HTTPError):
            get_todays_games()


def test_get_todays_games_returns_empty_when_no_focused_date_match():
    """get_todays_games returns an empty list when focusedDate has no games entry."""
    mock_data = {
        "focusedDate": "2026-05-12",
        "focusedDateCount": 0,
        "gamesByDate": [
            {"date": "2026-05-11", "games": [{"id": 1}]},
        ],
    }
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_data
        mock_get.return_value = mock_resp

        result = get_todays_games()

        assert result == []


def test_get_todays_games_calls_correct_url():
    """get_todays_games makes exactly one GET request to NHL_SCOREBOARD_URL."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_SCOREBOARD
        mock_get.return_value = mock_resp

        get_todays_games()

        mock_get.assert_called_once_with(
            "https://api-web.nhle.com/v1/scoreboard/now"
        )
