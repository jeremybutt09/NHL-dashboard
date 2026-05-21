"""Tests for SQLAlchemy models: Team, Game, OddsSnapshot, ModelFair."""

import os
import sys
from datetime import datetime

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "nhl-dashboard", "backend"))

from app import create_app  # noqa: E402
from extensions import db as _db  # noqa: E402
from models import Game, ModelFair, OddsSnapshot, Team  # noqa: E402


@pytest.fixture
def app():
    """Flask app wired to an in-memory SQLite database."""
    application = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "ENV": "testing",
    })
    with application.app_context():
        _db.create_all()
        yield application
        _db.drop_all()


@pytest.fixture
def session(app):
    """SQLAlchemy session scoped to the test."""
    return _db.session


def test_team_insert_and_retrieve(session):
    """Insert a Team row and query it back, asserting code and name match."""
    team = Team(code="TOR", name="Maple Leafs")
    session.add(team)
    session.commit()
    result = session.get(Team, "TOR")
    assert result.code == "TOR"
    assert result.name == "Maple Leafs"


def test_game_insert_and_retrieve(session):
    """Insert a Game with two Team FKs and query back, asserting all columns."""
    session.add_all([
        Team(code="TOR", name="Maple Leafs"),
        Team(code="BOS", name="Bruins"),
    ])
    session.commit()

    now = datetime(2026, 5, 17, 0, 0, 0)
    game = Game(
        id=2026020812,
        start_utc=now,
        venue="TD Garden",
        away_code="TOR",
        home_code="BOS",
        status="scheduled",
        period=None,
        clock=None,
        away_score=0,
        home_score=0,
        away_sog=0,
        home_sog=0,
        updated_at=now,
    )
    session.add(game)
    session.commit()

    result = session.get(Game, 2026020812)
    assert result.id == 2026020812
    assert result.venue == "TD Garden"
    assert result.away_code == "TOR"
    assert result.home_code == "BOS"
    assert result.status == "scheduled"
    assert result.period is None
    assert result.clock is None
    assert result.away_score == 0
    assert result.home_score == 0
    assert result.away_sog == 0
    assert result.home_sog == 0
    assert result.start_utc == now
    assert result.updated_at == now


def test_odds_snapshot_foreign_key(session):
    """Insert an OddsSnapshot referencing a valid Game, assert it persists."""
    session.add_all([
        Team(code="TOR", name="Maple Leafs"),
        Team(code="BOS", name="Bruins"),
    ])
    session.commit()

    now = datetime(2026, 5, 17, 0, 0, 0)
    session.add(Game(
        id=2026020812,
        start_utc=now,
        venue="TD Garden",
        away_code="TOR",
        home_code="BOS",
        status="scheduled",
        updated_at=now,
    ))
    session.commit()

    snapshot = OddsSnapshot(
        game_id=2026020812,
        fetched_at=now,
        book="consensus",
        away_ml=120,
        home_ml=-140,
        away_implied=45.45,
        home_implied=58.33,
    )
    session.add(snapshot)
    session.commit()

    result = session.get(OddsSnapshot, snapshot.id)
    assert result.game_id == 2026020812
    assert result.book == "consensus"
    assert result.away_ml == 120
    assert result.home_ml == -140


def test_model_fair_upsert(session):
    """Insert ModelFair, update away_fair, assert new value is stored."""
    session.add_all([
        Team(code="TOR", name="Maple Leafs"),
        Team(code="BOS", name="Bruins"),
    ])
    session.commit()

    now = datetime(2026, 5, 17, 0, 0, 0)
    session.add(Game(
        id=2026020812,
        start_utc=now,
        venue="TD Garden",
        away_code="TOR",
        home_code="BOS",
        status="scheduled",
        updated_at=now,
    ))
    session.commit()

    session.add(ModelFair(
        game_id=2026020812,
        away_fair=47.5,
        home_fair=52.5,
        computed_at=now,
    ))
    session.commit()

    result = session.get(ModelFair, 2026020812)
    result.away_fair = 50.0
    session.commit()

    updated = session.get(ModelFair, 2026020812)
    assert updated.away_fair == 50.0
