"""
Implied probability + edge math.

All values are in **percentage points (0–100)**, not fractions.
``american_to_implied(-110)`` → ``52.38``, not ``0.5238``.
``devig_two_way(52.38, 50.0)`` → ``(51.17, 48.83)`` (sum = 100.0).
``edge(fair_pct, market_pct)`` → signed difference in percentage points.

All functions accept raw American odds integers (+120, -140, etc.).
"""
from datetime import datetime, timezone
from extensions import db
from models import LiveGame, OddsSnapshot, ModelFair


def american_to_implied(odds: int) -> float:
    """Convert American odds to implied probability as a percentage (0–100).

    Args:
        odds: American moneyline integer, e.g. +120 or -140.

    Returns:
        Implied win probability in [0, 100], e.g. +120 → 45.45.

    Raises:
        ValueError: If odds is 0 (undefined).
    """
    if odds == 0:
        raise ValueError("odds=0 is undefined; use a positive or negative integer")
    if odds > 0:
        return 100 / (odds + 100) * 100
    return -odds / (-odds + 100) * 100


def devig_two_way(p_away: float, p_home: float) -> tuple[float, float]:
    """Remove the bookmaker's vig from a two-way market.

    Args:
        p_away: Raw implied probability for the away side (0–100 percentage points).
        p_home: Raw implied probability for the home side (0–100 percentage points).

    Returns:
        Tuple of (away_fair, home_fair) in percentage points, normalized so they
        sum to 100.0. Falls back to (50.0, 50.0) when both inputs are zero.
    """
    total = p_away + p_home
    if total == 0:
        return 50.0, 50.0
    return p_away / total * 100, p_home / total * 100


def edge(fair_pct: float, market_pct: float) -> float:
    """Positive edge = model thinks side is more likely than market prices.

    Args:
        fair_pct: Model fair-value probability in percentage points (0–100).
        market_pct: Market implied probability in percentage points (0–100).

    Returns:
        Signed difference in percentage points.
    """
    return fair_pct - market_pct


def compute_all_fair():
    """
    For each game with an OddsSnapshot, upsert a ModelFair row.
    v1: fair = de-vigged market implied (no proprietary model adjustment).
    """
    from sqlalchemy import select

    today_games = db.session.scalars(
        select(LiveGame).where(LiveGame.status.in_(['scheduled', 'live']))
    ).all()

    now = datetime.now(timezone.utc)
    for g in today_games:
        snap = db.session.scalars(
            select(OddsSnapshot)
            .where(OddsSnapshot.game_id == g.game_id)
            .order_by(OddsSnapshot.fetched_at.desc())
        ).first()
        if not snap:
            continue

        raw_away = american_to_implied(snap.away_ml)
        raw_home = american_to_implied(snap.home_ml)
        fair_away, fair_home = devig_two_way(raw_away, raw_home)

        mf = db.session.get(ModelFair, g.game_id)
        if mf is None:
            mf = ModelFair(game_id=g.game_id)
            db.session.add(mf)
        mf.away_fair = fair_away
        mf.home_fair = fair_home
        mf.computed_at = now

    db.session.commit()
