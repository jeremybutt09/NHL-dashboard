"""Tests verifying pytest infrastructure fixtures (Issue #87)."""
import pytest


def test_app_testing_flag_is_set(app):
    """TESTING config flag must be True."""
    assert app.config["TESTING"] is True


def test_app_uses_in_memory_sqlite(app):
    """Database URI must point to in-memory SQLite."""
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"


def test_database_starts_empty(db):
    """Each test receives a fresh, empty database."""
    from models import Team
    assert Team.query.count() == 0


def test_team_factory_creates_committed_row(team_factory, db):
    """team_factory(code, name) creates and persists a Team row."""
    from models import Team
    team = team_factory(code="TOR", name="Toronto Maple Leafs")
    assert team.code == "TOR"
    assert team.name == "Toronto Maple Leafs"
    assert Team.query.get("TOR") is not None


def test_game_factory_creates_live_row(game_factory, team_factory, db):
    """game_factory creates a live game with default scores 2-1."""
    from models import Game
    team_factory(code="TOR", name="Toronto Maple Leafs")
    team_factory(code="BOS", name="Boston Bruins")
    game = game_factory(away_code="TOR", home_code="BOS")
    assert game.status == "live"
    assert game.away_score == 2
    assert game.home_score == 1
    assert Game.query.get(game.id) is not None


def test_odds_snapshot_factory_creates_row(
    odds_snapshot_factory, game_factory, team_factory, db
):
    """odds_snapshot_factory creates one OddsSnapshot with valid American odds."""
    team_factory(code="TOR", name="Toronto Maple Leafs")
    team_factory(code="BOS", name="Boston Bruins")
    game = game_factory(away_code="TOR", home_code="BOS")
    snap = odds_snapshot_factory(game_id=game.id)
    assert snap.away_ml == -110
    assert snap.home_ml == 100


def test_model_fair_factory_creates_row(
    model_fair_factory, game_factory, team_factory, db
):
    """model_fair_factory creates a ModelFair row with home_fair=55.0, away_fair=45.0."""
    team_factory(code="TOR", name="Toronto Maple Leafs")
    team_factory(code="BOS", name="Boston Bruins")
    game = game_factory(away_code="TOR", home_code="BOS")
    fair = model_fair_factory(game_id=game.id)
    assert fair.home_fair == pytest.approx(55.0)
    assert fair.away_fair == pytest.approx(45.0)


def test_client_get_health_returns_response(client):
    """Flask test client issues requests without starting a real server."""
    response = client.get("/api/health")
    assert response.status_code == 200
