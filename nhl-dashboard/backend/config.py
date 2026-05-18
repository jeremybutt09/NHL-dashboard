import os


class Config:
    """Application configuration driven by environment variables."""

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 'sqlite:///instance/nhl.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ENV = os.environ.get('FLASK_ENV', 'development')
    POLL_INTERVAL_SLATE = int(os.environ.get('POLL_INTERVAL_SLATE', '300'))
    POLL_INTERVAL_LIVE = int(os.environ.get('POLL_INTERVAL_LIVE', '15'))
