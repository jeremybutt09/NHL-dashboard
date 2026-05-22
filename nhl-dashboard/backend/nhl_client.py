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

# gameType 2 = regular season, 3 = playoffs
_SERIES_GAME_TYPES = {2, 3}


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

    def __init__(self, slate_ttl: int = None, live_ttl: int = None, standings_ttl: int = None):
        slate_ttl = slate_ttl if slate_ttl is not None else Config.POLL_SLATE_INTERVAL
        live_ttl = live_ttl if live_ttl is not None else Config.POLL_LIVE_INTERVAL
        standings_ttl = standings_ttl if standings_ttl is not None else Config.POLL_STANDINGS_INTERVAL
        self._schedule_cache: TTLCache = TTLCache(maxsize=1, ttl=slate_ttl)
        self._boxscore_cache: TTLCache = TTLCache(maxsize=64, ttl=live_ttl)
        self._standings_cache: TTLCache = TTLCache(maxsize=1, ttl=standings_ttl)
        self._team_schedule_cache: TTLCache = TTLCache(maxsize=32, ttl=slate_ttl)

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
            resp = httpx.get(f"{BASE_URL}/schedule/now", follow_redirects=True)
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
            resp = httpx.get(f"{BASE_URL}/gamecenter/{game_id}/boxscore", follow_redirects=True)
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

    def get_standings(self) -> Optional[dict]:
        """Fetch current NHL standings, caching the result.

        Returns:
            Dict keyed by team abbreviation, each value a dict with wins,
            losses, ot_losses, l10_wins, l10_losses, l10_ot_losses. None on
            HTTP error.
        """
        cache_key = "standings"
        if cache_key in self._standings_cache:
            return self._standings_cache[cache_key]

        try:
            resp = httpx.get(f"{BASE_URL}/standings/now", follow_redirects=True)
            resp.raise_for_status()
        except Exception:
            logger.exception("Failed to fetch NHL standings")
            return None

        standings = self._parse_standings(resp.json())
        self._standings_cache[cache_key] = standings
        return standings

    def get_team_schedule(self, team_code: str) -> Optional[list]:
        """Fetch the full-season schedule for a team, caching the result.

        Args:
            team_code: Three-letter team abbreviation (e.g. 'TOR').

        Returns:
            Raw list of game dicts from the NHL club-schedule-season endpoint,
            or None on HTTP error.
        """
        if team_code in self._team_schedule_cache:
            return self._team_schedule_cache[team_code]

        try:
            resp = httpx.get(
                f"{BASE_URL}/club-schedule-season/{team_code}/now",
                follow_redirects=True,
            )
            resp.raise_for_status()
        except Exception:
            logger.exception("Failed to fetch team schedule for %s", team_code)
            return None

        games = resp.json().get("games", [])
        self._team_schedule_cache[team_code] = games
        return games

    def get_series(self, away_code: str, home_code: str) -> Optional[dict]:
        """Compute the season series record between two teams.

        Fetches the away team's schedule and counts completed regular-season
        and playoff games against the home team.

        Args:
            away_code: Abbreviation of today's away team (e.g. 'TOR').
            home_code: Abbreviation of today's home team (e.g. 'BOS').

        Returns:
            Dict with away_wins, home_wins, and games_played, or None if the
            schedule API is unavailable.
        """
        games = self.get_team_schedule(away_code)
        if games is None:
            return None

        away_wins = 0
        home_wins = 0
        games_played = 0

        for game in games:
            if game.get("gameType") not in _SERIES_GAME_TYPES:
                continue
            if game.get("gameState") not in _FINAL_STATES:
                continue

            g_away = game.get("awayTeam", {}).get("abbrev", "")
            g_home = game.get("homeTeam", {}).get("abbrev", "")

            if {g_away, g_home} != {away_code, home_code}:
                continue

            games_played += 1
            g_away_score = game.get("awayTeam", {}).get("score", 0)
            g_home_score = game.get("homeTeam", {}).get("score", 0)

            # Determine which of today's teams won this historical game.
            if g_away == away_code:
                if g_away_score > g_home_score:
                    away_wins += 1
                else:
                    home_wins += 1
            else:
                # away_code was home in this game
                if g_home_score > g_away_score:
                    away_wins += 1
                else:
                    home_wins += 1

        return {"away_wins": away_wins, "home_wins": home_wins, "games_played": games_played}

    def _parse_standings(self, data: dict) -> dict:
        """Extract per-team standings from the standings API response.

        Args:
            data: Raw JSON from GET /v1/standings/now.

        Returns:
            Dict keyed by team abbreviation string with wins, losses,
            ot_losses, l10_wins, l10_losses, l10_ot_losses integer fields.
        """
        result = {}
        for entry in data.get("standings", []):
            abbrev = entry.get("teamAbbrev", {}).get("default", "")
            if not abbrev:
                continue
            result[abbrev] = {
                "wins": entry.get("wins", 0),
                "losses": entry.get("losses", 0),
                "ot_losses": entry.get("otLosses", 0),
                "l10_wins": entry.get("l10Wins", 0),
                "l10_losses": entry.get("l10Losses", 0),
                "l10_ot_losses": entry.get("l10OtLosses", 0),
            }
        return result


# Module-level singleton used by services.
nhl_client = NhlClient()
