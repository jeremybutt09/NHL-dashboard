"""Unit tests for NHL API client with mocked HTTP responses (Issue #89)."""
import json
import os
from unittest.mock import MagicMock, patch

import httpx
import pytest

import nhl_client
from nhl_client import get_boxscore, get_schedule_now, get_score_now

_FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _fixture(name: str) -> dict:
    """Return parsed JSON from tests/fixtures/<name>."""
    with open(os.path.join(_FIXTURES, name)) as fh:
        return json.load(fh)


def _ok_response(data: dict) -> MagicMock:
    """Mock httpx response that succeeds and returns *data* from .json()."""
    m = MagicMock()
    m.raise_for_status.return_value = None
    m.json.return_value = data
    return m


def _error_response(status_code: int = 503) -> MagicMock:
    """Mock httpx response whose raise_for_status() raises HTTPStatusError."""
    m = MagicMock()
    m.raise_for_status.side_effect = httpx.HTTPStatusError(
        f"{status_code} Server Error",
        request=MagicMock(),
        response=MagicMock(status_code=status_code),
    )
    return m


@pytest.fixture(autouse=True)
def clear_nhl_cache():
    """Reset the module-level TTLCache before and after each test."""
    nhl_client._cache.clear()
    yield
    nhl_client._cache.clear()


class TestGetScheduleNow:
    def test_get_schedule_now_returns_game_list(self):
        """Schedule response contains a non-empty list of game dicts."""
        data = _fixture("schedule_now.json")
        with patch("nhl_client.httpx.get", return_value=_ok_response(data)):
            result = get_schedule_now()

        games = result["gameWeek"][0]["games"]
        assert isinstance(games, list)
        assert len(games) >= 2
        for g in games:
            assert isinstance(g, dict)
            assert "id" in g

    def test_get_schedule_now_ttl_cache_prevents_redundant_requests(self):
        """Two consecutive calls within the TTL hit the network only once."""
        data = _fixture("schedule_now.json")
        with patch("nhl_client.httpx.get", return_value=_ok_response(data)) as mock_get:
            get_schedule_now()
            get_schedule_now()

        assert mock_get.call_count == 1

    def test_get_schedule_now_5xx_raises_exception(self):
        """A 503 from the NHL API propagates as httpx.HTTPStatusError."""
        with patch("nhl_client.httpx.get", return_value=_error_response(503)):
            with pytest.raises(httpx.HTTPStatusError):
                get_schedule_now()


class TestGetBoxscore:
    def test_get_boxscore_returns_parsed_dict(self):
        """Boxscore endpoint returns a dict with expected top-level keys."""
        data = _fixture("boxscore_2024020001.json")
        with patch("nhl_client.httpx.get", return_value=_ok_response(data)):
            result = get_boxscore(2024020001)

        assert isinstance(result, dict)
        assert result["id"] == 2024020001
        assert "awayTeam" in result
        assert "homeTeam" in result
        assert "gameState" in result


class TestGetScoreNow:
    def test_get_score_now_returns_parsed_data(self):
        """Score endpoint returns dict with currentDate and a games list."""
        data = _fixture("score_now.json")
        with patch("nhl_client.httpx.get", return_value=_ok_response(data)):
            result = get_score_now()

        assert "games" in result
        assert isinstance(result["games"], list)
        assert len(result["games"]) == 3

    def test_get_score_now_game_entry_has_expected_keys(self):
        """Each game entry in the score response contains id, gameState, and team data."""
        data = _fixture("score_now.json")
        with patch("nhl_client.httpx.get", return_value=_ok_response(data)):
            result = get_score_now()

        game = result["games"][0]
        assert "id" in game
        assert "gameState" in game
        assert "awayTeam" in game
        assert "homeTeam" in game

    def test_get_score_now_ttl_cache_prevents_redundant_requests(self):
        """Two consecutive calls within the TTL hit the network only once."""
        data = _fixture("score_now.json")
        with patch("nhl_client.httpx.get", return_value=_ok_response(data)) as mock_get:
            get_score_now()
            get_score_now()

        assert mock_get.call_count == 1

    def test_get_score_now_5xx_raises_exception(self):
        """A 503 from the NHL API propagates as httpx.HTTPStatusError."""
        with patch("nhl_client.httpx.get", return_value=_error_response(503)):
            with pytest.raises(httpx.HTTPStatusError):
                get_score_now()
