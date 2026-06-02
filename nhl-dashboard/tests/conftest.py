"""Shared pytest fixtures for the nhl-dashboard backend test suite (Issue #87)."""
import sys
import os
import itertools
from datetime import datetime, timezone

import pytest

# Auto-incrementing game IDs for the boxscore_factory.
_boxscore_id_seq = itertools.count(8001)

# Make nhl-dashboard/backend importable without installing it as a package.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app import create_app  # noqa: E402
from extensions import db as _db  # noqa: E402
from models import Team, NhlOddsPartner, NhlOddsLine, Boxscore  # noqa: E402
from services.time_utils import today_et  # noqa: E402


@pytest.fixture()
def app():
    """Flask app configured for testing with a fresh in-memory SQLite database."""
    application = create_app(test_config={
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    """Flask test client bound to the test app; no real server is started."""
    return app.test_client()


@pytest.fixture()
def db(app):
    """SQLAlchemy db object with an active app context for the current test."""
    return _db


@pytest.fixture()
def team_factory(db):
    """Factory that creates and commits a Team row."""
    def make(code, name, team_id=None, franchise_id=None, full_name=None,
             league_id=None, raw_tricode=None):
        team = Team(tri_code=code, name=name, team_id=team_id,
                    franchise_id=franchise_id, full_name=full_name,
                    league_id=league_id, raw_tricode=raw_tricode)
        db.session.add(team)
        db.session.commit()
        return team

    return make


@pytest.fixture()
def boxscore_factory(db):
    """Factory that creates and commits a Boxscore row with sensible defaults."""
    def make(
        away_abbrev,
        home_abbrev,
        away_name=None,
        home_name=None,
        game_state="FUT",
        away_score=0,
        home_score=0,
        away_sog=0,
        home_sog=0,
        period=None,
        clock=None,
        game_date=None,
        game_id=None,
    ):
        gid = game_id if game_id is not None else next(_boxscore_id_seq)
        row = Boxscore(
            game_id=gid,
            away_abbrev=away_abbrev,
            home_abbrev=home_abbrev,
            away_name=away_name or away_abbrev,
            home_name=home_name or home_abbrev,
            game_state=game_state,
            away_score=away_score,
            home_score=home_score,
            away_sog=away_sog,
            home_sog=home_sog,
            period=period,
            clock=clock,
            game_date=game_date if game_date is not None else today_et(),
            start_time_est=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.session.add(row)
        db.session.commit()
        return row

    return make
