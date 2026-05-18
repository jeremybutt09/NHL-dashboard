"""Implied probability and edge calculation utilities."""


def american_to_implied(odds: int) -> float:
    """Convert American odds to implied probability percentage.

    Args:
        odds: American odds integer (e.g. +120 or -140).

    Returns:
        Implied probability as a percentage (e.g. 45.45).
    """
    if odds > 0:
        return 100 / (odds + 100) * 100
    return -odds / (-odds + 100) * 100


def devig_two_way(p_away: float, p_home: float) -> tuple[float, float]:
    """Remove the vig from a two-way market.

    Args:
        p_away: Raw implied probability for the away side.
        p_home: Raw implied probability for the home side.

    Returns:
        Tuple of (fair_away_pct, fair_home_pct) normalized to sum to 100.
    """
    total = p_away + p_home
    return p_away / total * 100, p_home / total * 100


def edge(fair_pct: float, market_pct: float) -> float:
    """Calculate the edge between a fair probability and the market price.

    Args:
        fair_pct: Model's fair probability percentage.
        market_pct: Market's implied probability percentage.

    Returns:
        Positive value means the model thinks this side is more likely
        than the market prices; negative means the opposite.
    """
    return fair_pct - market_pct
