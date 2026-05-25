"""
Thin wrapper around the public NHL APIs.

- Web API (scores/schedule): https://api-web.nhle.com/v1/
- Stats REST API (teams/franchises): https://api.nhle.com/stats/rest/en/

Web API responses are cached via TTLCache; stats API calls are uncached
because they are only made once at startup.
"""
import httpx
from cachetools import TTLCache

_BASE = 'https://api-web.nhle.com/v1'
_STATS_BASE = 'https://api.nhle.com/stats/rest/en'

# Cache: max 128 entries, 5-minute TTL
_cache: TTLCache = TTLCache(maxsize=128, ttl=300)


def _get(path: str) -> dict:
    if path in _cache:
        return _cache[path]
    url = f'{_BASE}{path}'
    resp = httpx.get(url, timeout=10, follow_redirects=True)
    resp.raise_for_status()
    data = resp.json()
    _cache[path] = data
    return data


def get_schedule_now() -> dict:
    """Today's schedule: GET /v1/schedule/now"""
    return _get('/schedule/now')


def get_boxscore(game_id: int) -> dict:
    """Game boxscore: GET /v1/gamecenter/{gameId}/boxscore"""
    return _get(f'/gamecenter/{game_id}/boxscore')


def get_score_now() -> dict:
    """Today's scores for all games: GET /v1/score/now

    Returns:
        Dict with keys ``currentDate`` (str) and ``games`` (list of game dicts).
        Each game dict contains ``id``, ``gameState``, ``periodDescriptor``,
        ``clock``, ``awayTeam``, and ``homeTeam``.
    """
    return _get('/score/now')


def get_all_teams() -> list[dict]:
    """All NHL franchises: GET https://api.nhle.com/stats/rest/en/team

    Returns:
        List of team dicts, each containing id, franchiseId, fullName,
        leagueId, rawTricode, and triCode.
    """
    url = f'{_STATS_BASE}/team'
    resp = httpx.get(url, timeout=10, follow_redirects=True)
    resp.raise_for_status()
    return resp.json().get('data', [])
