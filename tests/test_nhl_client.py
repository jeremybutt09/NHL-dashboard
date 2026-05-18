import sys
import os
import pytest
import httpx
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'nhl-dashboard', 'backend'))

import nhl_client

SCHEDULE_RESPONSE = {
    "gameWeek": [
        {
            "date": "2026-05-18",
            "games": [
                {"id": 1234, "awayTeam": {"abbrev": "TOR"}, "homeTeam": {"abbrev": "BOS"}},
                {"id": 5678, "awayTeam": {"abbrev": "MTL"}, "homeTeam": {"abbrev": "NYR"}},
            ],
        }
    ]
}

BOXSCORE_RESPONSE = {
    "id": 1234,
    "awayTeam": {"abbrev": "TOR", "score": 2},
    "homeTeam": {"abbrev": "BOS", "score": 3},
    "clock": {"timeRemaining": "00:00"},
    "periodDescriptor": {"number": 3},
}


def _mock_ok(json_data):
    """Return a mock httpx response with status 200."""
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.status_code = 200
    mock.raise_for_status.return_value = None
    return mock


def _mock_error(status_code):
    """Return a mock httpx response that raises HTTPStatusError."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.raise_for_status.side_effect = httpx.HTTPStatusError(
        f"HTTP {status_code}", request=MagicMock(), response=mock
    )
    return mock


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear module-level TTL caches before and after each test."""
    nhl_client._schedule_cache.clear()
    nhl_client._boxscore_cache.clear()
    yield
    nhl_client._schedule_cache.clear()
    nhl_client._boxscore_cache.clear()


def test_get_schedule_today_returns_list_of_dicts():
    with patch("httpx.get", return_value=_mock_ok(SCHEDULE_RESPONSE)) as mock_get:
        result = nhl_client.get_schedule_today()

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["id"] == 1234
    assert result[1]["id"] == 5678
    mock_get.assert_called_once()


def test_get_game_boxscore_returns_dict_with_expected_keys():
    with patch("httpx.get", return_value=_mock_ok(BOXSCORE_RESPONSE)):
        result = nhl_client.get_game_boxscore(1234)

    assert isinstance(result, dict)
    assert "id" in result
    assert "awayTeam" in result
    assert "homeTeam" in result
    assert result["id"] == 1234


def test_get_schedule_today_uses_cache_on_second_call():
    with patch("httpx.get", return_value=_mock_ok(SCHEDULE_RESPONSE)) as mock_get:
        nhl_client.get_schedule_today()
        nhl_client.get_schedule_today()

    mock_get.assert_called_once()


def test_get_game_boxscore_uses_cache_on_second_call():
    with patch("httpx.get", return_value=_mock_ok(BOXSCORE_RESPONSE)) as mock_get:
        nhl_client.get_game_boxscore(1234)
        nhl_client.get_game_boxscore(1234)

    mock_get.assert_called_once()


def test_get_schedule_today_raises_on_non_2xx():
    with patch("httpx.get", return_value=_mock_error(404)):
        with pytest.raises(httpx.HTTPStatusError):
            nhl_client.get_schedule_today()


def test_get_game_boxscore_raises_on_non_2xx():
    with patch("httpx.get", return_value=_mock_error(500)):
        with pytest.raises(httpx.HTTPStatusError):
            nhl_client.get_game_boxscore(9999)
