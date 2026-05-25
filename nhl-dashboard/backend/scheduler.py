import logging
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

_scheduler = None
_app = None
last_poll_time: datetime | None = None


def _with_ctx(fn):
    """Wrap a scheduler job so it runs inside a Flask app context."""
    def wrapper():
        global last_poll_time
        job_name = fn.__name__
        with _app.app_context():
            try:
                fn()
                logger.info("job %s completed", job_name)
            except Exception:
                logger.exception("job %s failed", job_name)
        last_poll_time = datetime.now(timezone.utc)
    return wrapper


def _poll_schedule():
    from services.slate import refresh_schedule
    refresh_schedule()


def _poll_live():
    from services.live import refresh_live
    refresh_live()


def _poll_odds():
    from services.slate import refresh_odds
    refresh_odds()


def _compute_fair():
    from services.implied import compute_all_fair
    compute_all_fair()


def _prune_snapshots():
    from services.slate import prune_old_snapshots
    prune_old_snapshots()


def start_scheduler(app):
    global _scheduler, _app, last_poll_time
    _app = app
    _scheduler = BackgroundScheduler(timezone='UTC')

    cfg = app.config

    _scheduler.add_job(_with_ctx(_poll_schedule),   'interval', seconds=cfg['POLL_SCHEDULE_INTERVAL'], id='poll_schedule', replace_existing=True)
    _scheduler.add_job(_with_ctx(_poll_live),      'interval', seconds=cfg['POLL_LIVE_INTERVAL'],    id='poll_live',   replace_existing=True)
    _scheduler.add_job(_with_ctx(_poll_odds),      'interval', seconds=cfg['POLL_ODDS_INTERVAL'],    id='poll_odds',   replace_existing=True)
    _scheduler.add_job(_with_ctx(_compute_fair),   'interval', seconds=cfg['COMPUTE_FAIR_INTERVAL'], id='compute_fair',replace_existing=True)
    _scheduler.add_job(_with_ctx(_prune_snapshots),'interval', seconds=cfg['PRUNE_INTERVAL'],        id='prune',       replace_existing=True)

    _scheduler.start()

    # Seed teams before the first slate refresh so FK lookups succeed immediately
    with app.app_context():
        from services.seed import seed_teams
        seed_teams()
        _poll_schedule()
        _poll_odds()
        _compute_fair()
    last_poll_time = datetime.now(timezone.utc)
