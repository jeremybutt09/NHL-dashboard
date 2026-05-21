"""Tests for the slate service — upserts Game and Team rows."""

import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "nhl-dashboard", "backend"))

from app import create_app  # noqa: E402
from extensions import db as _db  # noqa: E402
from models import Game, Team  # noqa: E402
from services.slate import build_slate  # noqa: E402

GAME_DATA = [
    {
        "id": 2026020812,
        "start_utc": "2026-05-20T23:00:00Z",
        "venue": "TD Garden",
        "away_code": "TOR",
        "away_name": "Maple Leafs",
        "home_code": "BOS",
        "home_name": "Bruins",
        "status": "scheduled",
    }
]


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


def test_build_slate_upserts_games(app):
    """Call build_slate() twice with same data; assert only one Game row per game ID."""
    mock_client = MagicMock()
    mock_client.get_schedule_today.return_value = GAME_DATA

    build_slate(client=mock_client)
    build_slate(client=mock_client)

    games = _db.session.query(Game).all()
    assert len(games) == 1
    assert games[0].id == 2026020812


def test_build_slate_creates_teams(app):
    """Assert Team rows are created for home and away team codes."""
    mock_client = MagicMock()
    mock_client.get_schedule_today.return_value = GAME_DATA

    build_slate(client=mock_client)

    away_team = _db.session.get(Team, "TOR")
    home_team = _db.session.get(Team, "BOS")
    assert away_team is not None
    assert away_team.name == "Maple Leafs"
    assert home_team is not None
    assert home_team.name == "Bruins"
