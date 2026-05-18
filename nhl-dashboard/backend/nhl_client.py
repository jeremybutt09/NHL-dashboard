"""NHL Stats API client with TTLCache caching."""

import httpx
from cachetools import TTLCache

BASE_URL = "https://api-web.nhle.com/v1"

_schedule_cache: TTLCache = TTLCache(maxsize=1, ttl=300)   # 5-minute TTL
_boxscore_cache: TTLCache = TTLCache(maxsize=256, ttl=15)  # 15-second TTL


def _fetch(url: str) -> dict:
    """Fetch a URL and return the parsed JSON body.

    Args:
        url: Full URL to request.

    Returns:
        Parsed JSON response as a dict.

    Raises:
        httpx.HTTPStatusError: If the response status is non-2xx.
    """
    response = httpx.get(url)
    response.raise_for_status()
    return response.json()


def get_schedule_today() -> list[dict]:
    """Return today's NHL games from /v1/schedule/now.

    Results are cached for 5 minutes.

    Returns:
        List of game dicts for the current day.

    Raises:
        httpx.HTTPStatusError: If the API returns a non-2xx response.
    """
    cache_key = "schedule"
    if cache_key in _schedule_cache:
        return _schedule_cache[cache_key]

    data = _fetch(f"{BASE_URL}/schedule/now")
    game_week = data.get("gameWeek", [])
    games: list[dict] = game_week[0].get("games", []) if game_week else []

    _schedule_cache[cache_key] = games
    return games


def get_game_boxscore(game_id: int) -> dict:
    """Return the boxscore for a specific game from /v1/gamecenter/{gameId}/boxscore.

    Results are cached for 15 seconds.

    Args:
        game_id: The NHL game ID.

    Returns:
        Boxscore dict for the requested game.

    Raises:
        httpx.HTTPStatusError: If the API returns a non-2xx response.
    """
    if game_id in _boxscore_cache:
        return _boxscore_cache[game_id]

    data = _fetch(f"{BASE_URL}/gamecenter/{game_id}/boxscore")
    _boxscore_cache[game_id] = data
    return data
