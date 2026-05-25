"""Shared pytest fixtures for the nhl-dashboard backend test suite (Issue #87)."""
import sys
import os
import itertools
from datetime import datetime, timezone

import pytest

# Unused — kept for potential future use if team_id becomes NOT NULL.
_team_id_seq = itertools.count(1)

# Make nhl-dashboard/backend importable without installing it as a package.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app import create_app  # noqa: E402
from extensions import db as _db  # noqa: E402
from models import Team, Game, OddsSnapshot, ModelFair  # noqa: E402


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
    """Factory that creates and commits a Team row.

    Args:
        code: Three-letter team code (primary key), e.g. ``"TOR"``.
        name: Full team name, e.g. ``"Toronto Maple Leafs"``.

    Returns:
        The committed Team instance.
    """
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
def game_factory(db):
    """Factory that creates and commits a Game row with sensible live defaults.

    Args:
        away_code: FK to Team.code for the away team.
        home_code: FK to Team.code for the home team.
        status: Game state string, defaults to ``"live"``.
        away_score: Away team score, defaults to ``2``.
        home_score: Home team score, defaults to ``1``.
        period: Current period string, defaults to ``"2"``.
        clock: Time remaining string, defaults to ``"10:00"``.

    Returns:
        The committed Game instance.
    """
    def make(
        away_code,
        home_code,
        status="live",
        away_score=2,
        home_score=1,
        period="2",
        clock="10:00",
    ):
        game = Game(
            away_code=away_code,
            home_code=home_code,
            status=status,
            away_score=away_score,
            home_score=home_score,
            period=period,
            clock=clock,
            start_utc=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.session.add(game)
        db.session.commit()
        return game

    return make


@pytest.fixture()
def odds_snapshot_factory(db):
    """Factory that creates and commits an OddsSnapshot row.

    Args:
        game_id: FK to Game.game_id.
        away_ml: Away moneyline in American odds format, defaults to ``-110``.
        home_ml: Home moneyline in American odds format, defaults to ``+100``.
        book: Book identifier string, defaults to ``"consensus"``.

    Returns:
        The committed OddsSnapshot instance.
    """
    def make(game_id, away_ml=-110, home_ml=100, book="consensus"):
        snap = OddsSnapshot(
            game_id=game_id,
            fetched_at=datetime.now(timezone.utc),
            book=book,
            away_ml=away_ml,
            home_ml=home_ml,
            away_implied=52.38,
            home_implied=50.0,
        )
        db.session.add(snap)
        db.session.commit()
        return snap

    return make


@pytest.fixture()
def model_fair_factory(db):
    """Factory that creates and commits a ModelFair row.

    Args:
        game_id: FK to Game.game_id.
        home_fair: Home win probability in percentage points (0–100), defaults to ``55.0``.
        away_fair: Away win probability in percentage points (0–100), defaults to ``45.0``.

    Returns:
        The committed ModelFair instance.
    """
    def make(game_id, home_fair=55.0, away_fair=45.0):
        fair = ModelFair(
            game_id=game_id,
            home_fair=home_fair,
            away_fair=away_fair,
            computed_at=datetime.now(timezone.utc),
        )
        db.session.add(fair)
        db.session.commit()
        return fair

    return make
