"""Tests for the standings service — upserts standings columns on Team rows."""

import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "nhl-dashboard", "backend"))

from app import create_app  # noqa: E402
from extensions import db as _db  # noqa: E402
from models import Team  # noqa: E402
from services.standings import build_standings  # noqa: E402

STANDINGS_DATA = {
    "TOR": {
        "wins": 24,
        "losses": 18,
        "ot_losses": 4,
        "l10_wins": 6,
        "l10_losses": 3,
        "l10_ot_losses": 1,
    }
}


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


def test_build_standings_upserts_team_columns(app):
    """Call build_standings() with mock data; assert Team standings columns are updated."""
    _db.session.add(Team(code="TOR", name="Maple Leafs"))
    _db.session.commit()

    mock_client = MagicMock()
    mock_client.get_standings.return_value = STANDINGS_DATA

    build_standings(client=mock_client)

    tor = _db.session.get(Team, "TOR")
    assert tor.wins == 24
    assert tor.losses == 18
    assert tor.ot_losses == 4
    assert tor.l10_wins == 6
    assert tor.l10_losses == 3
    assert tor.l10_ot_losses == 1


def test_build_standings_preserves_team_name(app):
    """Assert build_standings() does not overwrite the existing team name."""
    _db.session.add(Team(code="TOR", name="Maple Leafs"))
    _db.session.commit()

    mock_client = MagicMock()
    mock_client.get_standings.return_value = STANDINGS_DATA

    build_standings(client=mock_client)

    tor = _db.session.get(Team, "TOR")
    assert tor.name == "Maple Leafs"


def test_build_standings_no_crash_when_api_unavailable(app):
    """If get_standings() returns None, build_standings() exits silently."""
    mock_client = MagicMock()
    mock_client.get_standings.return_value = None

    build_standings(client=mock_client)  # must not raise
