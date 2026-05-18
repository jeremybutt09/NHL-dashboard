"""Tests for slate and live game services (Issue #27)."""

import sys
import os
import pytest
from unittest.mock import patch
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'nhl-dashboard', 'backend'))

# Realistic NHL API mock data
SCHEDULE_GAMES = [
    {
        "id": 2026010001,
        "startTimeUTC": "2026-05-18T23:00:00Z",
        "venue": {"default": "Scotiabank Arena"},
        "gameState": "FUT",
        "awayTeam": {"abbrev": "TOR", "placeName": {"default": "Toronto"}, "score": 0},
        "homeTeam": {"abbrev": "BOS", "placeName": {"default": "Boston"}, "score": 0},
    }
]

SCHEDULE_GAMES_LIVE = [
    {
        "id": 2026010001,
        "startTimeUTC": "2026-05-18T23:00:00Z",
        "venue": {"default": "Scotiabank Arena"},
        "gameState": "LIVE",
        "awayTeam": {"abbrev": "TOR", "placeName": {"default": "Toronto"}, "score": 1},
        "homeTeam": {"abbrev": "BOS", "placeName": {"default": "Boston"}, "score": 2},
    }
]

BOXSCORE_DATA = {
    "id": 2026010001,
    "awayTeam": {"abbrev": "TOR", "score": 2, "sog": 15},
    "homeTeam": {"abbrev": "BOS", "score": 3, "sog": 18},
    "clock": {"timeRemaining": "05:30"},
    "periodDescriptor": {"number": 2},
}


@pytest.fixture
def app_ctx(app):
    """Push app context and recreate tables for each test."""
    with app.app_context():
        from app import db
        db.create_all()
        yield app


def test_refresh_slate_creates_game_row(app_ctx):
    """refresh_slate() creates a Game row with correct fields."""
    from services.slate import refresh_slate
    from models import Game
    from app import db

    with patch('nhl_client.get_schedule_today', return_value=SCHEDULE_GAMES):
        refresh_slate()

    game = db.session.get(Game, 2026010001)
    assert game is not None
    assert game.away_code == "TOR"
    assert game.home_code == "BOS"
    assert game.status == "scheduled"
    assert game.venue == "Scotiabank Arena"
    assert game.updated_at is not None


def test_refresh_slate_is_idempotent(app_ctx):
    """Calling refresh_slate() twice produces the same single row."""
    from services.slate import refresh_slate
    from models import Game
    from app import db

    with patch('nhl_client.get_schedule_today', return_value=SCHEDULE_GAMES):
        refresh_slate()
        refresh_slate()

    count = db.session.query(Game).count()
    assert count == 1


def test_refresh_slate_updates_existing_row(app_ctx):
    """refresh_slate() updates fields on an existing row without duplicating it."""
    from services.slate import refresh_slate
    from models import Game
    from app import db

    with patch('nhl_client.get_schedule_today', return_value=SCHEDULE_GAMES):
        refresh_slate()

    with patch('nhl_client.get_schedule_today', return_value=SCHEDULE_GAMES_LIVE):
        refresh_slate()

    game = db.session.get(Game, 2026010001)
    assert db.session.query(Game).count() == 1
    assert game.status == "live"
    assert game.away_score == 1
    assert game.home_score == 2


def test_refresh_live_updates_score_period_clock(app_ctx):
    """refresh_live() updates score, period, clock, and sog for live games."""
    from services.live import refresh_live
    from models import Game, Team
    from app import db

    db.session.add(Team(code="TOR", name="Toronto"))
    db.session.add(Team(code="BOS", name="Boston"))
    db.session.add(Game(
        id=2026010001,
        away_code="TOR",
        home_code="BOS",
        status="live",
        away_score=0,
        home_score=0,
        away_sog=0,
        home_sog=0,
        updated_at=datetime.now(timezone.utc),
    ))
    db.session.commit()

    with patch('nhl_client.get_game_boxscore', return_value=BOXSCORE_DATA):
        refresh_live()

    game = db.session.get(Game, 2026010001)
    assert game.away_score == 2
    assert game.home_score == 3
    assert game.period == "2"
    assert game.clock == "05:30"
    assert game.away_sog == 15
    assert game.home_sog == 18


def test_refresh_live_skips_scheduled_games(app_ctx):
    """refresh_live() does not fetch boxscores for non-live games."""
    from services.live import refresh_live
    from models import Game, Team
    from app import db

    db.session.add(Team(code="TOR", name="Toronto"))
    db.session.add(Team(code="BOS", name="Boston"))
    db.session.add(Game(
        id=2026010002,
        away_code="TOR",
        home_code="BOS",
        status="scheduled",
        away_score=0,
        home_score=0,
        away_sog=0,
        home_sog=0,
        updated_at=datetime.now(timezone.utc),
    ))
    db.session.commit()

    with patch('nhl_client.get_game_boxscore') as mock_boxscore:
        refresh_live()
        mock_boxscore.assert_not_called()
