"""Env-driven configuration for the Flask app."""

import os


class Config:
    """Base configuration loaded from environment variables."""

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///instance/nhl.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    POLL_SLATE_INTERVAL = int(os.getenv("POLL_SLATE_INTERVAL", "300"))
    POLL_LIVE_INTERVAL = int(os.getenv("POLL_LIVE_INTERVAL", "15"))
    POLL_ODDS_INTERVAL = int(os.getenv("POLL_ODDS_INTERVAL", "300"))
