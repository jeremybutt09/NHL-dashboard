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


def _poll_nhl_odds():
    from services.scores import refresh_nhl_odds
    refresh_nhl_odds()


def _refresh_historical():
    from services.historical import refresh_recent_historical_games
    refresh_recent_historical_games()


def _refresh_boxscores():
    from services.boxscore import refresh_boxscores
    refresh_boxscores()


def _prune_stale_boxscores():
    from services.boxscore import prune_stale_boxscores
    prune_stale_boxscores()


def _refresh_player_stats():
    from services.player_stats import refresh_boxscore_player_stats
    refresh_boxscore_player_stats()


def start_scheduler(app):
    global _scheduler, _app, last_poll_time
    _app = app
    _scheduler = BackgroundScheduler(timezone='UTC')

    cfg = app.config

    _scheduler.add_job(_with_ctx(_poll_nhl_odds),           'interval', seconds=cfg['POLL_SCORE_INTERVAL'],    id='poll_nhl_odds',           replace_existing=True)
    _scheduler.add_job(_with_ctx(_refresh_historical),      'cron',     hour=8, minute=0,                      id='refresh_historical',      replace_existing=True)
    _scheduler.add_job(_with_ctx(_refresh_boxscores),       'interval', seconds=cfg['POLL_BOXSCORE_INTERVAL'], id='refresh_boxscores',       replace_existing=True)
    _scheduler.add_job(_with_ctx(_prune_stale_boxscores),   'interval', seconds=cfg['POLL_BOXSCORE_INTERVAL'], id='prune_stale_boxscores',   replace_existing=True)
    _scheduler.add_job(_with_ctx(_refresh_player_stats),    'interval', seconds=cfg['POLL_BOXSCORE_INTERVAL'], id='refresh_player_stats',    replace_existing=True)

    _scheduler.start()
    last_poll_time = datetime.now(timezone.utc)
