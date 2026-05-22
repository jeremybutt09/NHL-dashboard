"""APScheduler background jobs for the NHL Dashboard."""

from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from config import Config

_scheduler = BackgroundScheduler()
_last_poll = None


def prune_snapshots() -> None:
    """Delete OddsSnapshot rows with fetched_at older than 7 days.

    Must be called within an active Flask application context.
    """
    from extensions import db
    from models import OddsSnapshot

    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
    OddsSnapshot.query.filter(OddsSnapshot.fetched_at < cutoff).delete()
    db.session.commit()


def get_last_poll() -> datetime | None:
    """Return the UTC timestamp of the most recent poll_slate run.

    Returns:
        A naive UTC datetime, or None if poll_slate has not yet run.
    """
    return _last_poll


def init_scheduler(app) -> None:
    """Register all five background jobs on the module-level scheduler.

    Jobs are registered but the scheduler is not started here — the caller
    is responsible for calling _scheduler.start().

    Args:
        app: Flask application instance used to push an app context in each job.
    """
    def _poll_slate():
        global _last_poll
        with app.app_context():
            from services.slate import build_slate
            build_slate()
        _last_poll = datetime.now(timezone.utc).replace(tzinfo=None)

    def _poll_live():
        with app.app_context():
            from services.live import update_live_scores
            update_live_scores()

    def _poll_odds():
        from extensions import db
        from models import Game, OddsSnapshot
        from odds_client import get_odds

        with app.app_context():
            games = Game.query.all()
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            for game in games:
                odds = get_odds(game.id)
                db.session.add(OddsSnapshot(
                    game_id=game.id,
                    fetched_at=now,
                    book="consensus",
                    away_ml=odds["ml"]["away"],
                    home_ml=odds["ml"]["home"],
                    away_implied=odds["implied"]["away"],
                    home_implied=odds["implied"]["home"],
                ))
            db.session.commit()

    def _compute_fair():
        from extensions import db
        from models import Game, ModelFair, OddsSnapshot
        from services.implied import devig_two_way

        with app.app_context():
            games = Game.query.all()
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            for game in games:
                snapshot = (
                    OddsSnapshot.query
                    .filter_by(game_id=game.id)
                    .order_by(OddsSnapshot.fetched_at.desc())
                    .first()
                )
                if snapshot is None:
                    continue
                away_fair, home_fair = devig_two_way(
                    snapshot.away_implied, snapshot.home_implied
                )
                fair = db.session.get(ModelFair, game.id)
                if fair is None:
                    fair = ModelFair(game_id=game.id)
                    db.session.add(fair)
                fair.away_fair = away_fair
                fair.home_fair = home_fair
                fair.computed_at = now
            db.session.commit()

    def _poll_standings():
        with app.app_context():
            from services.standings import build_standings
            build_standings()

    def _prune_snapshots():
        with app.app_context():
            prune_snapshots()

    _scheduler.add_job(
        _poll_slate, "interval", minutes=5, id="poll_slate", replace_existing=True
    )
    _scheduler.add_job(
        _poll_live, "interval", seconds=15, id="poll_live", replace_existing=True
    )
    _scheduler.add_job(
        _poll_odds, "interval", minutes=5, id="poll_odds", replace_existing=True
    )
    _scheduler.add_job(
        _compute_fair, "interval", minutes=5, id="compute_fair", replace_existing=True
    )
    _scheduler.add_job(
        _poll_standings, "interval", seconds=Config.POLL_STANDINGS_INTERVAL,
        id="poll_standings", replace_existing=True,
    )
    _scheduler.add_job(
        _prune_snapshots, "interval", hours=1, id="prune_snapshots", replace_existing=True
    )
