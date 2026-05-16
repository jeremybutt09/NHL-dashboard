"""NHL API client skill for fetching live scoreboard data."""
import requests

NHL_SCOREBOARD_URL = "https://api-web.nhle.com/v1/scoreboard/now"

_LIVE_STATES = {"LIVE", "CRIT"}
_FINAL_STATES = {"FINAL", "OFF"}


def get_todays_games() -> list:
    """Fetches today's NHL games from the public NHL scoreboard API.

    Queries the scoreboard endpoint and returns the games for the API's
    ``focusedDate`` (i.e. today as determined by the NHL API).

    Returns:
        list[dict]: Game objects for today. Each dict contains fields such as
            ``id``, ``gameDate``, ``gameState``, ``homeTeam``, and
            ``awayTeam``. Returns an empty list if no games are scheduled.

    Raises:
        requests.HTTPError: If the API responds with a non-2xx HTTP status.
    """
    response = requests.get(NHL_SCOREBOARD_URL)
    response.raise_for_status()

    data = response.json()
    focused_date = data.get("focusedDate")

    for entry in data.get("gamesByDate", []):
        if entry.get("date") == focused_date:
            return entry.get("games", [])

    return []


def format_game(game: dict) -> dict:
    """Normalizes a raw NHL API game object for dashboard display.

    Args:
        game: Raw game dict from the NHL scoreboard API containing at minimum
            ``gameState``, ``homeTeam``, and ``awayTeam`` fields.

    Returns:
        dict: Simplified game with keys:
            - ``away`` (str): Away team abbreviation.
            - ``home`` (str): Home team abbreviation.
            - ``away_score`` (int): Away team score (0 if pre-game).
            - ``home_score`` (int): Home team score (0 if pre-game).
            - ``status`` (str): One of ``"live"``, ``"final"``, or
              ``"upcoming"``.
    """
    state = game.get("gameState", "")
    if state in _LIVE_STATES:
        status = "live"
    elif state in _FINAL_STATES:
        status = "final"
    else:
        status = "upcoming"

    home = game.get("homeTeam", {})
    away = game.get("awayTeam", {})

    return {
        "away": away.get("abbrev", ""),
        "home": home.get("abbrev", ""),
        "away_score": away.get("score", 0),
        "home_score": home.get("score", 0),
        "status": status,
    }
