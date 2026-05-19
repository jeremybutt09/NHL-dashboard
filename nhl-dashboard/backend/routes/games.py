"""GET /api/games/today — full game slate with odds, implied, fair, and edge."""

from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify
from zoneinfo import ZoneInfo

from app import db
from models import Game, ModelFair, OddsSnapshot, Team
from services.implied import edge as calc_edge

games_bp = Blueprint('games', __name__)

_EASTERN = ZoneInfo('America/New_York')


def _today_utc_range() -> tuple[datetime, datetime]:
    """Return naive UTC (start, end) bracketing today in US Eastern time.

    Returns:
        Tuple of (start_utc, end_utc) as naive datetimes for SQLite comparison.
    """
    now_eastern = datetime.now(_EASTERN)
    start_eastern = now_eastern.replace(hour=0, minute=0, second=0, microsecond=0)
    end_eastern = start_eastern + timedelta(days=1)
    start_utc = start_eastern.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_eastern.astimezone(timezone.utc).replace(tzinfo=None)
    return start_utc, end_utc


def _fmt_record(wins: int, losses: int, otl: int) -> str:
    """Format wins/losses/OTL as 'W-L-OT' string."""
    return f"{wins or 0}-{losses or 0}-{otl or 0}"


def _build_game_dict(game: Game) -> dict:
    """Assemble the full JSON dict for one game row.

    Args:
        game: Game ORM instance.

    Returns:
        Dict matching the HANDOFF §4 response shape.
    """
    latest_snap = (
        db.session.query(OddsSnapshot)
        .filter_by(game_id=game.id)
        .order_by(OddsSnapshot.fetched_at.desc())
        .first()
    )

    # Last 24 snapshots ordered oldest→newest for sparkline
    recent_snaps = (
        db.session.query(OddsSnapshot)
        .filter_by(game_id=game.id)
        .order_by(OddsSnapshot.fetched_at.desc())
        .limit(24)
        .all()
    )
    movement_24h = [float(s.away_implied) for s in reversed(recent_snaps)]

    fair_row = db.session.get(ModelFair, game.id)

    away_team = db.session.get(Team, game.away_code)
    home_team = db.session.get(Team, game.home_code)

    if latest_snap:
        ml = {"away": latest_snap.away_ml, "home": latest_snap.home_ml}
        ml_open = {
            "away": latest_snap.away_ml_open,
            "home": latest_snap.home_ml_open,
        }
        implied = {
            "away": latest_snap.away_implied,
            "home": latest_snap.home_implied,
        }
    else:
        ml = ml_open = implied = {"away": None, "home": None}

    if fair_row:
        fair = {"away": fair_row.away_fair, "home": fair_row.home_fair}
        away_implied_pct = latest_snap.away_implied if latest_snap else None
        edge_val = (
            round(calc_edge(fair_row.away_fair, away_implied_pct), 2)
            if away_implied_pct is not None
            else None
        )
    else:
        fair = {"away": None, "home": None}
        edge_val = None

    live = None
    if game.status == "live":
        live = {
            "period": game.period,
            "clock": game.clock,
            "away_score": game.away_score,
            "home_score": game.home_score,
            "away_sog": game.away_sog,
            "home_sog": game.home_sog,
        }

    start_str = (
        game.start_utc.strftime("%Y-%m-%dT%H:%M:%SZ") if game.start_utc else None
    )

    return {
        "id": game.id,
        "away": {
            "code": game.away_code,
            "name": away_team.name if away_team else game.away_code,
            "record": _fmt_record(game.away_wins, game.away_losses, game.away_otl),
            "l10": _fmt_record(game.away_l10_w, game.away_l10_l, game.away_l10_otl),
        },
        "home": {
            "code": game.home_code,
            "name": home_team.name if home_team else game.home_code,
            "record": _fmt_record(game.home_wins, game.home_losses, game.home_otl),
            "l10": _fmt_record(game.home_l10_w, game.home_l10_l, game.home_l10_otl),
        },
        "start": start_str,
        "venue": game.venue,
        "status": game.status,
        "live": live,
        "ml": ml,
        "ml_open": ml_open,
        "implied": implied,
        "fair": fair,
        "edge": edge_val,
        "movement_24h": movement_24h,
    }


@games_bp.get('/api/games/today')
def games_today():
    """Return today's NHL game slate in US Eastern time.

    Returns:
        JSON with ``updated_at`` timestamp and ``games`` list, each entry
        matching the HANDOFF §4 response shape.
    """
    now_utc = datetime.now(timezone.utc)
    start_utc, end_utc = _today_utc_range()

    games = (
        db.session.query(Game)
        .filter(Game.start_utc >= start_utc, Game.start_utc < end_utc)
        .order_by(Game.start_utc)
        .all()
    )

    return jsonify({
        "updated_at": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "games": [_build_game_dict(g) for g in games],
    })
