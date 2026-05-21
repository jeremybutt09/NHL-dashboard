"""NHL API client with TTLCache for the public NHL Stats API."""

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from cachetools import TTLCache

from config import Config

logger = logging.getLogger(__name__)

BASE_URL = "https://api-web.nhle.com/v1"

_PERIOD_LABELS = {1: "1st", 2: "2nd", 3: "3rd"}
_LIVE_STATES = {"LIVE", "CRIT"}
_FINAL_STATES = {"FINAL", "OFF"}


def _map_game_state(state: str) -> str:
    """Normalize NHL gameState codes to our status vocabulary.

    Args:
        state: Raw gameState string from the NHL API (e.g. "LIVE", "FUT").

    Returns:
        One of 'live', 'final', or 'scheduled'.
    """
    if state in _LIVE_STATES:
        return "live"
    if state in _FINAL_STATES:
        return "final"
    return "scheduled"


def _map_period(descriptor: dict) -> str:
    """Convert a periodDescriptor dict to a human-readable label.

    Args:
        descriptor: Dict with 'number' and 'periodType' keys.

    Returns:
        String like '1st', '2nd', 'OT', 'SO'.
    """
    period_type = descriptor.get("periodType", "REG")
    if period_type == "OT":
        return "OT"
    if period_type == "SO":
        return "SO"
    return _PERIOD_LABELS.get(descriptor.get("number", 0), str(descriptor.get("number", 0)))


class NhlClient:
    """Wrapper around the NHL public Stats API with in-memory TTL caching.

    Args:
        slate_ttl: Cache TTL in seconds for schedule responses.
        live_ttl: Cache TTL in seconds for boxscore responses.
    """

    def __init__(self, slate_ttl: int = None, live_ttl: int = None):
        slate_ttl = slate_ttl if slate_ttl is not None else Config.POLL_SLATE_INTERVAL
        live_ttl = live_ttl if live_ttl is not None else Config.POLL_LIVE_INTERVAL
        self._schedule_cache: TTLCache = TTLCache(maxsize=1, ttl=slate_ttl)
        self._boxscore_cache: TTLCache = TTLCache(maxsize=64, ttl=live_ttl)

    def _today(self) -> str:
        """Return today's UTC date as YYYY-MM-DD (isolated for easy mocking)."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def get_schedule_today(self) -> Optional[list]:
        """Fetch today's NHL game schedule, caching the result.

        Returns:
            List of game dicts with id, start_utc, venue, away_code, away_name,
            home_code, home_name, and status keys. None on HTTP error.
        """
        cache_key = "schedule"
        if cache_key in self._schedule_cache:
            return self._schedule_cache[cache_key]

        try:
            resp = httpx.get(f"{BASE_URL}/schedule/now")
            resp.raise_for_status()
        except Exception:
            logger.exception("Failed to fetch NHL schedule")
            return None

        games = self._parse_schedule(resp.json())
        self._schedule_cache[cache_key] = games
        return games

    def _parse_schedule(self, data: dict) -> list:
        """Extract and normalize today's game list from the schedule response.

        Args:
            data: Raw JSON from GET /v1/schedule/now.

        Returns:
            Flat list of normalized game dicts for today's date.
        """
        today_str = self._today()
        result = []
        for week_day in data.get("gameWeek", []):
            if week_day.get("date") != today_str:
                continue
            for game in week_day.get("games", []):
                result.append({
                    "id": game["id"],
                    "start_utc": game.get("startTimeUTC"),
                    "venue": game.get("venue", {}).get("default"),
                    "away_code": game["awayTeam"]["abbrev"],
                    "away_name": game["awayTeam"].get("commonName", {}).get("default", ""),
                    "home_code": game["homeTeam"]["abbrev"],
                    "home_name": game["homeTeam"].get("commonName", {}).get("default", ""),
                    "status": _map_game_state(game.get("gameState", "FUT")),
                })
        return result

    def get_boxscore(self, game_id: int) -> Optional[dict]:
        """Fetch the current boxscore for a game, caching the result.

        Args:
            game_id: The NHL game ID (gamePk).

        Returns:
            Dict with status, period, clock, away_score, home_score, away_sog,
            home_sog keys. None on HTTP error.
        """
        if game_id in self._boxscore_cache:
            return self._boxscore_cache[game_id]

        try:
            resp = httpx.get(f"{BASE_URL}/gamecenter/{game_id}/boxscore")
            resp.raise_for_status()
        except Exception:
            logger.exception("Failed to fetch boxscore for game %s", game_id)
            return None

        data = resp.json()
        parsed = {
            "status": _map_game_state(data.get("gameState", "FUT")),
            "period": _map_period(data.get("periodDescriptor", {})),
            "clock": data.get("clock", {}).get("timeRemaining"),
            "away_score": data.get("awayTeam", {}).get("score", 0),
            "home_score": data.get("homeTeam", {}).get("score", 0),
            "away_sog": data.get("awayTeam", {}).get("sog", 0),
            "home_sog": data.get("homeTeam", {}).get("sog", 0),
        }
        self._boxscore_cache[game_id] = parsed
        return parsed


# Module-level singleton used by services.
nhl_client = NhlClient()
