"""Tests for GET /api/games/today and GET /api/games/<id>."""

import os
import sys
from datetime import datetime
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "nhl-dashboard", "backend"))

from app import create_app  # noqa: E402
from extensions import db as _db  # noqa: E402
from models import Game, Team  # noqa: E402


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
def client(app):
    """Test client for the Flask app."""
    return app.test_client()


@pytest.fixture
def seeded_game(app):
    """Seed one Game and its two Teams into the in-memory DB."""
    now = datetime(2026, 5, 20, 23, 0, 0)
    _db.session.add_all([
        Team(code="TOR", name="Maple Leafs"),
        Team(code="BOS", name="Bruins"),
    ])
    _db.session.commit()
    _db.session.add(Game(
        id=2026020812,
        start_utc=now,
        venue="TD Garden",
        away_code="TOR",
        home_code="BOS",
        status="scheduled",
        updated_at=now,
    ))
    _db.session.commit()


def test_games_today_returns_200(client, seeded_game):
    """GET /api/games/today with one seeded Game should return 200."""
    response = client.get("/api/games/today")
    assert response.status_code == 200


def test_games_today_response_shape(client, seeded_game):
    """Response must have updated_at and games; each game row has required keys."""
    response = client.get("/api/games/today")
    data = response.get_json()
    assert "updated_at" in data
    assert "games" in data
    assert len(data["games"]) == 1
    game = data["games"][0]
    for key in ("away", "home", "ml", "implied", "edge", "movement_24h"):
        assert key in game, f"missing key: {key}"


def test_games_today_empty_when_no_games(client, app):
    """GET /api/games/today on an empty DB should return games as []."""
    response = client.get("/api/games/today")
    data = response.get_json()
    assert data["games"] == []


def test_game_detail_stub_returns_200(client, seeded_game):
    """GET /api/games/<id> with a seeded game should return 200."""
    response = client.get("/api/games/2026020812")
    assert response.status_code == 200


def test_game_detail_includes_series_field(client, seeded_game):
    """GET /api/games/<id> response must include a 'series' key."""
    mock_series = {"away_wins": 2, "home_wins": 1, "games_played": 3}
    with patch("routes.game_detail.nhl_client") as mock_client:
        mock_client.get_series.return_value = mock_series
        response = client.get("/api/games/2026020812")

    assert response.status_code == 200
    data = response.get_json()
    assert "series" in data
    assert data["series"]["away_wins"] == 2
    assert data["series"]["home_wins"] == 1
    assert data["series"]["games_played"] == 3


def test_game_detail_series_null_when_client_fails(client, seeded_game):
    """GET /api/games/<id> must return series=null when schedule fetch fails."""
    with patch("routes.game_detail.nhl_client") as mock_client:
        mock_client.get_series.return_value = None
        response = client.get("/api/games/2026020812")

    assert response.status_code == 200
    data = response.get_json()
    assert "series" in data
    assert data["series"] is None
