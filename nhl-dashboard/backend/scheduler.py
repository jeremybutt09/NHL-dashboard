"""APScheduler background jobs for polling NHL data and computing odds."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler


def poll_slate() -> None:
    """Fetch today's game slate and upsert Game/Team rows."""
    from services.slate import refresh_slate
    refresh_slate()


def poll_live() -> None:
    """Update scores, period, and clock for live games."""
    from services.live import refresh_live
    refresh_live()


def poll_odds() -> None:
    """Fetch odds for today's games, insert OddsSnapshot rows with implied values.

    For each Game whose start_utc falls on today's UTC date, calls
    ``odds_client.get_odds()`` and inserts one ``OddsSnapshot`` row with
    raw American odds and converted implied-probability percentages.
    """
    from app import db
    from models import Game, OddsSnapshot
    from services.implied import american_to_implied
    import odds_client

    today = str(datetime.now(timezone.utc).date())
    games = (
        db.session.query(Game)
        .filter(db.func.date(Game.start_utc) == today)
        .all()
    )

    now = datetime.now(timezone.utc)
    for game in games:
        odds = odds_client.get_odds(game.id)
        snap = OddsSnapshot(
            game_id=game.id,
            fetched_at=now,
            book="consensus",
            away_ml=odds["away_ml"],
            home_ml=odds["home_ml"],
            away_implied=american_to_implied(odds["away_ml"]),
            home_implied=american_to_implied(odds["home_ml"]),
        )
        db.session.add(snap)

    db.session.commit()


def compute_fair() -> None:
    """Devig the latest OddsSnapshot and upsert a ModelFair row for each game today.

    For each game, grabs the most-recent OddsSnapshot, removes the vig via
    ``services.implied.devig_two_way()``, and upserts a ``ModelFair`` row.
    """
    from app import db
    from models import Game, ModelFair, OddsSnapshot
    from services.implied import devig_two_way

    today = str(datetime.now(timezone.utc).date())
    games = (
        db.session.query(Game)
        .filter(db.func.date(Game.start_utc) == today)
        .all()
    )

    now = datetime.now(timezone.utc)
    for game in games:
        latest_snap = (
            db.session.query(OddsSnapshot)
            .filter_by(game_id=game.id)
            .order_by(OddsSnapshot.fetched_at.desc())
            .first()
        )
        if latest_snap is None:
            continue

        away_fair, home_fair = devig_two_way(
            latest_snap.away_implied, latest_snap.home_implied
        )

        fair = db.session.get(ModelFair, game.id)
        if fair is None:
            fair = ModelFair(game_id=game.id)
            db.session.add(fair)

        fair.away_fair = away_fair
        fair.home_fair = home_fair
        fair.computed_at = now

    db.session.commit()


def prune_snapshots() -> None:
    """Delete OddsSnapshot rows older than 7 days."""
    from app import db
    from models import OddsSnapshot

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    # synchronize_session=False avoids naive/aware datetime comparison in Python;
    # the DELETE executes at the DB level where the text comparison is valid.
    db.session.query(OddsSnapshot).filter(
        OddsSnapshot.fetched_at < cutoff
    ).delete(synchronize_session=False)
    db.session.commit()


def _make_scheduler(app) -> BackgroundScheduler:
    """Create a BackgroundScheduler pre-loaded with all 5 jobs (not started).

    Each job function is wrapped in an app-context push so it can access the
    SQLAlchemy session.  Call ``sched.start()`` to begin execution.

    Args:
        app: Flask application instance.

    Returns:
        Configured (but not started) BackgroundScheduler.
    """
    sched = BackgroundScheduler()

    def _ctx(fn):
        """Return a no-arg wrapper that pushes the Flask app context."""
        def job():
            with app.app_context():
                fn()
        return job

    sched.add_job(_ctx(poll_slate),       "interval", seconds=300,  id="poll_slate")
    sched.add_job(_ctx(poll_live),        "interval", seconds=15,   id="poll_live")
    sched.add_job(_ctx(poll_odds),        "interval", seconds=300,  id="poll_odds")
    sched.add_job(_ctx(compute_fair),     "interval", seconds=300,  id="compute_fair")
    sched.add_job(_ctx(prune_snapshots),  "interval", seconds=3600, id="prune_snapshots")

    return sched


def init_scheduler(app) -> Optional[BackgroundScheduler]:
    """Start the background scheduler unless the app is in testing mode.

    Checks ``app.config.get('TESTING')``.  If True, returns None without
    creating or starting any scheduler so tests run cleanly.

    Args:
        app: Flask application instance.

    Returns:
        Running BackgroundScheduler, or None if skipped.
    """
    if app.config.get("TESTING", False):
        return None

    sched = _make_scheduler(app)
    sched.start()
    return sched
