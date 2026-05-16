"""NHL API client skill for fetching live scoreboard data."""
import requests

NHL_SCOREBOARD_URL = "https://api-web.nhle.com/v1/scoreboard/now"
NHL_SCORE_URL = "https://api-web.nhle.com/v1/score/now"
NHL_TEAM_SCHEDULE_URL = "https://api-web.nhle.com/v1/club-schedule-season/{}/now"

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


def get_todays_score_now() -> list:
    """Fetches today's NHL games from the score/now endpoint.

    Returns the flat ``games`` list from the NHL score API, which includes
    per-team odds nested under ``awayTeam.odds`` and ``homeTeam.odds``.

    Returns:
        list[dict]: Game objects for today. Each dict contains ``gameState``,
            ``homeTeam``, ``awayTeam`` (with optional ``odds`` lists), etc.
            Returns an empty list if no games key is present.

    Raises:
        requests.HTTPError: If the API responds with a non-2xx HTTP status.
    """
    response = requests.get(NHL_SCORE_URL)
    response.raise_for_status()
    return response.json().get("games", [])


def extract_team_odds(team: dict) -> int | None:
    """Extracts a money line odds integer from a team dict's odds list.

    Reads ``team["odds"][0]["value"]`` and converts the string (e.g. ``"-120"``
    or ``"+105"``) to an integer.  Returns ``None`` when the odds field is
    absent, empty, or the value key is missing.

    Args:
        team: Team dict from the NHL score/now API, e.g. ``awayTeam`` or
            ``homeTeam``, which may contain an ``odds`` list.

    Returns:
        int | None: Integer money line value, or ``None`` when unavailable.
    """
    odds_list = team.get("odds", [])
    if not odds_list:
        return None
    value = odds_list[0].get("value")
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def get_team_last_5(team_abbrev: str) -> list:
    """Fetches the last 5 completed game results for a team.

    Args:
        team_abbrev: The team's three-letter abbreviation (e.g., ``"TOR"``).

    Returns:
        list[dict]: Up to 5 most recent completed games, each with keys:
            - ``result`` (str): ``"W"`` or ``"L"``.
            - ``score`` (str): ``"team_score-opponent_score"`` (e.g., ``"4-2"``).
        Returns an empty list when no completed games exist.

    Raises:
        requests.HTTPError: If the API responds with a non-2xx HTTP status.
    """
    url = NHL_TEAM_SCHEDULE_URL.format(team_abbrev)
    response = requests.get(url)
    response.raise_for_status()

    games = response.json().get("games", [])
    completed = [g for g in games if g.get("gameState") in _FINAL_STATES]
    return [_format_team_game_result(g, team_abbrev) for g in completed[-5:]]


def _format_team_game_result(game: dict, team_abbrev: str) -> dict:
    """Formats a single completed game as a win/loss result for the given team.

    Args:
        game: Raw game dict from the NHL schedule API.
        team_abbrev: The team abbreviation used to determine which side won.

    Returns:
        dict: ``{"result": "W"|"L", "score": "team_score-opp_score"}``.
    """
    home = game.get("homeTeam", {})
    away = game.get("awayTeam", {})
    is_home = home.get("abbrev") == team_abbrev
    team_score = home.get("score", 0) if is_home else away.get("score", 0)
    opp_score = away.get("score", 0) if is_home else home.get("score", 0)
    result = "W" if team_score > opp_score else "L"
    return {"result": result, "score": f"{team_score}-{opp_score}"}


def get_season_series(away_abbrev: str, home_abbrev: str) -> dict:
    """Fetches the season series record between two teams using the away team's schedule.

    Args:
        away_abbrev: Three-letter abbreviation of the team playing away today.
        home_abbrev: Three-letter abbreviation of the team playing at home today.

    Returns:
        dict: Season series summary with keys:
            - ``away_wins`` (int): Wins credited to the away team.
            - ``home_wins`` (int): Wins credited to the home team.
            - ``meetings`` (int): Total completed matchups between the two teams.

    Raises:
        requests.HTTPError: If the API responds with a non-2xx HTTP status.
    """
    url = NHL_TEAM_SCHEDULE_URL.format(away_abbrev)
    response = requests.get(url)
    response.raise_for_status()

    games = response.json().get("games", [])
    matchups = [
        g for g in games
        if g.get("gameState") in _FINAL_STATES
        and home_abbrev in (
            g.get("homeTeam", {}).get("abbrev"),
            g.get("awayTeam", {}).get("abbrev"),
        )
    ]

    away_wins = 0
    home_wins = 0
    for g in matchups:
        home = g.get("homeTeam", {})
        away = g.get("awayTeam", {})
        home_score = home.get("score", 0)
        away_score = away.get("score", 0)
        if home_score > away_score:
            winner = home.get("abbrev")
        else:
            winner = away.get("abbrev")
        if winner == away_abbrev:
            away_wins += 1
        else:
            home_wins += 1

    return {"away_wins": away_wins, "home_wins": home_wins, "meetings": len(matchups)}


def _extract_moneyline(game: dict) -> tuple:
    """Extracts away and home money line odds from a game object.

    Reads the first entry in the ``odds`` array of the game dict.  Returns
    ``(None, None)`` when the field is absent, empty, or missing expected keys.

    Args:
        game: Raw game dict that may contain an ``odds`` list.

    Returns:
        tuple[int | None, int | None]: ``(away_ml, home_ml)`` integer odds, or
            ``(None, None)`` when odds are unavailable or malformed.
    """
    odds_list = game.get("odds", [])
    if not odds_list:
        return None, None
    entry = odds_list[0]
    away_ml = entry.get("awayOdds")
    home_ml = entry.get("homeOdds")
    if away_ml is None or home_ml is None:
        return None, None
    return away_ml, home_ml


def format_game(
    game: dict,
    away_history: list | None = None,
    home_history: list | None = None,
    season_series: dict | None = None,
) -> dict:
    """Normalizes a raw NHL API game object for dashboard display.

    Args:
        game: Raw game dict from the NHL scoreboard API containing at minimum
            ``gameState``, ``homeTeam``, and ``awayTeam`` fields.  May
            optionally include an ``odds`` list with money line data.
        away_history: Pre-fetched last-5 results for the away team.  Each
            entry is ``{"result": "W"|"L", "score": "X-Y"}``.  Defaults to
            an empty list when not provided.
        home_history: Same as ``away_history`` but for the home team.
        season_series: Season series record between the two teams, with keys
            ``away_wins``, ``home_wins``, and ``meetings``.  Defaults to None
            when unavailable.

    Returns:
        dict: Simplified game with keys:
            - ``away`` (str): Away team abbreviation.
            - ``home`` (str): Home team abbreviation.
            - ``away_score`` (int): Away team score (0 if pre-game).
            - ``home_score`` (int): Home team score (0 if pre-game).
            - ``status`` (str): One of ``"live"``, ``"final"``, or
              ``"upcoming"``.
            - ``away_ml`` (int | None): Away team money line odds, or None.
            - ``home_ml`` (int | None): Home team money line odds, or None.
            - ``away_last5`` (list): Last 5 completed results for away team.
            - ``home_last5`` (list): Last 5 completed results for home team.
            - ``season_series`` (dict | None): Season series summary, or None.
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

    away_ml = extract_team_odds(away)
    home_ml = extract_team_odds(home)
    if away_ml is None and home_ml is None:
        away_ml, home_ml = _extract_moneyline(game)

    return {
        "away": away.get("abbrev", ""),
        "home": home.get("abbrev", ""),
        "away_score": away.get("score", 0),
        "home_score": home.get("score", 0),
        "status": status,
        "away_ml": away_ml,
        "home_ml": home_ml,
        "away_last5": away_history if away_history is not None else [],
        "home_last5": home_history if home_history is not None else [],
        "season_series": season_series,
    }
