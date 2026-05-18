"""Deterministic odds stub returning fixture data from the Dashboard.html prototype."""

# Fixture data sourced from the SLATE constant in src/components/dashboard/handoff/Dashboard.html.
# Values are American-odds integers; same value is always returned for a given game_id.
_FIXTURES = [
    {"away_ml": 120,  "home_ml": -140, "away_ml_open": 115,  "home_ml_open": -135},
    {"away_ml": -105, "home_ml": -115, "away_ml_open": -110, "home_ml_open": -110},
    {"away_ml": -160, "home_ml":  135, "away_ml_open": -145, "home_ml_open":  125},
    {"away_ml": 130,  "home_ml": -150, "away_ml_open":  120, "home_ml_open": -140},
    {"away_ml": 175,  "home_ml": -210, "away_ml_open":  185, "home_ml_open": -220},
    {"away_ml": 145,  "home_ml": -170, "away_ml_open":  135, "home_ml_open": -160},
    {"away_ml": 120,  "home_ml": -140, "away_ml_open":  125, "home_ml_open": -145},
    {"away_ml": -180, "home_ml":  155, "away_ml_open": -170, "home_ml_open":  148},
]


def get_odds(game_id: int) -> dict:
    """Return deterministic mock odds for a game.

    Cycles through the fixture table using ``game_id % len(_FIXTURES)`` so the
    return value is always the same for a given ``game_id`` and never random.

    Args:
        game_id: The NHL game ID.

    Returns:
        Dict with integer keys ``away_ml``, ``home_ml``, ``away_ml_open``,
        ``home_ml_open`` in American-odds format (e.g. +120 → 120).
    """
    return _FIXTURES[game_id % len(_FIXTURES)]
