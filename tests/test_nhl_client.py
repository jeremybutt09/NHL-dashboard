"""Tests for app/agents/nhl_client.py using TDD."""
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.agents.nhl_client import (
    extract_odds_partner,
    extract_team_odds,
    format_game,
    get_team_last_5,
    get_todays_games,
    get_todays_score_now,
)

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


# ---------------------------------------------------------------------------
# get_season_series and season_series in format_game (Issue #8)
# ---------------------------------------------------------------------------

# MTL is away today, TOR is home today.
# Game 200: TOR wins at home → home_wins++
# Game 201: MTL wins at home (MTL is today's away team) → away_wins++
# Game 202: TOR wins on road (away team wins) → home_wins++
# Game 203: different opponent — filtered out
# Game 204: upcoming — filtered out
MOCK_SERIES_SCHEDULE = {
    "games": [
        {
            "id": 200, "gameDate": "2026-01-10", "gameState": "FINAL",
            "homeTeam": {"abbrev": "TOR", "score": 4},
            "awayTeam": {"abbrev": "MTL", "score": 2},
        },
        {
            "id": 201, "gameDate": "2026-02-15", "gameState": "FINAL",
            "homeTeam": {"abbrev": "MTL", "score": 3},
            "awayTeam": {"abbrev": "TOR", "score": 1},
        },
        {
            "id": 202, "gameDate": "2026-03-20", "gameState": "FINAL",
            "homeTeam": {"abbrev": "MTL", "score": 2},
            "awayTeam": {"abbrev": "TOR", "score": 5},
        },
        {
            "id": 203, "gameDate": "2026-04-01", "gameState": "FINAL",
            "homeTeam": {"abbrev": "MTL", "score": 3},
            "awayTeam": {"abbrev": "BOS", "score": 2},
        },
        {
            "id": 204, "gameDate": "2026-05-16", "gameState": "PRE",
            "homeTeam": {"abbrev": "TOR", "score": 0},
            "awayTeam": {"abbrev": "MTL", "score": 0},
        },
    ]
}


def test_get_season_series_returns_dict():
    """get_season_series returns a dict with away_wins, home_wins, meetings keys."""
    from app.agents.nhl_client import get_season_series

    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_SERIES_SCHEDULE
        mock_get.return_value = mock_resp

        result = get_season_series("MTL", "TOR")

        assert isinstance(result, dict)
        assert "away_wins" in result
        assert "home_wins" in result
        assert "meetings" in result


def test_get_season_series_counts_meetings():
    """get_season_series counts only completed games between the two teams."""
    from app.agents.nhl_client import get_season_series

    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_SERIES_SCHEDULE
        mock_get.return_value = mock_resp

        result = get_season_series("MTL", "TOR")

        assert result["meetings"] == 3


def test_get_season_series_counts_away_wins():
    """get_season_series counts wins for the away team (today's context)."""
    from app.agents.nhl_client import get_season_series

    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_SERIES_SCHEDULE
        mock_get.return_value = mock_resp

        result = get_season_series("MTL", "TOR")

        assert result["away_wins"] == 1


def test_get_season_series_counts_home_wins():
    """get_season_series counts wins for the home team (today's context)."""
    from app.agents.nhl_client import get_season_series

    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_SERIES_SCHEDULE
        mock_get.return_value = mock_resp

        result = get_season_series("MTL", "TOR")

        assert result["home_wins"] == 2


def test_get_season_series_no_meetings():
    """get_season_series returns zeros when no completed matchups exist."""
    from app.agents.nhl_client import get_season_series

    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"games": []}
        mock_get.return_value = mock_resp

        result = get_season_series("MTL", "TOR")

        assert result == {"away_wins": 0, "home_wins": 0, "meetings": 0}


def test_get_season_series_raises_on_http_error():
    """get_season_series propagates HTTPError when the API returns a non-2xx status."""
    from app.agents.nhl_client import get_season_series

    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
        mock_get.return_value = mock_resp

        with pytest.raises(requests.HTTPError):
            get_season_series("MTL", "TOR")


def test_get_season_series_calls_correct_url():
    """get_season_series requests the away team's schedule endpoint."""
    from app.agents.nhl_client import get_season_series

    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"games": []}
        mock_get.return_value = mock_resp

        get_season_series("MTL", "TOR")

        mock_get.assert_called_once_with(
            "https://api-web.nhle.com/v1/club-schedule-season/MTL/now"
        )


def test_format_game_includes_season_series():
    """format_game includes season_series when provided."""
    series = {"away_wins": 1, "home_wins": 2, "meetings": 3}
    result = format_game(GAME_WITH_ODDS, season_series=series)
    assert result["season_series"] == series


def test_format_game_season_series_defaults_to_none():
    """format_game sets season_series to None when not provided."""
    result = format_game(GAME_WITH_ODDS)
    assert result["season_series"] is None


# ---------------------------------------------------------------------------
# extract_team_odds (Issue #20)
# ---------------------------------------------------------------------------

TEAM_WITH_NEGATIVE_ODDS = {"abbrev": "MTL", "odds": [{"providerId": 1, "value": "-120"}]}
TEAM_WITH_POSITIVE_ODDS = {"abbrev": "TOR", "odds": [{"providerId": 1, "value": "+105"}]}
TEAM_WITHOUT_ODDS_FIELD = {"abbrev": "VGK"}
TEAM_WITH_EMPTY_ODDS = {"abbrev": "EDM", "odds": []}
TEAM_WITH_MISSING_VALUE = {"abbrev": "CAR", "odds": [{"providerId": 1}]}


def test_extract_team_odds_returns_negative_int():
    """extract_team_odds converts a negative string value to an integer."""
    assert extract_team_odds(TEAM_WITH_NEGATIVE_ODDS) == -120


def test_extract_team_odds_returns_positive_int():
    """extract_team_odds converts a positive string value to an integer."""
    assert extract_team_odds(TEAM_WITH_POSITIVE_ODDS) == 105


def test_extract_team_odds_returns_none_when_odds_field_absent():
    """extract_team_odds returns None when the team dict has no odds key."""
    assert extract_team_odds(TEAM_WITHOUT_ODDS_FIELD) is None


def test_extract_team_odds_returns_none_when_odds_list_empty():
    """extract_team_odds returns None when the odds list is empty."""
    assert extract_team_odds(TEAM_WITH_EMPTY_ODDS) is None


def test_extract_team_odds_returns_none_when_value_key_missing():
    """extract_team_odds returns None when the odds entry has no value key."""
    assert extract_team_odds(TEAM_WITH_MISSING_VALUE) is None


# ---------------------------------------------------------------------------
# get_todays_score_now (Issue #20)
# ---------------------------------------------------------------------------

MOCK_SCORE_NOW = {
    "currentDate": "2026-05-11",
    "games": [
        {
            "id": 10,
            "gameDate": "2026-05-11",
            "gameState": "LIVE",
            "homeTeam": {"abbrev": "TOR", "score": 2, "odds": [{"providerId": 1, "value": "+105"}]},
            "awayTeam": {"abbrev": "MTL", "score": 1, "odds": [{"providerId": 1, "value": "-120"}]},
        }
    ],
}


def test_get_todays_score_now_returns_list():
    """get_todays_score_now returns a list on a successful response."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_SCORE_NOW
        mock_get.return_value = mock_resp

        result = get_todays_score_now()

        assert isinstance(result, list)


def test_get_todays_score_now_returns_games():
    """get_todays_score_now returns the top-level games list."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_SCORE_NOW
        mock_get.return_value = mock_resp

        result = get_todays_score_now()

        assert len(result) == 1
        assert result[0]["id"] == 10


def test_get_todays_score_now_calls_correct_url():
    """get_todays_score_now makes exactly one GET request to NHL_SCORE_URL."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_SCORE_NOW
        mock_get.return_value = mock_resp

        get_todays_score_now()

        mock_get.assert_called_once_with("https://api-web.nhle.com/v1/score/now")


def test_get_todays_score_now_raises_on_http_error():
    """get_todays_score_now propagates HTTPError when the API returns a non-2xx status."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
        mock_get.return_value = mock_resp

        with pytest.raises(requests.HTTPError):
            get_todays_score_now()


def test_get_todays_score_now_returns_empty_when_no_games_key():
    """get_todays_score_now returns an empty list when games key is absent."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"currentDate": "2026-05-11"}
        mock_get.return_value = mock_resp

        result = get_todays_score_now()

        assert result == []


# ---------------------------------------------------------------------------
# format_game with team-level odds (Issue #20)
# ---------------------------------------------------------------------------

GAME_WITH_TEAM_ODDS = {
    "gameState": "LIVE",
    "homeTeam": {"abbrev": "TOR", "score": 2, "odds": [{"providerId": 1, "value": "+105"}]},
    "awayTeam": {"abbrev": "MTL", "score": 1, "odds": [{"providerId": 1, "value": "-120"}]},
}

GAME_WITHOUT_TEAM_ODDS = {
    "gameState": "PRE",
    "homeTeam": {"abbrev": "VGK"},
    "awayTeam": {"abbrev": "EDM"},
}


def test_format_game_reads_away_ml_from_awayteam_odds():
    """format_game extracts away_ml from awayTeam.odds when present."""
    result = format_game(GAME_WITH_TEAM_ODDS)
    assert result["away_ml"] == -120


def test_format_game_reads_home_ml_from_hometeam_odds():
    """format_game extracts home_ml from homeTeam.odds when present."""
    result = format_game(GAME_WITH_TEAM_ODDS)
    assert result["home_ml"] == 105


def test_format_game_team_odds_none_when_no_team_level_odds():
    """format_game returns None odds when neither team has team-level odds."""
    result = format_game(GAME_WITHOUT_TEAM_ODDS)
    assert result["away_ml"] is None
    assert result["home_ml"] is None


# ---------------------------------------------------------------------------
# extract_odds_partner (Issue #21)
# ---------------------------------------------------------------------------

PARTNER_LIST = [
    {"partnerId": 1, "imageUrl": "http://logo.png", "siteUrl": "http://bet.com"},
    {"partnerId": 2, "imageUrl": "http://other.png", "siteUrl": "http://other.com"},
]


def test_extract_odds_partner_returns_matching_partner():
    """extract_odds_partner returns logo_url and site_url for a matching partnerId."""
    result = extract_odds_partner(PARTNER_LIST, 1)
    assert result == {"logo_url": "http://logo.png", "site_url": "http://bet.com"}


def test_extract_odds_partner_returns_second_partner():
    """extract_odds_partner returns the correct partner when there are multiple."""
    result = extract_odds_partner(PARTNER_LIST, 2)
    assert result == {"logo_url": "http://other.png", "site_url": "http://other.com"}


def test_extract_odds_partner_returns_empty_when_no_match():
    """extract_odds_partner returns empty dict when no partner matches the provider_id."""
    result = extract_odds_partner(PARTNER_LIST, 99)
    assert result == {}


def test_extract_odds_partner_returns_empty_when_provider_id_none():
    """extract_odds_partner returns empty dict when provider_id is None."""
    result = extract_odds_partner(PARTNER_LIST, None)
    assert result == {}


def test_extract_odds_partner_returns_empty_when_partners_empty():
    """extract_odds_partner returns empty dict when the partners list is empty."""
    result = extract_odds_partner([], 1)
    assert result == {}


def test_extract_odds_partner_handles_missing_image_url():
    """extract_odds_partner returns logo_url=None when imageUrl is absent."""
    partners = [{"partnerId": 1, "siteUrl": "http://bet.com"}]
    result = extract_odds_partner(partners, 1)
    assert result == {"logo_url": None, "site_url": "http://bet.com"}


def test_extract_odds_partner_handles_missing_site_url():
    """extract_odds_partner returns site_url=None when siteUrl is absent."""
    partners = [{"partnerId": 1, "imageUrl": "http://logo.png"}]
    result = extract_odds_partner(partners, 1)
    assert result == {"logo_url": "http://logo.png", "site_url": None}


# ---------------------------------------------------------------------------
# get_todays_score_now oddsPartners injection (Issue #21)
# ---------------------------------------------------------------------------

MOCK_SCORE_NOW_WITH_PARTNERS = {
    "currentDate": "2026-05-11",
    "oddsPartners": [
        {"partnerId": 1, "imageUrl": "http://logo.png", "siteUrl": "http://bet.com"},
    ],
    "games": [
        {
            "id": 10,
            "gameState": "LIVE",
            "homeTeam": {"abbrev": "TOR", "score": 2, "odds": [{"providerId": 1, "value": "+105"}]},
            "awayTeam": {"abbrev": "MTL", "score": 1, "odds": [{"providerId": 1, "value": "-120"}]},
        }
    ],
}


def test_get_todays_score_now_injects_odds_partners():
    """get_todays_score_now injects top-level oddsPartners into each game dict."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_SCORE_NOW_WITH_PARTNERS
        mock_get.return_value = mock_resp

        result = get_todays_score_now()

        assert "oddsPartners" in result[0]
        assert len(result[0]["oddsPartners"]) == 1
        assert result[0]["oddsPartners"][0]["partnerId"] == 1


def test_get_todays_score_now_injects_empty_odds_partners_when_absent():
    """get_todays_score_now sets oddsPartners to [] when key is missing from response."""
    with patch("app.agents.nhl_client.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"games": [{"id": 1}]}
        mock_get.return_value = mock_resp

        result = get_todays_score_now()

        assert result[0]["oddsPartners"] == []


# ---------------------------------------------------------------------------
# format_game with odds_partner (Issue #21)
# ---------------------------------------------------------------------------

GAME_WITH_PARTNER_ODDS = {
    "gameState": "LIVE",
    "homeTeam": {"abbrev": "TOR", "score": 2, "odds": [{"providerId": 1, "value": "+105"}]},
    "awayTeam": {"abbrev": "MTL", "score": 1, "odds": [{"providerId": 1, "value": "-120"}]},
    "oddsPartners": [
        {"partnerId": 1, "imageUrl": "http://logo.png", "siteUrl": "http://bet.com"},
    ],
}

GAME_WITH_NO_PARTNER_MATCH = {
    "gameState": "LIVE",
    "homeTeam": {"abbrev": "TOR", "score": 2, "odds": [{"providerId": 99, "value": "+105"}]},
    "awayTeam": {"abbrev": "MTL", "score": 1, "odds": [{"providerId": 99, "value": "-120"}]},
    "oddsPartners": [
        {"partnerId": 1, "imageUrl": "http://logo.png", "siteUrl": "http://bet.com"},
    ],
}


def test_format_game_includes_odds_partner_when_matched():
    """format_game includes odds_partner dict when provider matches a partner."""
    result = format_game(GAME_WITH_PARTNER_ODDS)
    assert result["odds_partner"] == {"logo_url": "http://logo.png", "site_url": "http://bet.com"}


def test_format_game_odds_partner_is_none_when_no_odds_partners():
    """format_game sets odds_partner to None when oddsPartners is absent."""
    result = format_game(GAME_WITH_TEAM_ODDS)
    assert result["odds_partner"] is None


def test_format_game_odds_partner_is_none_when_provider_id_not_matched():
    """format_game sets odds_partner to None when no partner matches the provider_id."""
    result = format_game(GAME_WITH_NO_PARTNER_MATCH)
    assert result["odds_partner"] is None


# ---------------------------------------------------------------------------
# Graceful handling of missing partner metadata (Issue #22)
# ---------------------------------------------------------------------------

_GAME_WITH_ODDS_PARTNER_NO_BRANDING = {
    "gameState": "LIVE",
    "homeTeam": {"abbrev": "TOR", "score": 2, "odds": [{"providerId": 1, "value": "+105"}]},
    "awayTeam": {"abbrev": "MTL", "score": 1, "odds": [{"providerId": 1, "value": "-120"}]},
    "oddsPartners": [{"partnerId": 1}],  # matched partner, but no imageUrl or siteUrl
}

_GAME_WITH_ODDS_EMPTY_PARTNERS = {
    "gameState": "LIVE",
    "homeTeam": {"abbrev": "TOR", "score": 2, "odds": [{"providerId": 1, "value": "+105"}]},
    "awayTeam": {"abbrev": "MTL", "score": 1, "odds": [{"providerId": 1, "value": "-120"}]},
    "oddsPartners": [],
}


def test_extract_odds_partner_handles_both_urls_missing():
    """extract_odds_partner returns both None values when partner has no imageUrl or siteUrl."""
    partners = [{"partnerId": 1}]
    result = extract_odds_partner(partners, 1)
    assert result == {"logo_url": None, "site_url": None}


def test_format_game_odds_partner_is_none_when_matched_partner_has_no_branding():
    """format_game returns odds_partner=None when the matched partner has neither logo nor site URL."""
    result = format_game(_GAME_WITH_ODDS_PARTNER_NO_BRANDING)
    assert result["odds_partner"] is None


def test_format_game_shows_odds_when_partner_has_no_branding():
    """format_game returns valid away_ml and home_ml even when matched partner has no branding."""
    result = format_game(_GAME_WITH_ODDS_PARTNER_NO_BRANDING)
    assert result["away_ml"] == -120
    assert result["home_ml"] == 105


def test_format_game_shows_odds_when_odds_partners_empty():
    """format_game returns valid odds and odds_partner=None when oddsPartners list is empty."""
    result = format_game(_GAME_WITH_ODDS_EMPTY_PARTNERS)
    assert result["away_ml"] == -120
    assert result["home_ml"] == 105
    assert result["odds_partner"] is None


def test_format_game_handles_game_with_no_odds_and_no_partners():
    """format_game sets all odds fields to None when game has neither odds nor partner data."""
    game = {
        "gameState": "PRE",
        "homeTeam": {"abbrev": "VGK"},
        "awayTeam": {"abbrev": "EDM"},
        "oddsPartners": [],
    }
    result = format_game(game)
    assert result["away_ml"] is None
    assert result["home_ml"] is None
    assert result["odds_partner"] is None
