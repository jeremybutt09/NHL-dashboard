"""Implied probability and edge math for moneyline markets."""


def american_to_implied(odds: int) -> float:
    """Convert American moneyline odds to implied probability.

    Args:
        odds: American odds integer, e.g. +120 or -140.

    Returns:
        Implied probability as a percentage (0–100).
        +120 → 45.45, -140 → 58.33.
    """
    if odds > 0:
        return 100 / (odds + 100) * 100
    return -odds / (-odds + 100) * 100


def devig_two_way(p_away: float, p_home: float) -> tuple[float, float]:
    """Remove the bookmaker's vig from a two-way market.

    Both raw implied probabilities usually sum to slightly more than 100
    because of the vig. This normalizes them so the result sums to exactly 100.

    Args:
        p_away: Raw implied probability for the away team (0–100).
        p_home: Raw implied probability for the home team (0–100).

    Returns:
        Tuple of (away_pct, home_pct) that sum to 100.0.
    """
    total = p_away + p_home
    return p_away / total * 100, p_home / total * 100


def edge(fair_pct: float, market_pct: float) -> float:
    """Compute the model edge over the market.

    Positive edge means the model thinks the side is more likely than
    the market prices imply.

    Args:
        fair_pct: Model fair probability (0–100).
        market_pct: Market implied probability (0–100).

    Returns:
        Edge in percentage points (fair − market).
    """
    return fair_pct - market_pct
