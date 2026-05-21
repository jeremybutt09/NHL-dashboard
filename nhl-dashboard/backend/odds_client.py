"""Odds provider client — deterministic stub using SLATE fixture data.

Fixture values are lifted verbatim from Dashboard.html's SLATE and MOVEMENT
constants so the frontend renders correctly without a real odds provider.
"""

# Lifted from Dashboard.html: SLATE (odds) + MOVEMENT (24h sparkline arrays).
_SLATE_ODDS = [
    {
        "ml": {"away": 120, "home": -140},
        "ml_open": {"away": 115, "home": -135},
        "implied": {"away": 45.0, "home": 55.0},
        "fair": {"away": 47.5, "home": 52.5},
        "edge": 2.1,
        "movement_24h": [
            46.38, 44.95, 44.14, 45.07, 44.14, 43.78, 44.91, 44.44,
            44.9,  45.95, 47.13, 46.81, 45.87, 45.58, 45.31, 45.5,
            44.68, 45.68, 44.41, 45.36, 43.91, 43.55, 43.64, 45.0,
        ],
    },
    {
        "ml": {"away": -105, "home": -115},
        "ml_open": {"away": -110, "home": -110},
        "implied": {"away": 51.0, "home": 49.0},
        "fair": {"away": 49.5, "home": 50.5},
        "edge": 1.5,
        "movement_24h": [
            54.17, 54.16, 53.84, 53.38, 53.08, 53.23, 52.65, 51.22,
            51.55, 50.03, 51.22, 52.22, 52.59, 51.13, 51.89, 52.82,
            52.03, 52.71, 53.72, 54.65, 53.51, 52.61, 52.03, 51.0,
        ],
    },
    {
        "ml": {"away": -160, "home": 135},
        "ml_open": {"away": -145, "home": 125},
        "implied": {"away": 62.0, "home": 38.0},
        "fair": {"away": 58.0, "home": 42.0},
        "edge": -1.2,
        "movement_24h": [
            61.73, 61.49, 60.54, 59.38, 60.68, 61.13, 62.39, 63.75,
            62.81, 61.62, 61.48, 62.26, 61.6,  61.8,  61.26, 62.04,
            62.75, 62.43, 63.32, 62.88, 62.84, 61.32, 60.06, 62.0,
        ],
    },
    {
        "ml": {"away": 130, "home": -150},
        "ml_open": {"away": 120, "home": -140},
        "implied": {"away": 43.0, "home": 57.0},
        "fair": {"away": 45.5, "home": 54.5},
        "edge": 2.5,
        "movement_24h": [
            42.15, 41.53, 41.63, 41.89, 40.83, 42.35, 42.74, 42.52,
            41.96, 42.99, 43.46, 42.11, 42.27, 41.6,  42.37, 41.46,
            41.92, 42.07, 41.27, 40.23, 42.05, 43.63, 42.38, 43.0,
        ],
    },
    {
        "ml": {"away": 175, "home": -210},
        "ml_open": {"away": 185, "home": -220},
        "implied": {"away": 36.0, "home": 64.0},
        "fair": {"away": 34.5, "home": 65.5},
        "edge": -1.5,
        "movement_24h": [
            37.36, 37.28, 37.4,  37.62, 36.03, 35.1,  36.46, 37.27,
            35.92, 35.36, 34.47, 35.76, 35.18, 35.6,  36.39, 35.65,
            35.66, 34.97, 35.69, 35.02, 36.06, 37.28, 36.57, 36.0,
        ],
    },
    {
        "ml": {"away": 145, "home": -170},
        "ml_open": {"away": 135, "home": -160},
        "implied": {"away": 41.0, "home": 59.0},
        "fair": {"away": 43.0, "home": 57.0},
        "edge": 2.0,
        "movement_24h": [
            41.78, 41.32, 42.48, 41.13, 40.72, 40.77, 41.17, 40.34,
            39.32, 40.93, 40.63, 39.74, 39.96, 39.49, 38.57, 39.68,
            39.32, 39.02, 37.97, 39.64, 38.95, 40.32, 40.21, 41.0,
        ],
    },
    {
        "ml": {"away": 120, "home": -140},
        "ml_open": {"away": 125, "home": -145},
        "implied": {"away": 45.0, "home": 55.0},
        "fair": {"away": 44.0, "home": 56.0},
        "edge": -1.0,
        "movement_24h": [
            47.57, 48.53, 47.18, 47.98, 48.1,  48.58, 47.22, 45.36,
            44.17, 43.18, 42.85, 43.27, 44.77, 46.11, 45.68, 44.06,
            43.9,  43.42, 44.77, 43.51, 43.75, 45.09, 44.71, 45.0,
        ],
    },
    {
        "ml": {"away": -180, "home": 155},
        "ml_open": {"away": -170, "home": 148},
        "implied": {"away": 64.0, "home": 36.0},
        "fair": {"away": 66.0, "home": 34.0},
        "edge": 2.0,
        "movement_24h": [
            65.99, 66.57, 66.26, 65.49, 63.79, 62.79, 64.45, 64.21,
            63.03, 63.95, 63.99, 65.06, 63.66, 64.1,  64.94, 64.61,
            63.63, 63.17, 62.44, 63.27, 64.57, 65.36, 65.0,  64.0,
        ],
    },
]


def get_odds(game_id: int) -> dict:
    """Return deterministic stub odds for a given game ID.

    Cycles through the SLATE fixture by (game_id % len) so every call is
    deterministic and different game IDs produce visually distinct rows.

    Args:
        game_id: NHL game ID (any integer).

    Returns:
        Dict with ml, ml_open, implied, fair, edge, and movement_24h keys.
    """
    return _SLATE_ODDS[game_id % len(_SLATE_ODDS)]
