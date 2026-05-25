import os

BASE_DIR = os.path.dirname(__file__)

class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f'sqlite:///{os.path.join(BASE_DIR, "instance", "nhl.db")}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')

    # Poll intervals (seconds)
    POLL_SCHEDULE_INTERVAL = int(os.environ.get('POLL_SCHEDULE_INTERVAL', 300))  # 5 min
    POLL_SLATE_INTERVAL  = int(os.environ.get('POLL_SLATE_INTERVAL',  300))   # 5 min (legacy alias)
    POLL_LIVE_INTERVAL   = int(os.environ.get('POLL_LIVE_INTERVAL',   15))    # 15 sec
    POLL_ODDS_INTERVAL   = int(os.environ.get('POLL_ODDS_INTERVAL',   300))   # 5 min
    COMPUTE_FAIR_INTERVAL = int(os.environ.get('COMPUTE_FAIR_INTERVAL', 300)) # 5 min
    PRUNE_INTERVAL       = int(os.environ.get('PRUNE_INTERVAL',       3600))  # 1 hr

    SCHEDULER_API_ENABLED = False
