"""Tests for NhlClient — NHL API wrapper with TTLCache."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "nhl-dashboard", "backend"))

from nhl_client import NhlClient, BASE_URL  # noqa: E402

STANDINGS_FIXTURE = {
    "standings": [
        {
            "teamAbbrev": {"default": "TOR"},
            "wins": 24,
            "losses": 18,
            "otLosses": 4,
            "l10Wins": 6,
            "l10Losses": 3,
            "l10OtLosses": 1,
        }
    ]
}

SCHEDULE_FIXTURE = {
    "gameWeek": [
        {
            "date": "2026-05-20",
            "games": [
                {
                    "id": 2026020812,
                    "startTimeUTC": "2026-05-20T23:00:00Z",
                    "venue": {"default": "TD Garden"},
                    "awayTeam": {
                        "abbrev": "TOR",
                        "commonName": {"default": "Maple Leafs"},
                    },
                    "homeTeam": {
                        "abbrev": "BOS",
                        "commonName": {"default": "Bruins"},
                    },
                    "gameState": "FUT",
                }
            ],
        }
    ]
}

BOXSCORE_FIXTURE = {
    "id": 2026020812,
    "gameState": "LIVE",
    "periodDescriptor": {"number": 2, "periodType": "REG"},
    "clock": {"timeRemaining": "12:34", "inIntermission": False},
    "awayTeam": {"abbrev": "TOR", "score": 3, "sog": 18},
    "homeTeam": {"abbrev": "BOS", "score": 2, "sog": 22},
}


def _ok_response(json_data):
    """Return a mock httpx response with status 200."""
    resp = MagicMock()
    resp.json.return_value = json_data
    return resp


def _error_response():
    """Return a mock httpx response whose raise_for_status raises."""
    resp = MagicMock()
    resp.raise_for_status.side_effect = Exception("HTTP 500 Server Error")
    return resp


def test_get_schedule_today_returns_game_list():
    """Mock HTTP; assert returns a list with expected game fields."""
    client = NhlClient(slate_ttl=60, live_ttl=15)
    with patch("httpx.get", return_value=_ok_response(SCHEDULE_FIXTURE)):
        with patch.object(client, "_today", return_value="2026-05-20"):
            games = client.get_schedule_today()

    assert isinstance(games, list)
    assert len(games) == 1
    game = games[0]
    assert game["id"] == 2026020812
    assert game["away_code"] == "TOR"
    assert game["home_code"] == "BOS"
    assert game["venue"] == "TD Garden"


def test_get_boxscore_returns_parsed_dict():
    """Mock HTTP; assert score, period, and clock fields are present."""
    client = NhlClient(slate_ttl=60, live_ttl=15)
    with patch("httpx.get", return_value=_ok_response(BOXSCORE_FIXTURE)):
        boxscore = client.get_boxscore(2026020812)

    assert boxscore is not None
    assert boxscore["away_score"] == 3
    assert boxscore["home_score"] == 2
    assert boxscore["away_sog"] == 18
    assert boxscore["home_sog"] == 22
    assert "period" in boxscore
    assert "clock" in boxscore


def test_get_schedule_today_caches_response():
    """Call get_schedule_today() twice; assert HTTP is hit only once."""
    client = NhlClient(slate_ttl=60, live_ttl=15)
    with patch("httpx.get", return_value=_ok_response(SCHEDULE_FIXTURE)) as mock_get:
        with patch.object(client, "_today", return_value="2026-05-20"):
            client.get_schedule_today()
            client.get_schedule_today()

    mock_get.assert_called_once()


def test_http_error_returns_none():
    """Mock a failing response; assert None is returned without raising."""
    client = NhlClient(slate_ttl=60, live_ttl=15)
    with patch("httpx.get", return_value=_error_response()):
        result = client.get_schedule_today()

    assert result is None


def test_get_schedule_today_follows_redirects():
    """Assert httpx.get is called with follow_redirects=True for schedule."""
    client = NhlClient(slate_ttl=60, live_ttl=15)
    with patch("httpx.get", return_value=_ok_response(SCHEDULE_FIXTURE)) as mock_get:
        with patch.object(client, "_today", return_value="2026-05-20"):
            games = client.get_schedule_today()

    mock_get.assert_called_once_with(
        f"{BASE_URL}/schedule/now", follow_redirects=True
    )
    assert games is not None
    assert len(games) == 1


def test_get_boxscore_follows_redirects():
    """Assert httpx.get is called with follow_redirects=True for boxscore."""
    client = NhlClient(slate_ttl=60, live_ttl=15)
    with patch("httpx.get", return_value=_ok_response(BOXSCORE_FIXTURE)) as mock_get:
        boxscore = client.get_boxscore(2026020812)

    mock_get.assert_called_once_with(
        f"{BASE_URL}/gamecenter/2026020812/boxscore", follow_redirects=True
    )
    assert boxscore is not None


def test_get_standings_returns_parsed_dict():
    """Mock HTTP; assert returns a dict keyed by abbrev with standings fields."""
    client = NhlClient(slate_ttl=60, live_ttl=15, standings_ttl=60)
    with patch("httpx.get", return_value=_ok_response(STANDINGS_FIXTURE)):
        standings = client.get_standings()

    assert isinstance(standings, dict)
    assert "TOR" in standings
    tor = standings["TOR"]
    assert tor["wins"] == 24
    assert tor["losses"] == 18
    assert tor["ot_losses"] == 4
    assert tor["l10_wins"] == 6
    assert tor["l10_losses"] == 3
    assert tor["l10_ot_losses"] == 1


def test_get_standings_returns_none_on_http_error():
    """Mock a failing response; assert None is returned without raising."""
    client = NhlClient(slate_ttl=60, live_ttl=15, standings_ttl=60)
    with patch("httpx.get", return_value=_error_response()):
        result = client.get_standings()

    assert result is None
