"""Tests for GET /api/games/today route (Issue #30)."""

import sys
import os
import pytest
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'nhl-dashboard', 'backend'))


@pytest.fixture
def app_ctx(app):
    """Push app context and recreate tables for each test."""
    with app.app_context():
        from app import db
        db.create_all()
        yield app


def _seed_db(db, status="scheduled"):
    """Seed one Game + OddsSnapshot + ModelFair for today."""
    from models import Team, Game, OddsSnapshot, ModelFair

    db.session.add(Team(code="TOR", name="Maple Leafs"))
    db.session.add(Team(code="BOS", name="Bruins"))

    game = Game(
        id=2026020812,
        start_utc=datetime.now(timezone.utc).replace(tzinfo=None),
        venue="TD Garden",
        away_code="TOR",
        home_code="BOS",
        status=status,
        away_score=3 if status == "live" else 0,
        home_score=2 if status == "live" else 0,
        away_sog=18 if status == "live" else 0,
        home_sog=22 if status == "live" else 0,
        period="2nd" if status == "live" else None,
        clock="12:34" if status == "live" else None,
        away_wins=24,
        away_losses=18,
        away_otl=4,
        home_wins=30,
        home_losses=15,
        home_otl=6,
        away_l10_w=6,
        away_l10_l=3,
        away_l10_otl=1,
        home_l10_w=7,
        home_l10_l=2,
        home_l10_otl=1,
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.session.add(game)

    db.session.add(OddsSnapshot(
        game_id=2026020812,
        fetched_at=datetime.now(timezone.utc).replace(tzinfo=None),
        book="consensus",
        away_ml=120,
        home_ml=-140,
        away_ml_open=115,
        home_ml_open=-135,
        away_implied=45.0,
        home_implied=55.0,
    ))

    db.session.add(ModelFair(
        game_id=2026020812,
        away_fair=47.5,
        home_fair=52.5,
        computed_at=datetime.now(timezone.utc).replace(tzinfo=None),
    ))

    db.session.commit()


def test_games_today_returns_200(app_ctx, client):
    """GET /api/games/today returns HTTP 200."""
    with app_ctx.app_context():
        from app import db
        _seed_db(db)

    response = client.get('/api/games/today')
    assert response.status_code == 200


def test_games_today_has_updated_at_and_games_keys(app_ctx, client):
    """Response contains updated_at and games top-level keys."""
    with app_ctx.app_context():
        from app import db
        _seed_db(db)

    data = client.get('/api/games/today').get_json()
    assert 'updated_at' in data
    assert 'games' in data


def test_games_today_game_has_all_required_fields(app_ctx, client):
    """games[0] contains all required top-level keys."""
    with app_ctx.app_context():
        from app import db
        _seed_db(db)

    game = client.get('/api/games/today').get_json()['games'][0]
    for key in ('id', 'away', 'home', 'start', 'venue', 'status',
                'live', 'ml', 'ml_open', 'implied', 'fair', 'edge', 'movement_24h'):
        assert key in game, f"Missing key: {key}"


def test_games_today_live_is_null_for_scheduled_game(app_ctx, client):
    """live is null for a scheduled game."""
    with app_ctx.app_context():
        from app import db
        _seed_db(db, status="scheduled")

    game = client.get('/api/games/today').get_json()['games'][0]
    assert game['live'] is None


def test_games_today_live_has_required_fields_for_live_game(app_ctx, client):
    """live contains period, clock, scores, and sog for a live game."""
    with app_ctx.app_context():
        from app import db
        _seed_db(db, status="live")

    game = client.get('/api/games/today').get_json()['games'][0]
    assert game['live'] is not None
    for key in ('period', 'clock', 'away_score', 'home_score', 'away_sog', 'home_sog'):
        assert key in game['live'], f"Missing live key: {key}"


def test_games_today_movement_24h_is_list_of_floats(app_ctx, client):
    """movement_24h is a list of floats (away implied %)."""
    with app_ctx.app_context():
        from app import db
        _seed_db(db)

    game = client.get('/api/games/today').get_json()['games'][0]
    assert isinstance(game['movement_24h'], list)
    for val in game['movement_24h']:
        assert isinstance(val, float)


def test_games_today_away_team_has_record_and_l10(app_ctx, client):
    """away and home dicts contain code, name, record, and l10."""
    with app_ctx.app_context():
        from app import db
        _seed_db(db)

    game = client.get('/api/games/today').get_json()['games'][0]
    for side in ('away', 'home'):
        for key in ('code', 'name', 'record', 'l10'):
            assert key in game[side], f"Missing {side}.{key}"
    assert game['away']['record'] == "24-18-4"
    assert game['home']['l10'] == "7-2-1"


def test_games_today_ml_open_reflects_stored_opening_odds(app_ctx, client):
    """ml_open reflects the away_ml_open/home_ml_open from OddsSnapshot."""
    with app_ctx.app_context():
        from app import db
        _seed_db(db)

    game = client.get('/api/games/today').get_json()['games'][0]
    assert game['ml_open']['away'] == 115
    assert game['ml_open']['home'] == -135
