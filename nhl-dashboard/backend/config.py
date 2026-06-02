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
    POLL_SCORE_INTERVAL     = int(os.environ.get('POLL_SCORE_INTERVAL',     30))   # 30 sec
    POLL_BOXSCORE_INTERVAL  = int(os.environ.get('POLL_BOXSCORE_INTERVAL',  60))   # 60 sec

    SCHEDULER_API_ENABLED = False
