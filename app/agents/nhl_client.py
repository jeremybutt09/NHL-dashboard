"""NHL API client skill for fetching live scoreboard data."""
import requests

NHL_SCOREBOARD_URL = "https://api-web.nhle.com/v1/scoreboard/now"


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
