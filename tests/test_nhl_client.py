"""Tests for app/agents/nhl_client.py using TDD."""
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.agents.nhl_client import format_game, get_team_last_5, get_todays_games

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


# ---------------------------------------------------------------------------
# format_game money line odds (Issue #6)
# ---------------------------------------------------------------------------

GAME_WITH_ODDS = {
    "gameState": "LIVE",
    "homeTeam": {"abbrev": "TOR", "score": 2},
    "awayTeam": {"abbrev": "MTL", "score": 1},
    "odds": [
        {"providerId": 1, "awayOdds": -120, "homeOdds": 105},
    ],
}

GAME_PREGAME_WITH_ODDS = {
    "gameState": "PRE",
    "homeTeam": {"abbrev": "NYR"},
    "awayTeam": {"abbrev": "BOS"},
    "odds": [
        {"providerId": 1, "awayOdds": 130, "homeOdds": -150},
    ],
}

GAME_WITHOUT_ODDS = {
    "gameState": "PRE",
    "homeTeam": {"abbrev": "VGK"},
    "awayTeam": {"abbrev": "EDM"},
}

GAME_MALFORMED_ODDS = {
    "gameState": "LIVE",
    "homeTeam": {"abbrev": "FLA", "score": 3},
    "awayTeam": {"abbrev": "CAR", "score": 2},
    "odds": [{"providerId": 1}],
}


def test_format_game_includes_away_ml_when_odds_present():
    """format_game returns away_ml from the first odds entry."""
    result = format_game(GAME_WITH_ODDS)
    assert result["away_ml"] == -120


def test_format_game_includes_home_ml_when_odds_present():
    """format_game returns home_ml from the first odds entry."""
    result = format_game(GAME_WITH_ODDS)
    assert result["home_ml"] == 105


def test_format_game_pregame_odds_extracted():
    """format_game extracts odds for a pregame (PRE state) game."""
    result = format_game(GAME_PREGAME_WITH_ODDS)
    assert result["away_ml"] == 130
    assert result["home_ml"] == -150


def test_format_game_away_ml_none_when_odds_missing():
    """format_game returns away_ml=None when odds field is absent."""
    result = format_game(GAME_WITHOUT_ODDS)
    assert result["away_ml"] is None


def test_format_game_home_ml_none_when_odds_missing():
    """format_game returns home_ml=None when odds field is absent."""
    result = format_game(GAME_WITHOUT_ODDS)
    assert result["home_ml"] is None


def test_format_game_odds_none_when_odds_list_empty():
    """format_game returns None odds when the odds list is empty."""
    game = {**GAME_WITHOUT_ODDS, "odds": []}
    result = format_game(game)
    assert result["away_ml"] is None
    assert result["home_ml"] is None


def test_format_game_odds_none_when_odds_keys_missing():
    """format_game returns None odds when expected keys are absent from entry."""
    result = format_game(GAME_MALFORMED_ODDS)
    assert result["away_ml"] is None
    assert result["home_ml"] is None


# ---------------------------------------------------------------------------
# get_team_last_5 and team history formatting (Issue #7)
# ---------------------------------------------------------------------------

MOCK_TOR_SCHEDULE = {
    "games": [
        {
            "id": 100, "gameDate": "2026-04-01", "gameState": "FINAL",
            "homeTeam": {"abbrev": "TOR", "score": 4},
            "awayTeam": {"abbrev": "MTL", "score": 2},
        },
        {
            "id": 101, "gameDate": "2026-04-03", "gameState": "FINAL",
            "homeTeam": {"abbrev": "BOS", "score": 3},
            "awayTeam": {"abbrev": "TOR", "score": 5},
        },
        {
            "id": 102, "gameDate": "2026-04-05", "gameState": "OFF",
            "homeTeam": {"abbrev": "TOR", "score": 2},
            "awayTeam": {"abbrev": "NYR", "score": 3},
        },
        {
            "id": 103, "gameDate": "2026-04-07", "gameState": "FINAL",
            "homeTeam": {"abbrev": "VGK", "score": 1},
            "awayTeam": {"abbrev": "TOR", "score": 4},
        },
        {
            "id": 104, "gameDate": "2026-04-09", "gameState": "FINAL",
            "homeTeam": {"abbrev": "TOR", "score": 3},
            "awayTeam": {"abbrev": "EDM", "score": 1},
        },
        {
            "id": 105, "gameDate": "2026-04-11", "gameState": "FINAL",
            "homeTeam": {"abbrev": "TOR", "score": 5},
            "awayTeam": {"abbrev": "FLA", "score": 4},
        },
        {
            "id": 106, "gameDate": "2026-05-15", "gameState": "PRE",
            "homeTeam": {"abbrev": "TOR", "score": 0},
            "awayTeam": {"abbrev": "CAR", "score": 0},
        },
    ]
}


def test_get_team_last_5_returns_list():
    """get_team_last_5 returns a list on a successful response."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_TOR_SCHEDULE
        mock_get.return_value = mock_resp

        result = get_team_last_5("TOR")

        assert isinstance(result, list)


def test_get_team_last_5_returns_at_most_5_games():
    """get_team_last_5 returns at most 5 results even when more completed games exist."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_TOR_SCHEDULE
        mock_get.return_value = mock_resp

        result = get_team_last_5("TOR")

        assert len(result) <= 5


def test_get_team_last_5_excludes_noncompleted_games():
    """get_team_last_5 counts 5 most recent FINAL/OFF games, skipping PRE/LIVE."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_TOR_SCHEDULE
        mock_get.return_value = mock_resp

        result = get_team_last_5("TOR")

        assert len(result) == 5


def test_get_team_last_5_returns_empty_when_no_completed_games():
    """get_team_last_5 returns empty list when no completed games exist."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"games": []}
        mock_get.return_value = mock_resp

        result = get_team_last_5("TOR")

        assert result == []


def test_get_team_last_5_raises_on_http_error():
    """get_team_last_5 propagates HTTPError when the API returns a non-2xx status."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
        mock_get.return_value = mock_resp

        with pytest.raises(requests.HTTPError):
            get_team_last_5("TOR")


def test_get_team_last_5_calls_correct_url():
    """get_team_last_5 requests the correct NHL schedule endpoint for the given team."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"games": []}
        mock_get.return_value = mock_resp

        get_team_last_5("TOR")

        mock_get.assert_called_once_with(
            "https://api-web.nhle.com/v1/club-schedule-season/TOR/now"
        )


def test_get_team_last_5_result_win_as_home():
    """get_team_last_5 returns 'W' when the queried team is the home winner."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "games": [
                {
                    "id": 100, "gameDate": "2026-04-01", "gameState": "FINAL",
                    "homeTeam": {"abbrev": "TOR", "score": 4},
                    "awayTeam": {"abbrev": "MTL", "score": 2},
                }
            ]
        }
        mock_get.return_value = mock_resp

        result = get_team_last_5("TOR")

        assert result[0]["result"] == "W"


def test_get_team_last_5_result_loss_as_home():
    """get_team_last_5 returns 'L' when the queried team is the home loser."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "games": [
                {
                    "id": 100, "gameDate": "2026-04-01", "gameState": "FINAL",
                    "homeTeam": {"abbrev": "TOR", "score": 1},
                    "awayTeam": {"abbrev": "MTL", "score": 3},
                }
            ]
        }
        mock_get.return_value = mock_resp

        result = get_team_last_5("TOR")

        assert result[0]["result"] == "L"


def test_get_team_last_5_result_win_as_away():
    """get_team_last_5 returns 'W' when the queried team is the away winner."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "games": [
                {
                    "id": 100, "gameDate": "2026-04-01", "gameState": "FINAL",
                    "homeTeam": {"abbrev": "BOS", "score": 2},
                    "awayTeam": {"abbrev": "TOR", "score": 5},
                }
            ]
        }
        mock_get.return_value = mock_resp

        result = get_team_last_5("TOR")

        assert result[0]["result"] == "W"


def test_get_team_last_5_result_contains_score():
    """get_team_last_5 returns team score vs opponent score in each result."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "games": [
                {
                    "id": 100, "gameDate": "2026-04-01", "gameState": "FINAL",
                    "homeTeam": {"abbrev": "TOR", "score": 4},
                    "awayTeam": {"abbrev": "MTL", "score": 2},
                }
            ]
        }
        mock_get.return_value = mock_resp

        result = get_team_last_5("TOR")

        assert result[0]["score"] == "4-2"


def test_format_game_includes_away_last5():
    """format_game includes away_last5 when history is provided."""
    history = [{"result": "W", "score": "4-2"}]
    result = format_game(GAME_WITH_ODDS, away_history=history)
    assert result["away_last5"] == history


def test_format_game_includes_home_last5():
    """format_game includes home_last5 when history is provided."""
    history = [{"result": "L", "score": "2-3"}]
    result = format_game(GAME_WITH_ODDS, home_history=history)
    assert result["home_last5"] == history


def test_format_game_last5_defaults_to_empty_list():
    """format_game sets away_last5 and home_last5 to empty lists when not provided."""
    result = format_game(GAME_WITH_ODDS)
    assert result["away_last5"] == []
    assert result["home_last5"] == []
